from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status

from app.dependencies import FeedbackRepositoryDep
from app.models.feedback import Feedback, FeedbackCreate
from app.persistence.feedback.schema.feedback import FeedbackRecord
from app.services import storage
from app.services.feedback import decode_screenshot, process_feedback

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED, operation_id="create_feedback")
async def create_feedback(
    data: FeedbackCreate,
    repository: FeedbackRepositoryDep,
    background_tasks: BackgroundTasks,
) -> Feedback:
    feedback_id = uuid4()
    screenshot_key: str | None = None
    if data.screenshot:
        screenshot = decode_screenshot(data.screenshot)
        if screenshot is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Screenshot muss ein PNG sein."
            )
        screenshot_key = f"feedback/{feedback_id}.png"
        await storage.save_file(screenshot_key, screenshot)
    feedback = await repository.create(
        FeedbackRecord(
            id=feedback_id,
            message=data.message.strip(),
            kind=data.kind.value if data.kind else None,
            url=data.url,
            project_id=data.project_id,
            user_name=data.user_name,
            user_agent=data.user_agent,
            screenshot_key=screenshot_key,
        )
    )
    background_tasks.add_task(process_feedback, feedback.id)
    logger.info("feedback_created", feedback_id=str(feedback.id))
    return feedback


@router.get("", operation_id="list_feedback")
async def list_feedback(repository: FeedbackRepositoryDep) -> list[Feedback]:
    return await repository.list_recent()


@router.get("/{feedback_id}/screenshot", operation_id="get_feedback_screenshot")
async def get_screenshot(
    feedback_id: UUID, repository: FeedbackRepositoryDep
) -> Response:
    record = await repository.get_record(feedback_id)
    if record is None or record.screenshot_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kein Screenshot vorhanden")
    content = await storage.read_file(record.screenshot_key)
    return Response(content=content, media_type="image/png")
