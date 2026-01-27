# Telegram PDF Chatbot - API Documentation

**Version:** 1.0  
**Date:** 2024-01-27  
**Status:** Final

---

## Table of Contents

1. [Telegram Bot API](#1-telegram-bot-api)
2. [Internal APIs](#2-internal-apis)
3. [External Dependencies](#3-external-dependencies)
4. [Webhook & HTTP Endpoints](#4-webhook--http-endpoints)
5. [Error Handling](#5-error-handling)

---

## 1. Telegram Bot API

### 1.1 Commands

#### `/start`
**Purpose**: Initialize bot interaction, show welcome message

**Syntax**: `/start`

**Response**:
```
Willkommen beim Automotive-Cybersecurity-Bot.

So funktioniert es:
1️⃣ Drücke /Start.
2️⃣ Stelle deine Frage oder nutze /screenshot für Seiten/Bilder/Tabellen.
⚠️ Hinweis: Die Dokumenteninhalte sind vertraulich.
```

**Reply Keyboard**: `[/start, /screenshot]`

**Implementation**: `handlers1.start_command()`

---

#### `/help`
**Purpose**: Display help information

**Syntax**: `/help`

**Response**:
```
Hilfe: /start (Startmenü) • /status (Index) • /screenshot (Seite/Bild/Tabelle).
```

**Implementation**: `handlers1.help_command()`

---

#### `/status`
**Purpose**: Show system status and indexing progress

**Syntax**: `/status`

**Response**:
```
VectorStore chunks: 1234
Persist dir: /app/chroma_db
Preindex: running=False, done=5/5
```

**Fields**:
- `total_chunks`: Number of indexed text chunks
- `persist_directory`: ChromaDB storage location
- `preindex_running`: Background indexing active (true/false)
- `preindex_done/total`: Indexing progress counter

**Implementation**: `handlers1.status_command()`

---

#### `/screenshot`
**Purpose**: Interactive page/table/figure screenshot workflow

**Syntax**: `/screenshot`

**Workflow**:
1. User: `/screenshot`
2. Bot: Document selection keyboard
3. User: Selects document
4. Bot: Prompt for target ("Seite 10", "Tabelle 3", etc.)
5. User: Target specification
6. Bot: Rendered page image (PNG)

**Supported Targets**:
- **Page numbers**: `Seite 10`, `Page 10`
- **Tables**: `Tabelle 3`, `Table 3`, `Table A.2`
- **Figures**: `Abbildung 2`, `Figure 2`, `Figure H-3`
- **Keywords**: Free text search in titles

**Screenshot Mode State Machine**:
```
IDLE
  ↓ /screenshot
PICK_DOC (show document keyboard)
  ↓ callback: shot_doc:N
AWAITING_TARGET (prompt for page/table/figure)
  ↓ text message matching target pattern
SEND_IMAGE → IDLE
```

**Implementation**: 
- `handlers1.screenshot_command()`
- `handlers1.button_callback()` (shot_* callbacks)
- `handlers1.handle_message()` (target detection)

---

### 1.2 Natural Language Queries

#### Text Message Handling

**Purpose**: Answer questions about PDF content

**Input**: Any text message (not starting with `/`)

**Processing Flow**:
1. **Language Detection**:
   - German keywords: `was`, `ist`, `sind`, `wie`, `ä`, `ö`, `ü`, `ß`
   - English: default if no German markers
   - Sets `context.user_data["lang"]` to `"DE"` or `"EN"`

2. **Index Check**:
   - Verify at least one PDF is indexed
   - If not: schedule indexing, prompt user to retry

3. **Semantic Search**:
   - Global retrieval across all PDFs
   - Per-document fallback if insufficient results
   - Acronym detection and definition prioritization

4. **LLM Generation**:
   - Context: top N excerpts (default: 12)
   - Prompt: system + user (see llm_client.py)
   - Output: HTML-formatted answer

5. **Response Formatting**:
   - Pagination if >3600 chars
   - Inline keyboard for navigation
   - Parse mode: HTML

**Examples**:
```
User: "Was ist TARA in ISO 21434?"
Bot: <b>TARA - Threat Analysis and Risk Assessment</b>
     TARA ist ein Prozess zur Identifizierung...
     
     [◀️ Prev] [▶️ Next]

User: "Explain the CAL levels"
Bot: <b>Cybersecurity Assurance Levels (CAL)</b>
     CAL defines four levels (1-4) of cybersecurity requirements...
```

**Implementation**: `handlers1.handle_message()`

---

### 1.3 Callback Queries (Inline Buttons)

#### Pagination Callbacks

**`page_prev`**:
- Navigate to previous page of long answer
- Updates message with new page content
- Maintains state in `user_pages_state`

**`page_next`**:
- Navigate to next page
- Similar to `page_prev`

**State**:
```python
user_pages_state[user_id] = {
    'pages': ["page 1 text", "page 2 text", ...],
    'idx': 0,  # current page index
    'html': True,  # HTML parse mode
    'last_message_id': 12345
}
```

#### Screenshot Workflow Callbacks

**`shot_start`**:
- Enter screenshot mode
- Show document selection keyboard

**`shot_doc:N`** (N = document index):
- User selected document N
- Set state: `awaiting_target`, store selected PDF path
- Prompt for page/table/figure

**`shot_goto:N:P`** (N = doc index, P = page):
- Direct navigation to page P of document N
- Render and send page image
- Used for multi-match selection

**Implementation**: `handlers1.button_callback()`

---

## 2. Internal APIs

### 2.1 llm_client Module

#### `ask_ollama()`
```python
async def ask_ollama(
    question: str,
    context: str,
    chunks_info: List[Dict] | None = None,
    target_language: str | None = None
) -> str
```

**Purpose**: Generate LLM answer from retrieved context

**Parameters**:
- `question`: User's original query
- `context`: Combined excerpts from vector search
- `chunks_info`: Metadata of retrieved chunks (optional, for advanced prompting)
- `target_language`: `"DE"` or `"EN"` (auto-detected if None)

**Returns**: HTML-formatted answer string

**Process**:
1. Build system + user prompts
2. Call Ollama chat API
3. Detect truncation (incomplete response)
4. Continuation prompts if needed (max 2 retries)
5. Normalize Markdown→HTML
6. Return sanitized response

**Error Handling**:
- Connection errors: return `"INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."`
- Timeout: handled by aiohttp.ClientTimeout (180s)
- Malformed JSON: fallback to raw text

**Configuration**:
- `OLLAMA_URL`: Endpoint
- `OLLAMA_MODEL`: Model name
- `OLLAMA_NUM_CTX`: Context window
- `MAX_TOKENS`: Max generation length
- `TEMPERATURE`, `TOP_P`, `TOP_K`: Sampling params

---

#### `test_ollama_connection()`
```python
async def test_ollama_connection() -> bool
```

**Purpose**: Health check for Ollama availability

**Returns**: `True` if Ollama `/api/tags` responds with HTTP 200

**Usage**: Called on bot startup (bot.py lifespan)

---

### 2.2 vector_store Module

#### `add_chunks()`
```python
def add_chunks(
    doc_id: str,
    chunks: List[str],
    metadata: Optional[Dict] = None
) -> bool
```

**Purpose**: Add pre-split text chunks to vector store

**Parameters**:
- `doc_id`: Document identifier (usually PDF path)
- `chunks`: List of text segments
- `metadata`: Additional metadata (e.g., `doc_version`, `source`)

**Process**:
1. Quality filtering (length, alpha ratio)
2. Batch embedding generation (sentence-transformers)
3. Add to ChromaDB collection with metadata
4. Persist to disk

**Returns**: `True` on success, `False` on failure

---

#### `search_in_document()`
```python
def search_in_document(
    query: str,
    doc_id: str,
    n_results: int = 5,
    *,
    similarity_threshold: Optional[float] = None
) -> List[Dict]
```

**Purpose**: Semantic search within a single document

**Parameters**:
- `query`: Search query
- `doc_id`: Target document identifier
- `n_results`: Number of results to return
- `similarity_threshold`: Min cosine similarity (default: 0.15)

**Returns**: List of chunk dicts:
```python
[
    {
        "doc_id": "path/to/doc.pdf",
        "chunk_id": "hash_chunk_42",
        "chunk_index": 42,
        "text": "Chunk content...",
        "similarity_score": 0.87,
        "metadata": {...}
    },
    ...
]
```

**Features**:
- Acronym boosting (+0.30 if term found in text)
- Definition prioritization (regex patterns)
- Progressive widening if <5 results

---

#### `search_global()`
```python
def search_global(
    query: str,
    n_results: int = 5,
    *,
    similarity_threshold: Optional[float] = None
) -> List[Dict]
```

**Purpose**: Semantic search across all indexed documents

**Similar to `search_in_document()` but without `doc_id` filter**

---

#### `has_document()`
```python
def has_document(doc_id: str) -> bool
```

**Purpose**: Check if document is indexed

**Returns**: `True` if at least one chunk exists for `doc_id`

---

#### `get_document_version()`
```python
def get_document_version(doc_id: str) -> Optional[str]
```

**Purpose**: Retrieve stored version hash of document

**Returns**: Version string (format: `"{size}-{mtime}"`) or `None`

---

### 2.3 retrieval Module

#### `get_best_chunks_for_document()`
```python
async def get_best_chunks_for_document(
    query: str,
    doc_id: str,
    max_chunks: int = 4
) -> List[Dict]
```

**Purpose**: High-level retrieval for a single document

**Process**:
1. Base retrieval (n_results = max_chunks * 3)
2. Acronym detection
3. Definition extraction (if acronym found)
4. Term filtering (exact matches)
5. Progressive widening if <5 results

**Returns**: Top `max_chunks` ranked by relevance

---

#### `get_best_chunks_global()`
```python
async def get_best_chunks_global(
    query: str,
    max_chunks: int = 12
) -> List[Dict]
```

**Purpose**: High-level retrieval across all documents

**Similar logic to per-document, but global scope**

---

#### `build_combined_excerpts()`
```python
def build_combined_excerpts(chunks: List[Dict]) -> str
```

**Purpose**: Format chunks into LLM prompt context

**Output Format**:
```
EXCERPT 1:
<sanitized chunk 1 text>
---
EXCERPT 2:
<sanitized chunk 2 text>
---
...
```

**Sanitization**:
- Remove figure/clause headers (not table headers)
- Deduplicate lines
- Truncate to 800 chars per chunk

---

#### `find_definition_in_chunks()`
```python
def find_definition_in_chunks(
    term: str,
    chunks: List[Dict]
) -> List[Dict]
```

**Purpose**: Extract definition-like sentences for a term

**Patterns**:
- `TERM - definition text`
- `TERM: definition text`
- `TERM (definition text)`
- Standard titles (ISO/SAE patterns)

**Returns**: Ranked definitions (prefer concise, filter bad words)

---

### 2.4 pdf_parser Module

#### `extract_paragraphs_from_pdf()`
```python
def extract_paragraphs_from_pdf(pdf_path: str) -> List[str]
```

**Purpose**: Extract text paragraphs from PDF

**Returns**: List of cleaned, normalized paragraphs

**Synchronous wrapper**: Uses `asyncio.run()` internally for compatibility with non-async contexts

**Async version**: `pdf_parser.extract_paragraphs_from_pdf()` (call directly if event loop active)

---

#### `extract_titles_from_pdf()`
```python
def extract_titles_from_pdf(pdf_path: str) -> List[Dict]
```

**Purpose**: Extract page titles/headings for screenshot feature

**Returns**:
```python
[
    {
        "title": "Figure 3.2 - System Overview",
        "page": 42,
        "type": "title"
    },
    ...
]
```

**Patterns**: `Figure`, `Abbildung`, `Table`, `Tabelle`, numbered sections

---

#### `get_page_image_bytes()`
```python
def get_page_image_bytes(
    pdf_path: str,
    page_num: int,
    dpi: int = 180
) -> bytes
```

**Purpose**: Render PDF page as PNG image

**Returns**: PNG bytes (or empty bytes on error)

**Usage**: Screenshot feature

---

### 2.5 indexer Module

#### `schedule_index()`
```python
def schedule_index(document_name: str) -> None
```

**Purpose**: Queue document for background indexing

**Non-blocking**: Returns immediately, task runs in background

**State Tracking**: Updates `preindex_inflight`, `preindex_total`, `preindex_done`

---

#### `ensure_document_indexed()`
```python
async def ensure_document_indexed(document_name: str) -> None
```

**Purpose**: Index document if missing or outdated

**Process**:
1. Compute version hash (size + mtime)
2. Check existing version
3. Delete old index if version changed
4. Extract paragraphs (pdf_parser)
5. Add chunks to vector store
6. Persist

**Concurrency Control**: Per-document lock to prevent duplicate indexing

---

### 2.6 acronym_utils Module

#### `detect_acronym()`
```python
def detect_acronym(text: str) -> Optional[str]
```

**Purpose**: Detect likely acronym/term in query

**Algorithm**:
1. Tokenize (2-20 char words)
2. Filter stop words
3. Score: +2 (has digit), +1 (uppercase), +3 (preferred term)
4. Return highest scored

**Preferred Terms**: `CAN`, `CAN-FD`, `OEM`, `RASIC`, `CAL`, `ISO`, `SAE`

**Examples**:
- `"What is ISO 21434?"` → `"ISO"`
- `"Explain TARA process"` → `"TARA"`
- `"CAN bus security"` → `"CAN"`

---

## 3. External Dependencies

### 3.1 Ollama API

**Base URL**: Configured via `OLLAMA_URL` (default: `http://localhost:11434`)

#### POST `/api/chat`
**Purpose**: Generate chat completion

**Request**:
```json
{
  "model": "qwen2.5:7b-instruct",
  "messages": [
    {"role": "system", "content": "System prompt..."},
    {"role": "user", "content": "User query..."}
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
    "content": "Generated answer..."
  },
  "done": true
}
```

**Used by**: `llm_client._call_ollama_chat()`

---

#### POST `/api/generate`
**Purpose**: Generate completion (fallback if chat API fails)

**Request**:
```json
{
  "model": "qwen2.5:7b-instruct",
  "prompt": "<<SYS>>System prompt\n<</SYS>>\nUser query",
  "options": {...},
  "stream": false
}
```

**Response**:
```json
{
  "response": "Generated text...",
  "done": true
}
```

**Used by**: `llm_client._call_ollama_api()`

---

#### GET `/api/tags`
**Purpose**: List available models (health check)

**Response**:
```json
{
  "models": [
    {"name": "qwen2.5:7b-instruct", "size": 4370000000, ...},
    ...
  ]
}
```

**Used by**: `llm_client.test_ollama_connection()`

---

### 3.2 Telegram Bot API

**Base URL**: `https://api.telegram.org/bot<TOKEN>`

#### POST `/setWebhook`
**Purpose**: Register webhook URL

**Request**:
```json
{
  "url": "https://bot.example.com/webhook/secret123",
  "drop_pending_updates": true,
  "allowed_updates": ["message", "callback_query"]
}
```

**Used by**: `bot.setup_webhook()`

---

#### POST `/sendMessage`
**Purpose**: Send text message

**Request**:
```json
{
  "chat_id": 123456789,
  "text": "Message content",
  "parse_mode": "HTML",
  "reply_markup": {...},
  "protect_content": true
}
```

**Used by**: `update.message.reply_text()` (python-telegram-bot wrapper)

---

#### POST `/sendPhoto`
**Purpose**: Send image

**Request** (multipart/form-data):
```
chat_id=123456789
photo=<binary PNG data>
caption=Page 42
protect_content=true
```

**Used by**: `context.bot.send_photo()` (screenshot feature)

---

#### POST `/editMessageText`
**Purpose**: Update existing message (pagination)

**Request**:
```json
{
  "chat_id": 123456789,
  "message_id": 456,
  "text": "Updated content",
  "reply_markup": {...}
}
```

**Used by**: `callback_query.edit_message_text()`

---

### 3.3 ChromaDB (Embedded)

**No external API**: Embedded Python library

**Database File**: `{CHROMA_DB_DIR}/chroma.sqlite3`

**Collections**:
- `pdf_chunks`: Main vector index
- `page_titles`: Optional title index (if `ENABLE_TITLE_INDEX=1`)

**Methods Used**:
- `collection.add()`: Insert embeddings
- `collection.query()`: Vector similarity search
- `collection.get()`: Metadata retrieval
- `collection.delete()`: Remove documents
- `client.persist()`: Flush to disk

---

## 4. Webhook & HTTP Endpoints

### 4.1 POST `/webhook/{WEBHOOK_SECRET}`

**Purpose**: Receive Telegram updates

**Authentication**: Path-based secret (e.g., `/webhook/secret123`)

**Request Body**:
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 456,
    "from": {"id": 789, "first_name": "Alice", ...},
    "chat": {"id": 789, "type": "private", ...},
    "text": "What is TARA?"
  }
}
```

**Response**: `200 OK` (immediate, processing continues in background)

**Processing**:
1. Parse update with `telegram.Update.de_json()`
2. Create background task with `asyncio.create_task()`
3. Return `200 OK` to Telegram
4. Process update asynchronously

**Concurrency**: Controlled by semaphore (`MAX_UPDATE_CONCURRENCY`)

**Implementation**: `bot.webhook_handler()`

---

### 4.2 GET `/health`

**Purpose**: Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "webhook_configured": true
}
```

**HTTP Status**: Always `200 OK` (if server is running)

**Used by**: Load balancers, monitoring systems

**Implementation**: `bot.health_check()`

---

## 5. Error Handling

### 5.1 User-Facing Errors

| Scenario | Error Message | Action |
|----------|---------------|--------|
| No PDFs indexed | "Keine PDFs vorhanden." | Add PDFs, restart bot |
| Indexing in progress | "Indexierung gestartet im Hintergrund. Prüfe den Fortschritt mit /status..." | Wait, retry later |
| No relevant information | "Keine relevanten Informationen gefunden." | Rephrase query |
| LLM unreachable | "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar." | Check Ollama status |
| Screenshot page not found | "Seite konnte nicht gerendert werden." | Verify page number |

### 5.2 Internal Error Handling

**Telegram API Errors**:
- `BadRequest`: Log warning, skip update
- `NetworkError`: Retry with exponential backoff
- `Unauthorized`: Fatal, bot token invalid

**Ollama Errors**:
- Connection refused: Return error message to user
- Timeout: Return partial response if available
- 400/422: Retry with simplified request (remove `num_predict`)

**ChromaDB Errors**:
- Write failures: Log warning, continue (data may be lost)
- Read failures: Return empty results
- Corruption: Requires manual `chroma_db/` deletion and reindexing

**PDF Parsing Errors**:
- File not found: Skip document, log error
- Encrypted PDF: Skip, log warning
- OCR failure: Fallback to text extraction

### 5.3 Logging

**Log Levels**:
- `DEBUG`: Detailed trace (prompts, chunk details)
- `INFO`: Normal operations (queries, indexing progress)
- `WARNING`: Recoverable errors (API retries, empty results)
- `ERROR`: Serious errors (crashes, data loss)

**Sensitive Data Handling**:
- `_CensorFilter`: Removes tokens, URLs, secrets from logs
- Patterns censored: Telegram tokens, ngrok URLs, webhook secrets

**Log Format**:
```
2024-01-27 12:34:56 - bot - INFO - Question from 123456789: What is TARA?
2024-01-27 12:34:57 - vector_store - INFO - Added 42 chunks for ISO_21434.pdf
2024-01-27 12:34:58 - llm_client - DEBUG - LLM system: Antworte AUSSCHLIESSLICH...
```

---

## Appendix: Quick Reference

### Commands
- `/start` - Initialize bot
- `/help` - Show help
- `/status` - System status
- `/screenshot` - Page rendering

### Internal Modules
- `llm_client` - Ollama integration
- `vector_store` - ChromaDB wrapper
- `retrieval` - Semantic search
- `pdf_parser` - Text extraction
- `indexer` - Background indexing
- `acronym_utils` - Term detection

### External APIs
- **Telegram**: Bot messaging
- **Ollama**: LLM inference (`/api/chat`, `/api/generate`)
- **ChromaDB**: Embedded (no network API)

### HTTP Endpoints
- `POST /webhook/{secret}` - Telegram updates
- `GET /health` - Health check

---

**Document End**
