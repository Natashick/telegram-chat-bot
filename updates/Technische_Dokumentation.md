## Technische Dokumentation

Diese Dokumentation beschreibt Architektur, Komponenten und Datenflüsse des Bots. Sie dient als Grundlage für Wartung und Erweiterungen durch zukünftige Entwicklerinnen und Entwickler.

### 1. Überblick
- Zweck: Fragen zu Automotive-Cybersecurity (z. B. ISO/SAE 21434, UN R155) beantworten, basierend auf lokal geparsten PDFs.
- Grundprinzip: Lokale Verarbeitung und Vektorsuche. Es werden keine Dokumentinhalte an externe Cloud-APIs gesendet.
- Schutz: Logging-Filter zensiert sensible Daten; Antworten und Screenshots werden mit `protect_content=True` gesendet; Link-Vorschauen sind deaktiviert.

### 2. Architektur (High-Level)
- Entry-/Web-Layer: `bot.py` (FastAPI + Telegram-Webhook, Lifespan, Healthcheck-Pfad), Gunicorn/Uvicorn als ASGI-Server.
- Interaktions-Layer: `handlers1.py` (Telegram-Kommandos, Nachrichtenfluss, Paginierung, Screenshot-Dialog, Sprachlogik, Status).
- Datenaufbereitung: `pdf_parser.py` (Text-Extraktion per PyPDF2, optional OCR mit Tesseract; Rausch- und Längenfilter).
- Vektor-Speicher: `vector_store.py` (ChromaDB SQLite-Persistenz, Add/Search, globale Suche).
- Retrieval-Logik: globales Chunk-Ranking, progressive Erweiterung bei großen Korpora (teilweise in separater `retrieval.py` oder integriert in Handlers/Vector-Store, je nach Projektstand).
- LLM-Schicht: `llm_client.py` (Ollama-Aufruf, Prompt-Templates, Tokenbudget, Kontexteinstellungen).
- Indexierung: `indexer.py` (Vorab-Indexierung/Preindex bei Start; Fortschritt für `/status`).
- Persistenz: `chroma_db/` Verzeichnis (SQLite + Binärdaten von Chroma).

### 3. Eingesetzte Technologien
- Programmiersprache: Python 3.11 (Slim-Image).
- Web/ASGI: FastAPI, Gunicorn, Uvicorn.
- Telegram-Bot: python-telegram-bot (Webhook-Modus).
- Embeddings & Vektor-Datenbank: Sentence-Transformers (lokale CPU-Embeddings) und ChromaDB (ohne eingebaute Remote-Embeddings).
- LLM: Ollama (lokal), z. B. `qwen2.5:7b-instruct` bzw. quantisierte Varianten; konfigurierbar via Umgebungsvariablen.
- PDF/ OCR: PyPDF2, pdf2image, Tesseract OCR (pytesseract), Pillow.
- Container: Docker Desktop, `Dockerfile`, `docker-compose.yml`.

### 4. Ablauf (Runtime-Flows)
1) Startup:
   - `bot.py` Lifespan: Initialisiert Bot, registriert Webhook, prüft Erreichbarkeit von Ollama (`test_ollama_connection()`), startet optional die Vorab-Indexierung (Preindex).
   - Healthcheck-Endpunkt für Docker überwacht Erreichbarkeit.
2) Indexierung:
   - PDFs werden geparst (`pdf_parser.py`), Absätze gefiltert, in Chunks überführt und als Embeddings im Chroma-Store gespeichert.
   - Fortschritt: `/status` zeigt `preindex_running`, `preindex_done`, `preindex_total` sowie Chroma-Infos.
3) Anfragebearbeitung (Message Flow):
   - `handlers1.py` erkennt Sprache (Standard EN; DE, wenn Text deutliche deutsche Marker enthält).
   - Globale Suche nach relevanten Chunks (Vector Store). Bei Bedarf progressive Erweiterung (breitere Suche) und paralleles Nachladen.
   - Kontext wird dedupliziert und aufbereitet. Antwort wird per Ollama generiert (`llm_client.py`), mit Pagination und `protect_content=True` versendet. Link-Vorschau ist deaktiviert.
4) Screenshot-Dialog:
   - `/screenshot`: Dokumentwahl per Inline-Buttons, anschließend Zielangabe (Seite/ Tabelle/ Figure/ Stichwort). Erzeugt PNG der Seite, sendet mit `protect_content=True`.

### 5. Module im Detail

#### 5.1 `pdf_parser.py` (OptimizedPDFParser)
- Extraktion:
  - Simple Pfad (PyPDF2-only) oder OCR-Pipeline (Tesseract via pdf2image).
  - OCR-Kontrolle: DPI, PSM, Sprachen (eng/deu), parallele Verarbeitung via `asyncio`-Semaphore.
- Qualitätsfilter:
  - Rauschfilter über Nicht-Alnum-Anteil: `OCR_NOISE_MAX_RATIO` steuert maximale Lärmquote.
  - Längenfilter pro Absatz: `MIN_PARA_CHARS` (0 deaktiviert Längenfilter).
  - Definitions-Heuristik (`DEFN_RE`): Kurze, prägnante Begriffe/Definitionen dürfen trotz Kürze passieren, sofern nicht noisy.
  - `_is_text_sufficient` für Seitentexte (zusätzliche Wortanzahl/Alnum-Prüfung).
- Zusatz:
  - Titel-/Struktur-Heuristik (`extract_titles_from_pdf`) zur Screenshot-Navigation.
  - `get_page_image_bytes` rendert Seiten als PNG für Screenshot-Funktion.

#### 5.2 `vector_store.py`
- ChromaDB initialisiert mit persistierendem Verzeichnis (SQLite). Telemetrie ist deaktiviert.
- Einfügen: Batching von Embeddings und `collection.add` zur Schonung von Speicher.
- Suche:
  - `search_global(query, n_results, similarity_threshold=None)` liefert global beste Treffer über alle Dokumente.
  - Tie-Breaker/Heuristiken: Acronym-Boosting, „definition-first“-Reordering, deduplizierte Ergebnisliste.

#### 5.3 Retrieval-Logik
- Ziel: Beste Chunks global finden, kurze Definitionen priorisieren, Dopplungen vermeiden.
- Progressive Weitung: Start mit moderater Ergebniszahl, sukzessive Erhöhung (×6 → ×20 → ×40), bis genügend hochwertige Chunks vorliegen.
- Fallbacks: Wenn Sanitizer zu viel verwirft, wird auf rohe Top-Chunks zurückgegriffen, damit das LLM stets Kontext erhält.
- Schwellwert: `MIN_SIM_THRESHOLD` (z. B. 0.15) für bessere Recall bei kurzen Fragen.

#### 5.4 `llm_client.py`
- Ollama-Aufruf mit konfigurierbaren Optionen (u. a. `num_ctx` über `OLLAMA_NUM_CTX`).
- Tokenbudget: Langantworten bis ca. 1600 Tokens (je nach `MAX_TOKENS`), kurze Antworten entsprechend geringer.
- Prompting: Instruktionen zur Vermeidung von Aufzählung der Chunks; Sprache gemäß Erkennung (DE/EN).

#### 5.5 `handlers1.py`
- Kommandos: `/start`, `/help`, `/status`, `/screenshot` (Buttons persistent im Menü).
- Sicherheit/Schutz:
  - Logging-Censor-Filter: zensiert sensible Inhalte (z. B. Pfade, Token, ngrok-URLs).
  - `disable_web_page_preview=True` für alle Antworten.
  - `protect_content=True` für LLM-Antworten und Screenshots.
  - Hinweis zu Vertraulichkeit in Start-/Help-Texten.
- Suche & Antwort:
  - Globale Retrieval-Funktion, parallele Fallbacks bei Bedarf.
  - Paginierung langer Antworten.
  - Sprachdetektion: Standard EN; DE, wenn starker DE-Anteil erkennbar.
- Screenshot-Interaktion:
  - Dokumentauswahl, dann Zielangabe („Seite X“, „Tabelle 3“, „Figure H.3“, Stichwort).
  - Regex robust gegenüber alphanumerischen Indizes.

#### 5.6 `bot.py`
- FastAPI-App, Lifespan:
  - Initialisierung/Start, Webhook-Setup, `test_ollama_connection()`-Prüfung, Preindex-Start.
  - Registrierung der Bot-Kommandos für das Telegram-Menü.
- Gunicorn-Workers auf 1 beschränkt (SQLite/Chroma-Sicherheit, kein doppeltes Webhook-Setzen).
- Healthcheck für Docker.

#### 5.7 `indexer.py`
- Preindex-Planung beim Start (optional via `PREINDEX_ENABLED`).
- Exportiert Fortschrittsvariablen (`preindex_running`, `preindex_done`, `preindex_total`) für `/status`.

### 6. Datenverarbeitungspipeline
1) PDF → Absätze: Parsing (mit/ohne OCR), Normalisierung, Rausch-/Längenfilter, Definitions-Heuristik.
2) Absätze → Chunks → Embeddings: Chunking, lokale CPU-Embeddings (Sentence-Transformers), Speicherung in Chroma.
3) Frage → Globale Suche: semantische Top-Treffer mit Heuristiken (Acronym/Definition), progressive Weitung.
4) Kontext → LLM: Konsolidierte Auszüge, Antworterzeugung, Paginierung, Schutz-Flags.

### 7. Sicherheit und Datenschutz
- Keine Cloud-Weitergabe von Dokumentinhalten; LLM/Embeddings lokal.
- Logging-Filter zensiert potentiell sensible Felder; keine Speicherung von Volltexten im Log.
- `protect_content=True` für Antworten und Screenshots (Weiterleiten/Kopieren/Speichern unterbunden; Screenshot-Block/ -Erschwernis je nach Client).
- Link-Vorschau deaktiviert (`disable_web_page_preview=True`).
- Chroma-Telemetrie deaktiviert.

### 8. Konfiguration (wichtige Umgebungsvariablen)
- Allgemein:
  - `MAX_EXCERPTS`: Anzahl an Kontext-Chunks für Antworten.
  - `MIN_PARA_CHARS`: Mindestlänge für Absatz (Parser; 0 deaktiviert Längenfilter; Empfehlung: 20).
  - `MIN_CHUNK_CHARS`, `MIN_CHUNK_WORDS`: Mindestgüte für Chunks im Vektor-Store.
  - `DISABLE_CHUNK_FILTER`: Wenn 1, werden bis auf triviale Fälle die meisten Chunks zugelassen.
  - `MIN_SIM_THRESHOLD`: Ähnlichkeitsschwelle für Suche (z. B. 0.15 für bessere Recall).
  - `OCR_ENABLED`, `OCR_CONCURRENCY`: OCR-Pfad aktivieren und OCR-Parallelität steuern.
  - `OCR_NOISE_MAX_RATIO`: Maximaler Anteil nicht-alphanumerischer Zeichen (Noise-Cutoff).
  - `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_NUM_CTX`: Modell, Host/Port, Kontextlänge.
  - `PREINDEX_ENABLED`: 0/1 – Vorabindexierung bei Start.
  - `GUNICORN_WORKERS`: auf `"1"` fixieren (Chroma/SQLite-Stabilität, Webhook nur einmal setzen).
  - `LOG_CHUNK_FILTER`, `LOG_LEVEL`, `DEBUG_PROMPTS`: Diagnose/Logging-Feingranularität.
- Pfade/Storage:
  - `CHROMA_PERSIST_DIR` (falls genutzt) bzw. Standard `./chroma_db`.

### 9. Container & Deployment
- `Dockerfile`:
  - Systempakete: `poppler-utils`, `tesseract-ocr` etc. für pdf2image/Tesseract.
  - Python-Abhängigkeiten inkl. `sentence-transformers`, `PyPDF2`, `pdf2image`, `pytesseract`, `Pillow`, `chromadb`.
  - Healthcheck (HTTP `GET /health`).
  - Start mit Gunicorn/Uvicorn, erzwungen `GUNICORN_WORKERS=1`.
- `docker-compose.yml`:
  - Services: Bot, Ollama (mit Modell- und Ressourcen-Parametern).
  - Speicherlimits und Volumes (Persistenz von `chroma_db/` und ggf. Modellen).
  - Wichtige Default-Werte für Parser/Retriever/LLM in `environment`-Sektion.

### 10. Diagnose & Tests
- `/status`: Zeigt Chroma-Infos und Preindex-Fortschritt.
- Start-Logs: Verbindungscheck zu Ollama, Indexstatus, Healthcheck-Ergebnis.
- Tipp: Einmal mit `LOG_CHUNK_FILTER=1` starten, um Statistik über kurze/leere Chunks zu prüfen; anschließend wieder auf 0 setzen.
- Fehlerbilder und Lösungen (erprobt):
  - Mehrere Worker → Chroma/SQLite-Fehler: `GUNICORN_WORKERS=1` setzen.
  - Modell nicht vorhanden: `ollama pull <MODEL>` und `OLLAMA_MODEL` abgleichen.
  - RAM-Engpässe: kleinere/quantisierte Modelle, `OLLAMA_NUM_CTX` reduzieren, Docker/WSL-Speicher erhöhen.

### 11. Erweiterbarkeit
- Weitere PDFs hinzufügen: Parser übernimmt; Indexer/Preindex neu starten.
- Retrieval anpassen: Schwellen (`MIN_SIM_THRESHOLD`), Weitungsfaktoren, Definition/Akronym-Boosts.
- LLM wechseln: `OLLAMA_MODEL`/`OLLAMA_NUM_CTX` anpassen; ggf. Prompting justieren.
- Neue Bot-Kommandos: In `handlers1.py` ergänzen; Menükonfiguration in `bot.py` anpassen.
- Sicherheit: Zusätzliche Censor-Regeln, strengere Screenshot-Policy-Hinweise.

### 12. Bekannte Grenzen
- OCR-Qualität variiert je nach Scan und Sprache.
- `protect_content` ist client-/plattformabhängig in seiner Wirksamkeit.
- Lange Antworten vs. Kontextfenster: Tokenbudget und `num_ctx` beachten.

### 13. Projektstruktur (aus Anwendersicht)
```
bot.py                  # FastAPI-App, Lifespan, Webhook, Commands
handlers1.py            # Telegram-Handlers, Retrieval-Aufruf, Screenshot-Dialog, Paginierung
pdf_parser.py           # Parsing/OCR, Rausch-/Längenfilter, Titel-Extraktion, Seitenrendering
vector_store.py         # ChromaDB-Persistenz, Add/Search, globale Suche/Heuristiken
llm_client.py           # Ollama-Client, Optionen (num_ctx), Tokenbudget, Prompts
indexer.py              # Preindex-Planung, Fortschrittswerte für /status
chroma_db/              # Persistente Vektordaten (SQLite/Binärdaten)
Dockerfile              # Build mit OCR/Poppler, Healthcheck, Gunicorn-Start
docker-compose.yml      # Services (bot, ollama), Ressourcen, Umgebungsvariablen
requirements.txt        # Python-Abhängigkeiten
updates/                # Änderungen & diese technische Dokumentation
```

---
Stand: aktuelle Implementierung laut Projektdateien und Änderungsverlauf. Bei größeren Umbauten bitte dieses Dokument mitziehen (insbesondere Variablen, Modell-/Ressourcen-Defaults und Sicherheitsmaßnahmen).

