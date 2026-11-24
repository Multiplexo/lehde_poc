"""Run the analysis of an inquiry package: read, classify, extract, compare."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

import anyio
import structlog

from app.config import Settings, get_settings
from app.models.analysis import (
    AnalysisStats,
    Claim,
    Discrepancy,
    DiscrepancyKind,
    PlanReference,
    ProjectAnalysis,
    Question,
)
from app.models.documents import (
    DOCUMENT_TYPE_LABELS,
    DocumentStatus,
    DocumentType,
    PageText,
    PlanEntry,
    ValueSource,
)
from app.models.projects import AnalysisStep, ProjectStatus
from app.persistence.projects.project_repository import (
    ProjectRepository,
    document_pages,
    project_analysis,
)
from app.persistence.projects.schema.project import DocumentRecord, ProjectRecord
from app.services import storage
from app.services.ai import AIService, UsageCounter, describe_error
from app.services.database import database_service
from app.services.pipeline.classify import Classification, classify_document
from app.services.pipeline.consolidate import consolidate
from app.services.pipeline.conversion import read_document
from app.services.pipeline.extract import DocumentFindings, extract_findings
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.planstand import check_plan_revisions
from app.services.pipeline.questions import build_questions

logger = structlog.get_logger(__name__)

READ_CONCURRENCY = 2


def document_names(records: list[DocumentRecord]) -> dict[UUID, str]:
    """Readable names for questions: the document type, or the file name."""
    type_counts: dict[str, int] = {}
    for record in records:
        if record.doc_type:
            type_counts[record.doc_type] = type_counts.get(record.doc_type, 0) + 1
    names: dict[UUID, str] = {}
    for record in records:
        doc_type = DocumentType(record.doc_type) if record.doc_type else None
        if (
            doc_type is not None
            and doc_type not in {DocumentType.SONSTIGES, DocumentType.PLAN}
            and type_counts[doc_type.value] == 1
        ):
            names[record.id] = DOCUMENT_TYPE_LABELS[doc_type]
        else:
            names[record.id] = record.title or record.filename
    return names


def plan_register(records: list[DocumentRecord]) -> list[PlanEntry]:
    """Plans in the package; a manual revision overrides a single-sheet plan."""
    register: list[PlanEntry] = []
    for record in records:
        if record.doc_type != DocumentType.PLAN.value:
            continue
        entries = [PlanEntry.model_validate(plan) for plan in record.plans]
        if len(entries) == 1 and record.meta_source == ValueSource.MANUAL.value:
            entries[0] = entries[0].model_copy(update={"revision": record.revision})
        register.extend(entries)
    return register


def _keep_review_state(
    discrepancies: list[Discrepancy], previous: list[Discrepancy]
) -> list[Discrepancy]:
    earlier = {item.id: item for item in previous}
    result: list[Discrepancy] = []
    for item in discrepancies:
        old = earlier.get(item.id)
        if old is not None:
            item = item.model_copy(
                update={
                    "status": old.status,
                    "note": old.note,
                    "recipient": old.recipient,
                    "question": old.question,
                }
            )
        result.append(item)
    return result


def _sorted(discrepancies: list[Discrepancy]) -> list[Discrepancy]:
    order = {"red": 0, "yellow": 1}
    return sorted(
        discrepancies,
        key=lambda item: (
            order[item.severity.value],
            item.kind != DiscrepancyKind.PLANSTAND,
        ),
    )


class AnalysisRun:
    def __init__(
        self, project_id: UUID, repository: ProjectRepository, settings: Settings
    ) -> None:
        self.project_id = project_id
        self.repository = repository
        self.settings = settings
        self.usage = UsageCounter()
        self.db_lock = asyncio.Lock()
        self.contents: dict[UUID, bytes] = {}
        self.pages: dict[UUID, list[PageText]] = {}

    async def progress(self, step: AnalysisStep, percent: int, message: str) -> None:
        async with self.db_lock:
            await self.repository.set_progress(
                self.project_id, ProjectStatus.PROCESSING, step, percent, message
            )

    async def _gather[Item, Result](
        self,
        items: list[Item],
        work: Callable[[Item], Awaitable[Result]],
        limit: int,
        on_done: Callable[[int], Awaitable[None]],
    ) -> list[Result]:
        semaphore = asyncio.Semaphore(limit)
        done = 0

        async def run(item: Item) -> Result:
            nonlocal done
            async with semaphore:
                result = await work(item)
            done += 1
            await on_done(done)
            return result

        return list(await asyncio.gather(*(run(item) for item in items)))

    async def read_documents(self, records: list[DocumentRecord]) -> None:
        total = len(records)

        async def read(record: DocumentRecord) -> None:
            content = await storage.read_file(record.storage_key)
            self.contents[record.id] = content
            if record.pages:
                self.pages[record.id] = document_pages(record)
                return
            pages = await anyio.to_thread.run_sync(
                read_document,
                content,
                record.content_type,
                self.settings.OCR_LANGUAGES if self.settings.PDF_OCR_ENABLED else None,
                self.settings.OCR_MIN_TEXT_CHARACTERS,
            )
            self.pages[record.id] = pages
            async with self.db_lock:
                record.pages = [page.model_dump(mode="json") for page in pages]
                record.page_count = len(pages)
                record.ocr_page_count = sum(page.ocr for page in pages)
                record.status = DocumentStatus.READ.value
                record.error = None
                await self.repository.save_document(record)
            logger.info(
                "document_read",
                document_id=str(record.id),
                page_count=len(pages),
                ocr_page_count=record.ocr_page_count,
            )

        async def done(count: int) -> None:
            await self.progress(
                AnalysisStep.READING,
                5 + int(25 * count / total),
                f"Dokumente lesen ({count}/{total})",
            )

        await self._gather(records, read, READ_CONCURRENCY, done)

    async def classify(self, ai: AIService, records: list[DocumentRecord]) -> None:
        total = len(records)

        async def classify(
            record: DocumentRecord,
        ) -> tuple[DocumentRecord, Classification]:
            pages = self.pages[record.id]
            index = DocumentIndex(record.id, pages, self.settings.CITATION_MIN_SCORE)
            result = await classify_document(
                ai,
                self.usage,
                record.id,
                record.filename,
                record.content_type,
                self.contents[record.id],
                pages,
                index,
            )
            return record, result

        async def done(count: int) -> None:
            await self.progress(
                AnalysisStep.CLASSIFYING,
                30 + int(20 * count / total),
                f"Dokumenttypen erkennen ({count}/{total})",
            )

        results = await self._gather(
            records, classify, self.settings.LLM_CONCURRENCY, done
        )
        async with self.db_lock:
            for record, result in results:
                if record.doc_type_source != ValueSource.MANUAL.value:
                    record.doc_type = result.doc_type.value
                    record.doc_type_source = ValueSource.AI.value
                if record.meta_source != ValueSource.MANUAL.value:
                    record.title = result.title
                    record.revision = result.revision
                    record.document_date = result.document_date
                    record.meta_source = ValueSource.AI.value
                record.classification_confidence = result.confidence
                record.plans = [plan.model_dump(mode="json") for plan in result.plans]
                record.status = DocumentStatus.CLASSIFIED.value
                await self.repository.save_document(record)

    async def extract(
        self, ai: AIService, records: list[DocumentRecord]
    ) -> list[DocumentFindings]:
        targets = [
            (number, record)
            for number, record in enumerate(records, start=1)
            if record.doc_type != DocumentType.PLAN.value
        ]
        total = max(1, len(targets))

        async def extract(item: tuple[int, DocumentRecord]) -> DocumentFindings:
            number, record = item
            pages = self.pages[record.id]
            return await extract_findings(
                ai,
                self.usage,
                f"D{number}",
                record.id,
                record.filename,
                DocumentType(record.doc_type or DocumentType.SONSTIGES.value),
                record.title,
                pages,
                DocumentIndex(record.id, pages, self.settings.CITATION_MIN_SCORE),
                self.settings.EXTRACTION_CHUNK_CHARACTERS,
            )

        async def done(count: int) -> None:
            await self.progress(
                AnalysisStep.EXTRACTING,
                50 + int(35 * count / total),
                f"Fakten mit Fundstellen extrahieren ({count}/{total})",
            )

        return await self._gather(targets, extract, self.settings.LLM_CONCURRENCY, done)

    async def execute(self) -> None:
        started = time.monotonic()
        project = await self.repository.get_record(self.project_id)
        if project is None:
            return
        records = await self.repository.list_document_records(self.project_id)
        if not records:
            raise ValueError("Project has no documents")

        await self.progress(AnalysisStep.READING, 2, "Dokumente lesen")
        await self.read_documents(records)

        ai = AIService(self.settings)
        try:
            await self.progress(AnalysisStep.CLASSIFYING, 30, "Dokumenttypen erkennen")
            await self.classify(ai, records)
            await self.progress(AnalysisStep.EXTRACTING, 50, "Fakten extrahieren")
            findings = await self.extract(ai, records)
            claims: list[Claim] = [claim for item in findings for claim in item.claims]
            references: list[PlanReference] = [
                reference for item in findings for reference in item.plan_references
            ]
            names = document_names(records)
            await self.progress(AnalysisStep.COMPARING, 88, "Unterlagen abgleichen")
            consolidation = await consolidate(ai, self.usage, claims, names)
        finally:
            await ai.close()

        register = plan_register(records)
        previous = project_analysis(project)
        discrepancies = _keep_review_state(
            _sorted(
                check_plan_revisions(register, references, names)
                + consolidation.discrepancies
            ),
            previous.discrepancies if previous else [],
        )
        previous_questions = [
            Question.model_validate(item) for item in project.questions
        ]
        questions = build_questions(
            discrepancies, consolidation.facts, previous_questions
        )
        analysis = ProjectAnalysis(
            created_at=datetime.now(UTC),
            model=self.settings.MODEL,
            summary=consolidation.summary,
            facts=consolidation.facts,
            claims=claims,
            plan_references=references,
            plan_register=register,
            discrepancies=discrepancies,
            stats=AnalysisStats(
                documents=len(records),
                pages=sum(len(pages) for pages in self.pages.values()),
                ocr_pages=sum(
                    page.ocr for pages in self.pages.values() for page in pages
                ),
                claims_found=len(claims) + len(references),
                claims_dropped=sum(item.dropped for item in findings),
                model_calls=self.usage.model_calls,
                input_tokens=self.usage.input_tokens,
                output_tokens=self.usage.output_tokens,
                duration_seconds=round(time.monotonic() - started, 1),
            ),
        )
        async with self.db_lock:
            await self.repository.save_analysis(project, analysis, questions)
            await self.repository.set_progress(
                self.project_id,
                ProjectStatus.READY,
                AnalysisStep.DONE,
                100,
                "Analyse abgeschlossen",
            )
        logger.info(
            "analysis_completed",
            project_id=str(self.project_id),
            duration_seconds=analysis.stats.duration_seconds,
            model_calls=self.usage.model_calls,
            discrepancy_count=len(discrepancies),
        )


async def run_analysis(project_id: UUID) -> None:
    """Entry point for the background task; marks the project failed on errors."""
    settings = get_settings()
    try:
        async with database_service.session_factory() as session:
            await AnalysisRun(
                project_id, ProjectRepository(session), settings
            ).execute()
    except Exception as error:
        logger.exception("analysis_failed", project_id=str(project_id))
        async with database_service.session_factory() as session:
            await ProjectRepository(session).set_progress(
                project_id,
                ProjectStatus.FAILED,
                None,
                0,
                None,
                error=describe_error(error, settings.MODEL),
            )


def refresh_plan_check(
    project: ProjectRecord, records: list[DocumentRecord]
) -> tuple[ProjectAnalysis, list[Question]] | None:
    """Re-run the rule-based plan check after a manual correction."""
    analysis = project_analysis(project)
    if analysis is None:
        return None
    register = plan_register(records)
    content = [
        item
        for item in analysis.discrepancies
        if item.kind != DiscrepancyKind.PLANSTAND
    ]
    discrepancies = _keep_review_state(
        _sorted(
            check_plan_revisions(
                register, analysis.plan_references, document_names(records)
            )
            + content
        ),
        analysis.discrepancies,
    )
    updated = analysis.model_copy(
        update={"plan_register": register, "discrepancies": discrepancies}
    )
    previous = [Question.model_validate(item) for item in project.questions]
    return updated, build_questions(discrepancies, updated.facts, previous)
