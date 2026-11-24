"""Check agents per area (contract/VOB, fire safety, soil, change orders)."""

import json
from uuid import UUID

import structlog

from app.models.checks import (
    CHECK_AREA_DOCUMENTS,
    CHECK_AREA_LABELS,
    CHECK_CATALOG,
    CheckArea,
    CheckFinding,
    CheckRule,
    CheckStatus,
)
from app.models.documents import DocumentType, PageText, SourceRef
from app.services.ai import AIService, UsageCounter, text_part
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.prompts import CHECK_INSTRUCTIONS
from app.services.pipeline.schemas import CheckResult

logger = structlog.get_logger(__name__)

AREA_CHARACTERS = 120_000
NEEDS_QUOTE = {CheckStatus.OK, CheckStatus.NOTE, CheckStatus.CRITICAL}


class CheckDocument:
    def __init__(
        self,
        document_id: UUID,
        name: str,
        doc_type: DocumentType,
        pages: list[PageText],
        index: DocumentIndex,
    ) -> None:
        self.document_id = document_id
        self.name = name
        self.doc_type = doc_type
        self.pages = pages
        self.index = index


def _finding(
    rule: CheckRule,
    status: CheckStatus,
    finding: str,
    sources: list[SourceRef] | None = None,
    question: str | None = None,
) -> CheckFinding:
    return CheckFinding(
        rule_id=rule.id,
        area=rule.area,
        title=rule.title,
        status=status,
        finding=finding,
        sources=sources or [],
        recipient=rule.recipient,
        action=rule.action,
        question=question,
    )


def _content(documents: list[CheckDocument]) -> str:
    budget = AREA_CHARACTERS // max(1, len(documents))
    blocks = []
    for document in documents:
        text = "\n".join(
            f"--- Seite {page.number} ---\n{page.text}" for page in document.pages
        )[:budget]
        blocks.append(
            f'<document document_id="{document.document_id}" name="{document.name}">\n'
            f"{text}\n</document>"
        )
    return "\n\n".join(blocks)


async def check_area(
    ai: AIService,
    usage: UsageCounter,
    area: CheckArea,
    documents: list[CheckDocument],
) -> list[CheckFinding]:
    rules = [rule for rule in CHECK_CATALOG if rule.area == area]
    relevant = [doc for doc in documents if doc.doc_type in CHECK_AREA_DOCUMENTS[area]]
    if area == CheckArea.CHANGE_ORDER and not any(
        doc.doc_type == DocumentType.NACHTRAG for doc in documents
    ):
        return [
            _finding(rule, CheckStatus.NOT_APPLICABLE, "Kein Nachtrag im Paket.")
            for rule in rules
        ]
    if not relevant:
        return [
            _finding(
                rule,
                CheckStatus.MISSING,
                f"Keine Unterlagen für {CHECK_AREA_LABELS[area]} im Paket.",
            )
            for rule in rules
        ]
    checklist = [
        {"rule_id": rule.id, "titel": rule.title, "pruefung": rule.instruction}
        for rule in rules
    ]
    result = await ai.parse(
        task=f"check_{area.value}",
        instructions=CHECK_INSTRUCTIONS,
        content=[
            text_part(
                "Checkliste:\n"
                + json.dumps(checklist, ensure_ascii=False, indent=1)
                + "\n\nUnterlagen:\n"
                + _content(relevant)
            )
        ],
        schema=CheckResult,
        usage=usage,
    )
    indexes = {str(doc.document_id): doc.index for doc in relevant}
    by_rule = {item.rule_id: item for item in result.results}
    findings: list[CheckFinding] = []
    for rule in rules:
        item = by_rule.get(rule.id)
        if item is None:
            findings.append(_finding(rule, CheckStatus.MISSING, "Nicht bewertet."))
            continue
        sources = [
            source
            for quote in item.quotes
            if quote.document_id in indexes
            for source in [indexes[quote.document_id].source(quote.quote, quote.page)]
            if source is not None
        ]
        status = CheckStatus(item.status)
        finding = item.finding.strip()
        if status in NEEDS_QUOTE and not sources:
            # No verifiable quote: the assessment is not shown.
            status = CheckStatus.MISSING
            finding = "In den Unterlagen keine belegbare Regelung gefunden."
        findings.append(
            _finding(
                rule,
                status,
                finding,
                sources,
                item.question.strip() if item.question else None,
            )
        )
    logger.info(
        "check_area_completed",
        area=area.value,
        critical_count=sum(f.status == CheckStatus.CRITICAL for f in findings),
        missing_count=sum(f.status == CheckStatus.MISSING for f in findings),
    )
    return findings
