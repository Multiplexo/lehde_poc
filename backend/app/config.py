import logging
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

import structlog
from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.logging import RichHandler


class Settings(BaseSettings):
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "lehde"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10

    # "console" for readable local output, "json" for log platforms in production.
    LOG_FORMAT: Literal["console", "json"] = "console"

    # Uploaded documents and feedback screenshots are stored below this directory.
    DATA_DIR: Path = Path("data")
    # "database" stores files in PostgreSQL (hosts without a persistent disk).
    STORAGE_BACKEND: Literal["filesystem", "database"] = "filesystem"
    MAX_UPLOAD_MB: int = Field(default=100, ge=1, le=1000)
    MAX_DOCUMENTS_PER_PROJECT: int = Field(default=20, ge=1, le=100)

    # OpenAI-compatible endpoint with EU hosting, e.g.
    # https://api.langdock.com/openai/eu/v1. Empty uses the OpenAI default.
    LLM_BASE_URL: str | None = None
    API_KEY: str = ""
    MODEL: str = ""
    LLM_MAX_RETRIES: int = Field(default=4, ge=0, le=10)
    LLM_TIMEOUT_SECONDS: float = Field(default=240, ge=10, le=900)
    # Parallel model calls during classification and fact extraction.
    LLM_CONCURRENCY: int = Field(default=4, ge=1, le=16)
    # Characters of document text sent per extraction call; longer documents are
    # split into several calls.
    EXTRACTION_CHUNK_CHARACTERS: int = Field(default=60_000, ge=5_000, le=400_000)

    # Pages with less text than this are treated as scans and read with OCR.
    OCR_MIN_TEXT_CHARACTERS: int = Field(default=25, ge=0)
    PDF_OCR_ENABLED: bool = True
    # Tesseract language packs, e.g. "deu+eng".
    OCR_LANGUAGES: str = "deu+eng"
    # Minimum similarity (0-100) for a quote to count as found in the document.
    CITATION_MIN_SCORE: float = Field(default=88, ge=50, le=100)

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    APP_URL: str = "http://localhost:5173"

    # Feedback is stored in the app; optionally posted as JSON to a ticket webhook.
    FEEDBACK_WEBHOOK_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[1] / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


def configure_logging(log_format: str) -> None:
    if log_format == "json":
        logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(ensure_ascii=False),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


configure_logging(get_settings().LOG_FORMAT)
