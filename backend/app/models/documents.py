from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    PLAN = "plan"
    BAUBESCHREIBUNG = "baubeschreibung"
    BRANDSCHUTZKONZEPT = "brandschutzkonzept"
    BODENGUTACHTEN = "bodengutachten"
    BAUGENEHMIGUNG = "baugenehmigung"
    LEISTUNGSVERZEICHNIS = "leistungsverzeichnis"
    VERTRAG = "vertrag"
    NACHTRAG = "nachtrag"
    SONSTIGES = "sonstiges"


DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.PLAN: "Plan",
    DocumentType.BAUBESCHREIBUNG: "Baubeschreibung",
    DocumentType.BRANDSCHUTZKONZEPT: "Brandschutzkonzept",
    DocumentType.BODENGUTACHTEN: "Bodengutachten",
    DocumentType.BAUGENEHMIGUNG: "Baugenehmigung",
    DocumentType.LEISTUNGSVERZEICHNIS: "Leistungsverzeichnis",
    DocumentType.VERTRAG: "Vertrag / Vertragsentwurf",
    DocumentType.NACHTRAG: "Nachtrag",
    DocumentType.SONSTIGES: "Sonstiges",
}


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    READ = "read"
    CLASSIFIED = "classified"
    FAILED = "failed"


class ValueSource(StrEnum):
    AI = "ai"
    MANUAL = "manual"


class Box(BaseModel):
    """Rectangle relative to the page size (0..1), origin top left."""

    x: float
    y: float
    width: float
    height: float


class PageLine(BaseModel):
    text: str
    box: Box | None = None


class PageText(BaseModel):
    number: int
    width: float = 0
    height: float = 0
    ocr: bool = False
    lines: list[PageLine] = Field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class SourceRef(BaseModel):
    document_id: UUID
    page: int
    quote: str
    boxes: list[Box] = Field(default_factory=list)
    # False when the quote could only be read from the page image (plan title
    # block) and not located in the page text.
    verified: bool = True


class PlanEntry(BaseModel):
    """One plan sheet read from its title block (Plankopf)."""

    plan_number: str
    title: str | None = None
    revision: str | None = None
    date: str | None = None
    document_id: UUID
    source: SourceRef | None = None


class DocumentSummary(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    status: DocumentStatus
    error: str | None = None
    page_count: int = 0
    ocr_page_count: int = 0
    doc_type: DocumentType | None = None
    doc_type_source: ValueSource | None = None
    title: str | None = None
    revision: str | None = None
    document_date: str | None = None
    meta_source: ValueSource | None = None
    classification_confidence: float | None = None
    plans: list[PlanEntry] = Field(default_factory=list)

    @property
    def is_pdf(self) -> bool:
        return self.content_type == "application/pdf"


class DocumentUpdate(BaseModel):
    doc_type: DocumentType | None = None
    title: str | None = Field(default=None, max_length=300)
    revision: str | None = Field(default=None, max_length=100)
    document_date: str | None = Field(default=None, max_length=100)


class DocumentPages(BaseModel):
    document_id: UUID
    pages: list[PageText]
