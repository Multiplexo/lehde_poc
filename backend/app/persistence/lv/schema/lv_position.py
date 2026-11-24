from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class LvPositionRecord(SQLModel, table=True):
    __tablename__ = "lv_position"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id", ondelete="CASCADE", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )
    origin: str = Field(sa_type=Text)
    sort_index: int = Field(sa_type=Integer)
    oz: str | None = Field(default=None, sa_type=Text)
    short_text: str = Field(sa_type=Text)
    long_text: str | None = Field(default=None, sa_type=Text)
    quantity: float | None = Field(default=None, sa_type=Float)
    unit: str | None = Field(default=None, sa_type=Text)
    quantity_formula: str | None = Field(default=None, sa_type=Text)
    trade_code: str | None = Field(default=None, sa_type=Text)
    trade_source: str | None = Field(default=None, sa_type=Text)
    trade_confidence: float | None = Field(default=None, sa_type=Float)
    source: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    assumption: str | None = Field(default=None, sa_type=Text)
    included: bool = Field(default=True, sa_type=Boolean)
