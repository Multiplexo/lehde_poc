from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete, func, select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.analysis import (
    DiscrepancyStatus,
    ProjectAnalysis,
    Question,
    Severity,
)
from app.models.documents import (
    DocumentStatus,
    DocumentSummary,
    DocumentType,
    PageText,
    PlanEntry,
    ValueSource,
)
from app.models.projects import (
    AnalysisStep,
    Project,
    ProjectListItem,
    ProjectProgress,
    ProjectStatus,
)
from app.persistence.projects.schema.project import DocumentRecord, ProjectRecord

logger = structlog.get_logger(__name__)


def document_summary(record: DocumentRecord) -> DocumentSummary:
    return DocumentSummary(
        id=record.id,
        project_id=record.project_id,
        filename=record.filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        status=DocumentStatus(record.status),
        error=record.error,
        page_count=record.page_count,
        ocr_page_count=record.ocr_page_count,
        doc_type=DocumentType(record.doc_type) if record.doc_type else None,
        doc_type_source=ValueSource(record.doc_type_source)
        if record.doc_type_source
        else None,
        title=record.title,
        revision=record.revision,
        document_date=record.document_date,
        meta_source=ValueSource(record.meta_source) if record.meta_source else None,
        classification_confidence=record.classification_confidence,
        plans=[PlanEntry.model_validate(plan) for plan in record.plans],
    )


def document_pages(record: DocumentRecord) -> list[PageText]:
    return [PageText.model_validate(page) for page in record.pages]


def project_analysis(record: ProjectRecord) -> ProjectAnalysis | None:
    if record.analysis is None:
        return None
    return ProjectAnalysis.model_validate(record.analysis)


def _open_counts(record: ProjectRecord) -> tuple[int, int]:
    analysis = project_analysis(record)
    if analysis is None:
        return 0, 0
    open_items = [
        item for item in analysis.discrepancies if item.status != DiscrepancyStatus.DONE
    ]
    return len(open_items), sum(item.severity == Severity.RED for item in open_items)


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _commit(self, event: str, **context: Any) -> None:
        try:
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception(event, **context)
            raise

    async def create(self, name: str) -> ProjectRecord:
        record = ProjectRecord(name=name)
        self.session.add(record)
        await self._commit("project_create_failed")
        await self.session.refresh(record)
        return record

    async def list_items(self) -> list[ProjectListItem]:
        counts = (
            select(
                col(DocumentRecord.project_id).label("project_id"),
                func.count().label("document_count"),
            )
            .group_by(col(DocumentRecord.project_id))
            .subquery()
        )
        statement = (
            select(ProjectRecord, counts.c.document_count)
            .join(counts, counts.c.project_id == ProjectRecord.id, isouter=True)
            .order_by(col(ProjectRecord.created_at).desc())
        )
        try:
            rows = (await self.session.exec(statement)).all()
        except SQLAlchemyError:
            logger.exception("project_list_failed")
            raise
        items: list[ProjectListItem] = []
        for record, document_count in rows:
            open_count, red_count = _open_counts(record)
            items.append(
                ProjectListItem(
                    id=record.id,
                    name=record.name,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    status=ProjectStatus(record.status),
                    document_count=document_count or 0,
                    open_discrepancies=open_count,
                    red_discrepancies=red_count,
                )
            )
        return items

    async def get_record(self, project_id: UUID) -> ProjectRecord | None:
        try:
            return await self.session.get(ProjectRecord, project_id)
        except SQLAlchemyError:
            logger.exception("project_get_failed", project_id=str(project_id))
            raise

    async def list_document_records(self, project_id: UUID) -> list[DocumentRecord]:
        statement = (
            select(DocumentRecord)
            .where(DocumentRecord.project_id == project_id)
            .order_by(col(DocumentRecord.created_at), col(DocumentRecord.filename))
        )
        try:
            return list((await self.session.exec(statement)).all())
        except SQLAlchemyError:
            logger.exception("document_list_failed", project_id=str(project_id))
            raise

    async def get(self, project_id: UUID) -> Project | None:
        record = await self.get_record(project_id)
        if record is None:
            return None
        documents = await self.list_document_records(project_id)
        return Project(
            id=record.id,
            name=record.name,
            created_at=record.created_at,
            updated_at=record.updated_at,
            status=ProjectStatus(record.status),
            progress=ProjectProgress(
                step=AnalysisStep(record.step) if record.step else None,
                percent=record.percent,
                message=record.message,
            ),
            error=record.error,
            documents=[document_summary(document) for document in documents],
            analysis=project_analysis(record),
            questions=[Question.model_validate(item) for item in record.questions],
        )

    async def rename(self, record: ProjectRecord, name: str) -> None:
        record.name = name
        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        await self._commit("project_rename_failed", project_id=str(record.id))

    async def delete(self, project_id: UUID) -> None:
        try:
            await self.session.exec(
                delete(DocumentRecord).where(
                    col(DocumentRecord.project_id) == project_id
                )
            )
            await self.session.exec(
                delete(ProjectRecord).where(col(ProjectRecord.id) == project_id)
            )
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("project_delete_failed", project_id=str(project_id))
            raise
        await self._commit("project_delete_failed", project_id=str(project_id))

    async def add_document(
        self,
        document_id: UUID,
        project_id: UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
        storage_key: str,
    ) -> DocumentSummary:
        record = DocumentRecord(
            id=document_id,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )
        self.session.add(record)
        await self._commit("document_create_failed", project_id=str(project_id))
        await self.session.refresh(record)
        return document_summary(record)

    async def count_documents(self, project_id: UUID) -> int:
        statement = select(func.count()).where(DocumentRecord.project_id == project_id)
        try:
            return (await self.session.exec(statement)).one()
        except SQLAlchemyError:
            logger.exception("document_count_failed", project_id=str(project_id))
            raise

    async def get_document_record(
        self, project_id: UUID, document_id: UUID
    ) -> DocumentRecord | None:
        try:
            record = await self.session.get(DocumentRecord, document_id)
        except SQLAlchemyError:
            logger.exception("document_get_failed", document_id=str(document_id))
            raise
        if record is None or record.project_id != project_id:
            return None
        return record

    async def save_document(self, record: DocumentRecord) -> DocumentSummary:
        self.session.add(record)
        await self._commit("document_save_failed", document_id=str(record.id))
        await self.session.refresh(record)
        return document_summary(record)

    async def delete_document(self, record: DocumentRecord) -> None:
        try:
            await self.session.delete(record)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("document_delete_failed", document_id=str(record.id))
            raise
        await self._commit("document_delete_failed", document_id=str(record.id))

    async def set_progress(
        self,
        project_id: UUID,
        status: ProjectStatus,
        step: AnalysisStep | None,
        percent: int,
        message: str | None,
        error: str | None = None,
    ) -> None:
        statement = (
            update(ProjectRecord)
            .where(col(ProjectRecord.id) == project_id)
            .values(
                status=status.value,
                step=step.value if step else None,
                percent=percent,
                message=message,
                error=error,
                updated_at=datetime.now(UTC),
            )
        )
        try:
            await self.session.exec(statement)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("project_progress_failed", project_id=str(project_id))
            raise
        await self._commit("project_progress_failed", project_id=str(project_id))

    async def try_start_processing(self, project_id: UUID) -> bool:
        """Mark the project as processing unless a run is already active."""
        statement = (
            update(ProjectRecord)
            .where(col(ProjectRecord.id) == project_id)
            .where(col(ProjectRecord.status) != ProjectStatus.PROCESSING.value)
            .values(
                status=ProjectStatus.PROCESSING.value,
                step=AnalysisStep.READING.value,
                percent=0,
                message="Verarbeitung wird gestartet",
                error=None,
                updated_at=datetime.now(UTC),
            )
        )
        try:
            result = await self.session.exec(statement)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("project_start_failed", project_id=str(project_id))
            raise
        await self._commit("project_start_failed", project_id=str(project_id))
        return result.rowcount == 1

    async def save_analysis(
        self,
        record: ProjectRecord,
        analysis: ProjectAnalysis,
        questions: list[Question],
    ) -> None:
        record.analysis = analysis.model_dump(mode="json")
        record.questions = [question.model_dump(mode="json") for question in questions]
        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        await self._commit("project_analysis_save_failed", project_id=str(record.id))

    async def save_questions(
        self, record: ProjectRecord, questions: list[Question]
    ) -> None:
        record.questions = [question.model_dump(mode="json") for question in questions]
        record.updated_at = datetime.now(UTC)
        self.session.add(record)
        await self._commit("project_questions_save_failed", project_id=str(record.id))

    async def mark_interrupted(self) -> int:
        """Fail runs that were active when the process stopped."""
        statement = (
            update(ProjectRecord)
            .where(col(ProjectRecord.status) == ProjectStatus.PROCESSING.value)
            .values(
                status=ProjectStatus.FAILED.value,
                error="Verarbeitung wurde durch einen Neustart unterbrochen. Bitte erneut starten.",
                updated_at=datetime.now(UTC),
            )
        )
        try:
            result = await self.session.exec(statement)
        except SQLAlchemyError:
            await self.session.rollback()
            logger.exception("project_mark_interrupted_failed")
            raise
        await self._commit("project_mark_interrupted_failed")
        return result.rowcount
