from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SubcontractorData(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    trade_codes: list[str] = Field(default_factory=list, max_length=40)
    postal_code: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    contact: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=2000)


class Subcontractor(SubcontractorData):
    id: UUID
    created_at: datetime


class SubcontractorImportResult(BaseModel):
    created: int
    skipped: list[str]
