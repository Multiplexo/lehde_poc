"""Project one-pager for the handover to technical office and precast department."""

from datetime import UTC, datetime
from uuid import UUID

from app.models.analysis import DiscrepancyStatus, FactStatus, ProjectAnalysis
from app.models.catalog import FACT_BY_KEY
from app.models.documents import DOCUMENT_TYPE_LABELS, DocumentSummary, SourceRef
from app.models.onepager import Onepager, OnepagerDocument, OnepagerSection

# Order of the one-pager sections (US-6): project, client, location, dates,
# precast scope, scope limits; then soil, permit and fire safety for the
# technical office.
ONEPAGER_SECTIONS: list[tuple[str, list[str]]] = [
    ("Bauvorhaben", ["bauvorhaben", "abmessungen", "nutzung", "baukomponenten"]),
    ("Kunde / Bauherr", ["bauherr"]),
    ("Architekt / Planer", ["architekt"]),
    ("Ort", ["ort"]),
    ("Termine", ["termine"]),
    ("Fertigteilumfang", ["fertigteilumfang"]),
    ("Leistungsgrenzen GU / Bauherr", ["leistungsgrenzen"]),
    ("Boden", ["bodenaufbau", "grundwasser", "kontaminationen"]),
    ("Genehmigung", ["genehmigungsauflagen"]),
    ("Brandschutz", ["brandschutz"]),
]


def source_label(source: SourceRef, names: dict[UUID, str]) -> str:
    return f"{names.get(source.document_id, 'Dokument')}, S. {source.page}"


def build_onepager(
    project_name: str,
    analysis: ProjectAnalysis | None,
    documents: list[DocumentSummary],
    names: dict[UUID, str],
) -> Onepager:
    facts = {fact.key: fact for fact in analysis.facts} if analysis else {}
    sections: list[OnepagerSection] = []
    for label, keys in ONEPAGER_SECTIONS:
        values: list[str] = []
        sources: list[str] = []
        for key in keys:
            fact = facts.get(key)
            if fact is None or fact.status == FactStatus.NOT_FOUND or not fact.value:
                continue
            prefix = f"{FACT_BY_KEY[key].label}: " if len(keys) > 1 else ""
            suffix = (
                " (widersprüchlich, siehe offene Punkte)"
                if fact.status == FactStatus.CONFLICT
                else ""
            )
            values.append(prefix + fact.value + suffix)
            for claim in fact.claims:
                label_text = source_label(claim.source, names)
                if label_text not in sources:
                    sources.append(label_text)
        sections.append(
            OnepagerSection(
                label=label,
                value="\n".join(values) if values else "nicht gefunden",
                sources=sources,
            )
        )
    open_points: list[str] = []
    if analysis:
        open_points = [
            f"{item.title}: {item.explanation}"
            for item in analysis.discrepancies
            if item.status != DiscrepancyStatus.DONE
        ]
        open_points += [
            f"Keine Angabe gefunden: {fact.label}"
            for fact in analysis.facts
            if fact.status == FactStatus.NOT_FOUND and FACT_BY_KEY[fact.key].onepager
        ]
    return Onepager(
        project_name=project_name,
        generated_at=datetime.now(UTC),
        summary=analysis.summary.text if analysis and analysis.summary else None,
        sections=sections,
        open_points=open_points,
        documents=[
            OnepagerDocument(
                filename=document.filename,
                doc_type=DOCUMENT_TYPE_LABELS[document.doc_type]
                if document.doc_type
                else "unbekannt",
                revision=document.revision,
                document_date=document.document_date,
            )
            for document in documents
        ],
    )
