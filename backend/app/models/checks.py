"""Check agents: an internal checklist, not the text of VOB or DIN standards.

Each check names the recipient and the follow-up action, so no result ends up
without someone acting on it.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.analysis import Recipient
from app.models.documents import DocumentType, SourceRef


class CheckArea(StrEnum):
    CONTRACT = "vertrag"
    FIRE = "brandschutz"
    SOIL = "baugrund"
    CHANGE_ORDER = "nachtrag"


CHECK_AREA_LABELS: dict[CheckArea, str] = {
    CheckArea.CONTRACT: "Vertrag / VOB",
    CheckArea.FIRE: "Brandschutz",
    CheckArea.SOIL: "Baugrund",
    CheckArea.CHANGE_ORDER: "Nachträge",
}

CHECK_AREA_DOCUMENTS: dict[CheckArea, set[DocumentType]] = {
    CheckArea.CONTRACT: {
        DocumentType.VERTRAG,
        DocumentType.BAUBESCHREIBUNG,
        DocumentType.LEISTUNGSVERZEICHNIS,
        DocumentType.SONSTIGES,
    },
    CheckArea.FIRE: {
        DocumentType.BRANDSCHUTZKONZEPT,
        DocumentType.BAUGENEHMIGUNG,
        DocumentType.BAUBESCHREIBUNG,
    },
    CheckArea.SOIL: {
        DocumentType.BODENGUTACHTEN,
        DocumentType.BAUBESCHREIBUNG,
        DocumentType.LEISTUNGSVERZEICHNIS,
    },
    CheckArea.CHANGE_ORDER: {DocumentType.NACHTRAG, DocumentType.VERTRAG},
}


class CheckRule(BaseModel):
    id: str
    area: CheckArea
    title: str
    instruction: str
    recipient: Recipient
    action: str


CHECK_CATALOG: list[CheckRule] = [
    CheckRule(
        id="vob_b",
        area=CheckArea.CONTRACT,
        title="VOB/B als Vertragsgrundlage",
        instruction="Ist die VOB/B vereinbart, und wird sie durch Sonderregelungen eingeschränkt oder abbedungen?",
        recipient=Recipient.KALKULATION,
        action="Abweichungen von der VOB/B in der Angebotsprüfung bewerten",
    ),
    CheckRule(
        id="price_type",
        area=CheckArea.CONTRACT,
        title="Pauschalierung und Vollständigkeitsklausel",
        instruction="Pauschalfestpreis, Mengenrisiko beim Auftragnehmer, Vollständigkeits- oder Komplettheitsklauseln? Bei Funktionalausschreibungen besonders kritisch.",
        recipient=Recipient.KALKULATION,
        action="Mengenrisiko einpreisen oder Vorbehalt ins Angebot",
    ),
    CheckRule(
        id="penalty",
        area=CheckArea.CONTRACT,
        title="Vertragsstrafe",
        instruction="Höhe je Werktag/Kalendertag und Obergrenze. Interne Schwelle: mehr als 0,3 % je Werktag oder mehr als 5 % gesamt ist kritisch.",
        recipient=Recipient.BAUHERR,
        action="Rückfrage oder Vorbehalt zur Vertragsstrafe",
    ),
    CheckRule(
        id="securities",
        area=CheckArea.CONTRACT,
        title="Sicherheiten",
        instruction="Vertragserfüllungs- und Mängelsicherheit (Höhe, Form). Interne Schwelle: mehr als 5 % Vertragserfüllung bzw. 5 % Mängelsicherheit ist ein Hinweis.",
        recipient=Recipient.KALKULATION,
        action="Avalkosten einpreisen",
    ),
    CheckRule(
        id="warranty",
        area=CheckArea.CONTRACT,
        title="Verjährung der Mängelansprüche",
        instruction="Vereinbarte Frist. VOB/B-Regelfrist für Bauwerke sind 4 Jahre; längere Fristen sind ein Hinweis.",
        recipient=Recipient.KALKULATION,
        action="Gewährleistungsrisiko bewerten",
    ),
    CheckRule(
        id="payment",
        area=CheckArea.CONTRACT,
        title="Zahlungsbedingungen",
        instruction="Abschlagszahlungen, Zahlungsfristen, Einbehalte, Skonto.",
        recipient=Recipient.KALKULATION,
        action="Finanzierungskosten prüfen",
    ),
    CheckRule(
        id="deadlines",
        area=CheckArea.CONTRACT,
        title="Vertragsfristen",
        instruction="Verbindliche Ausführungsfristen, Zwischentermine und deren Folgen.",
        recipient=Recipient.BAUHERR,
        action="Termine mit Fertigteilproduktion abstimmen",
    ),
    CheckRule(
        id="fire_resistance",
        area=CheckArea.FIRE,
        title="Feuerwiderstand des Tragwerks",
        instruction="Geforderte Feuerwiderstandsklasse der tragenden Bauteile (z. B. R 30, R 90) und Einheitlichkeit über alle Dokumente.",
        recipient=Recipient.ARCHITEKT,
        action="Fertigteilbemessung auf Feuerwiderstand auslegen",
    ),
    CheckRule(
        id="fire_compartments",
        area=CheckArea.FIRE,
        title="Brandabschnitte und Löschanlagen",
        instruction="Größe der Brandabschnitte, Brandwände, Sprinkler- oder Löschanlagen.",
        recipient=Recipient.ARCHITEKT,
        action="Brandwände und Anlagentechnik im Angebot berücksichtigen",
    ),
    CheckRule(
        id="smoke_extraction",
        area=CheckArea.FIRE,
        title="Rauch- und Wärmeabzug",
        instruction="Geforderte RWA-Flächen und Zuluft.",
        recipient=Recipient.ARCHITEKT,
        action="RWA im Dach und Steuerung anfragen",
    ),
    CheckRule(
        id="fire_access",
        area=CheckArea.FIRE,
        title="Feuerwehrzufahrt und -flächen",
        instruction="Umfahrt, Aufstell- und Bewegungsflächen, Zuständigkeit (GU oder bauseits).",
        recipient=Recipient.BAUHERR,
        action="Leistungsgrenze Außenanlagen klären",
    ),
    CheckRule(
        id="groundwater",
        area=CheckArea.SOIL,
        title="Grundwasser und Gründung",
        instruction="Grundwasser- und Bemessungswasserstand im Verhältnis zur Gründungstiefe; ist eine Wasserhaltung nötig und ausgeschrieben?",
        recipient=Recipient.KALKULATION,
        action="Wasserhaltung einpreisen oder Rückfrage",
    ),
    CheckRule(
        id="contamination",
        area=CheckArea.SOIL,
        title="Belastete Böden",
        instruction="Einstufung (z. B. LAGA Z-Werte), Mengen und wer die Entsorgung trägt.",
        recipient=Recipient.BAUHERR,
        action="Entsorgungskosten klären oder einpreisen",
    ),
    CheckRule(
        id="foundation",
        area=CheckArea.SOIL,
        title="Gründungsempfehlung",
        instruction="Empfohlene Gründungsart und Tragfähigkeit; passt sie zu den vorgesehenen Fertigteil-Köcherfundamenten?",
        recipient=Recipient.KALKULATION,
        action="Fundamentart mit Statik abstimmen",
    ),
    CheckRule(
        id="change_basis",
        area=CheckArea.CHANGE_ORDER,
        title="Anspruchsgrundlage",
        instruction="Ist die Grundlage des Nachtrags genannt (geänderte oder zusätzliche Leistung, Anordnung des Auftraggebers)?",
        recipient=Recipient.KALKULATION,
        action="Anspruchsgrundlage ergänzen",
    ),
    CheckRule(
        id="change_notice",
        area=CheckArea.CHANGE_ORDER,
        title="Ankündigung vor Ausführung",
        instruction="Wurde der Mehrvergütungsanspruch vor Ausführung angekündigt bzw. ist das dokumentiert?",
        recipient=Recipient.KALKULATION,
        action="Ankündigung nachweisen",
    ),
    CheckRule(
        id="change_pricing",
        area=CheckArea.CHANGE_ORDER,
        title="Preisermittlung",
        instruction="Ist der Nachtragspreis nachvollziehbar aus der Urkalkulation oder tatsächlichen Kosten abgeleitet, mit Mengennachweis?",
        recipient=Recipient.KALKULATION,
        action="Preisermittlung belegen",
    ),
]

CHECK_BY_ID = {rule.id: rule for rule in CHECK_CATALOG}


class CheckStatus(StrEnum):
    OK = "ok"
    NOTE = "note"
    CRITICAL = "critical"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class CheckFinding(BaseModel):
    rule_id: str
    area: CheckArea
    title: str
    status: CheckStatus
    finding: str
    sources: list[SourceRef] = Field(default_factory=list)
    recipient: Recipient
    action: str
    question: str | None = None
