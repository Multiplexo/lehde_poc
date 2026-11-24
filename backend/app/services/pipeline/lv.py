"""Bills of quantities: import (GAEB, PDF), trade assignment, draft from a
functional tender.
"""

import ast
import json
import operator
import re
from collections.abc import Callable
from uuid import UUID, uuid4

import structlog

from app.models.analysis import Claim
from app.models.catalog import FACT_BY_KEY
from app.models.documents import PageText, SourceRef, ValueSource
from app.models.lv import LvOrigin, LvPosition
from app.models.trades import FALLBACK_TRADE, TRADE_BY_CODE, TRADE_CATALOG
from app.services.ai import AIService, UsageCounter, text_part
from app.services.pipeline.gaeb import ITEMS_PER_PAGE, parse_gaeb
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.prompts import (
    LV_DRAFT_INSTRUCTIONS,
    LV_EXTRACTION_INSTRUCTIONS,
    TRADE_ASSIGNMENT_INSTRUCTIONS,
)
from app.services.pipeline.schemas import (
    LvDraftResult,
    LvExtractionResult,
    TradeAssignmentResult,
)

logger = structlog.get_logger(__name__)

TRADE_BATCH_SIZE = 60
LV_CHUNK_CHARACTERS = 30_000
_NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
_OPERATORS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def parse_number(raw: str) -> float | None:
    """Read German (1.250,5) and plain (1250.5) notation."""
    text = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", text):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def numbers_in(text: str) -> set[float]:
    return {
        value
        for value in (parse_number(match) for match in _NUMBER.findall(text))
        if value is not None
    }


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand)
    raise ValueError("Unsupported formula element")


def evaluate_formula(formula: str, allowed_numbers: set[float]) -> float | None:
    """Compute a quantity; every number must come from the cited statements."""
    normalized = re.sub(
        r"(\d),(\d)", r"\1.\2", formula.replace("x", "*").replace("×", "*")
    )
    if not re.fullmatch(r"[\d.\s+\-*/()]+", normalized):
        return None
    used = {float(token) for token in re.findall(r"\d+(?:\.\d+)?", normalized)}
    if used - allowed_numbers:
        return None
    try:
        value = _evaluate(ast.parse(normalized, mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError):
        return None
    return round(value, 3)


def gaeb_positions(
    project_id: UUID, document_id: UUID, content: bytes, start_index: int
) -> list[LvPosition]:
    items = parse_gaeb(content)
    # Page numbers match the readable pages built by read_gaeb.
    return [
        LvPosition(
            id=uuid4(),
            project_id=project_id,
            origin=LvOrigin.GAEB,
            sort_index=start_index + number,
            oz=item.oz,
            short_text=item.short_text,
            long_text=item.long_text,
            quantity=item.quantity,
            unit=item.unit,
            source=SourceRef(
                document_id=document_id,
                page=number // ITEMS_PER_PAGE + 1,
                quote=f"{item.oz} {item.short_text}",
            ),
        )
        for number, item in enumerate(items)
    ]


def _chunks(pages: list[PageText]) -> list[str]:
    chunks: list[str] = []
    current = ""
    for page in pages:
        block = f"--- Seite {page.number} ---\n{page.text}\n"
        if current and len(current) + len(block) > LV_CHUNK_CHARACTERS:
            chunks.append(current)
            current = ""
        current += block
    if current:
        chunks.append(current)
    return chunks


async def extract_lv_positions(
    ai: AIService,
    usage: UsageCounter,
    project_id: UUID,
    document_id: UUID,
    filename: str,
    pages: list[PageText],
    index: DocumentIndex,
    start_index: int,
) -> tuple[list[LvPosition], int]:
    """Positions from a PDF/DOCX LV; returns positions and dropped count."""
    positions: list[LvPosition] = []
    dropped = 0
    for chunk in _chunks(pages):
        result = await ai.parse(
            task="lv_extraction",
            instructions=LV_EXTRACTION_INSTRUCTIONS,
            content=[text_part(f"Dokument: {filename}\n\n{chunk}")],
            schema=LvExtractionResult,
            usage=usage,
        )
        for item in result.positions:
            source = index.source(item.quote, item.page)
            if source is None or not item.short_text.strip():
                dropped += 1
                continue
            quantity = item.quantity
            # Keep a quantity only if it is printed in the quoted text.
            if quantity is not None and quantity not in numbers_in(
                index.page_text(source.page)
            ):
                quantity = None
            positions.append(
                LvPosition(
                    id=uuid4(),
                    project_id=project_id,
                    origin=LvOrigin.DOCUMENT,
                    sort_index=start_index + len(positions),
                    oz=item.oz,
                    short_text=item.short_text.strip(),
                    long_text=item.long_text,
                    quantity=quantity,
                    unit=item.unit,
                    source=source,
                )
            )
    logger.info(
        "lv_positions_extracted",
        document_id=str(document_id),
        position_count=len(positions),
        dropped_count=dropped,
    )
    return positions, dropped


def _trade_text() -> str:
    return "\n".join(
        f"- {trade.code}: {trade.label} – {trade.hint}" for trade in TRADE_CATALOG
    )


async def assign_trades(
    ai: AIService, usage: UsageCounter, positions: list[LvPosition]
) -> None:
    """Assign a trade to each position without a manual trade (in place)."""
    targets = [
        position
        for position in positions
        if position.trade_source != ValueSource.MANUAL
    ]
    instructions = TRADE_ASSIGNMENT_INSTRUCTIONS.format(trades=_trade_text())
    for start in range(0, len(targets), TRADE_BATCH_SIZE):
        batch = targets[start : start + TRADE_BATCH_SIZE]
        payload = [
            {
                "id": str(position.id),
                "oz": position.oz,
                "kurztext": position.short_text,
                "langtext": (position.long_text or "")[:300],
            }
            for position in batch
        ]
        result = await ai.parse(
            task="trade_assignment",
            instructions=instructions,
            content=[text_part(json.dumps(payload, ensure_ascii=False))],
            schema=TradeAssignmentResult,
            usage=usage,
        )
        assignments = {item.id: item for item in result.assignments}
        for position in batch:
            assignment = assignments.get(str(position.id))
            code = assignment.trade_code if assignment else FALLBACK_TRADE
            position.trade_code = code if code in TRADE_BY_CODE else FALLBACK_TRADE
            position.trade_source = ValueSource.AI
            position.trade_confidence = (
                max(0.0, min(1.0, assignment.confidence)) if assignment else 0.0
            )


async def draft_lv(
    ai: AIService,
    usage: UsageCounter,
    project_id: UUID,
    claims: list[Claim],
    start_index: int,
) -> list[LvPosition]:
    """LV draft from a functional tender, based on verified statements."""
    if not claims:
        raise ValueError("No verified statements for the LV draft")
    by_id = {claim.id: claim for claim in claims}
    payload = [
        {
            "id": claim.id,
            "thema": FACT_BY_KEY[claim.topic].label,
            "aussage": claim.value,
            "zitat": claim.source.quote,
        }
        for claim in claims
    ]
    result = await ai.parse(
        task="lv_draft",
        instructions=LV_DRAFT_INSTRUCTIONS.format(trades=_trade_text()),
        content=[text_part(json.dumps(payload, ensure_ascii=False, indent=1))],
        schema=LvDraftResult,
        usage=usage,
    )
    positions: list[LvPosition] = []
    rejected_formulas = 0
    for item in result.positions:
        supporting = [
            by_id[claim_id] for claim_id in item.claim_ids if claim_id in by_id
        ]
        assumption = (item.assumption or "").strip() or None
        if not supporting and assumption is None:
            assumption = (
                "Übliche Leistung, in den Unterlagen nicht ausdrücklich beschrieben."
            )
        quantity: float | None = None
        formula = (item.quantity_formula or "").strip() or None
        if formula and supporting:
            allowed = set().union(
                *(
                    numbers_in(f"{claim.value} {claim.source.quote}")
                    for claim in supporting
                )
            )
            quantity = evaluate_formula(formula, allowed)
            if quantity is None:
                rejected_formulas += 1
                formula = None
        elif formula:
            formula = None
        code = item.trade_code if item.trade_code in TRADE_BY_CODE else FALLBACK_TRADE
        positions.append(
            LvPosition(
                id=uuid4(),
                project_id=project_id,
                origin=LvOrigin.DRAFT,
                sort_index=start_index + len(positions),
                short_text=item.short_text.strip(),
                long_text=item.long_text,
                quantity=quantity,
                unit=item.unit,
                quantity_formula=formula,
                trade_code=code,
                trade_source=ValueSource.AI,
                trade_confidence=None,
                source=supporting[0].source if supporting else None,
                assumption=None if supporting else assumption,
            )
        )
    _number_draft(positions)
    logger.info(
        "lv_draft_created",
        project_id=str(project_id),
        position_count=len(positions),
        assumption_count=sum(position.assumption is not None for position in positions),
        rejected_formulas=rejected_formulas,
    )
    return positions


def _number_draft(positions: list[LvPosition]) -> None:
    """OZ for the draft: trade as title, then running numbers."""
    if not positions:
        return
    base = min(position.sort_index for position in positions)
    order = {trade.code: index for index, trade in enumerate(TRADE_CATALOG)}
    positions.sort(key=lambda position: order.get(position.trade_code or "", 999))
    counters: dict[str, int] = {}
    titles: dict[str, int] = {}
    for index, position in enumerate(positions):
        code = position.trade_code or FALLBACK_TRADE
        titles.setdefault(code, len(titles) + 1)
        counters[code] = counters.get(code, 0) + 1
        position.oz = f"{titles[code]:02d}.{counters[code] * 10:04d}"
        position.sort_index = base + index
