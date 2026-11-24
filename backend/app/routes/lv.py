from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID, uuid4

import anyio
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response, status

from app.dependencies import (
    LvRepositoryDep,
    ProjectRecordDep,
    ProjectRepositoryDep,
    SubcontractorRepositoryDep,
)
from app.models.documents import ValueSource
from app.models.lv import (
    LvOrigin,
    LvOverview,
    LvPosition,
    LvPositionCreate,
    LvPositionUpdate,
)
from app.models.projects import Project
from app.models.trades import TRADE_BY_CODE, TRADE_CATALOG, Trade
from app.persistence.lv.schema.lv_position import LvPositionRecord
from app.persistence.projects.project_repository import (
    document_summary,
    project_analysis,
)
from app.persistence.projects.schema.project import ProjectRecord
from app.routes.common import (
    DOCX_MEDIA_TYPE,
    download,
    ensure_analysed,
    ensure_idle,
    slug,
)
from app.services.lv_exports import lv_xlsx, request_letter_docx
from app.services.matching import project_postal_code, trade_summaries
from app.services.onepager import build_onepager
from app.services.pipeline.jobs import run_lv_draft, run_lv_import
from app.services.pipeline.naming import document_names

logger = structlog.get_logger(__name__)

router = APIRouter()
trades_router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@trades_router.get("", operation_id="list_trades")
async def list_trades() -> list[Trade]:
    return TRADE_CATALOG


def _check_trade(code: str | None) -> None:
    if code is not None and code not in TRADE_BY_CODE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unbekanntes Gewerk")


@router.get("", operation_id="get_lv")
async def get_lv(
    project: ProjectRecordDep,
    lv: LvRepositoryDep,
    subcontractors: SubcontractorRepositoryDep,
) -> LvOverview:
    positions = await lv.list_positions(project.id)
    analysis = project_analysis(project)
    site = project_postal_code(analysis.claims) if analysis else None
    return LvOverview(
        positions=positions,
        trades=trade_summaries(positions, await subcontractors.list_all(), site),
        project_postal_code=site,
    )


async def _start(
    project: ProjectRecord,
    projects: ProjectRepositoryDep,
    background_tasks: BackgroundTasks,
    job: Callable[[UUID], Coroutine[Any, Any, None]],
) -> Project:
    ensure_analysed(project)
    if not await projects.try_start_processing(project.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Es läuft bereits ein Vorgang.")
    background_tasks.add_task(job, project.id)
    detail = await projects.get(project.id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projekt nicht gefunden")
    return detail


@router.post("/import", status_code=status.HTTP_202_ACCEPTED, operation_id="import_lv")
async def import_lv(
    project: ProjectRecordDep,
    projects: ProjectRepositoryDep,
    background_tasks: BackgroundTasks,
) -> Project:
    return await _start(project, projects, background_tasks, run_lv_import)


@router.post("/draft", status_code=status.HTTP_202_ACCEPTED, operation_id="draft_lv")
async def draft_lv(
    project: ProjectRecordDep,
    projects: ProjectRepositoryDep,
    background_tasks: BackgroundTasks,
) -> Project:
    return await _start(project, projects, background_tasks, run_lv_draft)


@router.post(
    "/positions", status_code=status.HTTP_201_CREATED, operation_id="create_lv_position"
)
async def create_position(
    data: LvPositionCreate, project: ProjectRecordDep, lv: LvRepositoryDep
) -> LvPosition:
    ensure_idle(project)
    _check_trade(data.trade_code)
    record = LvPositionRecord(
        id=uuid4(),
        project_id=project.id,
        origin=LvOrigin.MANUAL.value,
        sort_index=await lv.next_sort_index(project.id),
        oz=data.oz,
        short_text=data.short_text.strip(),
        long_text=data.long_text,
        quantity=data.quantity,
        unit=data.unit,
        trade_code=data.trade_code,
        trade_source=ValueSource.MANUAL.value if data.trade_code else None,
    )
    return await lv.save(record)


@router.patch("/positions/{position_id}", operation_id="update_lv_position")
async def update_position(
    position_id: UUID,
    data: LvPositionUpdate,
    project: ProjectRecordDep,
    lv: LvRepositoryDep,
) -> LvPosition:
    ensure_idle(project)
    record = await lv.get_record(project.id, position_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")
    changes = data.model_dump(exclude_unset=True)
    _check_trade(changes.get("trade_code"))
    for field, value in changes.items():
        setattr(record, field, value)
    if "trade_code" in changes:
        record.trade_source = ValueSource.MANUAL.value
        record.trade_confidence = None
    if "quantity" in changes:
        record.quantity_formula = None
    return await lv.save(record)


@router.delete(
    "/positions/{position_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_lv_position",
)
async def delete_position(
    position_id: UUID, project: ProjectRecordDep, lv: LvRepositoryDep
) -> None:
    ensure_idle(project)
    record = await lv.get_record(project.id, position_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Position nicht gefunden")
    await lv.delete(record)


@router.get("/export.xlsx", operation_id="export_lv_xlsx")
async def export_lv(
    project: ProjectRecordDep,
    lv: LvRepositoryDep,
    trade: Annotated[str | None, Query(max_length=10)] = None,
) -> Response:
    _check_trade(trade)
    positions = await lv.list_positions(project.id)
    content = await anyio.to_thread.run_sync(lv_xlsx, project.name, positions, trade)
    suffix = f"-{trade}" if trade else ""
    return download(content, XLSX_MEDIA_TYPE, f"LV-{slug(project.name)}{suffix}.xlsx")


@router.get("/requests/{trade_code}.docx", operation_id="export_request_letter")
async def export_request_letter(
    trade_code: str,
    project: ProjectRecordDep,
    projects: ProjectRepositoryDep,
    lv: LvRepositoryDep,
    subcontractors: SubcontractorRepositoryDep,
    subcontractor_id: UUID | None = None,
) -> Response:
    _check_trade(trade_code)
    records = await projects.list_document_records(project.id)
    onepager = build_onepager(
        project.name,
        project_analysis(project),
        [document_summary(record) for record in records],
        document_names(records),
    )
    positions = [
        item
        for item in await lv.list_positions(project.id)
        if item.included and item.trade_code == trade_code
    ]
    recipient: str | None = None
    if subcontractor_id is not None:
        sub = await subcontractors.get_record(subcontractor_id)
        if sub is not None:
            recipient = "\n".join(
                value
                for value in (
                    sub.name,
                    sub.contact,
                    " ".join(part for part in (sub.postal_code, sub.city) if part),
                )
                if value
            )
    content = await anyio.to_thread.run_sync(
        request_letter_docx, onepager, trade_code, positions, recipient
    )
    return download(
        content, DOCX_MEDIA_TYPE, f"Anfrage-{trade_code}-{slug(project.name)}.docx"
    )
