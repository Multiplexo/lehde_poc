"""LV import, check agents and the separate jobs for LV draft and re-checks."""

import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

import structlog

from app.config import Settings, get_settings
from app.models.analysis import ProjectAnalysis
from app.models.checks import CheckArea, CheckFinding
from app.models.documents import DocumentType, PageText, ValueSource
from app.models.lv import LvOrigin, LvPosition
from app.models.projects import AnalysisStep, ProjectStatus
from app.persistence.lv.lv_repository import LvRepository
from app.persistence.projects.project_repository import (
    ProjectRepository,
    document_pages,
    project_analysis,
)
from app.persistence.projects.schema.project import DocumentRecord
from app.services import storage
from app.services.ai import AIService, UsageCounter, describe_error
from app.services.database import database_service
from app.services.pipeline.checks import CheckDocument, check_area
from app.services.pipeline.gaeb import GAEB_CONTENT_TYPE
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.lv import (
    assign_trades,
    draft_lv,
    extract_lv_positions,
    gaeb_positions,
)
from app.services.pipeline.naming import document_names

logger = structlog.get_logger(__name__)

IMPORTED = {LvOrigin.GAEB, LvOrigin.DOCUMENT}
# Sort ranges: imported positions first, then the draft, then manual ones.
DRAFT_SORT_BASE = 100_000


def _keep_manual_trades(
    positions: list[LvPosition], previous: list[LvPosition]
) -> None:
    """A new import keeps trades that users corrected before."""
    manual = {
        (item.oz, item.short_text): item.trade_code
        for item in previous
        if item.trade_source == ValueSource.MANUAL
    }
    for position in positions:
        code = manual.get((position.oz, position.short_text))
        if code:
            position.trade_code = code
            position.trade_source = ValueSource.MANUAL


async def import_lv(
    ai: AIService,
    usage: UsageCounter,
    project_id: UUID,
    records: list[DocumentRecord],
    pages: dict[UUID, list[PageText]],
    contents: dict[UUID, bytes],
    repository: LvRepository,
    settings: Settings,
) -> int:
    """Read all LV documents (GAEB without a model, PDF/DOCX with quotes)."""
    lv_records = [
        record
        for record in records
        if record.doc_type == DocumentType.LEISTUNGSVERZEICHNIS.value
    ]
    previous = await repository.list_positions(project_id)
    positions: list[LvPosition] = []
    for record in lv_records:
        start = len(positions)
        if record.content_type == GAEB_CONTENT_TYPE:
            positions += gaeb_positions(
                project_id, record.id, contents[record.id], start
            )
            continue
        extracted, _ = await extract_lv_positions(
            ai,
            usage,
            project_id,
            record.id,
            record.filename,
            pages[record.id],
            DocumentIndex(record.id, pages[record.id], settings.CITATION_MIN_SCORE),
            start,
        )
        positions += extracted
    _keep_manual_trades(positions, previous)
    if positions:
        await assign_trades(ai, usage, positions)
    # Drafted and manual positions stay; they sort after imported ones.
    await repository.replace_origin(project_id, IMPORTED, positions)
    logger.info(
        "lv_imported", project_id=str(project_id), position_count=len(positions)
    )
    return len(positions)


async def run_check_agents(
    ai: AIService,
    usage: UsageCounter,
    records: list[DocumentRecord],
    pages: dict[UUID, list[PageText]],
    names: dict[UUID, str],
    settings: Settings,
) -> list[CheckFinding]:
    documents = [
        CheckDocument(
            record.id,
            names.get(record.id, record.filename),
            DocumentType(record.doc_type or DocumentType.SONSTIGES.value),
            pages[record.id],
            DocumentIndex(record.id, pages[record.id], settings.CITATION_MIN_SCORE),
        )
        for record in records
        if record.id in pages
    ]
    results = await asyncio.gather(
        *(check_area(ai, usage, area, documents) for area in CheckArea)
    )
    return [finding for findings in results for finding in findings]


async def _run_job(
    project_id: UUID,
    step: AnalysisStep,
    message: str,
    work: Callable[
        [ProjectRepository, AIService, list[DocumentRecord]], Awaitable[str]
    ],
) -> None:
    """Background job on an analysed project; status and errors as for analyses."""
    settings = get_settings()
    try:
        async with database_service.session_factory() as session:
            repository = ProjectRepository(session)
            await repository.set_progress(
                project_id, ProjectStatus.PROCESSING, step, 30, message
            )
            records = await repository.list_document_records(project_id)
            ai = AIService(settings)
            try:
                done_message = await work(repository, ai, records)
            finally:
                await ai.close()
            await repository.set_progress(
                project_id, ProjectStatus.READY, AnalysisStep.DONE, 100, done_message
            )
    except Exception as error:
        logger.exception(
            "project_job_failed", project_id=str(project_id), step=step.value
        )
        async with database_service.session_factory() as session:
            await ProjectRepository(session).set_progress(
                project_id,
                ProjectStatus.FAILED,
                None,
                0,
                None,
                error=describe_error(error, settings.MODEL),
            )


def _analysis(analysis: ProjectAnalysis | None) -> ProjectAnalysis:
    if analysis is None:
        raise ValueError("Project has not been analysed")
    return analysis


async def run_lv_draft(project_id: UUID) -> None:
    """LV draft from the functional description; replaces earlier drafts."""

    async def work(
        repository: ProjectRepository, ai: AIService, records: list[DocumentRecord]
    ) -> str:
        project = await repository.get_record(project_id)
        if project is None:
            return "Projekt nicht gefunden"
        analysis = _analysis(project_analysis(project))
        lv_repository = LvRepository(repository.session)
        drafted = await draft_lv(
            ai, UsageCounter(), project_id, analysis.claims, DRAFT_SORT_BASE
        )
        await lv_repository.replace_origin(project_id, {LvOrigin.DRAFT}, drafted)
        logger.info(
            "lv_draft_saved", project_id=str(project_id), draft_count=len(drafted)
        )
        return f"LV-Entwurf mit {len(drafted)} Positionen erstellt"

    await _run_job(
        project_id, AnalysisStep.DRAFTING, "LV-Entwurf wird abgeleitet", work
    )


async def run_checks(project_id: UUID) -> None:
    """Run the check agents again, e.g. after documents were added."""
    settings = get_settings()

    async def work(
        repository: ProjectRepository, ai: AIService, records: list[DocumentRecord]
    ) -> str:
        project = await repository.get_record(project_id)
        if project is None:
            return "Projekt nicht gefunden"
        _analysis(project_analysis(project))
        pages = {
            record.id: document_pages(record) for record in records if record.pages
        }
        findings = await run_check_agents(
            ai, UsageCounter(), records, pages, document_names(records), settings
        )
        await repository.save_checks(project, findings)
        return "Prüfung abgeschlossen"

    await _run_job(project_id, AnalysisStep.CHECKING, "Prüf-Agenten laufen", work)


async def run_lv_import(project_id: UUID) -> None:
    """Import LV documents again and reassign trades."""
    settings = get_settings()

    async def work(
        repository: ProjectRepository, ai: AIService, records: list[DocumentRecord]
    ) -> str:
        pages = {
            record.id: document_pages(record) for record in records if record.pages
        }
        contents = {
            record.id: await storage.read_file(record.storage_key)
            for record in records
            if record.content_type == GAEB_CONTENT_TYPE
        }
        count = await import_lv(
            ai,
            UsageCounter(),
            project_id,
            [record for record in records if record.id in pages],
            pages,
            contents,
            LvRepository(repository.session),
            settings,
        )
        return f"{count} LV-Positionen eingelesen"

    await _run_job(
        project_id, AnalysisStep.LV, "LV einlesen und Gewerke zuordnen", work
    )
