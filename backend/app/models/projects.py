from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.analysis import ProjectAnalysis, Question
from app.models.checks import CheckFinding
from app.models.documents import DocumentSummary


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AnalysisStep(StrEnum):
    READING = "reading"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    COMPARING = "comparing"
    LV = "lv"
    CHECKING = "checking"
    DRAFTING = "drafting"
    DONE = "done"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class ProjectListItem(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    status: ProjectStatus
    document_count: int
    open_discrepancies: int
    red_discrepancies: int


class ProjectProgress(BaseModel):
    step: AnalysisStep | None = None
    percent: int = 0
    message: str | None = None


class Project(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    status: ProjectStatus
    progress: ProjectProgress
    error: str | None = None
    documents: list[DocumentSummary]
    analysis: ProjectAnalysis | None = None
    questions: list[Question] = Field(default_factory=list)
    checks: list[CheckFinding] = Field(default_factory=list)
    checks_at: datetime | None = None


class QuestionsUpdate(BaseModel):
    questions: list[Question]
