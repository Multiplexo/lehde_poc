import csv
import io
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.dependencies import SubcontractorRepositoryDep
from app.models.subcontractors import (
    Subcontractor,
    SubcontractorData,
    SubcontractorImportResult,
)
from app.models.trades import TRADE_BY_CODE, TRADE_CATALOG

logger = structlog.get_logger(__name__)

router = APIRouter()

MAX_CSV_BYTES = 2 * 1024 * 1024
TRADE_BY_LABEL = {trade.label.lower(): trade.code for trade in TRADE_CATALOG}


def _check(data: SubcontractorData) -> SubcontractorData:
    unknown = [code for code in data.trade_codes if code not in TRADE_BY_CODE]
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Unbekannte Gewerke: {', '.join(unknown)}"
        )
    return data


def _trade_codes(raw: str) -> list[str]:
    """Accept codes ("013") or labels ("Erdarbeiten"), separated by , or ;."""
    codes: list[str] = []
    for part in raw.replace(";", ",").split(","):
        value = part.strip()
        code = value if value in TRADE_BY_CODE else TRADE_BY_LABEL.get(value.lower())
        if code and code not in codes:
            codes.append(code)
    return codes


@router.get("", operation_id="list_subcontractors")
async def list_subcontractors(
    repository: SubcontractorRepositoryDep,
) -> list[Subcontractor]:
    return await repository.list_all()


@router.post(
    "", status_code=status.HTTP_201_CREATED, operation_id="create_subcontractor"
)
async def create_subcontractor(
    data: SubcontractorData, repository: SubcontractorRepositoryDep
) -> Subcontractor:
    created = await repository.create_many([_check(data)])
    return created[0]


@router.put("/{subcontractor_id}", operation_id="update_subcontractor")
async def update_subcontractor(
    subcontractor_id: UUID,
    data: SubcontractorData,
    repository: SubcontractorRepositoryDep,
) -> Subcontractor:
    record = await repository.get_record(subcontractor_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subunternehmer nicht gefunden")
    return await repository.update(record, _check(data))


@router.delete(
    "/{subcontractor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_subcontractor",
)
async def delete_subcontractor(
    subcontractor_id: UUID, repository: SubcontractorRepositoryDep
) -> None:
    record = await repository.get_record(subcontractor_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subunternehmer nicht gefunden")
    await repository.delete(record)


@router.post("/import", operation_id="import_subcontractors")
async def import_subcontractors(
    repository: SubcontractorRepositoryDep,
    file: Annotated[UploadFile, File()],
) -> SubcontractorImportResult:
    """CSV with columns name, gewerke, plz, ort, ansprechpartner, email, telefon."""
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Datei zu groß")
    text = content.decode("utf-8-sig", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:2000], delimiters=";,").delimiter
    except csv.Error:
        delimiter = ";"
    rows = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    items: list[SubcontractorData] = []
    skipped: list[str] = []
    for number, row in enumerate(rows, start=2):
        values = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }
        try:
            items.append(
                SubcontractorData(
                    name=values.get("name", ""),
                    trade_codes=_trade_codes(values.get("gewerke", "")),
                    postal_code=values.get("plz") or None,
                    city=values.get("ort") or None,
                    contact=values.get("ansprechpartner") or None,
                    email=values.get("email") or None,
                    phone=values.get("telefon") or None,
                )
            )
        except ValidationError:
            skipped.append(f"Zeile {number}")
    created = await repository.create_many(items) if items else []
    logger.info(
        "subcontractors_imported",
        created_count=len(created),
        skipped_count=len(skipped),
    )
    return SubcontractorImportResult(created=len(created), skipped=skipped)
