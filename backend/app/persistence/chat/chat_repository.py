from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.chat import ChatMessage, ChatRole
from app.models.documents import SourceRef
from app.persistence.chat.schema.chat_message import ChatMessageRecord

logger = structlog.get_logger(__name__)


def chat_message(record: ChatMessageRecord) -> ChatMessage:
    return ChatMessage(
        id=record.id,
        project_id=record.project_id,
        created_at=record.created_at,
        role=ChatRole(record.role),
        content=record.content,
        sources=[SourceRef.model_validate(item) for item in record.sources],
        unsupported=record.unsupported,
    )


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_messages(
        self, project_id: UUID, limit: int = 200
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessageRecord)
            .where(ChatMessageRecord.project_id == project_id)
            .order_by(col(ChatMessageRecord.created_at))
            .limit(limit)
        )
        try:
            rows = (await self.session.exec(statement)).all()
        except SQLAlchemyError:
            logger.exception("chat_list_failed", project_id=str(project_id))
            raise
        return [chat_message(row) for row in rows]

    async def add(self, records: list[ChatMessageRecord]) -> list[ChatMessage]:
        try:
            self.session.add_all(records)
            await self.session.commit()
            for record in records:
                await self.session.refresh(record)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("chat_add_failed")
            raise
        return [chat_message(record) for record in records]

    async def clear(self, project_id: UUID) -> None:
        try:
            await self.session.exec(
                delete(ChatMessageRecord).where(
                    col(ChatMessageRecord.project_id) == project_id
                )
            )
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("chat_clear_failed", project_id=str(project_id))
            raise
