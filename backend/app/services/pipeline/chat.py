"""Project Q&A ("Supermind"): keyword retrieval over the pages, answer with quotes."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

import structlog

from app.models.chat import ChatMessage, ChatRole
from app.models.documents import PageText, SourceRef
from app.services.ai import AIService, UsageCounter, text_part
from app.services.pipeline.grounding import DocumentIndex
from app.services.pipeline.prompts import CHAT_INSTRUCTIONS
from app.services.pipeline.schemas import ChatAnswer

logger = structlog.get_logger(__name__)

PASSAGE_CHARACTERS = 1200
TOP_PASSAGES = 14
HISTORY_MESSAGES = 4
NO_ANSWER = (
    "Dazu habe ich in den Unterlagen keine belegte Aussage gefunden. "
    "Möglicherweise fehlt das passende Dokument im Paket."
)
_WORD = re.compile(r"[a-zäöüß0-9]{3,}")
_STOPWORDS = {
    "der", "die", "das", "und", "oder", "ist", "sind", "wir", "ihr", "sie",
    "ein", "eine", "einen", "für", "mit", "von", "den", "dem", "des", "auf",
    "wie", "was", "wer", "wann", "welche", "welcher", "gibt", "eigentlich",
    "nicht", "auch", "bei", "zum", "zur", "aus", "nach", "über", "unter",
}  # fmt: skip


@dataclass
class Passage:
    id: str
    document_id: UUID
    document_name: str
    page: int
    text: str


def _terms(text: str) -> list[str]:
    terms = []
    for word in _WORD.findall(text.lower()):
        if word in _STOPWORDS:
            continue
        # Light stemming so that "Gewährleistung" finds "Gewährleistungsfrist".
        terms.append(word[:7] if len(word) > 7 else word)
    return terms


def build_passages(
    documents: list[tuple[UUID, str, list[PageText]]],
) -> list[Passage]:
    passages: list[Passage] = []
    for number, (document_id, name, pages) in enumerate(documents, start=1):
        for page in pages:
            buffer = ""
            part = 0
            for line in page.lines:
                buffer += line.text + "\n"
                if len(buffer) >= PASSAGE_CHARACTERS:
                    part += 1
                    passages.append(
                        Passage(
                            f"D{number}-S{page.number}-{part}",
                            document_id,
                            name,
                            page.number,
                            buffer,
                        )
                    )
                    buffer = ""
            if buffer.strip():
                part += 1
                passages.append(
                    Passage(
                        f"D{number}-S{page.number}-{part}",
                        document_id,
                        name,
                        page.number,
                        buffer,
                    )
                )
    return passages


def rank_passages(question: str, passages: list[Passage]) -> list[Passage]:
    """BM25-like ranking on stemmed terms; no embeddings needed."""
    query = set(_terms(question))
    if not query or not passages:
        return passages[:TOP_PASSAGES]
    term_lists = [_terms(passage.text) for passage in passages]
    frequency = Counter(term for terms in term_lists for term in set(terms))
    total = len(passages)
    average = sum(len(terms) for terms in term_lists) / total or 1
    scored: list[tuple[float, Passage]] = []
    for passage, terms in zip(passages, term_lists, strict=True):
        counts = Counter(terms)
        score = 0.0
        for term in query:
            if term not in counts:
                continue
            idf = math.log(
                1 + (total - frequency[term] + 0.5) / (frequency[term] + 0.5)
            )
            tf = counts[term]
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(terms) / average))
        scored.append((score, passage))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [passage for score, passage in scored[:TOP_PASSAGES] if score > 0] or [
        passage for _, passage in scored[:4]
    ]


async def answer_question(
    ai: AIService,
    question: str,
    history: list[ChatMessage],
    passages: list[Passage],
    indexes: dict[UUID, DocumentIndex],
) -> tuple[str, list[SourceRef]]:
    selected = rank_passages(question, passages)
    by_id = {passage.id: passage for passage in selected}
    context = "\n\n".join(
        f'<passage passage_id="{passage.id}" dokument="{passage.document_name}" seite="{passage.page}">\n'
        f"{passage.text}</passage>"
        for passage in selected
    )
    earlier = "\n".join(
        f"{'Frage' if message.role == ChatRole.USER else 'Antwort'}: {message.content}"
        for message in history[-HISTORY_MESSAGES:]
    )
    result = await ai.parse(
        task="chat",
        instructions=CHAT_INSTRUCTIONS,
        content=[
            text_part(
                (f"Bisheriger Verlauf:\n{earlier}\n\n" if earlier else "")
                + f"Textstellen:\n{context}\n\nFrage: {question}"
            )
        ],
        schema=ChatAnswer,
        usage=UsageCounter(),
    )
    sources: list[SourceRef] = []
    for citation in result.citations:
        passage = by_id.get(citation.passage_id)
        if passage is None:
            continue
        source = indexes[passage.document_id].source(citation.quote, passage.page)
        if source is not None and source not in sources:
            sources.append(source)
    logger.info(
        "chat_answered",
        passage_count=len(selected),
        citation_count=len(result.citations),
        verified_count=len(sources),
    )
    if not sources:
        return NO_ANSWER, []
    return result.answer.strip(), sources
