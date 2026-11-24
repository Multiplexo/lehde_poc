"""Storage for uploaded documents and feedback screenshots.

"filesystem" keeps files below DATA_DIR. "database" keeps them in PostgreSQL,
for hosts whose disk is lost on every restart (e.g. free cloud instances).
"""

import shutil

import anyio
import structlog

from app.config import get_settings
from app.persistence.files.file_repository import FileRepository
from app.services.database import database_service

logger = structlog.get_logger(__name__)


def _in_database() -> bool:
    return get_settings().STORAGE_BACKEND == "database"


def _path(key: str) -> anyio.Path:
    if ".." in anyio.Path(key).parts:
        raise ValueError("Storage keys must not leave the data directory")
    return anyio.Path(get_settings().DATA_DIR) / key


async def save_file(key: str, content: bytes) -> None:
    if _in_database():
        async with database_service.session_factory() as session:
            await FileRepository(session).save(key, content)
        return
    path = _path(key)
    try:
        await path.parent.mkdir(parents=True, exist_ok=True)
        await path.write_bytes(content)
    except OSError:
        logger.exception("storage_save_failed", key=key)
        raise


async def read_file(key: str) -> bytes:
    if _in_database():
        async with database_service.session_factory() as session:
            content = await FileRepository(session).read(key)
        if content is None:
            raise FileNotFoundError(key)
        return content
    try:
        return await _path(key).read_bytes()
    except OSError:
        logger.exception("storage_read_failed", key=key)
        raise


async def delete_file(key: str) -> None:
    if _in_database():
        async with database_service.session_factory() as session:
            await FileRepository(session).delete_prefix(key)
        return
    try:
        await _path(key).unlink(missing_ok=True)
    except OSError:
        logger.exception("storage_delete_failed", key=key)
        raise


async def delete_folder(key: str) -> None:
    if _in_database():
        async with database_service.session_factory() as session:
            await FileRepository(session).delete_prefix(key.rstrip("/") + "/")
        return
    path = _path(key)
    if not await path.exists():
        return
    try:
        await anyio.to_thread.run_sync(shutil.rmtree, str(path))
    except OSError:
        logger.exception("storage_folder_delete_failed", key=key)
        raise
