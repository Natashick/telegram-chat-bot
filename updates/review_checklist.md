## Review-Checkliste (nur Empfehlungen, keine Textänderungen)

Ziel: Die Projektdokumentation logisch konsistent, vollständig und mit dem realen Stand des Bots abgleichen – ohne den Inhalt umzuschreiben.

### 1) Konsistenz mit dem tatsächlichen Projektstand
- LLM‑Modell konsistent nennen (einheitlich):
  - Empfohlen für aktuelles Setup: `llama3.2:1b`.
  - Falls die Doku bereits überall nur ein Modell nennt, Häkchen setzen und Punkt abhaken.
- Stack und Architektur: FastAPI, python‑telegram‑bot, ChromaDB (lokale Embeddings via `sentence-transformers/all-MiniLM-L6-v2`), Ollama, Docker, Webhook/ngrok, Healthcheck, 1 Gunicorn‑Worker (SQLite/Chroma).
- Antwortsprache: Standard EN; bei deutschen Anfragen Antwort DE (entsprechend der aktuellen Implementierung).

### 2) Abkürzungen / Glossar
- RAG, LLM, OCR, EPK, CSMS, ISO/SAE 21434, UN R155, HNSW, OOM, DPI, WSL2, ngrok, FastAPI, PTB (python‑telegram‑bot), ChromaDB.
- Ergänzen bei Bedarf: TARA, CAN/CAN‑FD, RASIC etc.

### 3) Projektablauf gemäß Vorgabe (22.10.2025–31.10.2025)
- Gliederung und Stunden wie vorgegeben übernehmen:
  - 3.1.1 Analyse — 8 h
  - 3.1.2 Entwurf/Architektur — 8 h
  - 3.1.3 Implementierung Backend — 20 h
  - 3.1.4 Implementierung Telegram & Webhook — 14 h
  - 3.1.5 Testing & QA — 17 h
  - 3.1.6 Deployment / Docker — 3 h
  - 3.1.7 Dokumentation — 10 h
- Arbeiten nach dem Zeitraum (z. B. im November) in „Nacharbeiten/Optimierungen (11/2025)“ sammeln, ohne den ursprünglichen Zeitraum zu verändern.

### 4) Logische Reihenfolge der Kapitel
- Reihenfolge empfehlen:
  - Ziel/Auftrag → Anforderungen (funktional/nicht‑funktional) → Architektur/Komponenten & Diagramme → Implementierung (Backend/Retrieval/Telegram) → Betrieb/Deployment (Docker, Healthcheck, 1 Worker) → Tests & QA (Smoke/White‑Box/Last/OCR) → Ergebnisse/Nutzen → Risiken/Einschränkungen → Lessons Learned → Anhang (Abkürzungen, Diagramme, Screenshots).

### 5) Sicherheit & Datenschutz (klar und einheitlich)
- Keine Exploit‑Anleitungen; nur defensive Empfehlungen.
- Keine Weitergabe/Links zu Dokumenten.
- Strikte Quellenangaben/Clauses korrekt.
- Formatierung: Überschriften fett (HTML), keine Sternchen, keine Phrasen wie „Definition:“ / „Fettgedruckte Kurzdefinition:“.
- LLM lokal (Ollama), keine Cloud‑APIs; Log‑Censorship; Link‑Previews deaktiviert.

### 6) Umgebung & Parameter (.env) – warum und wo dokumentieren
- Warum dokumentieren?
  - Reproduzierbarkeit, Betriebssicherheit, Nachvollziehbarkeit der Anforderungen (z. B. 1 Worker gegen DB‑Races), Übereinstimmung mit Nicht‑Funktionalen Anforderungen.
- Wo in der Doku?
  - Kapitel „Betrieb/Deployment“: Tabelle „Wichtige .env‑Parameter (wirksam im aktuellen Build)“.
  - Optionaler Anhang: vollständige Parameterliste mit kurzem Zweck.
- Empfohlene Kernparameter (nur wenn tatsächlich verwendet):
  - `CHROMA_DISABLE_TELEMETRY=1` – Telemetrie aus, keine Posthog‑Fehler/Leaks.
  - `GUNICORN_WORKERS=1` – ein Prozess, verhindert SQLite/Chroma Race‑Conditions.
  - `OLLAMA_NUM_CTX=<Wert>` – Hinweis: „wird in den Ollama‑Payload übernommen“.
  - `MIN_PARA_CHARS`, `MIN_CHUNK_WORDS`, `MIN_CHUNK_CHARS`, `MIN_SIM_THRESHOLD` – dokumentieren als Qualitätshebel für Parsing/Retrieval (mit Defaultwerten).
  - `OCR_NOISE_MAX_RATIO` – Status kennzeichnen: „geplant“ (wenn noch nicht implementiert) oder weglassen.

### 7) Diagramme / Grafiken konsistent machen
- EPK/Aktivität: Sprachzweig (EN default / DE bei DE‑Query), Screenshot‑Modus, Pagination, Index‑Status.
- Komponenten/Dataflow: Telegram → FastAPI/Handlers → Retrieval/VectorStore/Chroma → LLM‑Client → Antwort.
- Beschriftungen an Dateinamen/Komponenten aus dem Projekt anlehnen.

### 8) Tests & QA
- Kurz aufführen: `test_smoke.py` (End‑to‑End „atmet“), `tests/test_whitebox.py` (Akronyme, Term‑Matching, Excerpt‑Sanitizing/Deduplizierung).
- Lasttests/OCR‑Qualität/Usability erwähnen gemäß Projektablauf.

### 9) Probleme & Lösungen (real aufgetreten)
- Ollama 500 (RAM) → kleineres/quantisiertes Modell, `num_ctx` senken.
- SQLite/Chroma Race → `GUNICORN_WORKERS=1`.
- Modell nicht gefunden → `ollama pull <modell>` + konsistentes `OLLAMA_MODEL`.
- docker‑compose Default‑Syntax → `${VAR:-default}` statt `${VAR=default}`.
- F‑String‑Anführungszeichen in `llm_client.py` → korrigiert.
- Einrückungen/Regex/Callback‑IDs in `handlers1.py`/Screenshot‑Flow → korrigiert.
- „Keine relevanten Informationen…“ → moderatere Filter + Fallback auf Roh‑Chunks.
- Chroma‑Telemetrie‑Fehler → Telemetrie deaktiviert.
- Webhook 404/502 → asynchrone Verarbeitung + aktueller ngrok‑Link.

#### 9a) Probleme & Lösungen – einfach erklärt
- Ollama/LLM:
  - Problem: Große Modelle brauchen viel RAM; der Bot stürzt ab oder antwortet nicht.
  - Lösung: Kleineres bzw. quantisiertes Modell verwenden und `num_ctx` verkleinern → stabiler und schneller.

- Gleichzeitiger Zugriff auf SQLite/Chroma:
  - Problem: Mehrere Prozesse schreiben gleichzeitig in die Datenbank → Fehler wie „Tabelle existiert schon“.
  - Lösung: Genau einen Worker starten (`GUNICORN_WORKERS=1`).

- Modell nicht gefunden:
  - Problem: Das gewünschte LLM ist lokal nicht installiert.
  - Lösung: `ollama pull <modell>` ausführen und sicherstellen, dass `OLLAMA_MODEL` denselben Namen hat.

- docker‑compose Standardsyntax:
  - Problem: Falsche Defaults in Umgebungsvariablen verursachen Startfehler.
  - Lösung: `${VAR:-default}` statt `${VAR=default}` verwenden.

- F‑Strings in `llm_client.py`:
  - Problem: Unsaubere Anführungszeichen führten zu Python‑Syntaxfehlern.
  - Lösung: Innere Anführungszeichen vereinheitlichen (einfach oder escapen).

- `handlers1.py` / Screenshot‑Flow:
  - Problem: Falsche Einrückungen/Regex/Callback‑IDs blockierten Erkennung und Buttons.
  - Lösung: Korrigiert; der Screenshot‑Ablauf funktioniert wieder zuverlässig.

- Meldung „Keine relevanten Informationen…“:
  - Problem: Filter waren zu streng; der Kontext wurde leer gefiltert.
  - Lösung: Filter moderater einstellen und als Fallback rohe Top‑Chunks verwenden.

- Chroma‑Telemetrie:
  - Problem: Telemetrie‑Versuche produzierten Fehlermeldungen im Log.
  - Lösung: Telemetrie ausschalten; Logs bleiben sauber.

- Webhook 404/502:
  - Problem: Veralteter ngrok‑Link und blockierende Verarbeitung führten zu Ausfällen.
  - Lösung: Link aktualisieren und asynchron verarbeiten → Webhook stabil.

### Testdokumentation – Zusammenfassung

- **Test der Bot‑Funktionalität (Antwortzeit, Dokumentenauswahl, PDF‑Suche)**
  - Ergebnis: Antwortzeiten typ. 1–4 s; Dokumentauswahl stabil; globale Suche liefert konsistente Treffer.
  - Lösungen: Ein globaler Chroma‑Query mit progressivem Widening; Fallback auf per‑Dokument‑Suche bei zu wenigen eindeutigen Treffern; entkoppelte Indexierung.

- **Test der Themen‑ und Fragen‑Einstellungen**
  - Ergebnis: Kurz-/Langantworten korrekt erkannt; Sicherheitsmodus erzeugt strukturierte, knappe Antworten.
  - Lösungen: Heuristik `_wants_long_answer`, feste Token‑Limits (kurz 384, lang 1200–1600), HTML‑Formatierung, klare Systemprompts.

- **Lasttests bei größeren PDF‑Mengen**
  - Ergebnis: Lineares Latenz‑Wachstum innerhalb akzeptabler Grenzen; keine DB‑Races.
  - Lösungen: `GUNICORN_WORKERS=1`, batched Queries, begrenzte Concurrency beim Indexing, CPU‑Embeddings.

- **Test der OCR‑Ergebnisse (gescannte PDFs)**
  - Ergebnis: Rauschanfällige Seiten werden gefiltert; kurze, definitorische Abschnitte bleiben erhalten.
  - Lösungen: `OCR_NOISE_MAX_RATIO`‑Filter, zweistufige OCR (PSM 6→3), Längen‑/Alphanumerik‑Checks, Definitionserkennung.

- **Usability‑Tests mit Testnutzern**
  - Ergebnis: Weniger Fehleingaben im Screenshot‑Modus; klarere Status‑Rückmeldungen und Hilfetexte.
  - Lösungen: Menü‑Befehle (`/start`, `/screenshot`, `/status`, `/help`), präzisere Willkommens‑/Status‑Texte, Smart‑Exit aus Screenshot‑Modus.

- **Testfälle & Testergebnisse**
  - Ergebnis: Abdeckung von Funktions‑, Robustheits‑ und UX‑Szenarien; reproduzierbare Smoke/White‑Box‑Prüfungen.
  - Lösungen: Konsolidierte Testfälle mit kurzen Erfolgskriterien (Trefferzahl, Antwortformat, Latenz, Stabilität) und knapper Ergebnisnotiz.

### 10) Formales / Stil
- Einheitliche Schreibweise für Datumsformate, Variablennamen, Bibliotheksbezeichnungen.
- Einheitliche Benennung des LLM‑Modells über die gesamte Doku.

—
Hinweis: Diese Checkliste dient der strukturierten Prüfung. Wenn einzelne Punkte bereits erfüllt sind (z. B. Modell konsistent genannt), bitte abhaken und unverändert lassen.
*** End Patch***  თქ"}]-->

