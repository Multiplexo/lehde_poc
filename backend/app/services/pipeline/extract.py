from dataclasses import dataclass, field
from uuid import UUID

import structlog

from app.models.analysis import Claim, PlanReference
from app.models.catalog import FACT_CATALOG, FACT_KEYS
from app.models.documents import DOCUMENT_TYPE_LABELS, DocumentType, PageText
from app.services.ai import AIService, UsageCounter, text_part
from app.services.pipeline.grounding import DocumentIndex, normalize
from app.services.pipeline.prompts import EXTRACTION_INSTRUCTIONS
from app.services.pipeline.schemas import ExtractionResult

logger = structlog.get_logger(__name__)


@dataclass
class DocumentFindings:
    claims: list[Claim] = field(default_factory=list)
    plan_references: list[PlanReference] = field(default_factory=list)
    dropped: int = 0


def _catalog_text() -> str:
    return "\n".join(
        f"- {definition.key}: {definition.label}. {definition.hint}"
        for definition in FACT_CATALOG
    )


def _chunks(pages: list[PageText], limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for page in pages:
        block = f"--- Seite {page.number} ---\n{page.text}"
        if current and size + len(block) > limit:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(block[:limit])
        size += len(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


async def extract_findings(
    ai: AIService,
    usage: UsageCounter,
    prefix: str,
    document_id: UUID,
    filename: str,
    doc_type: DocumentType,
    title: str | None,
    pages: list[PageText],
    index: DocumentIndex,
    chunk_characters: int,
) -> DocumentFindings:
    """Extract claims and plan references; keep only those with a found quote."""
    findings = DocumentFindings()
    seen: set[tuple[str, str]] = set()
    seen_references: set[tuple[str, str]] = set()
    header = (
        f"Dokument: {filename}\nTyp: {DOCUMENT_TYPE_LABELS[doc_type]}\n"
        f"Titel: {title or 'unbekannt'}\n\n"
    )
    instructions = EXTRACTION_INSTRUCTIONS.format(catalog=_catalog_text())
    for chunk in _chunks(pages, chunk_characters):
        result = await ai.parse(
            task="extraction",
            instructions=instructions,
            content=[text_part(header + chunk)],
            schema=ExtractionResult,
            usage=usage,
        )
        for item in result.claims:
            key = (item.topic, normalize(item.value))
            if item.topic not in FACT_KEYS or key in seen:
                continue
            source = index.source(item.quote, item.page)
            if source is None:
                findings.dropped += 1
                logger.info(
                    "claim_dropped_without_quote",
                    document_id=str(document_id),
                    topic=item.topic,
                    page=item.page,
                )
                continue
            seen.add(key)
            findings.claims.append(
                Claim(
                    id=f"{prefix}-A{len(findings.claims) + 1}",
                    document_id=document_id,
                    topic=item.topic,
                    value=item.value.strip(),
                    source=source,
                )
            )
        for reference in result.plan_references:
            key = (
                normalize(reference.plan_number),
                normalize(reference.revision or ""),
            )
            if not reference.plan_number.strip() or key in seen_references:
                continue
            source = index.source(reference.quote, reference.page)
            if source is None:
                findings.dropped += 1
                continue
            seen_references.add(key)
            findings.plan_references.append(
                PlanReference(
                    id=f"{prefix}-P{len(findings.plan_references) + 1}",
                    document_id=document_id,
                    plan_number=reference.plan_number.strip(),
                    revision=reference.revision,
                    date=reference.date,
                    source=source,
                )
            )
    logger.info(
        "document_findings_extracted",
        document_id=str(document_id),
        claim_count=len(findings.claims),
        reference_count=len(findings.plan_references),
        dropped_count=findings.dropped,
    )
    return findings
