from uuid import UUID

from app.models.documents import DOCUMENT_TYPE_LABELS, DocumentType
from app.persistence.projects.schema.project import DocumentRecord


def document_names(records: list[DocumentRecord]) -> dict[UUID, str]:
    """Readable names for questions: the document type, or the file name."""
    type_counts: dict[str, int] = {}
    for record in records:
        if record.doc_type:
            type_counts[record.doc_type] = type_counts.get(record.doc_type, 0) + 1
    names: dict[UUID, str] = {}
    for record in records:
        doc_type = DocumentType(record.doc_type) if record.doc_type else None
        if (
            doc_type is not None
            and doc_type not in {DocumentType.SONSTIGES, DocumentType.PLAN}
            and type_counts[doc_type.value] == 1
        ):
            names[record.id] = DOCUMENT_TYPE_LABELS[doc_type]
        else:
            names[record.id] = record.title or record.filename
    return names
