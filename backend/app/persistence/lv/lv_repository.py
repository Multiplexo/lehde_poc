from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.documents import SourceRef, ValueSource
from app.models.lv import LvOrigin, LvPosition
from app.persistence.lv.schema.lv_position import LvPositionRecord

logger = structlog.get_logger(__name__)


def lv_position(record: LvPositionRecord) -> LvPosition:
    return LvPosition(
        id=record.id,
        project_id=record.project_id,
        origin=LvOrigin(record.origin),
        sort_index=record.sort_index,
        oz=record.oz,
        short_text=record.short_text,
        long_text=record.long_text,
        quantity=record.quantity,
        unit=record.unit,
        quantity_formula=record.quantity_formula,
        trade_code=record.trade_code,
        trade_source=ValueSource(record.trade_source) if record.trade_source else None,
        trade_confidence=record.trade_confidence,
        source=SourceRef.model_validate(record.source) if record.source else None,
        assumption=record.assumption,
        included=record.included,
    )


def lv_record(position: LvPosition) -> LvPositionRecord:
    return LvPositionRecord(
        id=position.id,
        project_id=position.project_id,
        origin=position.origin.value,
        sort_index=position.sort_index,
        oz=position.oz,
        short_text=position.short_text,
        long_text=position.long_text,
        quantity=position.quantity,
        unit=position.unit,
        quantity_formula=position.quantity_formula,
        trade_code=position.trade_code,
        trade_source=position.trade_source.value if position.trade_source else None,
        trade_confidence=position.trade_confidence,
        source=position.source.model_dump(mode="json") if position.source else None,
        assumption=position.assumption,
        included=position.included,
    )


class LvRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _commit(self, event: str, **context: str) -> None:
        try:
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception(event, **context)
            raise

    async def list_records(self, project_id: UUID) -> list[LvPositionRecord]:
        statement = (
            select(LvPositionRecord)
            .where(LvPositionRecord.project_id == project_id)
            .order_by(col(LvPositionRecord.sort_index))
        )
        try:
            return list((await self.session.exec(statement)).all())
        except SQLAlchemyError:
            logger.exception("lv_list_failed", project_id=str(project_id))
            raise

    async def list_positions(self, project_id: UUID) -> list[LvPosition]:
        return [lv_position(record) for record in await self.list_records(project_id)]

    async def get_record(
        self, project_id: UUID, position_id: UUID
    ) -> LvPositionRecord | None:
        try:
            record = await self.session.get(LvPositionRecord, position_id)
        except SQLAlchemyError:
            logger.exception("lv_get_failed", position_id=str(position_id))
            raise
        if record is None or record.project_id != project_id:
            return None
        return record

    async def next_sort_index(self, project_id: UUID) -> int:
        statement = select(func.max(LvPositionRecord.sort_index)).where(
            LvPositionRecord.project_id == project_id
        )
        try:
            current = (await self.session.exec(statement)).one()
        except SQLAlchemyError:
            logger.exception("lv_sort_index_failed", project_id=str(project_id))
            raise
        # Manual positions go after imported (0..) and drafted (100000..) ones.
        return max(current or 0, 200_000) + 1

    async def replace_origin(
        self, project_id: UUID, origins: set[LvOrigin], positions: list[LvPosition]
    ) -> None:
        """Replace all positions of the given origins (e.g. a new import run)."""
        try:
            await self.session.exec(
                delete(LvPositionRecord)
                .where(col(LvPositionRecord.project_id) == project_id)
                .where(
                    col(LvPositionRecord.origin).in_([item.value for item in origins])
                )
            )
            self.session.add_all([lv_record(position) for position in positions])
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("lv_replace_failed", project_id=str(project_id))
            raise
        await self._commit("lv_replace_failed", project_id=str(project_id))

    async def save(self, record: LvPositionRecord) -> LvPosition:
        self.session.add(record)
        await self._commit("lv_save_failed", position_id=str(record.id))
        await self.session.refresh(record)
        return lv_position(record)

    async def save_all(self, records: list[LvPositionRecord]) -> None:
        self.session.add_all(records)
        await self._commit("lv_save_all_failed")

    async def delete(self, record: LvPositionRecord) -> None:
        try:
            await self.session.delete(record)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("lv_delete_failed", position_id=str(record.id))
            raise
        await self._commit("lv_delete_failed", position_id=str(record.id))
