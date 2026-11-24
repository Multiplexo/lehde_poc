import re
import unicodedata

from fastapi import HTTPException, Response, status

from app.models.projects import ProjectStatus
from app.persistence.projects.schema.project import ProjectRecord

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def ensure_idle(project: ProjectRecord) -> None:
    if project.status == ProjectStatus.PROCESSING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Die Analyse läuft gerade. Bitte warten."
        )


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-")[:60] or "projekt"


def download(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def ensure_analysed(project: ProjectRecord) -> None:
    if project.analysis is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Bitte zuerst die Analyse ausführen."
        )
