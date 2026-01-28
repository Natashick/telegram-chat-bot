# PFLICHTENHEFT
## Telegram PDF Chatbot - Funktionale Spezifikation

**Projekt**: Telegram PDF Chatbot für Automotive Cybersecurity  
**Version**: 1.0  
**Datum**: 27.01.2024  
**Status**: Finalisiert  
**Basierend auf**: Lastenheft v1.0

---

## Inhaltsverzeichnis

1. [Einleitung](#1-einleitung)
2. [Systemübersicht](#2-systemübersicht)
3. [Funktionale Spezifikationen](#3-funktionale-spezifikationen)
4. [Datenmodell](#4-datenmodell)
5. [Schnittstellenspezifikation](#5-schnittstellenspezifikation)
6. [Technisches Design](#6-technisches-design)
7. [Testkonzept](#7-testkonzept)
8. [Deployment-Konzept](#8-deployment-konzept)

---

## 1. Einleitung

### 1.1 Zweck des Dokuments

Dieses Pflichtenheft beschreibt die technische Umsetzung des Telegram PDF Chatbots für Automotive Cybersecurity gemäß dem Lastenheft v1.0. Es dient als verbindliche Grundlage für Implementierung, Test und Abnahme.

### 1.2 Gültigkeitsbereich

**Gilt für**:
- Entwicklungs-Team
- DevOps/Deployment-Team
- Test-Team
- Technische Dokumentation

### 1.3 Referenzen

- **Lastenheft v1.0**: Anforderungsspezifikation
- **System Architecture**: Technisches Design
- **API Documentation**: Schnittstellen-Referenz

---

## 2. Systemübersicht

### 2.1 Systemarchitektur (Komponentensicht)

```
┌────────────────────────────────────────────────────────────┐
│                     Telegram User                          │
└─────────────────────┬──────────────────────────────────────┘
                      │ HTTPS (Webhook)
                      ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Application (bot.py)                    │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Webhook Endpoint: POST /webhook/{secret}              │  │
│  │  Health Check: GET /health                             │  │
│  └────────────┬───────────────────────────────────────────┘  │
└───────────────┼──────────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
┌──────────────┐  ┌──────────────┐
│ handlers1.py │  │  indexer.py  │
│              │  │              │
│ - /start     │  │ - Background │
│ - /help      │  │   indexing   │
│ - /status    │  │ - Version    │
│ - /screenshot│  │   control    │
│ - Text Q&A   │  │ - Scheduling │
└───────┬──────┘  └──────┬───────┘
        │                │
        ▼                ▼
┌─────────────────────────────────┐
│      retrieval.py               │
│                                 │
│  - get_best_chunks_for_document │
│  - get_best_chunks_global       │
│  - find_definition_in_chunks    │
│  - build_combined_excerpts      │
└────┬─────────────────────┬──────┘
     │                     │
     ▼                     ▼
┌──────────┐         ┌──────────────┐
│ vector_  │         │  llm_client  │
│ store.py │         │              │
│          │         │ - ask_ollama │
│ ChromaDB │         │ - Prompts    │
│ Wrapper  │         │ - Ollama API │
└────┬─────┘         └──────────────┘
     │
     ▼
┌─────────────┐
│ pdf_parser  │
│             │
│ - PyPDF2    │
│ - pdfplumber│
│ - OCR       │
└─────────────┘
```

### 2.2 Technologie-Stack

| Schicht | Technologie | Version | Zweck |
|---------|-------------|---------|-------|
| **Runtime** | Python | 3.11+ | Programmiersprache |
| **Web Framework** | FastAPI | 0.104.1 | Webhook-Server |
| **ASGI Server** | Uvicorn | 0.24.0 | Production Server |
| **Bot SDK** | python-telegram-bot | 20.7 | Telegram-Integration |
| **Vector DB** | ChromaDB | 0.4.22 | Semantic Search |
| **Embeddings** | sentence-transformers | 2.7.0 | CPU-basierte Vektoren |
| **LLM Interface** | Ollama API | - | Lokales LLM |
| **PDF Parsing** | PyPDF2, pdfplumber | 3.0.1, 0.10.3 | Text-Extraktion |
| **OCR** | pytesseract, Tesseract | 0.3.10, 5.x | Bild-zu-Text |
| **Container** | Docker, Docker Compose | 20.10+, 2.0+ | Deployment |

---

## 3. Funktionale Spezifikationen

### 3.1 FS-001: PDF-Indexierung

**Lastenheft-Referenz**: FA-001, FA-009

**Beschreibung**: Automatische Hintergrund-Indexierung aller PDFs im konfigurierten Verzeichnis.

**Komponenten**: `indexer.py`, `pdf_parser.py`, `vector_store.py`

**Ablauf**:
1. **Startup**: Bot-Startup triggert `preindex_all_pdfs()` (wenn `PREINDEX_ENABLED=1`)
2. **Scheduling**: Für jedes PDF wird `schedule_index()` aufgerufen
3. **Background Task**: `_index_worker()` läuft asynchron mit Semaphore-Control
4. **Version Check**: `_compute_doc_version()` berechnet Hash aus Größe + mtime
5. **Extraction**: `pdf_parser.extract_paragraphs_from_pdf()` extrahiert Text
6. **Chunking**: `vector_store.add_chunks()` split in 800-Wort-Chunks
7. **Embedding**: sentence-transformers generiert 384-dim Vektoren (CPU)
8. **Storage**: ChromaDB speichert Embeddings + Metadaten
9. **Persistierung**: `client.persist()` schreibt auf Disk

**Datenfluss**:
```
PDF-Datei → pdf_parser (PyPDF2/pdfplumber/OCR)
         → TextNormalizer (Hyphenation, Ligatures, Unicode)
         → List[paragraphs]
         → vector_store.add_chunks()
         → Chunking (800 words, 160 overlap)
         → Quality Filter (min 60 chars, 25% alpha)
         → Embedding (sentence-transformers, batch=16)
         → ChromaDB.add(embeddings, metadata)
         → Persist to chroma_db/
```

**Fehlerbehandlung**:
- PDF nicht lesbar: Skip, Log ERROR
- OCR-Fehler: Fallback auf Text-Only-Modus
- ChromaDB-Fehler: Log WARNING, Continue (Daten evtl. verloren)

**Konfiguration**:
```bash
PREINDEX_ENABLED=1           # Auto-start indexing
INDEX_CONCURRENCY=2          # Max parallel tasks
CHUNK_SIZE=800               # Words per chunk
CHUNK_OVERLAP=160            # Overlap words
MIN_CHUNK_CHARS=60           # Min chunk length
EMBED_BATCH_SIZE=16          # Embedding batch size
```

**Performance**:
- **Ohne OCR**: 100-500 Seiten/Minute
- **Mit OCR**: 10-50 Seiten/Minute

**Status-Tracking**: Global Variables in `indexer.py`:
- `preindex_running` (bool)
- `preindex_total` (int)
- `preindex_done` (int)
- `preindex_inflight` (int)

---

### 3.2 FS-002: Semantische Suche

**Lastenheft-Referenz**: FA-002, FA-006

**Beschreibung**: Bedeutungsbasierte Retrieval über vector similarity search.

**Komponenten**: `retrieval.py`, `vector_store.py`, `acronym_utils.py`

**Ablauf (User Query)**:
1. **Input**: User-Nachricht (z.B. "Was ist TARA?")
2. **Acronym Detection**: `detect_acronym(query)` → "TARA"
3. **Global Retrieval**: `get_best_chunks_global(query, max_chunks=12)`
   - Embedding generieren für Query
   - ChromaDB cosine similarity search
   - Top-K Kandidaten (n_results * 6 = 72)
   - Acronym-Boosting: +0.30 Score wenn Term im Text
   - Filter: Similarity ≥ 0.15 (konfigurierbar)
   - Progressive Widening: Falls <5 Results, erhöhe auf 20x, dann 40x
4. **Definition Extraction**: `find_definition_in_chunks(term, chunks)`
   - Regex-Patterns: `TERM - Def`, `TERM: Def`, `TERM (Def)`
   - Scoring: Kürze bevorzugt, Bad-Words filtern
   - Return: Top 3 Definitionen
5. **Fallback: Term Filter**: `filter_chunks_by_term(term, chunks)`
   - Exakte Term-Präsenz (normalisiert)
   - Bonus für ISO/SAE/CAN-Patterns
6. **Context Building**: `build_combined_excerpts(chunks)`
   - Sanitization (Figure/Clause-Header entfernen)
   - Deduplication
   - Format: `EXCERPT 1:\n<text>\n---\nEXCERPT 2:\n...`

**Algorithmen**:

**Acronym Scoring** (acronym_utils.py):
```python
def detect_acronym(text: str) -> Optional[str]:
    tokens = re.findall(r"\b[A-Za-z0-9\-/]{2,20}\b", text)
    scores = []
    for tok in tokens:
        score = 0
        if has_digit(tok): score += 2  # ISO 21434
        if is_uppercase(tok): score += 1  # TARA, CAN
        if tok in PREFERRED: score += 3  # CAN, OEM, RASIC
        scores.append((score, tok))
    return max(scores, key=lambda x: x[0])[1] if scores else None
```

**Acronym Boosting** (vector_store.py):
```python
def search_in_document(...):
    results = collection.query(embeddings=[q_emb], n_results=top_k)
    for doc, dist in results:
        base_sim = 1.0 / (1.0 + dist)
        if acronym in doc.lower():
            sim = min(1.0, base_sim + 0.30)  # Boost
        if sim >= threshold:
            yield {"text": doc, "similarity_score": sim, ...}
```

**Progressive Widening** (retrieval.py):
```python
async def get_best_chunks_global(query, max_chunks=12):
    chunks = await vector_store.search_global(query, n_results=max_chunks*6)
    if len(deduplicate(chunks)) < max_chunks * 3:
        chunks += await vector_store.search_global(query, n_results=max_chunks*20)
    if len(deduplicate(chunks)) < max_chunks * 3:
        chunks += await vector_store.search_global(query, n_results=max_chunks*40)
    return deduplicate(chunks)[:max_chunks]
```

**Konfiguration**:
```bash
MIN_SIM_THRESHOLD=0.15       # Min cosine similarity
MAX_EXCERPTS=12              # Max chunks to LLM
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Performance**:
- **Vector Search**: 50-200ms (1000s Chunks)
- **Embedding Generation**: 10-50ms (Query)

---

### 3.3 FS-003: LLM-Integration

**Lastenheft-Referenz**: FA-004, FA-005

**Beschreibung**: Ollama-basierte Answer-Generation mit Prompt Engineering.

**Komponenten**: `llm_client.py`

**Funktion**: `ask_ollama(question, context, chunks_info, target_language)`

**Prompt Engineering**:

**System Prompt (Deutsch)**:
```
Antworte AUSSCHLIESSLICH auf Basis der EXCERPTS.
Toleranz für Schreibvarianten (Groß/Klein, Bindestrich, Slash, Leerzeichen).
Keine Exploit-/Angriffsanleitungen.
Wenn die EXCERPTS nicht ausreichen, gib GENAU EINMAL: "Keine relevanten Informationen im Kontext.".
Ausgabeformat NUR als HTML:
- Überschriften in <b>...</b>
- Tabellen als ASCII in <pre>...</pre>
- Keine Markdown-Syntax, kein Codeblock-Markdown.
```

**User Prompt**:
```
FRAGE: {question}

EXCERPTS (nur diese verwenden):
{context}

Gib eine strukturierte, sachliche HTML-Antwort mit <b>-Überschriften.
Wenn Tabellen sinnvoll sind, nutze ein ASCII-Raster in <pre>.
```

**Token Management**:
```python
def _estimate_tokens(prompt, want_long=False):
    if _wants_long_answer(prompt):
        return min(3500, MAX_TOKENS)  # Detailed answers
    else:
        return min(1500, MAX_TOKENS)  # Short answers

def _wants_long_answer(q):
    return (
        len(q) > 100 or
        any(k in q.lower() for k in ["ausführlich", "erkläre", "liste", "schritte", "explain", "detailed", "steps"]) or
        re.search(r"\b(ISO|SAE|UNR)\s*\d{3,5}", q)
    )
```

**Continuation Logic** (bei Truncation):
```python
response = await _call_ollama_chat(system, user, want_long)
max_cont = 2
cont = 0
while _is_truncated(response) and cont < max_cont:
    tail = response[-200:]
    more = await _call_ollama_chat(system, f"Fahre fort ab:\n{tail}\n...")
    response += "\n" + more
    cont += 1
```

**Markdown→HTML Normalisierung**:
```python
def normalize_to_html(text):
    # **bold** → <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Markdown-Tabellen → <pre>...</pre>
    text = _md_table_to_pre(text)
    return text
```

**API-Aufruf**:
```python
async def _call_ollama_chat(system, user, want_long):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": _estimate_tokens(user, want_long),
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_ctx": OLLAMA_NUM_CTX
        },
        "stream": False
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            data = await resp.json()
            return data["message"]["content"]
```

**Fehlerbehandlung**:
- **Connection Error**: Return "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."
- **Timeout (180s)**: Return partial response if available
- **400/422 (Invalid Options)**: Retry ohne `num_predict` (Kompatibilität)

**Konfiguration**:
```bash
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_NUM_CTX=2048
MAX_TOKENS=4096
DEBUG_PROMPTS=0  # Log prompts (first 800 chars)
```

**Performance**:
- **llama3.2:1b**: 2-5s (CPU), 1-3s (GPU)
- **qwen2.5:7b**: 5-12s (CPU), 2-5s (GPU)

---

### 3.4 FS-004: Telegram Message Handling

**Lastenheft-Referenz**: FA-003, FA-004, FA-008

**Beschreibung**: Verarbeitung von Telegram-Commands und Text-Nachrichten.

**Komponenten**: `handlers1.py`, `bot.py`

**Commands**:

**`/start`**:
```python
async def start_command(update, context):
    pdfs = get_pdf_files()
    if not pdfs:
        return await update.message.reply_text("Keine PDFs gefunden...")
    kb = ReplyKeyboardMarkup([["/start", "/screenshot"]], resize_keyboard=True)
    await update.message.reply_text(
        "Willkommen beim Automotive-Cybersecurity-Bot.\n\n"
        "So funktioniert es:\n"
        "1️⃣ Drücke /Start.\n"
        "2️⃣ Stelle deine Frage oder nutze /screenshot.\n"
        "⚠️ Hinweis: Die Dokumenteninhalte sind vertraulich.",
        reply_markup=kb
    )
```

**`/status`**:
```python
async def status_command(update, context):
    info = await asyncio.to_thread(vector_store.get_document_info)
    text = (
        f"VectorStore chunks: {info['total_chunks']}\n"
        f"Persist dir: {info['persist_directory']}\n"
        f"Preindex: running={preindex_running}, done={preindex_done}/{preindex_total}\n"
    )
    await update.message.reply_text(text)
```

**Text Message Handling**:
```python
async def handle_message(update, context):
    user_question = update.message.text.strip()
    
    # 1. Language Detection
    is_german = any(w in user_question.lower() for w in ["was", "ist", "wie", ...]) or \
                any(ch in user_question for ch in ["ä","ö","ü","ß"])
    context.user_data["lang"] = "DE" if is_german else "EN"
    
    # 2. Index Check
    pdfs = get_pdf_files()
    has_any = await asyncio.to_thread(lambda: any(vector_store.has_document(p) for p in pdfs))
    if not has_any:
        for p in pdfs:
            schedule_index(p)
        return await update.message.reply_text("Indexierung gestartet...")
    
    # 3. Retrieval
    all_chunks = await get_best_chunks_global(user_question, max_chunks=MAX_EXCERPTS)
    if not all_chunks:
        return await update.message.reply_text("Keine relevanten Informationen gefunden.")
    
    # 4. Acronym-Definition Prioritization
    term = detect_acronym(user_question)
    if term:
        defs = find_definition_in_chunks(term, all_chunks)
        if defs:
            # Use definitions as context
            context_text = "\n\n".join([d["text"] for d in defs[:3]])
            answer = await ask_ollama(user_question, context_text, defs, context.user_data["lang"])
            return await _send_paginated(update, context, answer)
    
    # 5. Normal LLM Call
    combined = build_combined_excerpts(all_chunks[:MAX_EXCERPTS])
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    answer = await ask_ollama(user_question, combined, all_chunks, context.user_data["lang"])
    
    # 6. Paginated Response
    await _send_paginated(update, context, answer)
```

**Pagination**:
```python
async def _send_paginated(update, context, text):
    pages = _split_pages(text, max_len=3600)  # Smart splitting by paragraphs
    if len(pages) == 1:
        await update.message.reply_text(pages[0], parse_mode=ParseMode.HTML, protect_content=PROTECT_CONTENT)
    else:
        user_pages_state[user_id] = {'pages': pages, 'idx': 0, 'html': True}
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
            InlineKeyboardButton("▶️ Next", callback_data="page_next")
        ]])
        await update.message.reply_text(
            pages[0] + f"\n\n📄 1/{len(pages)}",
            reply_markup=kb,
            parse_mode=ParseMode.HTML,
            protect_content=PROTECT_CONTENT
        )
```

**Callback Query Handling** (Pagination):
```python
async def button_callback(update, context):
    q = update.callback_query
    await q.answer()
    
    if q.data in ("page_prev", "page_next"):
        st = user_pages_state.get(q.from_user.id) or {}
        pages = st.get("pages") or []
        idx = st.get("idx", 0)
        
        if q.data == "page_prev":
            idx = max(0, idx - 1)
        else:
            idx = min(len(pages) - 1, idx + 1)
        
        if idx == st.get("idx"):  # No change
            return
        
        st["idx"] = idx
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
            InlineKeyboardButton("▶️ Next", callback_data="page_next")
        ]])
        await q.edit_message_text(
            pages[idx] + f"\n\n📄 {idx+1}/{len(pages)}",
            reply_markup=kb,
            parse_mode=ParseMode.HTML
        )
```

**Log Sanitization** (_CensorFilter):
```python
class _CensorFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Censor tokens, URLs, secrets
        msg = re.sub(r"\d{8,}:[A-Za-z0-9_\-]{20,}", "[CENSORED]", msg)  # Telegram token
        msg = re.sub(r"https?://[^\s]+\.ngrok-free\.app[^\s]*", "[CENSORED]", msg)  # ngrok URL
        msg = re.sub(re.escape(WEBHOOK_SECRET), "[CENSORED]", msg)  # Webhook secret
        record.msg = msg
        record.args = ()
        return True
```

**Konfiguration**:
```bash
MAX_EXCERPTS=12                # Max chunks to LLM
PROTECT_CONTENT=1              # Prevent screenshots/forwarding
MAX_UPDATE_CONCURRENCY=10      # Parallel updates
```

---

### 3.5 FS-005: Screenshot-Funktion

**Lastenheft-Referenz**: FA-007

**Beschreibung**: Interaktive Seiten-/Tabellen-/Abbildungs-Rendering.

**Komponenten**: `handlers1.py`, `pdf_parser.py`

**Workflow**:
1. **User**: `/screenshot`
2. **Bot**: `screenshot_command()` → Document selection keyboard
3. **User**: Click document button (callback `shot_doc:N`)
4. **Bot**: Set state `awaiting_target`, prompt for target
5. **User**: Enter target ("Seite 10", "Tabelle 3", "Abbildung H.2")
6. **Bot**: `handle_message()` → `_is_screenshot_target_query()` → Extract target
7. **Rendering**: `get_page_image_bytes(pdf_path, page, dpi=180)` → PNG bytes
8. **Bot**: `send_photo(chat_id, photo=PNG, caption=..., protect_content=True)`

**Target Detection Patterns**:
```python
def _is_screenshot_target_query(text):
    if re.search(r"(?i)\b(seite|page)\s*\d+\b", text):
        return True  # "Seite 10", "Page 42"
    if re.search(r"(?i)\b(tab(?:elle)?|table)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", text):
        return True  # "Tabelle 3", "Table A.2"
    if re.search(r"(?i)\b(fig(?:ure)?|abbildung)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", text):
        return True  # "Abbildung 2", "Figure H-3"
    return False
```

**Page Rendering**:
```python
def get_page_image_bytes(pdf_path, page_num, dpi=180):
    images = pdf2image.convert_from_path(
        pdf_path,
        first_page=page_num,
        last_page=page_num,
        dpi=dpi,
        fmt='PNG'
    )
    if not images:
        return b""
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue()
```

**Title Extraction** (for Table/Figure lookup):
```python
def extract_titles_from_pdf(pdf_path):
    titles = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            for line in text.splitlines():
                if re.match(r'^(Figure|Abbildung|Table|Tabelle)\s*', line, re.I):
                    titles.append({"title": line, "page": i+1, "type": "title"})
    return titles
```

**State Management**:
```python
SCREENSHOT_STATE[user_id] = {
    "mode": "awaiting_target",  # or "pick_doc"
    "doc": "/app/pdfs/ISO_21434.pdf"
}
```

**Multi-Match Selection**:
Wenn mehrere Tabellen/Abbildungen zum Keyword passen:
```python
hits = [t for t in titles if keyword in t["title"].lower()]
if len(hits) > 1:
    # Show selection keyboard
    rows = [
        [InlineKeyboardButton(
            f"S.{h['page']}: {h['title'][:40]}",
            callback_data=f"shot_goto:{doc_idx}:{h['page']}"
        )]
        for h in hits[:10]
    ]
    await update.message.reply_text("Mehrere Treffer – bitte wählen:", reply_markup=InlineKeyboardMarkup(rows))
```

**Konfiguration**:
```bash
# No specific config, uses pdf2image defaults
# DPI hardcoded: 180 (balance between quality and speed)
```

**Performance**:
- **Rendering**: 200-500ms per page (depends on complexity)

---

## 4. Datenmodell

### 4.1 Vector Store Schema

**Collection**: `pdf_chunks`

**Document**:
```json
{
  "id": "a3f8d92c_chunk_42",
  "document": "Text content of chunk...",
  "embedding": [0.123, -0.456, 0.789, ...],  // 384-dim vector
  "metadata": {
    "doc_id": "/app/pdfs/ISO_21434.pdf",
    "source": "/app/pdfs/ISO_21434.pdf",
    "chunk_id": "a3f8d92c_chunk_42",
    "chunk_index": 42,
    "total_chunks": 150,
    "type": "pdf",
    "doc_version": "12345678-1706371200"
  }
}
```

**Index**: HNSW (Hierarchical Navigable Small World)  
**Distance Metric**: Cosine Similarity

---

### 4.2 User State Schema

**Pagination State** (`user_pages_state`):
```python
user_pages_state[123456789] = {
    'pages': ["page 1 text", "page 2 text", ...],  # List of page strings
    'idx': 0,                                       # Current page index
    'html': True,                                   # HTML parse mode
    'last_message_id': 456                          # Telegram message ID
}
```

**Screenshot State** (`SCREENSHOT_STATE`):
```python
SCREENSHOT_STATE[123456789] = {
    'mode': 'awaiting_target',                      # or 'pick_doc'
    'doc': '/app/pdfs/ISO_21434.pdf'                # Selected PDF path
}
```

---

### 4.3 Retrieval Result Schema

**Chunk Dict**:
```python
{
    "doc_id": "/app/pdfs/ISO_21434.pdf",
    "chunk_id": "a3f8d92c_chunk_42",
    "chunk_index": 42,
    "text": "TARA - Threat Analysis and Risk Assessment is a process...",
    "similarity_score": 0.87,
    "metadata": {
        "source": "/app/pdfs/ISO_21434.pdf",
        "total_chunks": 150,
        "doc_version": "12345678-1706371200"
    }
}
```

---

## 5. Schnittstellenspezifikation

### 5.1 Telegram Bot API

**Inbound**: POST `/webhook/{WEBHOOK_SECRET}`

**Request**:
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 456,
    "from": {"id": 789, "first_name": "Alice", ...},
    "chat": {"id": 789, "type": "private", ...},
    "text": "Was ist TARA?"
  }
}
```

**Response**: `200 OK` (immediate, processing continues async)

---

**Outbound**: Telegram Bot API Calls

**Send Message**:
```python
await update.message.reply_text(
    text="<b>TARA</b> - Threat Analysis...",
    parse_mode=ParseMode.HTML,
    reply_markup=keyboard,
    protect_content=True
)
```

**Send Photo**:
```python
await context.bot.send_photo(
    chat_id=update.effective_chat.id,
    photo=io.BytesIO(png_bytes),
    caption="📄 ISO 21434 – Seite 42",
    protect_content=True
)
```

---

### 5.2 Ollama API

**POST** `{OLLAMA_URL}/api/chat`

**Request**:
```json
{
  "model": "qwen2.5:7b-instruct",
  "messages": [
    {"role": "system", "content": "Antworte AUSSCHLIESSLICH..."},
    {"role": "user", "content": "FRAGE:\nWas ist TARA?\n\nEXCERPTS:\n..."}
  ],
  "options": {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_predict": 3500,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "num_ctx": 2048
  },
  "stream": false
}
```

**Response**:
```json
{
  "message": {
    "role": "assistant",
    "content": "<b>TARA - Threat Analysis and Risk Assessment</b>\n\nTARA ist..."
  },
  "done": true,
  "total_duration": 12345678900,
  "prompt_eval_count": 512,
  "eval_count": 256
}
```

---

### 5.3 ChromaDB (Embedded)

**Add Embeddings**:
```python
collection.add(
    documents=["Text chunk 1", "Text chunk 2", ...],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...], ...],
    metadatas=[{"doc_id": "...", ...}, {"doc_id": "...", ...}, ...],
    ids=["hash_chunk_0", "hash_chunk_1", ...]
)
```

**Query**:
```python
results = collection.query(
    query_embeddings=[[0.5, 0.6, ...]],
    n_results=10,
    where={"source": "/app/pdfs/ISO_21434.pdf"},  # Optional filter
    include=["documents", "metadatas", "distances"]
)
```

**Response**:
```python
{
    "ids": [["hash_chunk_42", "hash_chunk_15", ...]],
    "documents": [["Text content...", "More text...", ...]],
    "metadatas": [[{"doc_id": "...", ...}, {...}, ...]],
    "distances": [[0.234, 0.456, ...]]  # Cosine distance (0=identical, 2=opposite)
}
```

---

## 6. Technisches Design

### 6.1 Deployment-Architektur

**Docker-Container** (Single-Container-Deployment):
```
┌─────────────────────────────────────────────────┐
│  Docker Container: telegram-pdf-bot:latest      │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Python 3.11 + Dependencies               │  │
│  │  - FastAPI + Uvicorn (Port 8000)          │  │
│  │  - python-telegram-bot 20.7               │  │
│  │  - ChromaDB 0.4.22                        │  │
│  │  - sentence-transformers 2.7.0            │  │
│  │  - PyPDF2, pdfplumber, pytesseract        │  │
│  │  - Tesseract OCR 5.x (system package)     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Volume Mounts:                                 │
│  - ./pdfs → /app/pdfs (Read-Only)              │
│  - ./chroma_db → /app/chroma_db (Read-Write)   │
│                                                 │
│  Resource Limits:                               │
│  - Memory: 12 GB                                │
│  - CPU: 2.0 cores                               │
└─────────────────────────────────────────────────┘
         │
         ├─► Telegram API (HTTPS outbound)
         │
         └─► Ollama (http://host.docker.internal:11434)
```

---

### 6.2 Sicherheitskonzept

**1. Secrets Management**:
- Telegram-Token via `TELEGRAM_TOKEN` Umgebungsvariable
- Webhook-Secret via `WEBHOOK_SECRET`
- Niemals hartkodiert, niemals in Git committed
- Log-Sanitization via `_CensorFilter`

**2. Network Security**:
- Webhook-Secret in URL-Pfad (verhindert unautorisierten Zugriff)
- Bind auf `127.0.0.1:8000` (nur lokal, Reverse-Proxy erforderlich)
- Read-Only-Mount für PDFs (verhindert Manipulation)

**3. Content Protection**:
- `protect_content=True` auf allen Telegram-Nachrichten
- Verhindert Screenshots/Forwarding durch User

**4. Container-Isolation**:
- Docker-Netzwerk-Isolation
- Keine Privileged-Mode
- Non-Root-User möglich (optional)

---

### 6.3 Performance-Optimierung

**1. Async-First-Design**:
- FastAPI async endpoints
- `asyncio.create_task()` für Background-Processing
- `asyncio.to_thread()` für Blocking-Calls (ChromaDB, sentence-transformers)

**2. Concurrency Control**:
- Semaphore für Updates (`MAX_UPDATE_CONCURRENCY`)
- Semaphore für Indexing (`INDEX_CONCURRENCY`)
- Semaphore für OCR (`OCR_CONCURRENCY`)

**3. Batch Processing**:
- Embedding-Generierung in Batches (16-32)
- ChromaDB-Adds in Batches (4)

**4. Caching**:
- ChromaDB persistent (kein Re-Embedding bei Restart)
- Embedding-Modell geladen bei Startup (nicht pro Request)

**5. Progressive Retrieval**:
- Initial: 6x requested chunks
- Widening: 20x, dann 40x bei Bedarf
- Early Exit bei ausreichenden Ergebnissen

---

## 7. Testkonzept

### 7.1 Unit-Tests

**Module**: `tests/unit/`

**Test Coverage**:
- `test_acronym_utils.py`: Acronym detection logic
- `test_pdf_parser.py`: Text normalization, chunking
- `test_vector_store.py`: Embedding, search, filtering
- `test_retrieval.py`: Definition extraction, term filtering
- `test_llm_client.py`: Prompt generation, response normalization

**Beispiel** (test_acronym_utils.py):
```python
def test_detect_acronym():
    assert detect_acronym("Was ist TARA?") == "TARA"
    assert detect_acronym("Explain ISO 21434") == "ISO"
    assert detect_acronym("CAN bus security") == "CAN"
    assert detect_acronym("What is the weather?") is None
```

**Ausführung**:
```bash
pytest tests/unit/ -v
```

---

### 7.2 Integrations-Tests

**Module**: `tests/integration/`

**Test Coverage**:
- `test_indexing.py`: End-to-end PDF indexing
- `test_retrieval_flow.py`: Query → Retrieval → LLM flow
- `test_telegram_handlers.py`: Command + message handling

**Beispiel** (test_retrieval_flow.py):
```python
@pytest.mark.asyncio
async def test_query_flow():
    # Index test PDF
    await ensure_document_indexed("tests/data/test.pdf")
    
    # Query
    chunks = await get_best_chunks_global("What is TARA?", max_chunks=5)
    
    # Assertions
    assert len(chunks) > 0
    assert any("TARA" in c["text"] for c in chunks)
    assert all(c["similarity_score"] > 0.15 for c in chunks)
```

**Ausführung**:
```bash
pytest tests/integration/ -v -m integration
```

---

### 7.3 End-to-End-Tests

**Module**: `tests/e2e/`

**Test Coverage**:
- `test_telegram_bot.py`: Simulate Telegram updates, check responses

**Beispiel**:
```python
@pytest.mark.asyncio
async def test_start_command():
    update = create_mock_update(text="/start")
    await start_command(update, context)
    
    # Check reply
    assert update.message.reply_text.called
    assert "Willkommen" in update.message.reply_text.call_args[0][0]
```

**Ausführung**:
```bash
pytest tests/e2e/ -v -m e2e
```

---

### 7.4 Performance-Tests

**Tools**: `pytest-benchmark`, `locust`

**Metriken**:
- Indexing: Seiten/Minute
- Retrieval: Latenz (ms)
- LLM: Response Time (s)
- End-to-End: User Request → Response (s)

**Beispiel** (pytest-benchmark):
```python
def test_embedding_performance(benchmark):
    texts = ["Test text"] * 100
    result = benchmark(embedder.encode, texts, batch_size=16)
    # Target: <500ms for 100 texts
```

**Load Test** (locust):
```python
class BotUser(HttpUser):
    @task
    def query_bot(self):
        self.client.post("/webhook/secret123", json={
            "update_id": random.randint(1, 1000000),
            "message": {"text": "What is TARA?", ...}
        })
```

---

### 7.5 Abnahme-Tests

**Referenz**: Lastenheft Kap. 9

**Checkliste**:
- [ ] FA-001: PDF-Indexierung funktioniert
- [ ] FA-002: Semantische Suche findet relevante Chunks
- [ ] FA-003: Alle Telegram-Befehle funktionieren
- [ ] FA-004: Freitextanfragen werden beantwortet
- [ ] FA-005: Deutsch/Englisch automatisch erkannt
- [ ] FA-006: Akronym-Definitionen priorisiert
- [ ] FA-007: Screenshot-Funktion rendert Seiten
- [ ] FA-008: Lange Antworten paginiert
- [ ] FA-009: Hintergrund-Indexierung non-blocking
- [ ] FA-010: `/health` endpoint erreichbar
- [ ] NFA-001: 95% Antworten <15s
- [ ] NFA-002: 10-50 concurrent users supported
- [ ] NFA-003: 99% Uptime (7-Tage-Test)
- [ ] NFA-005: 100% lokale Verarbeitung (keine ext. APIs)
- [ ] NFA-006: Secrets nicht geloggt
- [ ] NFA-007: `protect_content=True` auf Nachrichten

---

## 8. Deployment-Konzept

### 8.1 Deployment-Schritte

**Voraussetzungen**:
1. Docker + Docker Compose installiert
2. Telegram Bot Token erstellt
3. Öffentliche Webhook-URL (HTTPS)
4. Ollama installiert und Modell gepullt

**Schritte**:
```bash
# 1. Repository klonen
git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot

# 2. .env konfigurieren
cat > .env << 'EOF'
TELEGRAM_TOKEN=your_token_here
WEBHOOK_URL=https://your-domain.com
WEBHOOK_SECRET=$(openssl rand -hex 16)
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
EOF

# 3. PDFs kopieren
mkdir -p pdfs
cp /path/to/*.pdf pdfs/

# 4. Ollama starten
ollama pull qwen2.5:7b-instruct
ollama serve &

# 5. Bot bauen und starten
docker-compose up -d --build

# 6. Logs prüfen
docker-compose logs -f bot

# 7. Health Check
curl http://localhost:8000/health

# 8. Bot in Telegram testen
# - /start
# - "Was ist TARA?"
```

---

### 8.2 Produktions-Konfiguration

**docker-compose.yml** (Production):
```yaml
services:
  bot:
    image: telegram-pdf-bot:latest
    restart: unless-stopped
    env_file: .env
    environment:
      LOG_LEVEL: INFO
      MAX_UPDATE_CONCURRENCY: 20
      INDEX_CONCURRENCY: 2
    volumes:
      - ./pdfs:/app/pdfs:ro
      - ./chroma_db:/app/chroma_db
    ports:
      - "127.0.0.1:8000:8000"
    mem_limit: 12g
    cpus: "4.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### 8.3 Monitoring

**Health Check**:
```bash
while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$STATUS" -ne 200 ]; then
        echo "$(date): Health check failed (HTTP $STATUS)"
        docker-compose restart bot
    fi
    sleep 60
done
```

**Logs**:
```bash
# Docker Compose Logs
docker-compose logs -f bot | grep -i "error\|exception"

# Systemd-Service (optional)
journalctl -u telegram-bot -f
```

**Metriken** (optional):
- Prometheus Exporter für Bot-Metriken
- Grafana Dashboard: Query Rate, Response Time, Error Rate

---

### 8.4 Backup & Recovery

**Backup**:
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf backup-chroma-$DATE.tar.gz chroma_db/
tar -czf backup-pdfs-$DATE.tar.gz pdfs/
cp .env backup-env-$DATE.env
```

**Cron** (täglich um 2 Uhr):
```cron
0 2 * * * /opt/telegram-chat-bot/backup.sh
```

**Recovery**:
```bash
# Restore ChromaDB
tar -xzf backup-chroma-20240127.tar.gz

# Restore PDFs
tar -xzf backup-pdfs-20240127.tar.gz

# Restore Config
cp backup-env-20240127.env .env

# Restart Bot
docker-compose restart bot
```

---

## Anhang

### A. Technologie-Entscheidungen

| Entscheidung | Begründung |
|--------------|------------|
| **Python 3.11** | Moderne Async-Features, große ML/AI-Bibliotheken-Ökosystem |
| **FastAPI** | Schnell, async-native, OpenAPI-Docs, WebSocket-Support |
| **python-telegram-bot** | Vollständige Bot-API-Abdeckung, aktive Community |
| **ChromaDB** | Open-Source, embedded, gut skalierbar, einfache API |
| **sentence-transformers** | CPU-friendly, gute Qualität, keine GPU erforderlich |
| **Ollama** | Lokales LLM, GPU-optional, einfache API, viele Modelle |
| **Docker** | Portabilität, Reproduzierbarkeit, einfaches Deployment |

---

### B. Offene Punkte & Future Work

1. **Multi-User-Isolation**: Separate Document-Sets pro User
2. **Admin-Panel**: Web-GUI für Document-Management
3. **Erweiterte OCR**: Tesseract-Feintuning für Automotive-Docs
4. **GPU-Embeddings**: Optional CUDA-Beschleunigung für sentence-transformers
5. **Weitere Sprachen**: FR, ES, IT Support
6. **Export-Funktion**: Konversationen als PDF/Markdown exportieren

---

### C. Versionierung

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 27.01.2024 | Initial Release |

---

**Dokument-Ende**
