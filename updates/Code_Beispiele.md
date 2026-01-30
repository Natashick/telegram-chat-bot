## Kurze, verständliche Code-Beispiele mit Erklärung

Im Folgenden sind kompakte Ausschnitte aus dem Projekt versammelt, die zentrale Funktionen, bekannte Objekte und wichtige Parameter zeigen. Jeder Ausschnitt enthält kurze Kommentare sowie eine kurze Erläuterung.

### 1) Logging‑Zensurfilter (Schutz sensibler Daten) – `handlers1.py`

```python
def _censor(text: str) -> str:
    if not text:
        return text
    s = str(text)
    patterns = [
        r"\b\d{8,}:[A-Za-z0-9_\-]{20,}\b",                  # Tokens
        r"(?:https?://)?[a-z0-9\-]+\.ngrok-free\.app[^\s]*", # ngrok-URLs
        re.escape(_WEBHOOK_SECRET) if _WEBHOOK_SECRET else None,
        r"[A-Za-z]:\\[^\s]+",                                # Windows-Pfade
        r"/app/pdfs/[^\s]+",                                 # Container-Pfade
    ]
    for pat in filter(None, patterns):
        s = re.sub(pat, "[CENSORED]", s, flags=re.IGNORECASE)
    return s

class _CensorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Nachricht „umschreiben“
        try:
            msg = record.getMessage()
            record.msg = _censor(msg)
            record.args = ()
        except Exception:
            pass
        # Häufige Zusatzfelder ebenfalls säubern
        for attr in ("text", "data"):
            if hasattr(record, attr):
                try:
                    setattr(record, attr, _censor(getattr(record, attr)))
                except Exception:
                    pass
        return True
```

Erläuterung: Der Filter ersetzt Tokens, ngrok‑URLs, absolute Pfade u. a. durch `[CENSORED]`, bevor etwas ins Log gelangt.

### 2) Screenshot‑Zielerkennung (Seite/Tabelle/Figur) – `handlers1.py`

```python
def _is_screenshot_target_query(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    if re.search(r"(?i)\b(seite|page)\s*\d+\b", t):
        return True
    # numerisch (3) und alphanumerisch wie H.3 / H-3 / H3
    if re.search(r"(?i)\b(tab(?:elle)?|table)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", t):
        return True
    if re.search(r"(?i)\b(fig(?:ure)?|abbildung)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", t):
        return True
    return False
```

Erläuterung: Robust gegen Schreibweisen; erkennt sowohl einfache Zahlen als auch Indizes wie „H.3“.

### 3) Paginierte Antworten mit Schutzflags – `handlers1.py`

```python
async def _send_paginated(update, _context, text: str):
    pages = _split_pages(text)
    if len(pages) == 1:
        await update.message.reply_text(
            pages[0],
            disable_web_page_preview=True,  # keine Link-Vorschau
            parse_mode=ParseMode.HTML,
            protect_content=PROTECT_CONTENT, # Telegram‑Schutzflag
        )
        return
    # ... (Navigationstasten etc.)
```

Erläuterung: Lange Antworten werden in mehrere Seiten aufgeteilt; dabei sind Link‑Vorschau deaktiviert und Inhalte geschützt.

### 4) Einfache DE/EN‑Spracherkennung – `handlers1.py`

```python
def _detect_lang_de_en(text: str) -> str:
    if not text:
        return "DE"
    low = text.strip().casefold()
    en_hits = sum(w in f" {low} " for w in (" what ", " is ", " are ", " should ", " how ", " when ", " why ", " the ", " and ", " about ", " security "))
    de_hits = sum(w in f" {low} " for w in (" was ", " ist ", " sind ", " sollte ", " wie ", " wann ", " warum ", " worum ", " worauf ", " inwiefern ", " der ", " die ", " das ", " über ", " und "))
    if any(ch in text for ch in ("ä","ö","ü","Ä","Ö","Ü","ß")):
        de_hits += 2
    return "EN" if en_hits > de_hits + 1 else "DE"
```

Erläuterung: Sehr leichtgewichtige Heuristik; bevorzugt Deutsch bei Unsicherheit (Umlaute geben DE‑Bias).

### 5) OCR‑Rauschfilter und Absatzprüfung – `pdf_parser.py`

```python
def _is_noisy(self, text: str) -> bool:
    if not text:
        return True
    s2 = re.sub(r"\s+", "", str(text))
    if not s2:
        return True
    non_word = sum(1 for ch in s2 if not ch.isalnum())
    ratio = non_word / max(1, len(s2))
    return ratio >= self.noise_max_ratio  # OCR_NOISE_MAX_RATIO

def _is_usable_para(self, p: str) -> bool:
    if not p:
        return False
    if DEFN_RE.search(p):
        return not self._is_noisy(p)     # kurze Definitionen erlaubt, wenn nicht noisy
    cleaned = re.sub(r'\s+', '', p)
    if self.min_text_length > 0 and len(cleaned) < self.min_text_length:  # MIN_PARA_CHARS
        return False
    if self._is_noisy(p):
        return False
    return True
```

Erläuterung: Kürzere Glossar‑Zeilen sind zulässig, solange sie nicht „noisy“ sind; Länge und Noise sind per Umgebungsvariablen steuerbar.

### 6) Globale Vektorsuche mit Akronym‑Boost – `vector_store.py`

```python
def search_global(self, query: str, n_results: int = 5, *, similarity_threshold: Optional[float] = None) -> List[Dict]:
    q_emb = self._embed([query])[0]
    acr = detect_acronym(query)
    acr_cf = acr.casefold() if acr else None
    top_k = max(50, n_results * 6)
    thr = self.min_sim_threshold if similarity_threshold is None else float(similarity_threshold)

    res = self.collection.query(query_embeddings=[q_emb], n_results=top_k, include=["documents","metadatas","distances"])
    # ... (Scores berechnen, Akronym‑Boost, Definition‑first‑Reordering)
    return out[:n_results]
```

Erläuterung: Semantische Suche über alle Dokumente; wenn ein Akronym im Treffertext vorkommt, wird der Score erhöht und „Definition zuerst“ sortiert.

### 7) Progressive Weitung der globalen Suche – `retrieval.py`

```python
async def get_best_chunks_global(query: str, max_chunks: int = 12) -> List[Dict]:
    base = await asyncio.to_thread(vector_store.search_global, query, n_results=max_chunks * 6)
    chunks = base or []
    # wenn noch zu wenig einzigartige Treffer: weiter weiten
    if _uniq_len(chunks) < max_chunks * 3:
        extra1 = await asyncio.to_thread(vector_store.search_global, query, n_results=max(max_chunks * 20, 200))
        if extra1: chunks.extend(extra1)
    if _uniq_len(chunks) < max_chunks * 3:
        extra2 = await asyncio.to_thread(vector_store.search_global, query, n_results=max(max_chunks * 40, 400))
        if extra2: chunks.extend(extra2)
    # ... (Deduplizierung, Definitionen/Begriffe priorisieren)
    return chunks[:max_chunks]
```

Erläuterung: Für große Korpora wird die Ergebnisbreite schrittweise erhöht, bis genügend qualitativ gute Chunks vorliegen.

### 8) LLM‑Aufruf mit konfigurierbarer Kontextlänge – `llm_client.py`
Au
```python
payload = {
    "model": OLLAMA_MODEL,                     
    "prompt": f"<<SYS>>{system_prompt}\n<</SYS>>\n{user_prompt}",
    "options": {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "num_predict": _estimate_tokens(user_prompt, want_long=want_long),
        "top_k": TOP_K,
        "repeat_penalty": REPEAT_PENALTY,
        "num_thread": 2,
        "num_ctx": OLLAMA_NUM_CTX,            # Kontextfenster aus ENV
    },
    "stream": OLLAMA_STREAM
}
```

Erläuterung: Das Kontextfenster (`num_ctx`) und das Token‑Budget werden über ENV/Heuristik angepasst; robust gegenüber unterschiedlichen Ollama‑Antwortformaten.

### 9) Preindex‑Fortschritt und sichere Re‑Indexierung – `indexer.py`

```python
# Fortschrittszähler (werden in /status angezeigt)
preindex_inflight = 0
preindex_total = 0
preindex_done = 0
preindex_running = False

async def ensure_document_indexed(document_name: str):
    async with _doc_lock(document_name):
        current_version = _compute_doc_version(document_name)
        existing_version = await asyncio.to_thread(vector_store.get_document_version, document_name)
        if existing_version and existing_version != current_version:
            await asyncio.to_thread(vector_store.delete_document, document_name)  # alte Version entfernen
        # ... (Parsing, Titelindex optional, add_chunks mit doc_version)
```

Erläuterung: Verhindert Doppelindexierung und erkennt Datei‑Versionen; Statuswerte erscheinen in `/status`.

### 10) Startup‑Checks und Preindex‑Start – `bot.py`

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    await application.initialize()
    await application.start()
    await setup_webhook(application)
    # Ollama‑Verfügbarkeit prüfen
    ok = await test_ollama_connection()
    # Optionaler Preindex‑Start (flag‑gesteuert)
    pre_enabled = os.getenv("PREINDEX_ENABLED", "1") != "0"
    if pre_enabled:
        from handlers1 import get_pdf_files
        from indexer import preindex_all_pdfs as _preindex
        pdfs = get_pdf_files()
        asyncio.create_task(_preindex(pdfs))
    yield
```

Erläuterung: Stellt sicher, dass Webhook/LLM verfügbar sind und startet die Vorab‑Indexierung bei Bedarf im Hintergrund.

---
Hinweis: Parameter wie `MIN_PARA_CHARS`, `OCR_NOISE_MAX_RATIO`, `MIN_SIM_THRESHOLD`, `OLLAMA_NUM_CTX`, `PROTECT_CONTENT` u. a. sind über Umgebungsvariablen steuerbar und in der technischen Doku beschrieben.

