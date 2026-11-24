from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.documents import PlanEntry, SourceRef


class Claim(BaseModel):
    """A statement of one document on a catalog topic, backed by a found quote."""

    id: str
    document_id: UUID
    topic: str
    value: str
    source: SourceRef


class PlanReference(BaseModel):
    """A document mentions a plan with a revision (Planstand)."""

    id: str
    document_id: UUID
    plan_number: str
    revision: str | None = None
    date: str | None = None
    source: SourceRef


class FactStatus(StrEnum):
    FOUND = "found"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


class Fact(BaseModel):
    key: str
    label: str
    group: str
    status: FactStatus
    value: str | None = None
    claims: list[Claim] = Field(default_factory=list)


class Severity(StrEnum):
    RED = "red"
    YELLOW = "yellow"


class DiscrepancyKind(StrEnum):
    PLANSTAND = "planstand"
    CONTENT = "content"


class Recipient(StrEnum):
    ARCHITEKT = "architekt"
    BAUHERR = "bauherr"
    KALKULATION = "kalkulation"


class DiscrepancyStatus(StrEnum):
    OPEN = "open"
    QUESTION = "question"
    RESERVATION = "reservation"
    DONE = "done"


class DiscrepancySide(BaseModel):
    document_id: UUID
    value: str
    source: SourceRef | None = None


class Discrepancy(BaseModel):
    id: str
    kind: DiscrepancyKind
    topic: str
    title: str
    explanation: str
    severity: Severity
    side_a: DiscrepancySide
    side_b: DiscrepancySide | None = None
    recipient: Recipient
    question: str
    status: DiscrepancyStatus = DiscrepancyStatus.OPEN
    note: str | None = None


class DiscrepancyUpdate(BaseModel):
    status: DiscrepancyStatus | None = None
    recipient: Recipient | None = None
    question: str | None = Field(default=None, min_length=3, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class Question(BaseModel):
    id: str
    text: str
    recipient: Recipient
    included: bool = True
    discrepancy_id: str | None = None
    fact_key: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    text: str
    claim_ids: list[str] = Field(default_factory=list)


class AnalysisStats(BaseModel):
    documents: int = 0
    pages: int = 0
    ocr_pages: int = 0
    claims_found: int = 0
    claims_dropped: int = 0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0


class ProjectAnalysis(BaseModel):
    created_at: datetime
    model: str
    summary: ProjectSummary | None = None
    facts: list[Fact]
    claims: list[Claim]
    plan_references: list[PlanReference]
    plan_register: list[PlanEntry]
    discrepancies: list[Discrepancy]
    stats: AnalysisStats
