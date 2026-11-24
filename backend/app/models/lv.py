from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.documents import SourceRef, ValueSource


class LvOrigin(StrEnum):
    GAEB = "gaeb"
    DOCUMENT = "document"
    DRAFT = "draft"
    MANUAL = "manual"


class LvPosition(BaseModel):
    id: UUID
    project_id: UUID
    origin: LvOrigin
    sort_index: int
    oz: str | None = None
    short_text: str
    long_text: str | None = None
    quantity: float | None = None
    unit: str | None = None
    # How a drafted quantity was derived, e.g. "60,00 * 25,00".
    quantity_formula: str | None = None
    trade_code: str | None = None
    trade_source: ValueSource | None = None
    trade_confidence: float | None = None
    source: SourceRef | None = None
    # Drafted positions without a quote are assumptions and are marked as such.
    assumption: str | None = None
    included: bool = True


class LvPositionUpdate(BaseModel):
    oz: str | None = Field(default=None, max_length=50)
    short_text: str | None = Field(default=None, min_length=1, max_length=500)
    long_text: str | None = Field(default=None, max_length=10000)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=30)
    trade_code: str | None = Field(default=None, max_length=10)
    included: bool | None = None


class LvPositionCreate(BaseModel):
    oz: str | None = Field(default=None, max_length=50)
    short_text: str = Field(min_length=1, max_length=500)
    long_text: str | None = Field(default=None, max_length=10000)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=30)
    trade_code: str | None = Field(default=None, max_length=10)


class SubcontractorSuggestion(BaseModel):
    subcontractor_id: UUID
    name: str
    city: str | None = None
    postal_code: str | None = None
    email: str | None = None
    reason: str


class TradeSummary(BaseModel):
    code: str
    label: str
    own_work: bool
    position_count: int
    draft_count: int
    assumption_count: int
    suggestions: list[SubcontractorSuggestion] = Field(default_factory=list)


class LvOverview(BaseModel):
    positions: list[LvPosition]
    trades: list[TradeSummary]
    project_postal_code: str | None = None
