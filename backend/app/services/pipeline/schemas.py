"""Structured output schemas for model calls (strict: every field required)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentTypeName = Literal[
    "plan",
    "baubeschreibung",
    "brandschutzkonzept",
    "bodengutachten",
    "baugenehmigung",
    "leistungsverzeichnis",
    "vertrag",
    "nachtrag",
    "sonstiges",
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanSheet(_Strict):
    plan_number: str = Field(description="Plannummer wie im Plankopf")
    title: str | None = Field(description="Planinhalt, z. B. Grundriss EG")
    revision: str | None = Field(description="Index oder Planstand")
    date: str | None = Field(description="Datum des Planstands")
    page: int = Field(description="Seitenzahl im PDF, beginnend bei 1")
    title_block_quote: str = Field(description="Wörtlicher Text aus dem Plankopf")


class ClassificationResult(_Strict):
    doc_type: DocumentTypeName
    title: str | None
    revision: str | None
    document_date: str | None
    confidence: float = Field(description="0 bis 1")
    evidence_quote: str
    plans: list[PlanSheet]


class ExtractedClaim(_Strict):
    topic: str = Field(description="Schlüssel aus dem Faktenkatalog")
    value: str
    quote: str
    page: int


class ExtractedPlanReference(_Strict):
    plan_number: str
    revision: str | None
    date: str | None
    quote: str
    page: int


class ExtractionResult(_Strict):
    claims: list[ExtractedClaim]
    plan_references: list[ExtractedPlanReference]


class ConsolidatedFact(_Strict):
    topic: str
    value: str
    claim_ids: list[str]


class ConsolidatedDiscrepancy(_Strict):
    topic: str
    title: str = Field(description="Kurzer Titel, z. B. Hallenbreite abweichend")
    explanation: str
    severity: Literal["red", "yellow"]
    claim_a: str
    claim_b: str
    recipient: Literal["architekt", "bauherr", "kalkulation"]
    question: str


class ConsolidatedSummary(_Strict):
    text: str
    claim_ids: list[str]


class ConsolidationResult(_Strict):
    facts: list[ConsolidatedFact]
    discrepancies: list[ConsolidatedDiscrepancy]
    summary: ConsolidatedSummary


class FeedbackTriageResult(_Strict):
    kind: Literal["bug", "feature", "question"]
    module: Literal[
        "upload",
        "dokumente",
        "fakten",
        "abweichungen",
        "rueckfragen",
        "steckbrief",
        "lv",
        "pruefung",
        "fragen",
        "subunternehmer",
        "sonstiges",
    ]
    summary: str
    duplicate_of: str | None


class ExtractedLvPosition(_Strict):
    oz: str | None
    short_text: str
    long_text: str | None
    quantity: float | None
    unit: str | None
    quote: str
    page: int


class LvExtractionResult(_Strict):
    positions: list[ExtractedLvPosition]


class TradeAssignment(_Strict):
    id: str
    trade_code: str
    confidence: float


class TradeAssignmentResult(_Strict):
    assignments: list[TradeAssignment]


class DraftPosition(_Strict):
    trade_code: str
    short_text: str
    long_text: str | None
    unit: str | None
    quantity_formula: str | None
    claim_ids: list[str]
    assumption: str | None


class LvDraftResult(_Strict):
    positions: list[DraftPosition]


class CheckQuote(_Strict):
    document_id: str
    page: int
    quote: str


class CheckResultItem(_Strict):
    rule_id: str
    status: Literal["ok", "note", "critical", "missing", "not_applicable"]
    finding: str
    quotes: list[CheckQuote]
    question: str | None


class CheckResult(_Strict):
    results: list[CheckResultItem]


class ChatCitation(_Strict):
    passage_id: str
    quote: str


class ChatAnswer(_Strict):
    answer: str
    citations: list[ChatCitation]
