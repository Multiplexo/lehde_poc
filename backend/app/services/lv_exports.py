"""Excel and Word exports for the LV and the subcontractor requests per trade."""

from datetime import UTC, datetime
from io import BytesIO

from docx import Document
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.models.lv import LvOrigin, LvPosition
from app.models.onepager import Onepager
from app.models.trades import FALLBACK_TRADE, TRADE_BY_CODE

HEADER_FILL = PatternFill("solid", fgColor="F0B800")
NOTE = "Erstellt mit KI-Prototyp. Positionen und Mengen vor Versand fachlich prüfen."
COLUMNS = [
    ("OZ", 12),
    ("Kurztext", 48),
    ("Langtext", 60),
    ("Menge", 12),
    ("Einheit", 9),
    ("EP (€)", 12),
    ("GP (€)", 14),
    ("Hinweis", 40),
]


def _hint(position: LvPosition) -> str:
    if position.assumption:
        return f"Annahme: {position.assumption}"
    if position.origin == LvOrigin.DRAFT and position.quantity_formula:
        return f"Menge abgeleitet: {position.quantity_formula}"
    if position.origin == LvOrigin.DRAFT:
        return "Aus Funktionalbeschreibung abgeleitet"
    return ""


def _sheet_title(text: str) -> str:
    cleaned = "".join(char for char in text if char not in "[]:*?/\\")
    return cleaned[:31] or "LV"


def lv_xlsx(
    project_name: str, positions: list[LvPosition], trade_code: str | None
) -> bytes:
    """Whole LV (one sheet per trade) or a single trade for a request."""
    workbook = Workbook()
    workbook.remove(workbook.active)  # pyright: ignore[reportArgumentType]
    codes = (
        [trade_code]
        if trade_code
        else list(
            dict.fromkeys(item.trade_code or FALLBACK_TRADE for item in positions)
        )
    )
    for code in codes:
        trade = TRADE_BY_CODE.get(code, TRADE_BY_CODE[FALLBACK_TRADE])
        items = [
            item
            for item in positions
            if item.included and (item.trade_code or FALLBACK_TRADE) == code
        ]
        sheet = workbook.create_sheet(_sheet_title(f"{code} {trade.label}"))
        sheet.append([f"{project_name} – {code} {trade.label}"])
        sheet["A1"].font = Font(bold=True, size=13)
        sheet.append([NOTE])
        sheet.append([])
        sheet.append([name for name, _ in COLUMNS])
        for index, (_, width) in enumerate(COLUMNS, start=1):
            cell = sheet.cell(row=4, column=index)
            cell.font = Font(bold=True)
            cell.fill = HEADER_FILL
            sheet.column_dimensions[get_column_letter(index)].width = width
        for item in items:
            row = sheet.max_row + 1
            sheet.append(
                [
                    item.oz,
                    item.short_text,
                    item.long_text,
                    item.quantity,
                    item.unit,
                    None,
                    f'=IF(AND(ISNUMBER(D{row}),ISNUMBER(F{row})),D{row}*F{row},"")',
                    _hint(item),
                ]
            )
            for column in (2, 3, 8):
                sheet.cell(row=row, column=column).alignment = Alignment(
                    wrap_text=True, vertical="top"
                )
        total_row = sheet.max_row + 1
        sheet.cell(row=total_row, column=6, value="Summe").font = Font(bold=True)
        sheet.cell(
            row=total_row, column=7, value=f"=SUM(G5:G{max(5, total_row - 1)})"
        ).font = Font(bold=True)
        sheet.freeze_panes = "A5"
    if not workbook.sheetnames:
        workbook.create_sheet("LV").append(["Keine Positionen"])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def request_letter_docx(
    onepager: Onepager,
    trade_code: str,
    positions: list[LvPosition],
    recipient: str | None,
) -> bytes:
    """Cover letter for a subcontractor request; the positions go in the Excel file."""
    trade = TRADE_BY_CODE.get(trade_code, TRADE_BY_CODE[FALLBACK_TRADE])
    sections = {section.label: section.value for section in onepager.sections}
    document = Document()
    if recipient:
        document.add_paragraph(recipient)
    document.add_paragraph(f"Datum: {datetime.now(UTC):%d.%m.%Y}")
    document.add_heading(f"Anfrage {trade.label}: {onepager.project_name}", level=1)
    document.add_paragraph(
        "Sehr geehrte Damen und Herren,\n\nfür das unten beschriebene Bauvorhaben "
        f"bitten wir um Ihr Angebot für das Gewerk {trade.label}. Das "
        f"Leistungsverzeichnis mit {len(positions)} Positionen liegt als Excel-Datei "
        "bei; bitte tragen Sie Einheitspreise ein."
    )
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Grid Accent 1"
    for label in ("Bauvorhaben", "Ort", "Termine", "Kunde / Bauherr"):
        value = sections.get(label)
        if value and value != "nicht gefunden":
            cells = table.add_row().cells
            cells[0].text = label
            cells[1].text = value
    assumptions = [item for item in positions if item.assumption]
    if assumptions:
        document.add_paragraph(
            f"{len(assumptions)} Positionen beruhen auf Annahmen und sind im "
            "Leistungsverzeichnis gekennzeichnet. Bitte prüfen Sie Umfang und Mengen."
        )
    document.add_paragraph(
        "Bitte senden Sie uns Ihr Angebot bis zum ____________ zu.\n\n"
        "Mit freundlichen Grüßen"
    )
    run = document.add_paragraph().add_run(NOTE)
    run.font.size = Pt(8)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
