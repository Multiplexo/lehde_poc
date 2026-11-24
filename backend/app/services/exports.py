"""DOCX, PDF and text exports for the question list and the one-pager."""

from io import BytesIO
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.analysis import Question, Recipient
from app.models.onepager import Onepager
from app.services.onepager import source_label

RECIPIENT_LABELS = {
    Recipient.ARCHITEKT: "Architekt / Planer",
    Recipient.BAUHERR: "Bauherr",
    Recipient.KALKULATION: "Kalkulation (intern)",
}
PROTOTYPE_NOTE = "Erstellt mit KI-Prototyp. Inhalte vor Versand fachlich prüfen."


def _grouped(questions: list[Question]) -> list[tuple[Recipient, list[Question]]]:
    included = [question for question in questions if question.included]
    return [
        (recipient, [q for q in included if q.recipient == recipient])
        for recipient in Recipient
        if any(q.recipient == recipient for q in included)
    ]


def questions_text(
    project_name: str, questions: list[Question], names: dict[UUID, str]
) -> str:
    lines = [f"Rückfragen zum Anfragepaket: {project_name}", ""]
    number = 0
    for recipient, items in _grouped(questions):
        lines += [f"An: {RECIPIENT_LABELS[recipient]}", ""]
        for question in items:
            number += 1
            lines.append(f"{number}. {question.text}")
            sources = "; ".join(
                source_label(source, names) for source in question.sources
            )
            if sources:
                lines.append(f"   Quelle: {sources}")
            lines.append("")
    lines.append(PROTOTYPE_NOTE)
    return "\n".join(lines)


def questions_docx(
    project_name: str, questions: list[Question], names: dict[UUID, str]
) -> bytes:
    document = Document()
    document.add_heading(f"Rückfragen: {project_name}", level=1)
    number = 0
    for recipient, items in _grouped(questions):
        document.add_heading(f"An: {RECIPIENT_LABELS[recipient]}", level=2)
        for question in items:
            number += 1
            paragraph = document.add_paragraph()
            paragraph.add_run(f"{number}. ").bold = True
            paragraph.add_run(question.text)
            sources = "; ".join(
                source_label(source, names) for source in question.sources
            )
            if sources:
                note = document.add_paragraph()
                run = note.add_run(f"Quelle: {sources}")
                run.italic = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x55, 0x60, 0x6B)
    footer = document.add_paragraph()
    footer_run = footer.add_run(PROTOTYPE_NOTE)
    footer_run.font.size = Pt(8)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def onepager_docx(onepager: Onepager) -> bytes:
    document = Document()
    document.add_heading(f"Projektsteckbrief: {onepager.project_name}", level=1)
    if onepager.summary:
        document.add_paragraph(onepager.summary)
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Grid Accent 1"
    for section in onepager.sections:
        cells = table.add_row().cells
        cells[0].text = section.label
        cells[1].text = section.value
        if section.sources:
            run = (
                cells[1]
                .add_paragraph()
                .add_run("Quelle: " + "; ".join(section.sources))
            )
            run.italic = True
            run.font.size = Pt(8)
    document.add_heading("Offene Punkte", level=2)
    if not onepager.open_points:
        document.add_paragraph("Keine")
    for point in onepager.open_points:
        document.add_paragraph(point, style="List Bullet")
    document.add_heading("Unterlagen", level=2)
    for item in onepager.documents:
        details = ", ".join(
            value
            for value in (item.doc_type, item.revision, item.document_date)
            if value
        )
        document.add_paragraph(f"{item.filename} ({details})", style="List Bullet")
    footer = document.add_paragraph()
    run = footer.add_run(
        f"Stand {onepager.generated_at:%d.%m.%Y %H:%M} UTC. {PROTOTYPE_NOTE}"
    )
    run.font.size = Pt(8)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _paragraph(text: str, style: Any) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def onepager_pdf(onepager: Onepager) -> bytes:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    label = ParagraphStyle("label", parent=body, fontName="Helvetica-Bold")
    source = ParagraphStyle(
        "source",
        parent=body,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#55606b"),
    )
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Projektsteckbrief {onepager.project_name}",
    )
    story: list = [
        _paragraph(f"Projektsteckbrief: {onepager.project_name}", styles["Heading1"])
    ]
    if onepager.summary:
        story += [_paragraph(onepager.summary, body), Spacer(1, 4 * mm)]
    rows = []
    for section in onepager.sections:
        cell = [_paragraph(section.value, body)]
        if section.sources:
            cell.append(_paragraph("Quelle: " + "; ".join(section.sources), source))
        rows.append([_paragraph(section.label, label), cell])
    table = Table(rows, colWidths=[45 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dde5")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story += [table, Spacer(1, 4 * mm), _paragraph("Offene Punkte", styles["Heading3"])]
    story += [_paragraph(f"• {point}", body) for point in onepager.open_points] or [
        _paragraph("Keine", body)
    ]
    story += [Spacer(1, 3 * mm), _paragraph("Unterlagen", styles["Heading3"])]
    for item in onepager.documents:
        details = ", ".join(
            value
            for value in (item.doc_type, item.revision, item.document_date)
            if value
        )
        story.append(_paragraph(f"• {item.filename} ({details})", body))
    story += [
        Spacer(1, 4 * mm),
        _paragraph(
            f"Stand {onepager.generated_at:%d.%m.%Y %H:%M} UTC. {PROTOTYPE_NOTE}",
            source,
        ),
    ]
    document.build(story)
    return buffer.getvalue()
