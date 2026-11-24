"""FastAPI application setup and shared exception handling."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.persistence.projects.project_repository import ProjectRepository
from app.routes.assistant import router as assistant_router
from app.routes.feedback import router as feedback_router
from app.routes.lv import router as lv_router
from app.routes.lv import trades_router
from app.routes.projects import router as projects_router
from app.routes.subcontractors import router as subcontractors_router
from app.services.database import database_service

logger = structlog.get_logger(__name__)


class HealthResponse(BaseModel):
    status: str = "ok"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with database_service.session_factory() as session:
        interrupted = await ProjectRepository(session).mark_interrupted()
    if interrupted:
        logger.info("interrupted_analyses_marked_failed", project_count=interrupted)
    try:
        yield
    finally:
        try:
            await database_service.engine.dispose()
        except SQLAlchemyError:
            logger.exception("database_dispose_failed")
            raise


app = FastAPI(title="Anfrageprüfung API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(OSError)
async def infrastructure_error(request: Request, exc: Exception) -> JSONResponse:
    """Return HTTP 503 without exposing database or storage details."""
    logger.exception("infrastructure_error", path=request.url.path)
    return JSONResponse(
        status_code=503, content={"detail": "Datenbank oder Ablage nicht verfügbar"}
    )


app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(lv_router, prefix="/projects/{project_id}/lv", tags=["lv"])
app.include_router(
    assistant_router, prefix="/projects/{project_id}", tags=["assistant"]
)
app.include_router(trades_router, prefix="/trades", tags=["lv"])
app.include_router(
    subcontractors_router, prefix="/subcontractors", tags=["subcontractors"]
)
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])


@app.get("/health", operation_id="get_health")
async def health() -> HealthResponse:
    return HealthResponse()
