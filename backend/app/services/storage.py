"""Local file storage for uploaded documents and feedback screenshots."""

import shutil

import anyio
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


def _path(key: str) -> anyio.Path:
    root = anyio.Path(get_settings().DATA_DIR)
    path = root / key
    if ".." in anyio.Path(key).parts:
        raise ValueError("Storage keys must not leave the data directory")
    return path


async def save_file(key: str, content: bytes) -> None:
    path = _path(key)
    try:
        await path.parent.mkdir(parents=True, exist_ok=True)
        await path.write_bytes(content)
    except OSError:
        logger.exception("storage_save_failed", key=key)
        raise


async def read_file(key: str) -> bytes:
    try:
        return await _path(key).read_bytes()
    except OSError:
        logger.exception("storage_read_failed", key=key)
        raise


async def delete_file(key: str) -> None:
    try:
        await _path(key).unlink(missing_ok=True)
    except OSError:
        logger.exception("storage_delete_failed", key=key)
        raise


async def delete_folder(key: str) -> None:
    path = _path(key)
    if not await path.exists():
        return
    try:
        await anyio.to_thread.run_sync(shutil.rmtree, str(path))
    except OSError:
        logger.exception("storage_folder_delete_failed", key=key)
        raise
