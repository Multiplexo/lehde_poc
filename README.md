# Anfrageprüfung – KI-Prototyp für Ausschreibungs- und Projektunterlagen

Klickbarer Prototyp für die Kalkulation eines GU im Fertigteilbau. Ein Anfragepaket
(bis ca. 20 PDFs/DOCX) wird eingelesen. Der Prototyp erkennt die Dokumenttypen und
Planstände und zieht kalkulationsrelevante Fakten mit Fundstelle heraus. Er zeigt
Widersprüche zwischen den Unterlagen und erzeugt daraus eine Rückfrageliste und
einen Projektsteckbrief für die Übergabe.

Der Prototyp ist ein Gesprächsinstrument, kein Produktivsystem: keine Anmeldung,
keine Rollen, keine Anbindung an Kundensysteme.

## Ablauf

1. **Lesen:** PDFium liest Text mit Positionen. Seiten ohne Textebene (Scans) liest
   Tesseract (Deutsch). DOCX wird absatzweise gelesen.
2. **Klassifizieren:** Das Modell bestimmt Typ, Titel, Planstand und Datum. Bei
   Plänen liest es zusätzlich den Plankopf aus dem Seitenbild.
3. **Extrahieren:** Je Dokument entstehen Aussagen zum Faktenkatalog
   (`backend/app/models/catalog.py`) und Planverweise, jeweils mit wörtlichem Zitat.
4. **Belegen:** Jedes Zitat muss im Dokumenttext gefunden werden; Zahlen müssen
   exakt übereinstimmen. Aussagen ohne Fundstelle werden verworfen und gezählt.
5. **Abgleichen:** Planstände prüft eine feste Regel. Inhaltliche Widersprüche
   findet das Modell, ausschließlich auf Basis der belegten Aussagen.
6. **Folgeaktion:** Jede Abweichung hat einen Empfänger und eine Folgeaktion
   (Rückfrage, Annahme/Vorbehalt, erledigt). Daraus entstehen die Rückfrageliste
   (DOCX/TXT) und der Steckbrief (PDF/DOCX).

Feedback-Button (unten rechts): erzeugt ein Ticket mit Screenshot, URL und
Freitext. Das Modell ordnet es nach Art, Bereich und Duplikaten ein. Optional geht
es an einen Webhook (`FEEDBACK_WEBHOOK_URL`).

## Lokal starten

Voraussetzungen: Docker, uv, Bun und Tesseract mit deutschen Sprachdaten
(`apt install tesseract-ocr tesseract-ocr-deu` bzw. `brew install tesseract tesseract-lang`).

```sh
cp .env.example .env   # POSTGRES_PASSWORD, API_KEY und MODEL setzen
docker compose up -d postgres
uv --directory backend sync
uv --directory backend run alembic upgrade head
uv --directory backend run uvicorn app.main:app --reload
```

In einem zweiten Terminal:

```sh
cd frontend && bun install && bun run dev
```

Danach [die App](http://localhost:5173) öffnen und das Demo-Paket aus
`demo/anfragepaket/` hochladen. `demo/erwartung.md` listet, was gefunden werden
muss. Das Paket lässt sich neu erzeugen mit
`uv --directory backend run python -m scripts.create_demo_package`.

Komplett in Docker: `docker compose --profile app up -d --build`, dann Port 8080.

## Kunden-Look

Farben und Schrift stehen in `frontend/src/index.css` (Abschnitt „Kunden-Theme“),
Name und Produkttitel in `frontend/src/lib/brand.ts` bzw. `VITE_CUSTOMER_NAME`.
Bis das Corporate Design vorliegt, ist ein neutraler Platzhalter gesetzt.

## Datenschutz

Nur Anbieter mit EU-Hosting und Zero-Data-Retention verwenden (z. B. Langdock EU).
Dokumente liegen im Dateisystem unter `DATA_DIR`. Testdaten anderer Mandanten
gehören nicht in diese Instanz.
