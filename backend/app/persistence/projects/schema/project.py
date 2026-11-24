from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(UTC)


class ProjectRecord(SQLModel, table=True):
    __tablename__ = "project"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(sa_type=Text)
    created_at: datetime = Field(
        default_factory=_now, sa_type=DateTime(timezone=True), index=True
    )
    updated_at: datetime = Field(default_factory=_now, sa_type=DateTime(timezone=True))
    status: str = Field(default="draft", sa_type=Text)
    step: str | None = Field(default=None, sa_type=Text)
    percent: int = Field(default=0, sa_type=Integer)
    message: str | None = Field(default=None, sa_type=Text)
    error: str | None = Field(default=None, sa_type=Text)
    analysis: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    questions: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSONB)


class DocumentRecord(SQLModel, table=True):
    __tablename__ = "document"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", ondelete="CASCADE", index=True)
    filename: str = Field(sa_type=Text)
    content_type: str = Field(sa_type=Text)
    size_bytes: int = Field(sa_type=BigInteger)
    storage_key: str = Field(sa_type=Text)
    created_at: datetime = Field(default_factory=_now, sa_type=DateTime(timezone=True))
    status: str = Field(default="uploaded", sa_type=Text)
    error: str | None = Field(default=None, sa_type=Text)
    page_count: int = Field(default=0, sa_type=Integer)
    ocr_page_count: int = Field(default=0, sa_type=Integer)
    pages: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSONB)
    doc_type: str | None = Field(default=None, sa_type=Text)
    doc_type_source: str | None = Field(default=None, sa_type=Text)
    title: str | None = Field(default=None, sa_type=Text)
    revision: str | None = Field(default=None, sa_type=Text)
    document_date: str | None = Field(default=None, sa_type=Text)
    meta_source: str | None = Field(default=None, sa_type=Text)
    classification_confidence: float | None = Field(default=None, sa_type=Float)
    plans: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSONB)
