"""Trades (Gewerke) based on the StLB-Bau work sections, plus own precast work."""

from pydantic import BaseModel


class Trade(BaseModel):
    code: str
    label: str
    hint: str
    # Work the precast GU usually performs itself; no subcontractor request.
    own_work: bool = False


TRADE_CATALOG: list[Trade] = [
    Trade(
        code="000",
        label="Baustelleneinrichtung",
        hint="Einrichten, Vorhalten, Räumen, Kran, Container, Bauzaun",
    ),
    Trade(
        code="002",
        label="Erdarbeiten",
        hint="Aushub, Bodenaustausch, Verfüllen, Planum, Entsorgung Boden",
    ),
    Trade(
        code="008",
        label="Wasserhaltung",
        hint="Grundwasserabsenkung, offene Wasserhaltung",
    ),
    Trade(
        code="009",
        label="Entwässerungskanalarbeiten",
        hint="Grundleitungen, Schächte, Kanalanschluss",
    ),
    Trade(code="012", label="Mauerarbeiten", hint="Mauerwerk, Innenwände gemauert"),
    Trade(
        code="013",
        label="Betonarbeiten (Ortbeton)",
        hint="Fundamente, Bodenplatte, Ortbeton, Bewehrung",
    ),
    Trade(
        code="FT",
        label="Betonfertigteile (Eigenleistung)",
        hint="Fertigteilstützen, Binder, Riegel, Wandplatten, Hohlplatten, Treppen, Montage",
        own_work=True,
    ),
    Trade(
        code="016",
        label="Zimmer- und Holzbauarbeiten",
        hint="Holzkonstruktionen, Holzdach",
    ),
    Trade(
        code="017",
        label="Stahlbauarbeiten",
        hint="Stahlträger, Stahlkonstruktion, Bühnen",
    ),
    Trade(
        code="018",
        label="Abdichtungsarbeiten",
        hint="Bauwerksabdichtung, erdberührte Bauteile",
    ),
    Trade(
        code="020", label="Dachdeckungsarbeiten", hint="Dachdeckung geneigter Dächer"
    ),
    Trade(
        code="021",
        label="Dachabdichtungsarbeiten",
        hint="Flachdach, Trapezblech mit Dämmung und Abdichtung, Lichtkuppeln, RWA im Dach",
    ),
    Trade(
        code="022",
        label="Klempnerarbeiten",
        hint="Dachrinnen, Fallrohre, Attikaabdeckungen",
    ),
    Trade(
        code="023", label="Putz- und Stuckarbeiten", hint="Innenputz, Außenputz, WDVS"
    ),
    Trade(
        code="024",
        label="Fliesen- und Plattenarbeiten",
        hint="Fliesen in Sanitär- und Sozialräumen",
    ),
    Trade(
        code="025",
        label="Estricharbeiten",
        hint="Estrich, Hallenboden-Beschichtung, Industrieboden",
    ),
    Trade(code="027", label="Tischlerarbeiten", hint="Innentüren, Einbauten"),
    Trade(
        code="030",
        label="Rollladen- und Torarbeiten",
        hint="Sektionaltore, Rolltore, Sonnenschutz",
    ),
    Trade(
        code="031",
        label="Metallbauarbeiten",
        hint="Außentüren, Geländer, Treppen aus Stahl, Fenster Metall",
    ),
    Trade(
        code="032",
        label="Verglasungsarbeiten",
        hint="Pfosten-Riegel, Lichtbänder, Verglasung",
    ),
    Trade(
        code="034", label="Maler- und Lackierarbeiten", hint="Anstriche, Beschichtungen"
    ),
    Trade(code="036", label="Bodenbelagarbeiten", hint="Linoleum, Teppich, Vinyl"),
    Trade(
        code="038",
        label="Fassadenarbeiten",
        hint="Vorgehängte Fassade, Sandwichpaneele, Kassettenwand",
    ),
    Trade(
        code="039", label="Trockenbauarbeiten", hint="Ständerwände, abgehängte Decken"
    ),
    Trade(
        code="040", label="Heizungsanlagen", hint="Heizung, Wärmepumpe, Hallenheizung"
    ),
    Trade(
        code="042",
        label="Sanitäranlagen",
        hint="Gas, Wasser, Entwässerung im Gebäude, Sanitärobjekte",
    ),
    Trade(
        code="053",
        label="Elektroanlagen",
        hint="Niederspannung, Beleuchtung, Blitzschutz, PV",
    ),
    Trade(
        code="063",
        label="Brandschutzanlagen",
        hint="Sprinkler, Brandmeldeanlage, RWA-Steuerung, Feuerlöscher",
    ),
    Trade(code="069", label="Aufzugsanlagen", hint="Aufzüge"),
    Trade(code="075", label="Raumlufttechnik", hint="Lüftung, Klima"),
    Trade(
        code="080",
        label="Außenanlagen und Verkehrsflächen",
        hint="Pflaster, Asphalt, Stellplätze, Zaun, Begrünung",
    ),
    Trade(
        code="099",
        label="Sonstiges / nicht zuordenbar",
        hint="Allgemeines, Stundenlohn, nicht eindeutig",
    ),
]

TRADE_BY_CODE = {trade.code: trade for trade in TRADE_CATALOG}
FALLBACK_TRADE = "099"
