from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackKind(StrEnum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"


class FeedbackModule(StrEnum):
    UPLOAD = "upload"
    DOCUMENTS = "dokumente"
    FACTS = "fakten"
    DISCREPANCIES = "abweichungen"
    QUESTIONS = "rueckfragen"
    ONEPAGER = "steckbrief"
    LV = "lv"
    CHECKS = "pruefung"
    CHAT = "fragen"
    SUBCONTRACTORS = "subunternehmer"
    OTHER = "sonstiges"


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    kind: FeedbackKind | None = None
    url: str = Field(max_length=2000)
    project_id: UUID | None = None
    # PNG as data URL, captured in the browser.
    screenshot: str | None = Field(default=None, max_length=15_000_000)
    user_name: str | None = Field(default=None, max_length=200)
    user_agent: str | None = Field(default=None, max_length=500)


class FeedbackTriage(BaseModel):
    kind: FeedbackKind
    module: FeedbackModule
    summary: str
    duplicate_of: UUID | None = None


class Feedback(BaseModel):
    id: UUID
    created_at: datetime
    message: str
    kind: FeedbackKind | None = None
    url: str
    project_id: UUID | None = None
    user_name: str | None = None
    user_agent: str | None = None
    has_screenshot: bool
    triage: FeedbackTriage | None = None
    forwarded_at: datetime | None = None
