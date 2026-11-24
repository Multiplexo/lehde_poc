"""Check agents and project Q&A (Supermind) for an analysed project."""

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.config import SettingsDep
from app.dependencies import ChatRepositoryDep, ProjectRecordDep, ProjectRepositoryDep
from app.models.chat import ChatMessage, ChatQuestion, ChatRole
from app.models.checks import CHECK_CATALOG, CheckRule
from app.models.projects import Project
from app.persistence.chat.schema.chat_message import ChatMessageRecord
from app.persistence.projects.project_repository import document_pages
from app.routes.common import ensure_analysed
from app.services.ai import AIService, describe_error
from app.services.pipeline.chat import answer_question, build_passages
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.jobs import run_checks
from app.services.pipeline.naming import document_names

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/checks/catalog", operation_id="get_check_catalog")
async def get_check_catalog() -> list[CheckRule]:
    return CHECK_CATALOG


@router.post("/checks", status_code=status.HTTP_202_ACCEPTED, operation_id="run_checks")
async def start_checks(
    project: ProjectRecordDep,
    projects: ProjectRepositoryDep,
    background_tasks: BackgroundTasks,
) -> Project:
    ensure_analysed(project)
    if not await projects.try_start_processing(project.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Es läuft bereits ein Vorgang.")
    background_tasks.add_task(run_checks, project.id)
    detail = await projects.get(project.id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projekt nicht gefunden")
    return detail


@router.get("/chat", operation_id="list_chat")
async def list_chat(
    project: ProjectRecordDep, chat: ChatRepositoryDep
) -> list[ChatMessage]:
    return await chat.list_messages(project.id)


@router.delete(
    "/chat", status_code=status.HTTP_204_NO_CONTENT, operation_id="clear_chat"
)
async def clear_chat(project: ProjectRecordDep, chat: ChatRepositoryDep) -> None:
    await chat.clear(project.id)


@router.post("/chat", operation_id="ask_project")
async def ask(
    data: ChatQuestion,
    project: ProjectRecordDep,
    projects: ProjectRepositoryDep,
    chat: ChatRepositoryDep,
    settings: SettingsDep,
) -> list[ChatMessage]:
    """Answer a question about the documents; returns question and answer."""
    records = [
        record
        for record in await projects.list_document_records(project.id)
        if record.pages
    ]
    if not records:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Bitte zuerst die Analyse ausführen."
        )
    names = document_names(records)
    pages = {record.id: document_pages(record) for record in records}
    passages = build_passages(
        [(record.id, names[record.id], pages[record.id]) for record in records]
    )
    indexes = {
        record.id: DocumentIndex(
            record.id, pages[record.id], settings.CITATION_MIN_SCORE
        )
        for record in records
    }
    history = await chat.list_messages(project.id)
    try:
        ai = AIService(settings)
    except ValueError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, describe_error(error, settings.MODEL)
        ) from error
    try:
        answer, sources = await answer_question(
            ai, data.question.strip(), history, passages, indexes
        )
    except Exception as error:
        logger.exception("chat_failed", project_id=str(project.id))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, describe_error(error, settings.MODEL)
        ) from error
    finally:
        await ai.close()
    return await chat.add(
        [
            ChatMessageRecord(
                project_id=project.id, role=ChatRole.USER.value, content=data.question
            ),
            ChatMessageRecord(
                project_id=project.id,
                role=ChatRole.ASSISTANT.value,
                content=answer,
                sources=[source.model_dump(mode="json") for source in sources],
                unsupported=not sources,
            ),
        ]
    )
