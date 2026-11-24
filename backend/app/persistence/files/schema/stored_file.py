from datetime import UTC, datetime

from sqlalchemy import DateTime, LargeBinary, Text
from sqlmodel import Field, SQLModel


class StoredFileRecord(SQLModel, table=True):
    """File content kept in PostgreSQL for hosts without a persistent disk."""

    __tablename__ = "stored_file"  # pyright: ignore[reportAssignmentType]

    key: str = Field(primary_key=True, sa_type=Text)
    content: bytes = Field(sa_type=LargeBinary)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )
