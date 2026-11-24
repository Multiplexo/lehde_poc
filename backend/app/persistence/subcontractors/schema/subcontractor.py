from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class SubcontractorRecord(SQLModel, table=True):
    __tablename__ = "subcontractor"  # pyright: ignore[reportAssignmentType]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )
    name: str = Field(sa_type=Text)
    trade_codes: list[str] = Field(default_factory=list, sa_type=JSONB)
    postal_code: str | None = Field(default=None, sa_type=Text)
    city: str | None = Field(default=None, sa_type=Text)
    contact: str | None = Field(default=None, sa_type=Text)
    email: str | None = Field(default=None, sa_type=Text)
    phone: str | None = Field(default=None, sa_type=Text)
    note: str | None = Field(default=None, sa_type=Text)
