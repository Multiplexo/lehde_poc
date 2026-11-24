"""Feedback tickets: store, pre-sort with the model, forward to a webhook."""

import base64
import binascii
import json
from uuid import UUID

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.models.feedback import Feedback, FeedbackKind, FeedbackModule, FeedbackTriage
from app.persistence.feedback.feedback_repository import (
    FeedbackRepository,
    feedback_model,
)
from app.services.ai import AIService, UsageCounter, text_part
from app.services.database import database_service
from app.services.pipeline.prompts import FEEDBACK_TRIAGE_INSTRUCTIONS
from app.services.pipeline.schemas import FeedbackTriageResult

logger = structlog.get_logger(__name__)

PNG_PREFIX = "data:image/png;base64,"
WEBHOOK_TIMEOUT_SECONDS = 5
TRIAGE_HISTORY = 40


def decode_screenshot(data_url: str) -> bytes | None:
    if not data_url.startswith(PNG_PREFIX):
        return None
    try:
        content = base64.b64decode(data_url.removeprefix(PNG_PREFIX), validate=True)
    except binascii.Error:
        return None
    if not content.startswith(b"\x89PNG"):
        return None
    return content


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, max=2),
    reraise=True,
)
async def _post(url: str, payload: dict[str, object]) -> None:
    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


def _webhook_payload(feedback: Feedback, app_url: str) -> dict[str, object]:
    screenshot = (
        f"{app_url}/api/feedback/{feedback.id}/screenshot"
        if feedback.has_screenshot
        else None
    )
    kind = feedback.triage.kind if feedback.triage else feedback.kind
    title = f"Prototyp-Feedback ({kind.value if kind else 'neu'})"
    lines = [title, "", feedback.message, f"Seite: {feedback.url}"]
    if feedback.triage:
        lines.append(f"Bereich: {feedback.triage.module.value}")
    if screenshot:
        lines.append(f"Screenshot: {screenshot}")
    return {
        "text": "\n".join(lines),
        "title": title,
        "feedback": feedback.model_dump(mode="json"),
        "screenshot_url": screenshot,
    }


async def _triage(
    repository: FeedbackRepository, feedback: Feedback
) -> FeedbackTriage | None:
    settings = get_settings()
    if not settings.API_KEY or not settings.MODEL:
        return None
    history = [
        {"id": str(item.id), "message": item.message[:500]}
        for item in await repository.list_recent(TRIAGE_HISTORY)
        if item.id != feedback.id
    ]
    ai = AIService(settings)
    try:
        result = await ai.parse(
            task="feedback_triage",
            instructions=FEEDBACK_TRIAGE_INSTRUCTIONS,
            content=[
                text_part(
                    json.dumps(
                        {
                            "neues_feedback": {
                                "message": feedback.message,
                                "seite": feedback.url,
                                "art_laut_nutzer": feedback.kind,
                            },
                            "fruehere_feedbacks": history,
                        },
                        ensure_ascii=False,
                    )
                )
            ],
            schema=FeedbackTriageResult,
            usage=UsageCounter(),
        )
    finally:
        await ai.close()
    known_ids = {item["id"] for item in history}
    return FeedbackTriage(
        kind=FeedbackKind(result.kind),
        module=FeedbackModule(result.module),
        summary=result.summary,
        duplicate_of=UUID(result.duplicate_of)
        if result.duplicate_of in known_ids
        else None,
    )


async def process_feedback(feedback_id: UUID) -> None:
    """Background step after a ticket was stored: triage, then forward."""
    settings = get_settings()
    async with database_service.session_factory() as session:
        repository = FeedbackRepository(session)
        record = await repository.get_record(feedback_id)
        if record is None:
            return
        feedback = feedback_model(record)
        try:
            triage = await _triage(repository, feedback)
            if triage is not None:
                feedback = await repository.set_triage(record, triage)
        except Exception:
            logger.exception("feedback_triage_failed", feedback_id=str(feedback_id))
        if not settings.FEEDBACK_WEBHOOK_URL:
            return
        try:
            await _post(
                settings.FEEDBACK_WEBHOOK_URL,
                _webhook_payload(feedback, settings.APP_URL),
            )
        except httpx.HTTPError:
            logger.exception("feedback_forward_failed", feedback_id=str(feedback_id))
            return
        await repository.mark_forwarded(record)
        logger.info("feedback_forwarded", feedback_id=str(feedback_id))
