from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.feedback import Feedback, FeedbackKind, FeedbackTriage
from app.persistence.feedback.schema.feedback import FeedbackRecord

logger = structlog.get_logger(__name__)


def feedback_model(record: FeedbackRecord) -> Feedback:
    return Feedback(
        id=record.id,
        created_at=record.created_at,
        message=record.message,
        kind=FeedbackKind(record.kind) if record.kind else None,
        url=record.url,
        project_id=record.project_id,
        user_name=record.user_name,
        user_agent=record.user_agent,
        has_screenshot=record.screenshot_key is not None,
        triage=FeedbackTriage.model_validate(record.triage) if record.triage else None,
        forwarded_at=record.forwarded_at,
    )


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _save(self, record: FeedbackRecord, event: str) -> Feedback:
        try:
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception(event, feedback_id=str(record.id))
            raise
        return feedback_model(record)

    async def create(self, record: FeedbackRecord) -> Feedback:
        return await self._save(record, "feedback_create_failed")

    async def get_record(self, feedback_id: UUID) -> FeedbackRecord | None:
        try:
            return await self.session.get(FeedbackRecord, feedback_id)
        except SQLAlchemyError:
            logger.exception("feedback_get_failed", feedback_id=str(feedback_id))
            raise

    async def set_triage(
        self, record: FeedbackRecord, triage: FeedbackTriage
    ) -> Feedback:
        record.triage = triage.model_dump(mode="json")
        return await self._save(record, "feedback_triage_save_failed")

    async def mark_forwarded(self, record: FeedbackRecord) -> Feedback:
        record.forwarded_at = datetime.now(UTC)
        return await self._save(record, "feedback_forward_save_failed")

    async def list_recent(self, limit: int = 200) -> list[Feedback]:
        statement = (
            select(FeedbackRecord)
            .order_by(col(FeedbackRecord.created_at).desc())
            .limit(limit)
        )
        try:
            rows = (await self.session.exec(statement)).all()
        except SQLAlchemyError:
            logger.exception("feedback_list_failed")
            raise
        return [feedback_model(row) for row in rows]
