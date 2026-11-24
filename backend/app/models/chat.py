from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.documents import SourceRef


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    id: UUID
    project_id: UUID
    created_at: datetime
    role: ChatRole
    content: str
    sources: list[SourceRef] = Field(default_factory=list)
    # True when the model gave no verifiable quote and the answer was withheld.
    unsupported: bool = False


class ChatQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
