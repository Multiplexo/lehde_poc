import re
import unicodedata
from typing import Annotated
from uuid import UUID, uuid4

import anyio
import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.config import SettingsDep
from app.dependencies import (
    DocumentRecordDep,
    ProjectRecordDep,
    ProjectRepositoryDep,
)
from app.models.analysis import Discrepancy, DiscrepancyUpdate
from app.models.catalog import FACT_CATALOG, FactDefinition
from app.models.documents import (
    DocumentPages,
    DocumentSummary,
    DocumentUpdate,
    ValueSource,
)
from app.models.onepager import Onepager
from app.models.projects import (
    Project,
    ProjectCreate,
    ProjectListItem,
    ProjectStatus,
    QuestionsUpdate,
)
from app.persistence.projects.project_repository import (
    document_pages,
    document_summary,
    project_analysis,
)
from app.persistence.projects.schema.project import ProjectRecord
from app.services import exports, storage
from app.services.onepager import build_onepager
from app.services.pipeline.conversion import (
    SUPPORTED_CONTENT_TYPES,
    detect_content_type,
)
from app.services.pipeline.questions import sync_discrepancy_question
from app.services.pipeline.runner import (
    document_names,
    refresh_plan_check,
    run_analysis,
)

logger = structlog.get_logger(__name__)

router = APIRouter()

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _ensure_idle(project: ProjectRecord) -> None:
    if project.status == ProjectStatus.PROCESSING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Die Analyse läuft gerade. Bitte warten."
        )


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-")[:60] or "projekt"


def _download(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _load_project(repository: ProjectRepositoryDep, project_id: UUID) -> Project:
    project = await repository.get(project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projekt nicht gefunden")
    return project


@router.get("/catalog", operation_id="get_fact_catalog")
async def get_catalog() -> list[FactDefinition]:
    return FACT_CATALOG


@router.get("", operation_id="list_projects")
async def list_projects(repository: ProjectRepositoryDep) -> list[ProjectListItem]:
    return await repository.list_items()


@router.post("", status_code=status.HTTP_201_CREATED, operation_id="create_project")
async def create_project(
    data: ProjectCreate, repository: ProjectRepositoryDep
) -> Project:
    record = await repository.create(data.name.strip())
    logger.info("project_created", project_id=str(record.id))
    return await _load_project(repository, record.id)


@router.get("/{project_id}", operation_id="get_project")
async def get_project(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Project:
    return await _load_project(repository, project.id)


@router.patch("/{project_id}", operation_id="rename_project")
async def rename_project(
    data: ProjectCreate, project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Project:
    await repository.rename(project, data.name.strip())
    return await _load_project(repository, project.id)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_project",
)
async def delete_project(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> None:
    _ensure_idle(project)
    await repository.delete(project.id)
    await storage.delete_folder(f"projects/{project.id}")
    logger.info("project_deleted", project_id=str(project.id))


@router.post(
    "/{project_id}/documents",
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_documents",
)
async def upload_documents(
    project: ProjectRecordDep,
    repository: ProjectRepositoryDep,
    settings: SettingsDep,
    files: Annotated[list[UploadFile], File()],
) -> list[DocumentSummary]:
    _ensure_idle(project)
    existing = await repository.count_documents(project.id)
    if existing + len(files) > settings.MAX_DOCUMENTS_PER_PROJECT:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Maximal {settings.MAX_DOCUMENTS_PER_PROJECT} Dokumente je Anfragepaket.",
        )
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    prepared: list[tuple[str, str, bytes]] = []
    for upload in files:
        filename = (upload.filename or "dokument").rsplit("/", 1)[-1]
        content = await upload.read(limit + 1)
        if len(content) > limit:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                f"{filename} ist größer als {settings.MAX_UPLOAD_MB} MB.",
            )
        content_type = detect_content_type(content, filename)
        if content_type not in SUPPORTED_CONTENT_TYPES:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"{filename}: nur PDF und DOCX werden unterstützt.",
            )
        prepared.append((filename, content_type, content))

    documents: list[DocumentSummary] = []
    for filename, content_type, content in prepared:
        document_id = uuid4()
        suffix = ".pdf" if content_type == "application/pdf" else ".docx"
        key = f"projects/{project.id}/{document_id}{suffix}"
        await storage.save_file(key, content)
        documents.append(
            await repository.add_document(
                document_id, project.id, filename, content_type, len(content), key
            )
        )
    logger.info(
        "documents_uploaded", project_id=str(project.id), document_count=len(documents)
    )
    return documents


@router.patch("/{project_id}/documents/{document_id}", operation_id="update_document")
async def update_document(
    data: DocumentUpdate,
    project: ProjectRecordDep,
    document: DocumentRecordDep,
    repository: ProjectRepositoryDep,
) -> Project:
    _ensure_idle(project)
    changes = data.model_dump(exclude_unset=True)
    if "doc_type" in changes and data.doc_type is not None:
        document.doc_type = data.doc_type.value
        document.doc_type_source = ValueSource.MANUAL.value
    meta_fields = {"title", "revision", "document_date"} & changes.keys()
    for field in meta_fields:
        setattr(document, field, (changes[field] or "").strip() or None)
    if meta_fields:
        document.meta_source = ValueSource.MANUAL.value
    await repository.save_document(document)

    records = await repository.list_document_records(project.id)
    refreshed = refresh_plan_check(project, records)
    if refreshed is not None:
        analysis, questions = refreshed
        await repository.save_analysis(project, analysis, questions)
    return await _load_project(repository, project.id)


@router.delete(
    "/{project_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_document",
)
async def delete_document(
    project: ProjectRecordDep,
    document: DocumentRecordDep,
    repository: ProjectRepositoryDep,
) -> None:
    _ensure_idle(project)
    await repository.delete_document(document)
    await storage.delete_file(document.storage_key)


@router.get(
    "/{project_id}/documents/{document_id}/file", operation_id="get_document_file"
)
async def get_document_file(document: DocumentRecordDep) -> Response:
    content = await storage.read_file(document.storage_key)
    return Response(
        content=content,
        media_type=document.content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.get(
    "/{project_id}/documents/{document_id}/pages", operation_id="get_document_pages"
)
async def get_document_pages(document: DocumentRecordDep) -> DocumentPages:
    return DocumentPages(document_id=document.id, pages=document_pages(document))


@router.post(
    "/{project_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="start_analysis",
)
async def start_analysis(
    project: ProjectRecordDep,
    repository: ProjectRepositoryDep,
    background_tasks: BackgroundTasks,
) -> Project:
    if await repository.count_documents(project.id) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Bitte zuerst Dokumente hochladen."
        )
    if not await repository.try_start_processing(project.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Die Analyse läuft bereits.")
    background_tasks.add_task(run_analysis, project.id)
    logger.info("analysis_started", project_id=str(project.id))
    return await _load_project(repository, project.id)


@router.patch(
    "/{project_id}/discrepancies/{discrepancy_id}",
    operation_id="update_discrepancy",
)
async def update_discrepancy(
    discrepancy_id: str,
    data: DiscrepancyUpdate,
    project: ProjectRecordDep,
    repository: ProjectRepositoryDep,
) -> Project:
    _ensure_idle(project)
    analysis = project_analysis(project)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Noch keine Analyse vorhanden")
    current = next(
        (item for item in analysis.discrepancies if item.id == discrepancy_id), None
    )
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abweichung nicht gefunden")
    updated: Discrepancy = current.model_copy(
        update=data.model_dump(exclude_unset=True, exclude_none=True)
    )
    analysis.discrepancies = [
        updated if item.id == discrepancy_id else item
        for item in analysis.discrepancies
    ]
    project_detail = await _load_project(repository, project.id)
    questions = sync_discrepancy_question(project_detail.questions, updated)
    await repository.save_analysis(project, analysis, questions)
    return await _load_project(repository, project.id)


@router.put("/{project_id}/questions", operation_id="update_questions")
async def update_questions(
    data: QuestionsUpdate, project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Project:
    _ensure_idle(project)
    await repository.save_questions(project, data.questions)
    return await _load_project(repository, project.id)


async def _onepager(
    project: ProjectRecord, repository: ProjectRepositoryDep
) -> tuple[Onepager, dict[UUID, str]]:
    records = await repository.list_document_records(project.id)
    names = document_names(records)
    onepager = build_onepager(
        project.name,
        project_analysis(project),
        [document_summary(record) for record in records],
        names,
    )
    return onepager, names


@router.get("/{project_id}/onepager", operation_id="get_onepager")
async def get_onepager(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Onepager:
    onepager, _ = await _onepager(project, repository)
    return onepager


@router.get("/{project_id}/exports/onepager.docx", operation_id="export_onepager_docx")
async def export_onepager_docx(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Response:
    onepager, _ = await _onepager(project, repository)
    content = await anyio.to_thread.run_sync(exports.onepager_docx, onepager)
    return _download(
        content, DOCX_MEDIA_TYPE, f"Projektsteckbrief-{_slug(project.name)}.docx"
    )


@router.get("/{project_id}/exports/onepager.pdf", operation_id="export_onepager_pdf")
async def export_onepager_pdf(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Response:
    onepager, _ = await _onepager(project, repository)
    content = await anyio.to_thread.run_sync(exports.onepager_pdf, onepager)
    return _download(
        content, "application/pdf", f"Projektsteckbrief-{_slug(project.name)}.pdf"
    )


@router.get(
    "/{project_id}/exports/questions.docx", operation_id="export_questions_docx"
)
async def export_questions_docx(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Response:
    detail = await _load_project(repository, project.id)
    names = document_names(await repository.list_document_records(project.id))
    content = await anyio.to_thread.run_sync(
        exports.questions_docx, project.name, detail.questions, names
    )
    return _download(
        content, DOCX_MEDIA_TYPE, f"Rueckfragen-{_slug(project.name)}.docx"
    )


@router.get("/{project_id}/exports/questions.txt", operation_id="export_questions_txt")
async def export_questions_txt(
    project: ProjectRecordDep, repository: ProjectRepositoryDep
) -> Response:
    detail = await _load_project(repository, project.id)
    names = document_names(await repository.list_document_records(project.id))
    content = exports.questions_text(project.name, detail.questions, names)
    return _download(
        content.encode("utf-8"),
        "text/plain; charset=utf-8",
        f"Rueckfragen-{_slug(project.name)}.txt",
    )
