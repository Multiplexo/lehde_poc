# Anfrageprüfung – KI-Prototyp für Ausschreibungs- und Projektunterlagen

Klickbarer Prototyp für die Kalkulation eines GU im Fertigteilbau. Ein Anfragepaket
(bis ca. 20 PDFs, DOCX oder GAEB-Dateien) wird eingelesen. Er deckt alle Use Cases
aus dem Briefing ab:

- Unterlagen-Abgleich und Fakten-Extraktion mit Fundstelle, Planstand-Prüfung
- LV einlesen (GAEB X83/X84 ohne KI, LV-PDF mit Zitatpflicht) und Gewerken
  zuordnen (StLB-Leistungsbereiche plus „Betonfertigteile, Eigenleistung“)
- LV-Entwurf aus einer Funktionalausschreibung: Mengen nur, wenn sie aus belegten
  Maßen nachrechenbar sind; alles andere ist als Annahme markiert
- Subunternehmer je Gewerk und Region (PLZ-Bereich), Anfragepaket je Gewerk als
  Excel-LV-Auszug und Anschreiben
- Prüf-Agenten für Vertrag/VOB, Brandschutz, Baugrund und Nachträge nach interner
  Checkliste, mit Empfänger und Folgeaktion
- Fragen an die Unterlagen („Was schulden wir eigentlich?“), Antworten nur mit
  belegtem Zitat
- Rückfrageliste (DOCX/TXT) und Projektsteckbrief (PDF/DOCX)

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
6. **LV und Prüfung:** LV-Dokumente werden eingelesen und Gewerken zugeordnet,
   danach laufen die Prüf-Agenten. Der LV-Entwurf aus der Funktionalbeschreibung
   wird auf Knopfdruck abgeleitet.
7. **Folgeaktion:** Jede Abweichung hat einen Empfänger und eine Folgeaktion
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
`demo/anfragepaket/` hochladen (inkl. GAEB-LV und Vertragsentwurf). `demo/erwartung.md` listet, was gefunden werden
muss. Das Paket lässt sich neu erzeugen mit
`uv --directory backend run python -m scripts.create_demo_package`.

Komplett in Docker: `docker compose --profile app up -d --build`, dann Port 8080.

## Kostenlos auf Render

`render.yaml` legt einen kostenlosen Web-Service und eine kostenlose PostgreSQL
in Frankfurt an (Render-Dashboard: New → Blueprint → dieses Repo). Danach im
Dashboard `API_KEY` (Langdock) und `DEMO_PASSWORD` setzen; ohne Passwort startet
der Container nicht. Die ganze App liegt hinter einem Login (Benutzer `lehde`).

- Ein Container (`deploy/render/Dockerfile`): nginx mit Login, Frontend und API.
- Dateien liegen in PostgreSQL (`STORAGE_BACKEND=database`), weil das
  Dateisystem freier Instanzen bei jedem Neustart leer ist.
- Freie Instanzen schlafen bei Inaktivität ein; der erste Aufruf danach dauert
  rund eine Minute. Vor einer Demo die Seite einmal öffnen.
- Die kostenlose Datenbank läuft nach einer begrenzten Zeit ab (Stand der
  Render-Bedingungen im Dashboard prüfen). Für echte Kundendaten einen bezahlten
  Plan und den Auftragsverarbeitungsvertrag von Render prüfen.
- Die KI-Aufrufe kosten weiterhin Langdock-Budget.

## Kunden-Look

Farben und Schrift stehen in `frontend/src/index.css` (Abschnitt „Kunden-Theme“),
Name und Produkttitel in `frontend/src/lib/brand.ts` bzw. `VITE_CUSTOMER_NAME`.
Bis das Corporate Design vorliegt, ist ein neutraler Platzhalter gesetzt.

## Datenschutz

Nur Anbieter mit EU-Hosting und Zero-Data-Retention verwenden (z. B. Langdock EU).
Dokumente liegen im Dateisystem unter `DATA_DIR`. Testdaten anderer Mandanten
gehören nicht in diese Instanz.
