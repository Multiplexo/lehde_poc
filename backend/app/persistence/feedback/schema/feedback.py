from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class FeedbackRecord(SQLModel, table=True):
    __tablename__ = "feedback"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
        index=True,
    )
    message: str = Field(sa_type=Text)
    kind: str | None = Field(default=None, sa_type=Text)
    url: str = Field(sa_type=Text)
    project_id: UUID | None = Field(
        default=None, foreign_key="project.id", ondelete="SET NULL"
    )
    user_name: str | None = Field(default=None, sa_type=Text)
    user_agent: str | None = Field(default=None, sa_type=Text)
    screenshot_key: str | None = Field(default=None, sa_type=Text)
    triage: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    forwarded_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
