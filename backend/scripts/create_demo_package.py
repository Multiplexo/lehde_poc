"""Create a fictitious inquiry package with known contradictions for demos.

All names, addresses and figures are invented. Run from the backend folder:

    uv run python -m scripts.create_demo_package
"""

from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from rich.console import Console

OUTPUT = Path(__file__).resolve().parents[2] / "demo" / "anfragepaket"
console = Console()

STYLES = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=STYLES["BodyText"], fontSize=10.5, leading=14.5)
HEADING = STYLES["Heading2"]
TITLE = STYLES["Title"]

PROJECT = "Neubau Logistikhalle mit Bürotrakt, Gewerbepark Nord, Am Kanal 12, 39999 Musterstadt"


def text_pdf(blocks: list[tuple[str, str]], title: str, header: str) -> bytes:
    buffer = BytesIO()

    def decorate(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(20 * mm, 287 * mm, header)
        canvas.drawRightString(190 * mm, 10 * mm, f"Seite {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, title=title
    )
    story: list = [Paragraph(title, TITLE), Spacer(1, 4 * mm)]
    for kind, text in blocks:
        if kind == "h":
            story.append(Paragraph(text, HEADING))
        elif kind == "page":
            story.append(Spacer(1, 230 * mm))
        else:
            story.append(Paragraph(text, BODY))
            story.append(Spacer(1, 2 * mm))
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()


def anschreiben() -> bytes:
    return text_pdf(
        [
            ("p", "Muster Logistik GmbH · Industriestraße 4 · 39999 Musterstadt"),
            ("p", "Datum: 03.11.2026"),
            ("h", f"Anfrage Generalunternehmerleistung: {PROJECT}"),
            (
                "p",
                (
                    "Sehr geehrte Damen und Herren, wir bitten um ein Angebot für die "
                    "schlüsselfertige Errichtung unserer neuen Logistikhalle mit Bürotrakt "
                    "auf Grundlage der beigefügten Unterlagen."
                ),
            ),
            ("p", "Abgabe des Angebots bis spätestens 18.12.2026, 12:00 Uhr."),
            (
                "p",
                (
                    "Der Baubeginn ist für April 2027 vorgesehen, die Übergabe der Halle "
                    "an den Nutzer muss bis zum 30.11.2027 erfolgen."
                ),
            ),
            (
                "p",
                (
                    "Der Leistungsumfang des Generalunternehmers umfasst auch die "
                    "Erdarbeiten einschließlich Bodenaustausch sowie die Bodenplatte. "
                    "Die Außenanlagen werden bauseits separat vergeben."
                ),
            ),
            (
                "p",
                (
                    "Ansprechpartner Bauherr: Herr Beispiel, Projektleitung. "
                    "Mit freundlichen Grüßen, Muster Logistik GmbH"
                ),
            ),
        ],
        "Anfrage Generalunternehmerleistung",
        "Muster Logistik GmbH – Anschreiben",
    )


def baubeschreibung() -> bytes:
    return text_pdf(
        [
            ("p", f"Bauvorhaben: {PROJECT}"),
            (
                "p",
                "Bauherr: Muster Logistik GmbH, Industriestraße 4, 39999 Musterstadt",
            ),
            (
                "p",
                (
                    "Entwurfsverfasser: Planungsbüro Beispiel Architekten PartGmbB, "
                    "Lindenallee 7, 39998 Beispielstadt"
                ),
            ),
            ("p", "Stand: 15.09.2026, Version 2"),
            ("h", "1. Allgemeines"),
            (
                "p",
                (
                    "Errichtet wird eine eingeschossige Logistikhalle mit einem "
                    "angebauten, zweigeschossigen Bürotrakt. Die Halle dient als "
                    "Lagerhalle mit Kommissionierung. Eine Produktion ist nicht vorgesehen."
                ),
            ),
            (
                "p",
                (
                    "Die Halle hat die Außenabmessungen 60,00 m x 25,00 m bei einer "
                    "Traufhöhe von 9,00 m. Der Bürotrakt hat die Abmessungen "
                    "25,00 m x 12,50 m."
                ),
            ),
            (
                "p",
                (
                    "Grundlage dieser Baubeschreibung sind die Pläne A-101 Grundriss EG "
                    "Index C und A-201 Schnitt A-A Index B."
                ),
            ),
            ("h", "2. Tragwerk und Fertigteile"),
            (
                "p",
                (
                    "Das Tragwerk der Halle wird aus Stahlbetonfertigteilen hergestellt: "
                    "22 Fertigteilstützen in Köcherfundamenten, 11 Spannbetonbinder mit "
                    "25,00 m Spannweite und Achsraster 6,00 m. Die Außenwände werden aus "
                    "Sandwich-Wandplatten d = 30 cm hergestellt."
                ),
            ),
            (
                "p",
                (
                    "Der Bürotrakt erhält Fertigteildecken als Hohlplatten und "
                    "Fertigteilstützen; die Treppenläufe werden als Fertigteile geliefert."
                ),
            ),
            ("h", "3. Gründung"),
            (
                "p",
                (
                    "Die Gründung erfolgt über Einzelfundamente nach Vorgabe der Statik. "
                    "Grundwasser ist nach derzeitigem Kenntnisstand im Gründungsbereich "
                    "nicht zu erwarten; eine Wasserhaltung ist nicht einzukalkulieren."
                ),
            ),
            ("page", ""),
            ("h", "4. Termine"),
            (
                "p",
                (
                    "Baubeginn ist im März 2027 vorgesehen. Die Fertigstellung der "
                    "Gesamtmaßnahme ist für den 30.11.2027 geplant."
                ),
            ),
            ("h", "5. Leistungsgrenzen"),
            (
                "p",
                (
                    "Die Erdarbeiten bis zur Herstellung des Planums werden bauseits durch "
                    "den Bauherrn erbracht. Ab Planum beginnt die Leistung des "
                    "Generalunternehmers."
                ),
            ),
            (
                "p",
                (
                    "Nicht enthalten sind Außenanlagen, Regalanlagen und die "
                    "Fördertechnik des Nutzers."
                ),
            ),
            ("h", "6. Brandschutz"),
            (
                "p",
                (
                    "Der Brandschutz ist gemäß Brandschutzkonzept umzusetzen. Die "
                    "tragenden Bauteile der Halle sind in R 30 auszuführen."
                ),
            ),
        ],
        "Baubeschreibung",
        "Planungsbüro Beispiel Architekten – Baubeschreibung",
    )


def brandschutzkonzept() -> bytes:
    return text_pdf(
        [
            ("p", f"Objekt: {PROJECT}"),
            ("p", "Verfasser: Ingenieurbüro Brandschutz Muster, Stand 20.07.2026"),
            ("h", "1. Grundlagen"),
            (
                "p",
                (
                    "Grundlage dieses Brandschutzkonzepts sind der Grundriss EG, "
                    "Plan-Nr. A-101, Index B vom 14.07.2026 sowie der Schnitt A-A, "
                    "Plan-Nr. A-201, Index B."
                ),
            ),
            ("h", "2. Gebäudebeschreibung"),
            (
                "p",
                (
                    "Die Halle hat eine Grundfläche von 1.440 m² (60,00 m x 24,00 m). "
                    "Die Nutzung erfolgt als Lagerhalle ohne Produktion."
                ),
            ),
            ("h", "3. Anforderungen"),
            (
                "p",
                (
                    "Die Halle bildet einen Brandabschnitt mit weniger als 1.800 m². Eine "
                    "Sprinkleranlage ist nicht erforderlich."
                ),
            ),
            (
                "p",
                (
                    "Die tragenden und aussteifenden Bauteile sind feuerhemmend (R 30) "
                    "auszuführen."
                ),
            ),
            (
                "p",
                (
                    "Es sind Rauch- und Wärmeabzugsgeräte mit einer aerodynamisch "
                    "wirksamen Fläche von mindestens 2 % der Dachfläche vorzusehen."
                ),
            ),
            (
                "p",
                (
                    "Eine Feuerwehrumfahrt mit einer Breite von mindestens 3,50 m ist "
                    "um die Halle herzustellen."
                ),
            ),
        ],
        "Brandschutzkonzept",
        "Ingenieurbüro Brandschutz Muster – Brandschutzkonzept",
    )


def bodengutachten() -> bytes:
    return text_pdf(
        [
            ("p", f"Projekt: {PROJECT}"),
            ("p", "Gutachter: Baugrundbüro Beispiel GmbH, Bericht vom 28.05.2026"),
            ("h", "1. Bodenaufbau"),
            (
                "p",
                (
                    "Unter einer Auffüllung mit einer Mächtigkeit von 0,6 m bis 1,2 m "
                    "folgen Sande bis ca. 4,0 m unter Geländeoberkante (GOK), darunter "
                    "Geschiebemergel."
                ),
            ),
            (
                "p",
                (
                    "Die Gründung kann über Einzelfundamente in den Sanden erfolgen. Die "
                    "Auffüllung ist im Bereich der Fundamente vollständig auszutauschen."
                ),
            ),
            ("h", "2. Grundwasser"),
            (
                "p",
                (
                    "Grundwasser wurde bei den Bohrungen in einer Tiefe von 2,40 m unter "
                    "GOK angetroffen. Der Bemessungswasserstand liegt bei 1,50 m unter "
                    "GOK. Für Fundamente mit einer Gründungssohle tiefer als 1,50 m unter "
                    "GOK ist eine Wasserhaltung vorzusehen."
                ),
            ),
            ("h", "3. Umwelttechnische Untersuchung"),
            (
                "p",
                (
                    "Die Auffüllung ist aufgrund erhöhter PAK-Gehalte als Z 2 nach LAGA "
                    "einzustufen. Ausgehobenes Material der Auffüllung ist getrennt zu "
                    "lagern und kostenpflichtig zu entsorgen."
                ),
            ),
        ],
        "Geotechnischer Bericht",
        "Baugrundbüro Beispiel GmbH – Baugrundgutachten",
    )


def baugenehmigung_scan() -> bytes:
    """A permit as image-only PDF, so the demo shows OCR."""
    content = text_pdf(
        [
            ("p", "Stadt Musterstadt · Bauordnungsamt"),
            ("p", "Bescheid vom 02.10.2026, Aktenzeichen 63-BG-2026-0815"),
            ("h", "Baugenehmigung"),
            (
                "p",
                (
                    "Für das Vorhaben Neubau einer Lager- und Produktionshalle mit "
                    "Bürotrakt auf dem Grundstück Am Kanal 12, Gemarkung Musterstadt, "
                    "Flur 3, Flurstück 112, wird die Baugenehmigung erteilt."
                ),
            ),
            ("h", "Nebenbestimmungen"),
            (
                "p",
                (
                    "1. Das Brandschutzkonzept vom 20.07.2026 ist Bestandteil dieser "
                    "Genehmigung und vollständig umzusetzen."
                ),
            ),
            (
                "p",
                (
                    "2. Vor Baubeginn ist ein von einem Prüfingenieur geprüfter "
                    "Standsicherheitsnachweis vorzulegen."
                ),
            ),
            ("p", "3. Auf dem Grundstück sind 24 Pkw-Stellplätze herzustellen."),
            (
                "p",
                (
                    "4. Das Niederschlagswasser der Dachflächen ist auf dem Grundstück "
                    "zu versickern."
                ),
            ),
            (
                "p",
                (
                    "5. Lärmintensive Bauarbeiten sind nur werktags von 7:00 bis "
                    "20:00 Uhr zulässig."
                ),
            ),
        ],
        "Bescheid",
        "Stadt Musterstadt – Bauordnungsamt",
    )
    pdf = pdfium.PdfDocument(content)
    images: list[Image.Image] = []
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=2)
            images.append(bitmap.to_pil().convert("L").rotate(0.4, fillcolor=255))
            bitmap.close()
            page.close()
    finally:
        pdf.close()
    buffer = BytesIO()
    images[0].save(
        buffer, format="PDF", save_all=True, append_images=images[1:], resolution=144
    )
    return buffer.getvalue()


def plan_sheet(
    canvas: Canvas, number: str, title: str, revision: str, date: str, drawing: str
) -> None:
    width, height = landscape(A3)
    canvas.setLineWidth(1.2)
    canvas.rect(10 * mm, 10 * mm, width - 20 * mm, height - 20 * mm)
    if drawing == "grundriss":
        x, y, w, h = 60 * mm, 80 * mm, 240 * mm, 100 * mm
        canvas.rect(x, y, w, h)
        canvas.rect(x + w, y, 50 * mm, 50 * mm)
        for axis in range(11):
            canvas.circle(x + axis * w / 10, y + h, 1.5 * mm, fill=1)
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(x + w / 2, y - 12 * mm, "60,00")
        canvas.drawString(x - 22 * mm, y + h / 2, "25,00")
        canvas.drawCentredString(x + w / 2, y + h / 2, "Lager / Kommissionierung")
        canvas.drawCentredString(x + w + 25 * mm, y + 25 * mm, "Büro")
    elif drawing == "schnitt":
        canvas.line(60 * mm, 80 * mm, 300 * mm, 80 * mm)
        canvas.line(60 * mm, 80 * mm, 60 * mm, 170 * mm)
        canvas.line(300 * mm, 80 * mm, 300 * mm, 170 * mm)
        canvas.line(60 * mm, 170 * mm, 180 * mm, 185 * mm)
        canvas.line(180 * mm, 185 * mm, 300 * mm, 170 * mm)
        canvas.setFont("Helvetica", 12)
        canvas.drawString(305 * mm, 170 * mm, "Traufe +9,00")
    else:
        canvas.rect(40 * mm, 80 * mm, 300 * mm, 90 * mm)
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(190 * mm, 125 * mm, "Ansicht Nord")
    box_x, box_y = width - 130 * mm, 10 * mm
    canvas.rect(box_x, box_y, 120 * mm, 55 * mm)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(
        box_x + 4 * mm, box_y + 48 * mm, "Planungsbüro Beispiel Architekten"
    )
    canvas.setFont("Helvetica", 9)
    canvas.drawString(box_x + 4 * mm, box_y + 41 * mm, "Bauherr: Muster Logistik GmbH")
    canvas.drawString(
        box_x + 4 * mm, box_y + 35 * mm, "Neubau Logistikhalle mit Bürotrakt"
    )
    canvas.drawString(box_x + 4 * mm, box_y + 27 * mm, f"Planinhalt: {title}")
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(box_x + 4 * mm, box_y + 18 * mm, f"Plan-Nr. {number}")
    canvas.drawString(box_x + 60 * mm, box_y + 18 * mm, f"Index {revision}")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(box_x + 4 * mm, box_y + 9 * mm, f"Datum: {date}   Maßstab 1:200")


def plaene() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=landscape(A3))
    canvas.setTitle("Plansatz Entwurf")
    sheets = [
        ("A-101", "Grundriss EG", "C", "12.09.2026", "grundriss"),
        ("A-201", "Schnitt A-A", "B", "14.07.2026", "schnitt"),
        ("A-301", "Ansichten", "A", "14.07.2026", "ansicht"),
    ]
    for sheet in sheets:
        plan_sheet(canvas, *sheet)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def vertragsentwurf() -> bytes:
    return text_pdf(
        [
            ("p", f"Bauvorhaben: {PROJECT}"),
            ("p", "Auftraggeber: Muster Logistik GmbH · Entwurf vom 01.11.2026"),
            ("h", "§ 1 Vertragsgrundlagen"),
            (
                "p",
                (
                    "Vertragsbestandteile sind dieser Vertrag, die Baubeschreibung vom "
                    "15.09.2026 und die VOB/B in der bei Vertragsschluss gültigen Fassung, "
                    "soweit in diesem Vertrag nichts Abweichendes geregelt ist."
                ),
            ),
            ("h", "§ 2 Vergütung"),
            (
                "p",
                (
                    "Die Leistungen werden zu einem Pauschalfestpreis vergütet. Der "
                    "Auftragnehmer hat sich über alle Umstände der Ausführung informiert; "
                    "Leistungen, die zur vollständigen und funktionsfähigen Herstellung "
                    "erforderlich sind, sind mit dem Pauschalpreis abgegolten, auch wenn "
                    "sie in den Unterlagen nicht gesondert beschrieben sind."
                ),
            ),
            ("h", "§ 3 Ausführungsfristen und Vertragsstrafe"),
            (
                "p",
                (
                    "Die Fertigstellung hat bis zum 30.11.2027 zu erfolgen. Bei "
                    "Überschreitung zahlt der Auftragnehmer eine Vertragsstrafe von "
                    "0,5 % der Netto-Auftragssumme je Werktag, insgesamt höchstens 10 % "
                    "der Netto-Auftragssumme."
                ),
            ),
            ("h", "§ 4 Sicherheiten"),
            (
                "p",
                (
                    "Der Auftragnehmer stellt eine Vertragserfüllungsbürgschaft in Höhe "
                    "von 10 % der Netto-Auftragssumme. Als Sicherheit für Mängelansprüche "
                    "werden 5 % der Schlussrechnungssumme einbehalten."
                ),
            ),
            ("h", "§ 5 Mängelansprüche"),
            (
                "p",
                (
                    "Die Verjährungsfrist für Mängelansprüche beträgt 5 Jahre und "
                    "6 Wochen ab Abnahme."
                ),
            ),
            ("h", "§ 6 Zahlung"),
            (
                "p",
                (
                    "Abschlagszahlungen werden nach Zahlungsplan geleistet und sind "
                    "30 Kalendertage nach Eingang der prüffähigen Rechnung fällig."
                ),
            ),
        ],
        "Generalunternehmervertrag (Entwurf)",
        "Muster Logistik GmbH – Vertragsentwurf",
    )


LV_ITEMS = [
    (
        "01",
        "Baustelleneinrichtung",
        [
            ("0010", "Baustelleneinrichtung einrichten und räumen", 1, "psch"),
            ("0020", "Turmdrehkran vorhalten, Standzeit", 20, "Wo"),
        ],
    ),
    (
        "02",
        "Erdarbeiten",
        [
            ("0010", "Oberboden abtragen und seitlich lagern, d = 30 cm", 2400, "m2"),
            ("0020", "Bodenaushub für Einzelfundamente, Bodenklasse 3-4", 380, "m3"),
            ("0030", "Auffüllung Z 2 (PAK) laden, abfahren und entsorgen", 450, "t"),
            ("0040", "Planum herstellen, Verdichtung Ev2 >= 45 MN/m2", 1800, "m2"),
        ],
    ),
    (
        "03",
        "Betonarbeiten",
        [
            ("0010", "Köcherfundament Ortbeton C25/30 für Fertigteilstützen", 22, "St"),
            ("0020", "Bodenplatte Stahlbeton C30/37, d = 20 cm, Halle", 1500, "m2"),
        ],
    ),
    (
        "04",
        "Betonfertigteile",
        [
            (
                "0010",
                "Fertigteilstütze 50/50 cm, h = 9,00 m, liefern und montieren",
                22,
                "St",
            ),
            ("0020", "Spannbetonbinder L = 25,00 m, liefern und montieren", 11, "St"),
            (
                "0030",
                "Sandwich-Wandplatte d = 30 cm, liefern und montieren",
                1520,
                "m2",
            ),
            ("0040", "Hohlplattendecke d = 26,5 cm Bürotrakt", 312, "m2"),
        ],
    ),
    (
        "05",
        "Dach",
        [
            ("0010", "Trapezblech-Dach mit Dämmung und Abdichtung", 1500, "m2"),
            ("0020", "RWA-Lichtkuppel 1,20 x 1,80 m mit Öffner", 18, "St"),
        ],
    ),
    (
        "06",
        "Tore und Türen",
        [
            ("0010", "Sektionaltor 4,00 x 4,50 m, elektrisch", 4, "St"),
        ],
    ),
]


def gaeb_lv() -> bytes:
    """GAEB DA XML 3.3 (X83) with categories and items."""
    categories = []
    for number, label, items in LV_ITEMS:
        item_xml = "".join(
            f'<Item RNoPart="{oz}"><Qty>{qty}</Qty><QU>{unit}</QU><Description>'
            f"<CompleteText><DetailTxt><Text><p><span>{text}. Ausführung nach "
            f"Baubeschreibung.</span></p></Text></DetailTxt><OutlineText><OutlTxt>"
            f"<TextOutlTxt><p><span>{text}</span></p></TextOutlTxt></OutlTxt>"
            f"</OutlineText></CompleteText></Description></Item>"
            for oz, text, qty, unit in items
        )
        categories.append(
            f'<BoQCtgy RNoPart="{number}"><LblTx><p><span>{label}</span></p></LblTx>'
            f"<BoQBody><Itemlist>{item_xml}</Itemlist></BoQBody></BoQCtgy>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<GAEB xmlns="http://www.gaeb.de/GAEB_DA_XML/DA83/3.3">'
        "<GAEBInfo><Version>3.3</Version></GAEBInfo>"
        "<Award><DP>83</DP><BoQ><BoQInfo><Name>LV Rohbau Logistikhalle</Name></BoQInfo>"
        f"<BoQBody>{''.join(categories)}</BoQBody></BoQ></Award></GAEB>"
    )
    return xml.encode("utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = {
        "01_Anschreiben_Anfrage.pdf": anschreiben(),
        "02_Baubeschreibung.pdf": baubeschreibung(),
        "03_Brandschutzkonzept.pdf": brandschutzkonzept(),
        "04_Bodengutachten.pdf": bodengutachten(),
        "05_Baugenehmigung_Scan.pdf": baugenehmigung_scan(),
        "06_Plaene_Entwurf.pdf": plaene(),
        "07_LV_Rohbau.x83": gaeb_lv(),
        "08_Vertragsentwurf.pdf": vertragsentwurf(),
    }
    for name, content in files.items():
        (OUTPUT / name).write_bytes(content)
        console.print(f"[green]erstellt[/green] {name} ({len(content) // 1024} KB)")


if __name__ == "__main__":
    main()
