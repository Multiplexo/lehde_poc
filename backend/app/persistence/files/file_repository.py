import structlog
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.persistence.files.schema.stored_file import StoredFileRecord

logger = structlog.get_logger(__name__)


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, key: str, content: bytes) -> None:
        statement = (
            insert(StoredFileRecord)
            .values(key=key, content=content)
            .on_conflict_do_update(index_elements=["key"], set_={"content": content})
        )
        try:
            await self.session.exec(statement)
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("file_save_failed", key=key)
            raise

    async def read(self, key: str) -> bytes | None:
        try:
            record = await self.session.get(StoredFileRecord, key)
        except SQLAlchemyError:
            logger.exception("file_read_failed", key=key)
            raise
        return record.content if record else None

    async def delete_prefix(self, prefix: str) -> None:
        try:
            await self.session.exec(
                delete(StoredFileRecord).where(
                    col(StoredFileRecord.key).startswith(prefix)
                )
            )
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("file_delete_failed", prefix=prefix)
            raise
