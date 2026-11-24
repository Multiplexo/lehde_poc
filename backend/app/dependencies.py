from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.persistence.chat.chat_repository import ChatRepository
from app.persistence.feedback.feedback_repository import FeedbackRepository
from app.persistence.lv.lv_repository import LvRepository
from app.persistence.projects.project_repository import ProjectRepository
from app.persistence.projects.schema.project import DocumentRecord, ProjectRecord
from app.persistence.subcontractors.subcontractor_repository import (
    SubcontractorRepository,
)
from app.services.database import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_project_repository(session: SessionDep) -> ProjectRepository:
    return ProjectRepository(session)


async def get_feedback_repository(session: SessionDep) -> FeedbackRepository:
    return FeedbackRepository(session)


async def get_lv_repository(session: SessionDep) -> LvRepository:
    return LvRepository(session)


async def get_chat_repository(session: SessionDep) -> ChatRepository:
    return ChatRepository(session)


async def get_subcontractor_repository(session: SessionDep) -> SubcontractorRepository:
    return SubcontractorRepository(session)


ProjectRepositoryDep = Annotated[ProjectRepository, Depends(get_project_repository)]
LvRepositoryDep = Annotated[LvRepository, Depends(get_lv_repository)]
ChatRepositoryDep = Annotated[ChatRepository, Depends(get_chat_repository)]
SubcontractorRepositoryDep = Annotated[
    SubcontractorRepository, Depends(get_subcontractor_repository)
]
FeedbackRepositoryDep = Annotated[FeedbackRepository, Depends(get_feedback_repository)]


async def get_project_record(
    project_id: UUID, repository: ProjectRepositoryDep
) -> ProjectRecord:
    record = await repository.get_record(project_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projekt nicht gefunden")
    return record


ProjectRecordDep = Annotated[ProjectRecord, Depends(get_project_record)]


async def get_document_record(
    project: ProjectRecordDep, document_id: UUID, repository: ProjectRepositoryDep
) -> DocumentRecord:
    record = await repository.get_document_record(project.id, document_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nicht gefunden")
    return record


DocumentRecordDep = Annotated[DocumentRecord, Depends(get_document_record)]
