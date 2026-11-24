"""Locate model quotes in the document text.

Every statement shown to users needs a quote that is actually in the document.
Quotes that cannot be found are dropped instead of shown (hallucination guard).
"""

import re
from dataclasses import dataclass
from uuid import UUID

from rapidfuzz import fuzz

from app.models.documents import Box, PageText, SourceRef

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
MIN_QUOTE_CHARACTERS = 4
MIN_FUZZY_QUOTE_CHARACTERS = 12
_TRANSLATION = str.maketrans(
    {
        "„": '"',
        "“": '"',
        "”": '"',
        "‚": "'",
        "‘": "'",
        "’": "'",
        "–": "-",
        "—": "-",
        "‑": "-",
        " ": " ",
        "­": "",
    }
)


def normalize(text: str) -> str:
    return " ".join(text.translate(_TRANSLATION).lower().split())


@dataclass
class _IndexedPage:
    number: int
    text: str
    spans: list[tuple[int, int, Box | None]]


@dataclass
class GroundedQuote:
    page: int
    quote: str
    boxes: list[Box]


def _index_page(page: PageText) -> _IndexedPage:
    parts: list[str] = []
    spans: list[tuple[int, int, Box | None]] = []
    position = 0
    for line in page.lines:
        text = normalize(line.text)
        if not text:
            continue
        if parts:
            position += 1
        spans.append((position, position + len(text), line.box))
        parts.append(text)
        position += len(text)
    return _IndexedPage(number=page.number, text=" ".join(parts), spans=spans)


class DocumentIndex:
    def __init__(self, document_id: UUID, pages: list[PageText], min_score: float):
        self.document_id = document_id
        self.min_score = min_score
        self._pages = [_index_page(page) for page in pages]
        self._original = {page.number: page for page in pages}

    @property
    def page_numbers(self) -> list[int]:
        return [page.number for page in self._pages]

    def _find_on_page(
        self, page: _IndexedPage, quote: str
    ) -> tuple[int, int, float] | None:
        start = page.text.find(quote)
        if start >= 0:
            return start, start + len(quote), 100.0
        if len(quote) < MIN_FUZZY_QUOTE_CHARACTERS or not page.text:
            return None
        alignment = fuzz.partial_ratio_alignment(
            quote, page.text, score_cutoff=self.min_score
        )
        if alignment is None:
            return None
        # Similar text with a changed figure is not the same statement.
        found = page.text[max(0, alignment.dest_start - 8) : alignment.dest_end + 8]
        if set(_NUMBER.findall(quote)) - set(_NUMBER.findall(found)):
            return None
        return alignment.dest_start, alignment.dest_end, alignment.score

    def locate(self, quote: str, page_hint: int | None) -> GroundedQuote | None:
        """Find the quote, preferring the page the model named."""
        normalized = normalize(quote)
        if len(normalized) < MIN_QUOTE_CHARACTERS:
            return None
        ordered = sorted(
            self._pages,
            key=lambda page: (page.number != page_hint, page.number),
        )
        best: tuple[_IndexedPage, int, int, float] | None = None
        for page in ordered:
            found = self._find_on_page(page, normalized)
            if found is None:
                continue
            start, end, score = found
            if score >= 100:
                best = (page, start, end, score)
                break
            if best is None or score > best[3]:
                best = (page, start, end, score)
        if best is None:
            return None
        page, start, end, _ = best
        boxes = [
            box
            for span_start, span_end, box in page.spans
            if box is not None and span_start < end and span_end > start
        ]
        return GroundedQuote(page=page.number, quote=quote.strip(), boxes=boxes)

    def source(self, quote: str, page_hint: int | None) -> SourceRef | None:
        grounded = self.locate(quote, page_hint)
        if grounded is None:
            return None
        return SourceRef(
            document_id=self.document_id,
            page=grounded.page,
            quote=grounded.quote,
            boxes=grounded.boxes,
        )

    def page_text(self, number: int) -> str:
        page = self._original.get(number)
        return page.text if page else ""
