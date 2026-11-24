from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.subcontractors import Subcontractor, SubcontractorData
from app.persistence.subcontractors.schema.subcontractor import SubcontractorRecord

logger = structlog.get_logger(__name__)


def subcontractor_model(record: SubcontractorRecord) -> Subcontractor:
    return Subcontractor(
        id=record.id,
        created_at=record.created_at,
        name=record.name,
        trade_codes=list(record.trade_codes),
        postal_code=record.postal_code,
        city=record.city,
        contact=record.contact,
        email=record.email,
        phone=record.phone,
        note=record.note,
    )


class SubcontractorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _commit(self, event: str) -> None:
        try:
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception(event)
            raise

    async def list_all(self) -> list[Subcontractor]:
        statement = select(SubcontractorRecord).order_by(col(SubcontractorRecord.name))
        try:
            rows = (await self.session.exec(statement)).all()
        except SQLAlchemyError:
            logger.exception("subcontractor_list_failed")
            raise
        return [subcontractor_model(row) for row in rows]

    async def get_record(self, subcontractor_id: UUID) -> SubcontractorRecord | None:
        try:
            return await self.session.get(SubcontractorRecord, subcontractor_id)
        except SQLAlchemyError:
            logger.exception("subcontractor_get_failed")
            raise

    async def create_many(self, items: list[SubcontractorData]) -> list[Subcontractor]:
        records = [SubcontractorRecord(**item.model_dump()) for item in items]
        self.session.add_all(records)
        await self._commit("subcontractor_create_failed")
        for record in records:
            await self.session.refresh(record)
        return [subcontractor_model(record) for record in records]

    async def update(
        self, record: SubcontractorRecord, data: SubcontractorData
    ) -> Subcontractor:
        for field, value in data.model_dump().items():
            setattr(record, field, value)
        self.session.add(record)
        await self._commit("subcontractor_update_failed")
        await self.session.refresh(record)
        return subcontractor_model(record)

    async def delete(self, record: SubcontractorRecord) -> None:
        try:
            await self.session.delete(record)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("subcontractor_delete_failed")
            raise
        await self._commit("subcontractor_delete_failed")
