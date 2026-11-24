from dataclasses import dataclass
from uuid import UUID

import anyio
import structlog

from app.models.documents import (
    DOCUMENT_TYPE_LABELS,
    DocumentType,
    PageText,
    PlanEntry,
    SourceRef,
)
from app.services.ai import AIService, UsageCounter, image_part, text_part
from app.services.pipeline.conversion import PDF_CONTENT_TYPE, render_page_images
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.prompts import CLASSIFICATION_INSTRUCTIONS
from app.services.pipeline.schemas import ClassificationResult, PlanSheet

logger = structlog.get_logger(__name__)

PREVIEW_PAGES = 3
PREVIEW_PAGE_CHARACTERS = 6000
MAX_IMAGE_PAGES = 8
# Drawings carry little text per page; such documents get all page images.
DRAWING_TEXT_PER_PAGE = 1500


@dataclass
class Classification:
    doc_type: DocumentType
    title: str | None
    revision: str | None
    document_date: str | None
    confidence: float
    plans: list[PlanEntry]


def _image_pages(pages: list[PageText]) -> tuple[list[int], bool]:
    if not pages:
        return [], False
    average_text = sum(len(page.text) for page in pages) / len(pages)
    if len(pages) <= MAX_IMAGE_PAGES and average_text < DRAWING_TEXT_PER_PAGE:
        return [page.number for page in pages], True
    return [1], True


def _plan_entry(document_id: UUID, index: DocumentIndex, sheet: PlanSheet) -> PlanEntry:
    """Ground the title block quote; plans read only from the image stay unverified."""
    quote = sheet.title_block_quote.strip()
    source = index.source(quote, sheet.page) if quote else None
    if source is None:
        source = SourceRef(
            document_id=document_id, page=sheet.page, quote=quote, verified=False
        )
    return PlanEntry(
        plan_number=sheet.plan_number.strip(),
        title=sheet.title,
        revision=sheet.revision,
        date=sheet.date,
        document_id=document_id,
        source=source,
    )


async def classify_document(
    ai: AIService,
    usage: UsageCounter,
    document_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
    pages: list[PageText],
    index: DocumentIndex,
) -> Classification:
    preview = "\n\n".join(
        f"--- Seite {page.number} ---\n{page.text[:PREVIEW_PAGE_CHARACTERS]}"
        for page in pages[:PREVIEW_PAGES]
    )
    parts = [
        text_part(
            f"Dateiname: {filename}\nSeitenzahl: {len(pages)}\n\n"
            f"Text der ersten Seiten:\n{preview or '(kein Text erkannt)'}"
        )
    ]
    if content_type == PDF_CONTENT_TYPE:
        page_numbers, with_title_block = _image_pages(pages)
        images = await anyio.to_thread.run_sync(
            render_page_images, content, page_numbers, with_title_block
        )
        for number, page_images in images.items():
            parts.append(
                text_part(f"Seitenbild Seite {number} (ggf. mit Ausschnitt Plankopf):")
            )
            parts.extend(image_part(image) for image in page_images)

    result = await ai.parse(
        task="classification",
        instructions=CLASSIFICATION_INSTRUCTIONS,
        content=parts,
        schema=ClassificationResult,
        usage=usage,
    )
    doc_type = DocumentType(result.doc_type)
    plans = [
        _plan_entry(document_id, index, sheet)
        for sheet in result.plans
        if sheet.plan_number.strip()
    ]
    if doc_type != DocumentType.PLAN:
        plans = []
    revision = result.revision
    if doc_type == DocumentType.PLAN and len(plans) == 1 and not revision:
        revision = plans[0].revision
    logger.info(
        "document_classified",
        document_id=str(document_id),
        doc_type=doc_type.value,
        label=DOCUMENT_TYPE_LABELS[doc_type],
        plan_count=len(plans),
        confidence=result.confidence,
    )
    return Classification(
        doc_type=doc_type,
        title=result.title,
        revision=revision,
        document_date=result.document_date,
        confidence=max(0.0, min(1.0, result.confidence)),
        plans=plans,
    )
