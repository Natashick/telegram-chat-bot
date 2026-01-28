# Telegram PDF Chatbot - System Architecture

**Version:** 1.0  
**Date:** 2024-01-27  
**Status:** Final

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Principles](#2-architecture-principles)
3. [Component Architecture](#3-component-architecture)
4. [Data Flow](#4-data-flow)
5. [Technology Stack](#5-technology-stack)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Performance Characteristics](#7-performance-characteristics)
8. [Security Architecture](#8-security-architecture)

---

## 1. System Overview

### 1.1 Purpose

The Telegram PDF Chatbot is an intelligent document search and question-answering system that enables users to query multiple PDF documents through a natural language interface via Telegram. The system uses semantic search and local LLM processing to provide accurate, context-aware responses while maintaining complete data privacy.

### 1.2 High-Level Architecture

```
┌─────────────────┐
│  Telegram User  │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────┐
│     FastAPI Webhook Server          │
│  ┌───────────────────────────────┐  │
│  │   bot.py (Application Entry)  │  │
│  └─────────────┬─────────────────┘  │
└────────────────┼────────────────────┘
                 │
         ┌───────┴────────┐
         │                │
         ▼                ▼
┌──────────────┐  ┌──────────────┐
│  handlers1.py│  │ indexer.py   │
│  (Message    │  │ (Background  │
│   Handling)  │  │  Indexing)   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────────┐
│      retrieval.py                │
│  (Semantic Search Orchestration) │
└──────┬────────────────────┬──────┘
       │                    │
       ▼                    ▼
┌─────────────┐      ┌─────────────┐
│ vector_store│      │ llm_client  │
│  (ChromaDB) │      │   (Ollama)  │
└──────┬──────┘      └─────────────┘
       │
       ▼
┌─────────────┐
│ pdf_parser  │
│  (Extraction)│
└─────────────┘
```

### 1.3 Key Features

- **Semantic Search**: Meaning-based document retrieval using vector embeddings
- **Local LLM Processing**: Complete data privacy with Ollama-based inference
- **Multi-Document Support**: Concurrent search across multiple PDFs
- **Bilingual**: Automatic German/English detection and response
- **Acronym Intelligence**: Specialized handling for technical abbreviations (TARA, CAN, ECU, etc.)
- **Screenshot Capability**: Page rendering for visual content
- **Scalable Design**: Async processing with configurable concurrency

---

## 2. Architecture Principles

### 2.1 Design Goals

1. **Privacy First**: All processing happens locally, no external API calls (except Telegram)
2. **Modularity**: Clear separation of concerns between components
3. **Scalability**: Async-first design with semaphore-based concurrency control
4. **Resilience**: Graceful degradation, comprehensive error handling
5. **Performance**: Optimized vector search and LLM token management
6. **Maintainability**: Clean code, extensive logging, configuration-driven behavior

### 2.2 Architectural Patterns

- **Webhook-based Architecture**: FastAPI serves Telegram webhook endpoints
- **Background Task Processing**: Non-blocking async tasks for indexing and queries
- **Vector Store Pattern**: ChromaDB for semantic similarity search
- **Adapter Pattern**: LLM client abstracts Ollama API specifics
- **Strategy Pattern**: Multiple retrieval strategies (per-document, global, acronym-aware)

---

## 3. Component Architecture

### 3.1 bot.py - Application Entry Point

**Purpose**: FastAPI application bootstrapping and webhook handling

**Key Responsibilities**:
- FastAPI app initialization with lifespan management
- Telegram bot application setup
- Webhook registration and request routing
- Startup tasks: Ollama connection test, preindexing trigger
- Concurrency control (semaphore-based update processing)

**Configuration**:
```python
TELEGRAM_TOKEN: str           # Telegram bot token (required)
WEBHOOK_URL: str              # Public webhook URL (required)
WEBHOOK_SECRET: str           # Webhook path secret (default: "secret123")
PORT: int                     # Server port (default: 8000)
HOST: str                     # Bind host (default: "0.0.0.0")
MAX_UPDATE_CONCURRENCY: int   # Max parallel updates (default: 10)
PREINDEX_ENABLED: str         # Auto-preindex on startup (default: "1")
```

**Endpoints**:
- `POST /webhook/{WEBHOOK_SECRET}`: Telegram update handler
- `GET /health`: Health check endpoint

**Data Flow**:
1. Telegram sends update to webhook
2. Update parsed and queued for background processing
3. Semaphore controls concurrent processing
4. Response sent back to Telegram

### 3.2 handlers1.py - Message Handling

**Purpose**: Telegram message processing and command routing

**Key Responsibilities**:
- Command handlers: `/start`, `/help`, `/status`, `/screenshot`
- Natural language query processing
- Language detection (German/English)
- Pagination for long responses
- Screenshot mode state management

**Architecture**:
```python
┌─────────────────────────────┐
│   Telegram Update           │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Language Detection         │
│  (German/English heuristics)│
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Query Routing              │
│  - Commands → handlers      │
│  - Screenshot → state flow  │
│  - Text → Q&A pipeline      │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Retrieval + LLM            │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│  Response Formatting        │
│  - Pagination               │
│  - HTML rendering           │
│  - Protection flags         │
└─────────────────────────────┘
```

**Message Flow**:
1. Receive user message
2. Detect language (DE/EN based on keywords and special chars)
3. Check if PDFs are indexed; schedule indexing if needed
4. Retrieve best chunks (global + per-document fallback)
5. Process acronyms/definitions with priority
6. Call LLM with retrieved context
7. Format and paginate response

**Special Features**:
- **Screenshot Mode**: Multi-step interactive flow for page/table/figure extraction
- **Log Sanitization**: `_CensorFilter` removes tokens, URLs, secrets from logs
- **Pagination**: Intelligent text splitting respecting paragraphs and HTML tags

### 3.3 llm_client.py - LLM Integration

**Purpose**: Ollama LLM API abstraction and prompt engineering

**Key Responsibilities**:
- Ollama API communication (chat & generate endpoints)
- Prompt generation (system + user prompts)
- Response post-processing (Markdown→HTML, truncation detection)
- Token budget management
- Continuation logic for incomplete responses

**Configuration**:
```python
OLLAMA_URL: str              # Ollama endpoint (default: "http://localhost:11434")
OLLAMA_MODEL: str            # Model name (default: "llama3.2:1b")
OLLAMA_NUM_CTX: int          # Context window (default: 1024)
MAX_TOKENS: int              # Max generation tokens (default: 4096)
TEMPERATURE: float           # Sampling temperature (0.1)
TOP_P: float                 # Nucleus sampling (0.9)
DEBUG_PROMPTS: bool          # Log prompts (default: False)
```

**Prompt Engineering**:

**System Prompt (German)**:
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
FRAGE: {user_question}

EXCERPTS (nur diese verwenden):
{context_chunks}

Gib eine strukturierte, sachliche HTML-Antwort mit <b>-Überschriften.
Wenn Tabellen sinnvoll sind, nutze ein ASCII-Raster in <pre>.
```

**Token Management**:
- Short answers: 1500 tokens (default)
- Long answers: 3500 tokens (for "explain", "detailed", "steps", etc.)
- Capped by `MAX_TOKENS` global limit

**Response Processing**:
1. Call Ollama (chat API preferred, fallback to generate)
2. Detect truncation (unfinished sentences, unclosed tags)
3. If truncated: continuation prompt (up to 2 retries)
4. Normalize Markdown→HTML (`**bold**` → `<b>bold</b>`, tables → `<pre>`)
5. Return sanitized response

### 3.4 pdf_parser.py - PDF Extraction

**Purpose**: Robust PDF text extraction with OCR fallback

**Key Responsibilities**:
- Text extraction: PyPDF2 (primary) + pdfplumber (fallback)
- OCR pipeline: pdf2image + Tesseract (optional)
- Text normalization: Unicode, hyphenation, ligatures
- Title/heading extraction for screenshot feature

**Architecture**:

```python
┌────────────────────────┐
│  PDF Input             │
└──────┬─────────────────┘
       │
       ▼
┌────────────────────────┐
│  PyPDF2 Extraction     │
└──────┬─────────────────┘
       │
       ├──► Sufficient? ──Yes──► Normalize → Output
       │
       No
       │
       ▼
┌────────────────────────┐
│  pdfplumber Extraction │
│  (complex layouts)     │
└──────┬─────────────────┘
       │
       ├──► Sufficient? ──Yes──► Normalize → Output
       │
       No (OCR_ENABLED=1)
       │
       ▼
┌────────────────────────┐
│  OCR Pipeline          │
│  - Render @ 180 DPI    │
│  - Preprocess (gray)   │
│  - Tesseract PSM 6     │
└──────┬─────────────────┘
       │
       ├──► Sufficient? ──Yes──► Normalize → Output
       │
       No
       │
       ▼
┌────────────────────────┐
│  OCR Fallback          │
│  - Render @ 240 DPI    │
│  - Tesseract PSM 3     │
└──────┬─────────────────┘
       │
       ▼
    Normalize → Output
```

**Text Normalization** (TextNormalizer class):
1. Unicode normalization (NFKC)
2. Hyphenation removal: `threat-\nanalysis` → `threatanalysis`
3. Newline handling: single `\n` → space, preserve `\n\n` (paragraphs)
4. Ligature replacement: `ﬁ` → `fi`, `ﬂ` → `fl`
5. Whitespace cleanup

**Configuration**:
```python
OCR_ENABLED: int              # Enable OCR (0=off, 1=on)
OCR_CONCURRENCY: int          # Parallel OCR tasks (default: 1)
MIN_PARA_CHARS: int           # Min paragraph length (default: 30)
OCR_NOISE_MAX_RATIO: float    # Max non-alphanumeric ratio (default: 0.7)
```

**Performance**:
- Without OCR: 100-500 pages/min (fast text extraction)
- With OCR: 10-50 pages/min (depends on DPI, language)

### 3.5 vector_store.py - Vector Database

**Purpose**: ChromaDB wrapper for semantic search

**Key Responsibilities**:
- Embedding generation (sentence-transformers, CPU)
- Vector storage and retrieval (ChromaDB persistent)
- Chunking strategy (sliding window)
- Acronym-aware boosting
- Definition prioritization

**Architecture**:

```python
┌─────────────────────────┐
│  Text Input             │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Chunking               │
│  - Size: 800 words      │
│  - Overlap: 160 words   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Quality Filter         │
│  - Min length: 60 chars │
│  - Min alpha ratio: 25% │
│  - Preserve definitions │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Embedding Generation   │
│  (sentence-transformers)│
│  - Batch: 16            │
│  - L2 normalization     │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  ChromaDB Storage       │
│  - Cosine similarity    │
│  - HNSW index           │
└─────────────────────────┘
```

**Chunking Strategy**:
- Fixed word-based chunks (default: 800 words)
- Sliding window with overlap (default: 160 words)
- Quality filters: length, alphanumeric ratio, noise detection
- Special handling: table rows, definitions preserved

**Search Strategy**:

**Per-Document Search**:
```python
def search_in_document(query, doc_id, n_results):
    1. Generate query embedding
    2. Detect acronym (if any)
    3. Retrieve top_k candidates (n_results * 6)
    4. Boost score if acronym found in text (+0.30)
    5. Filter by similarity threshold (default: 0.15)
    6. Re-rank: definitions first, then by score
    7. Return top n_results
```

**Global Search**:
```python
def search_global(query, n_results):
    1. Generate query embedding
    2. Detect acronym
    3. Retrieve candidates (n_results * 6)
    4. Progressive widening if too few results (up to 40x)
    5. Boost + filter + re-rank (same as per-document)
    6. Deduplicate by chunk_id
    7. Return top n_results
```

**Configuration**:
```python
CHROMA_DB_DIR: str            # Persist directory
CHUNK_SIZE: int               # Words per chunk (default: 800)
CHUNK_OVERLAP: int            # Overlap words (default: 160)
BATCH_SIZE: int               # Add batch size (default: 4)
EMBED_BATCH_SIZE: int         # Embedding batch (default: 16)
EMBEDDING_MODEL: str          # Model name (default: all-MiniLM-L6-v2)
MIN_SIM_THRESHOLD: float      # Min similarity (default: 0.15)
MIN_CHUNK_CHARS: int          # Min chunk length (default: 60)
DISABLE_CHUNK_FILTER: bool    # Disable quality filter (default: False)
```

### 3.6 retrieval.py - Search Orchestration

**Purpose**: High-level semantic search orchestration

**Key Responsibilities**:
- Unified search interface (per-document + global)
- Acronym detection and definition extraction
- Context building for LLM
- Progressive result widening

**Retrieval Flow**:

```python
┌─────────────────────────┐
│  User Query             │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Acronym Detection      │
│  (acronym_utils)        │
└──────┬──────────────────┘
       │
       ├───► Acronym? ──Yes──► Definition Search
       │                       (regex patterns)
       │                             │
       │                             ├─► Found? ──Yes──► Return definitions
       │                             │
       │                             No
       │                             │
       │                             └─► Term Filter Search
       │                                 (exact term in chunks)
       │                                       │
       │                                       └─► Return filtered chunks
       │
       No
       │
       ▼
┌─────────────────────────┐
│  Semantic Search        │
│  (vector_store)         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Insufficient Results?  │
│  (<5 unique chunks)     │
└──────┬──────────────────┘
       │
       Yes
       │
       ▼
┌─────────────────────────┐
│  Progressive Widening   │
│  (10x → 30x retrieval)  │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Deduplicate + Sort     │
└──────┬──────────────────┘
       │
       ▼
    Return top N chunks
```

**Definition Extraction**:
- Regex patterns: `TERM - definition`, `TERM: definition`, `TERM (definition)`
- Standard title extraction: ISO/SAE patterns
- Bad definition filtering (foreword, TOC, copyright)
- Length scoring (prefer concise)

**Term Filtering**:
- Normalized matching (ignore spaces, hyphens, case)
- Acronym boosting (ISO, CAN, SAE patterns)
- Exact boundary matching for short acronyms

### 3.7 indexer.py - Background Indexing

**Purpose**: Asynchronous document indexing coordinator

**Key Responsibilities**:
- Background task scheduling
- Document versioning (mtime + size hash)
- Concurrency control (semaphore)
- Progress tracking

**Architecture**:

```python
┌─────────────────────────┐
│  Startup / User Request │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  schedule_index(pdf)    │
│  - Increment inflight   │
│  - Create async task    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  _index_worker (task)   │
│  - Acquire semaphore    │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  ensure_document_indexed│
│  - Per-doc lock         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Version Check          │
│  - Compute hash         │
│  - Compare existing     │
└──────┬──────────────────┘
       │
       ├───► Changed? ──Yes──► Delete old index
       │
       No (already indexed)
       │
       ├───► Return (skip)
       │
       New/Changed
       │
       ▼
┌─────────────────────────┐
│  PDF Extraction         │
│  (pdf_parser)           │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Title Indexing         │
│  (optional, if enabled) │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Vector Store Add       │
│  (vector_store)         │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│  Task Done Callback     │
│  - Decrement inflight   │
│  - Increment done       │
└─────────────────────────┘
```

**Versioning**:
```python
def _compute_doc_version(file_path):
    stat = os.stat(file_path)
    return f"{stat.st_size}-{int(stat.st_mtime)}"
```

**Configuration**:
```python
INDEX_CONCURRENCY: int        # Max parallel indexing (default: 1)
PREINDEX_ENABLED: str         # Auto-preindex on startup (default: "1")
ENABLE_TITLE_INDEX: str       # Index page titles (default: "0")
MAX_INDEX_CHUNKS: int         # Max chunks per doc (0=unlimited)
```

### 3.8 acronym_utils.py - Acronym Intelligence

**Purpose**: Shared acronym detection logic

**Key Responsibilities**:
- Detect likely acronyms/terms in queries
- Prioritize automotive/security terms
- Filter stop words

**Algorithm**:
```python
def detect_acronym(text):
    1. Tokenize (2-20 char words)
    2. Filter stop words (was, ist, the, and, ...)
    3. Score each token:
       - Has digit: +2 (e.g., "21434")
       - All uppercase: +1 (e.g., "CAN", "OEM")
       - Preferred term: +3 (CAN, CAN-FD, OEM, RASIC, CAL, ISO, SAE)
    4. Sort by score (desc), then position (asc)
    5. Return highest scored term (or None if score ≤ 0)
```

**Preferred Terms**:
- `CAN`, `CAN-FD`, `OEM`, `RASIC`, `CAL`, `ISO`, `SAE`

**Stop Words** (DE+EN):
- German: `was`, `ist`, `das`, `der`, `die`, `und`, `ein`, `mit`, `im`, `in`, `von`
- English: `what`, `is`, `are`, `the`, `and`, `for`, `to`, `of`, `or`, `an`, `a`, `on`, `in`, `at`, `by`, `with`

---

## 4. Data Flow

### 4.1 Indexing Flow

```
PDF File
  │
  ▼
pdf_parser.extract_paragraphs_from_pdf()
  │
  ├─► PyPDF2 extraction
  │     │
  │     └─► pdfplumber fallback (if insufficient)
  │           │
  │           └─► OCR pipeline (if OCR_ENABLED)
  │
  ▼
TextNormalizer.normalize_text()
  │
  ├─► Unicode normalization (NFKC)
  ├─► Hyphenation removal
  ├─► Newline handling
  ├─► Ligature replacement
  └─► Whitespace cleanup
  │
  ▼
List[str] paragraphs
  │
  ▼
vector_store.add_chunks()
  │
  ├─► Chunking (800 words, 160 overlap)
  ├─► Quality filtering
  ├─► Embedding generation (sentence-transformers)
  └─► ChromaDB storage
  │
  ▼
Indexed Document
  │
  └─► Persist to disk (chroma_db/)
```

### 4.2 Query Flow

```
User Query (Telegram)
  │
  ▼
handlers1.handle_message()
  │
  ├─► Language detection (DE/EN)
  ├─► Screenshot mode check
  └─► Index status check
  │
  ▼
retrieval.get_best_chunks_global()
  │
  ├─► acronym_utils.detect_acronym()
  │     │
  │     └─► Returns: "TARA", "CAN", "ISO 21434", etc.
  │
  ├─► vector_store.search_global()
  │     │
  │     ├─► Embedding generation
  │     ├─► ChromaDB query (cosine similarity)
  │     ├─► Acronym boosting (+0.30 if found in text)
  │     └─► Threshold filtering (0.15 default)
  │
  ├─► Progressive widening (if <5 results)
  │
  ├─► find_definition_in_chunks() [if acronym detected]
  │     │
  │     └─► Regex matching: "TERM - definition", "TERM: ...", "TERM (...)"
  │
  └─► filter_chunks_by_term() [fallback]
  │
  ▼
List[Dict] chunks (top N, sorted by similarity)
  │
  ▼
build_combined_excerpts()
  │
  ├─► Sanitize (remove figure/clause headers)
  ├─► Deduplicate
  └─► Format as EXCERPT 1, EXCERPT 2, ...
  │
  ▼
llm_client.ask_ollama()
  │
  ├─► _create_prompts() → system + user prompt
  ├─► _call_ollama_chat() → Ollama API (chat endpoint)
  ├─► Truncation detection → continuation if needed
  └─► normalize_to_html() → Markdown → HTML
  │
  ▼
HTML Response
  │
  ▼
_send_paginated()
  │
  ├─► _split_pages() → intelligent pagination (3600 chars)
  └─► Telegram reply (inline keyboard if multiple pages)
  │
  ▼
User receives response
```

### 4.3 Screenshot Flow

```
User: /screenshot
  │
  ▼
screenshot_command()
  │
  └─► Set state: "pick_doc"
  └─► Show document selection keyboard
  │
  ▼
User selects document (callback_query)
  │
  ▼
button_callback() → "shot_doc:N"
  │
  └─► Set state: "awaiting_target", doc=selected_pdf
  └─► Prompt for target (page/table/figure)
  │
  ▼
User: "Seite 10" / "Table 3" / "Figure A.2"
  │
  ▼
handle_message() → _is_screenshot_target_query()
  │
  ├─► Regex match: page number, table, figure
  │
  ├─► extract_titles_from_pdf() (for table/figure lookup)
  │     │
  │     └─► pdfplumber/PyPDF2 title extraction
  │
  └─► get_page_image_bytes()
        │
        └─► pdf2image.convert_from_path() @ 180 DPI
  │
  ▼
Telegram photo message (protect_content=True)
```

---

## 5. Technology Stack

### 5.1 Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Core language |
| **Web Framework** | FastAPI | 0.104.1 | Webhook server |
| **ASGI Server** | Uvicorn | 0.24.0 | Production server |
| **Bot Framework** | python-telegram-bot | 20.7 | Telegram integration |
| **Vector DB** | ChromaDB | 0.4.22 | Semantic search |
| **Embeddings** | sentence-transformers | 2.7.0 | Vector generation (CPU) |
| **LLM Integration** | Ollama | N/A | Local LLM inference |
| **PDF Parsing** | PyPDF2, pdfplumber | 3.0.1, 0.10.3 | Text extraction |
| **OCR** | Tesseract, pytesseract | 0.3.10 | Image-to-text |
| **HTTP Client** | aiohttp | 3.9.1 | Async HTTP |

### 5.2 Dependencies

**requirements.txt**:
```
python-telegram-bot==20.7
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
chromadb==0.4.22
PyPDF2==3.0.1
pdf2image==1.16.3
pytesseract==0.3.10
Pillow==10.1.0
pdfplumber==0.10.3
aiohttp==3.9.1
requests==2.31.0
httpx==0.25.2
python-dotenv==1.0.1
numpy==1.26.4
sentence-transformers==2.7.0
```

### 5.3 External Services

| Service | Purpose | Protocol | Fallback |
|---------|---------|----------|----------|
| **Telegram Bot API** | User interface | HTTPS (webhook) | None (required) |
| **Ollama** | LLM inference | HTTP REST | Error message to user |
| **Tesseract OCR** | Image text extraction | Local binary | Skip OCR (optional) |

---

## 6. Deployment Architecture

### 6.1 Docker Architecture

```
┌─────────────────────────────────────────┐
│  Host Machine                           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Docker Container (bot:latest)    │  │
│  │                                   │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │  FastAPI + Uvicorn          │  │  │
│  │  │  (bot.py)                   │  │  │
│  │  │  Port: 8000                 │  │  │
│  │  └─────────────────────────────┘  │  │
│  │                                   │  │
│  │  Volume Mounts:                   │  │
│  │  - ./pdfs → /app/pdfs (ro)       │  │
│  │  - ./chroma_db → /app/chroma_db   │  │
│  │                                   │  │
│  │  Resource Limits:                 │  │
│  │  - Memory: 12 GB                  │  │
│  │  - CPU: 2.0 cores                 │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Ollama Service                   │  │
│  │  (host.docker.internal:11434)    │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Tesseract OCR (optional)         │  │
│  │  (included in Docker image)       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼ HTTPS
┌─────────────────────┐
│  Telegram Servers   │
└─────────────────────┘
```

### 6.2 Network Architecture

```
Internet
   │
   ▼
Reverse Proxy (optional: nginx, Caddy)
   │ HTTPS (with Let's Encrypt)
   │
   ▼
Docker Container (bot:latest)
   │ Port 8000
   │
   ├──► Telegram Bot API (HTTPS outbound)
   │
   └──► Ollama (HTTP: host.docker.internal:11434)
```

### 6.3 Storage Architecture

```
Host Filesystem
│
├── /app/pdfs/                    # PDF documents (read-only)
│   ├── ISO_21434.pdf
│   ├── UNR_155.pdf
│   └── ...
│
├── /app/chroma_db/               # ChromaDB persistent storage
│   ├── chroma.sqlite3            # Vector index
│   ├── *.parquet                 # Embeddings
│   └── ...
│
├── .env                          # Environment configuration
│
└── docker-compose.yml            # Deployment manifest
```

### 6.4 Process Architecture

**Container Process Tree**:
```
PID 1: uvicorn bot:app
  │
  ├─► Worker Threads (async event loop)
  │   ├─► Webhook handler (FastAPI endpoint)
  │   ├─► Background indexing tasks
  │   └─► Message processing tasks
  │
  ├─► sentence-transformers (CPU-bound)
  │   └─► Embedding generation threads
  │
  └─► pdf2image + Tesseract (if OCR_ENABLED)
      └─► Subprocess pool
```

---

## 7. Performance Characteristics

### 7.1 Latency Profile

| Operation | Latency | Factors |
|-----------|---------|---------|
| **Webhook receipt** | 10-50ms | Network + parsing |
| **Vector search** | 50-200ms | Index size, n_results |
| **LLM inference** | 2-10s | Model size, token count, GPU/CPU |
| **PDF indexing** | 0.5-5s/page | OCR, complexity |
| **Screenshot** | 200-500ms | DPI, page complexity |
| **End-to-end response** | 5-15s | Search + LLM + formatting |

### 7.2 Throughput

| Metric | Value | Configuration |
|--------|-------|---------------|
| **Concurrent users** | 10-50 | MAX_UPDATE_CONCURRENCY |
| **Indexing throughput** | 100-500 pages/min | Without OCR |
| **Indexing throughput** | 10-50 pages/min | With OCR |
| **Vector search QPS** | 100-500 | Depends on index size |
| **LLM QPS** | 1-5 | Ollama capacity |

### 7.3 Resource Usage

| Resource | Idle | Under Load | Peak |
|----------|------|------------|------|
| **Memory** | 2-4 GB | 6-10 GB | 12 GB |
| **CPU** | 5-10% | 50-100% | 200% (2 cores) |
| **Disk I/O** | Minimal | 10-50 MB/s | 100 MB/s (indexing) |
| **Network** | <1 KB/s | 100-500 KB/s | 5 MB/s |

### 7.4 Scalability Limits

| Dimension | Limit | Mitigation |
|-----------|-------|------------|
| **Total PDFs** | 100-1000 | Index optimization, sharding |
| **Total pages** | 10,000-100,000 | Chunk filtering, retrieval limits |
| **Total chunks** | 100,000-1M | ChromaDB HNSW scales well |
| **Concurrent queries** | 10-50 | Horizontal scaling (multiple containers) |
| **Single PDF size** | 10-500 MB | Progressive indexing |

---

## 8. Security Architecture

### 8.1 Threat Model

**In Scope**:
- Unauthorized webhook access
- Sensitive data leakage (tokens, URLs)
- Malicious PDF uploads (if enabled)
- LLM prompt injection
- Document content exfiltration

**Out of Scope**:
- Telegram infrastructure compromise
- Ollama binary vulnerabilities
- Host OS exploitation

### 8.2 Security Controls

| Control | Implementation | Purpose |
|---------|----------------|---------|
| **Webhook Secret** | Path-based secret (`/webhook/{SECRET}`) | Prevent unauthorized updates |
| **Token Sanitization** | `_CensorFilter` in logs | Hide bot tokens, secrets |
| **Content Protection** | `protect_content=True` on Telegram messages | Prevent screenshot/forward |
| **Input Validation** | Command parsing, state checks | Prevent injection |
| **Local Processing** | Ollama + embeddings on localhost | Data privacy |
| **No External APIs** | Except Telegram (required) | Minimize attack surface |
| **Read-only PDFs** | Docker volume mount `:ro` | Prevent tampering |
| **Telemetry Disabled** | ChromaDB, Ollama settings | No tracking |

### 8.3 Data Privacy

**Data Flow**:
1. User message → Telegram → Webhook (HTTPS)
2. Processing: 100% local (PDF extraction, embeddings, LLM)
3. Response → Telegram (HTTPS)

**Data Retention**:
- PDFs: Persistent (user-managed)
- ChromaDB: Persistent (until cleared)
- Logs: Local (no external shipping)
- User messages: Not stored (transient in memory)

**GDPR Compliance**:
- No user profiling
- No tracking cookies/analytics
- Processing basis: User consent (explicit query)
- Right to erasure: Delete `chroma_db/` directory

---

## Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Chunk** | Text segment (800 words) used for embedding and retrieval |
| **Embedding** | Vector representation of text (384-dim for all-MiniLM-L6-v2) |
| **Semantic Search** | Meaning-based retrieval (vs. keyword matching) |
| **Acronym Boosting** | Similarity score increase when acronym found in text |
| **Progressive Widening** | Iteratively increasing retrieval window to find results |
| **Preindexing** | Background indexing of all PDFs on startup |

### B. References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [sentence-transformers](https://www.sbert.net/)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

**Document End**
