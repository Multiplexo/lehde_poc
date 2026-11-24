from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatMessageRecord(SQLModel, table=True):
    __tablename__ = "chat_message"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        index=True,
    )
    role: str = Field(sa_type=Text)
    content: str = Field(sa_type=Text)
    sources: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSONB)
    unsupported: bool = Field(default=False, sa_type=Boolean)
