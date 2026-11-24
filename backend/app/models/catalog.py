"""Fact catalog v0 from the customer interview; to be extended with the customer."""

from pydantic import BaseModel


class FactDefinition(BaseModel):
    key: str
    label: str
    group: str
    hint: str
    # Facts shown on the project one-pager for the handover.
    onepager: bool = True


FACT_CATALOG: list[FactDefinition] = [
    FactDefinition(
        key="bauvorhaben",
        label="Kern des Bauvorhabens",
        group="Bauvorhaben",
        hint="Was wird gebaut? Art des Gebäudes in einem Satz, z. B. Logistikhalle mit Bürotrakt.",
    ),
    FactDefinition(
        key="abmessungen",
        label="Abmessungen",
        group="Bauvorhaben",
        hint="Länge, Breite, Höhe, Traufhöhe, Achsraster, Flächen (BGF, Hallenfläche) mit Einheit.",
    ),
    FactDefinition(
        key="nutzung",
        label="Nutzung",
        group="Bauvorhaben",
        hint="Vorgesehene Nutzung, z. B. Lager, Produktion, Büro, Sozialräume.",
    ),
    FactDefinition(
        key="baukomponenten",
        label="Baukomponenten",
        group="Bauvorhaben",
        hint="Gebäudeteile wie Halle, Bürotrakt, Anbau, Vordach, Geschosse.",
    ),
    FactDefinition(
        key="fertigteilumfang",
        label="Fertigteilumfang",
        group="Bauvorhaben",
        hint="Vorgesehene Fertigteile und Konstruktion: Stützen, Binder, Wandplatten, Decken, Stückzahlen, Tragwerk.",
    ),
    FactDefinition(
        key="bauherr",
        label="Bauherr",
        group="Beteiligte",
        hint="Name des Bauherrn oder Auftraggebers.",
    ),
    FactDefinition(
        key="architekt",
        label="Architekt / Planer",
        group="Beteiligte",
        hint="Entwurfsverfasser, Architekturbüro, Fachplaner.",
    ),
    FactDefinition(
        key="ort",
        label="Ort / Grundstück",
        group="Beteiligte",
        hint="Adresse, Gemarkung, Flurstück des Baugrundstücks.",
    ),
    FactDefinition(
        key="termine",
        label="Terminvorstellungen",
        group="Termine",
        hint="Angebotsabgabe, Baubeginn, Fertigstellung, Zwischentermine des Bauherrn.",
    ),
    FactDefinition(
        key="bodenaufbau",
        label="Bodenaufbau",
        group="Boden",
        hint="Schichtenfolge, Tragfähigkeit, Gründungsempfehlung.",
    ),
    FactDefinition(
        key="grundwasser",
        label="Grundwasserstand",
        group="Boden",
        hint="Gemessener Grundwasserstand und Bemessungswasserstand mit Bezug (m u. GOK oder m NHN).",
    ),
    FactDefinition(
        key="kontaminationen",
        label="Kontaminationen",
        group="Boden",
        hint="Belastete Böden, Altlasten, Einstufung (z. B. LAGA Z-Werte), Entsorgungshinweise.",
    ),
    FactDefinition(
        key="genehmigungsauflagen",
        label="Auflagen der Baugenehmigung",
        group="Genehmigung",
        hint="Nebenbestimmungen und Auflagen der Baugenehmigung, die Kosten oder Ablauf beeinflussen.",
    ),
    FactDefinition(
        key="brandschutz",
        label="Brandschutz-Kernanforderungen",
        group="Brandschutz",
        hint="Feuerwiderstand des Tragwerks, Brandabschnitte, Sprinkler, Rauchabzug, Feuerwehrzufahrt.",
    ),
    FactDefinition(
        key="brandschutz_planstand",
        label="Brandschutz: referenzierter Planstand",
        group="Brandschutz",
        hint="Auf welche Pläne und welchen Planstand (Index, Datum) sich das Brandschutzkonzept bezieht.",
        onepager=False,
    ),
    FactDefinition(
        key="leistungsgrenzen",
        label="Leistungsgrenzen GU / Bauherr",
        group="Leistungsgrenzen",
        hint="Welche Leistungen erbringt der GU, welche der Bauherr oder Dritte (bauseits, nicht enthalten).",
    ),
]

FACT_KEYS = {definition.key for definition in FACT_CATALOG}
FACT_BY_KEY = {definition.key: definition for definition in FACT_CATALOG}
