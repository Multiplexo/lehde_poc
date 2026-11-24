from datetime import datetime

from pydantic import BaseModel, Field


class OnepagerSection(BaseModel):
    label: str
    value: str
    sources: list[str] = Field(default_factory=list)


class OnepagerDocument(BaseModel):
    filename: str
    doc_type: str
    revision: str | None = None
    document_date: str | None = None


class Onepager(BaseModel):
    project_name: str
    generated_at: datetime
    summary: str | None = None
    sections: list[OnepagerSection]
    open_points: list[str]
    documents: list[OnepagerDocument]
