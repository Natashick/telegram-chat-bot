# Telegram PDF Chatbot - Configuration Reference

**Version:** 1.0  
**Date:** 2024-01-27  
**Status:** Final

---

## Table of Contents

1. [Environment Variables](#1-environment-variables)
2. [Configuration Files](#2-configuration-files)
3. [Performance Tuning](#3-performance-tuning)
4. [Security Configuration](#4-security-configuration)
5. [Feature Toggles](#5-feature-toggles)

---

## 1. Environment Variables

### 1.1 Required Configuration

#### `TELEGRAM_TOKEN`
**Type**: String (required)  
**Format**: `{bot_id}:{token}` (e.g., `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)  
**Purpose**: Telegram Bot API authentication  
**Obtain**: Create bot via [@BotFather](https://t.me/BotFather)  
**Security**: NEVER commit to Git, use secrets management

**Example**:
```bash
TELEGRAM_TOKEN=987654321:XyZ_aBc123dEfGhIjKlMnOpQrStUvWxYz
```

---

#### `WEBHOOK_URL`
**Type**: String (required)  
**Format**: Full HTTPS URL (no trailing slash)  
**Purpose**: Public webhook endpoint for Telegram updates  
**Requirements**: 
- Must be HTTPS (except localhost for testing)
- Must be publicly accessible
- Port 443, 80, 88, or 8443

**Examples**:
```bash
# Production
WEBHOOK_URL=https://bot.example.com

# ngrok (testing)
WEBHOOK_URL=https://abc123.ngrok-free.app

# Railway
WEBHOOK_URL=https://telegram-bot-production.up.railway.app
```

---

### 1.2 LLM Configuration

#### `OLLAMA_URL`
**Type**: String  
**Default**: `http://localhost:11434`  
**Purpose**: Ollama API endpoint

**Docker Context**:
```bash
# Linux
OLLAMA_URL=http://172.17.0.1:11434

# macOS/Windows
OLLAMA_URL=http://host.docker.internal:11434

# Remote server
OLLAMA_URL=https://ollama.example.com:11434
```

---

#### `OLLAMA_MODEL`
**Type**: String  
**Default**: `llama3.2:1b`  
**Purpose**: LLM model name

**Recommended Models**:
| Model | Size | RAM | Speed | Quality |
|-------|------|-----|-------|---------|
| `llama3.2:1b` | 1.3 GB | 2-4 GB | ⚡⚡⚡ | ⭐⭐ |
| `llama3.2:3b` | 2.0 GB | 4-6 GB | ⚡⚡ | ⭐⭐⭐ |
| `qwen2.5:7b-instruct` | 4.7 GB | 6-10 GB | ⚡ | ⭐⭐⭐⭐ |
| `llama3.1:8b` | 4.9 GB | 8-12 GB | ⚡ | ⭐⭐⭐⭐ |

**Pull Model**:
```bash
ollama pull qwen2.5:7b-instruct
```

---

#### `OLLAMA_NUM_CTX`
**Type**: Integer  
**Default**: `1024`  
**Range**: `512` - `32768` (model-dependent)  
**Purpose**: Context window size (tokens)

**Recommendations**:
- Small docs (<100 pages): `1024`
- Medium docs (100-500 pages): `2048`
- Large docs (>500 pages): `4096`

**Trade-offs**:
- Larger = more context, slower generation, more RAM
- Smaller = faster, less context

**Example**:
```bash
OLLAMA_NUM_CTX=2048
```

---

#### `MAX_TOKENS`
**Type**: Integer  
**Default**: `4096`  
**Purpose**: Maximum tokens for LLM generation

**Relation to answer length**:
- Short answers: ~500-1500 tokens
- Long answers: ~2000-3500 tokens
- Capped by this setting

**Example**:
```bash
MAX_TOKENS=8192  # For very detailed answers
```

---

### 1.3 Storage Configuration

#### `PDF_DIR`
**Type**: String (path)  
**Default**: `/app/pdfs` (Docker), `./pdfs` (local)  
**Purpose**: PDF documents directory

**Docker Mount**:
```yaml
volumes:
  - ./pdfs:/app/pdfs:ro  # Read-only for security
```

**Permissions**: Container must have read access

---

#### `CHROMA_DB_DIR`
**Type**: String (path)  
**Default**: `/app/chroma_db` (Docker), `./chroma_db` (local)  
**Purpose**: ChromaDB persistent storage

**Docker Mount**:
```yaml
volumes:
  - ./chroma_db:/app/chroma_db  # Read-write required
```

**Persistence**: All vector embeddings stored here

---

### 1.4 Chunking & Retrieval

#### `CHUNK_SIZE`
**Type**: Integer  
**Default**: `800`  
**Unit**: Words  
**Purpose**: Text chunk size for vector embeddings

**Recommendations**:
- Technical docs: `800-1200`
- Narrative text: `600-800`
- Very detailed: `1200-1600`

**Trade-offs**:
- Larger = more context per chunk, fewer chunks, less granular
- Smaller = more precise retrieval, more chunks

**Example**:
```bash
CHUNK_SIZE=1000
```

---

#### `CHUNK_OVERLAP`
**Type**: Integer  
**Default**: `160`  
**Unit**: Words  
**Purpose**: Sliding window overlap

**Typical Range**: 10-25% of `CHUNK_SIZE`

**Examples**:
```bash
# 20% overlap (recommended)
CHUNK_SIZE=800
CHUNK_OVERLAP=160

# 25% overlap (high precision)
CHUNK_SIZE=1000
CHUNK_OVERLAP=250
```

---

#### `MAX_EXCERPTS`
**Type**: Integer  
**Default**: `12`  
**Purpose**: Maximum chunks sent to LLM as context

**Recommendations**:
- Fast responses: `6-8`
- Balanced: `10-12`
- Comprehensive: `15-20`

**Trade-offs**:
- More excerpts = better recall, slower LLM, more context tokens
- Fewer = faster, less context

**Example**:
```bash
MAX_EXCERPTS=15
```

---

#### `MIN_SIM_THRESHOLD`
**Type**: Float  
**Default**: `0.15`  
**Range**: `0.0` - `1.0`  
**Purpose**: Minimum cosine similarity for retrieval

**Recommendations**:
- Strict (high precision): `0.25-0.30`
- Balanced: `0.15-0.20`
- Lenient (high recall): `0.10-0.15`

**Example**:
```bash
MIN_SIM_THRESHOLD=0.20
```

---

### 1.5 Concurrency & Performance

#### `MAX_UPDATE_CONCURRENCY`
**Type**: Integer  
**Default**: `10`  
**Purpose**: Maximum parallel Telegram update processing

**Recommendations**:
- Low load (<10 users): `5-10`
- Medium load (10-50 users): `10-20`
- High load (>50 users): `20-50`

**Limits**: CPU, RAM, LLM capacity

**Example**:
```bash
MAX_UPDATE_CONCURRENCY=20
```

---

#### `INDEX_CONCURRENCY`
**Type**: Integer  
**Default**: `1`  
**Purpose**: Maximum parallel PDF indexing tasks

**Recommendations**:
- Single-core CPU: `1`
- Multi-core CPU: `2-4`
- High-end server: `4-8`

**Note**: Indexing is CPU/RAM intensive

**Example**:
```bash
INDEX_CONCURRENCY=2
```

---

#### `EMBED_BATCH_SIZE`
**Type**: Integer  
**Default**: `16`  
**Purpose**: Batch size for embedding generation

**Recommendations**:
- Low RAM: `8`
- Balanced: `16`
- High RAM: `32-64`

**Trade-offs**: Larger batches = faster indexing, more RAM

**Example**:
```bash
EMBED_BATCH_SIZE=32
```

---

### 1.6 Quality Filtering

#### `MIN_PARA_CHARS`
**Type**: Integer  
**Default**: `30` (now `20` in production for better glossaries)  
**Purpose**: Minimum paragraph length (chars)

**Use Cases**:
- Technical glossaries: `20-30` (preserve definitions)
- General text: `50-100`

**Example**:
```bash
MIN_PARA_CHARS=25
```

---

#### `MIN_CHUNK_CHARS`
**Type**: Integer  
**Default**: `60` (now `50` in production)  
**Purpose**: Minimum chunk length after quality filter

**Similar to `MIN_PARA_CHARS` but applied to final chunks**

---

#### `MIN_CHUNK_WORDS`
**Type**: Integer  
**Default**: `8`  
**Purpose**: Minimum word count per chunk

**Prevents very short, low-quality chunks**

---

#### `DISABLE_CHUNK_FILTER`
**Type**: Boolean  
**Default**: `0` (False)  
**Values**: `0` (disabled), `1` (enabled)  
**Purpose**: Disable all quality filtering

**Use When**: Debugging, or PDFs with unusual formatting

**Example**:
```bash
DISABLE_CHUNK_FILTER=1
```

---

### 1.7 Optional Features

#### `OCR_ENABLED`
**Type**: Boolean  
**Default**: `0` (disabled)  
**Values**: `0` (off), `1` (on)  
**Purpose**: Enable OCR for scanned PDFs

**Requirements**: Tesseract OCR installed in container

**Performance Impact**: 10-100x slower indexing

**Example**:
```bash
OCR_ENABLED=1
```

---

#### `OCR_CONCURRENCY`
**Type**: Integer  
**Default**: `1`  
**Purpose**: Max parallel OCR tasks

**Recommendations**: Same as `INDEX_CONCURRENCY` or lower

---

#### `OCR_NOISE_MAX_RATIO`
**Type**: Float  
**Default**: `0.7`  
**Range**: `0.0` - `1.0`  
**Purpose**: Max non-alphanumeric ratio for OCR output

**Filters out garbage OCR results**

---

#### `PREINDEX_ENABLED`
**Type**: Boolean  
**Default**: `1` (enabled)  
**Purpose**: Auto-index all PDFs on startup

**Disable** if you have many large PDFs and want manual control

**Example**:
```bash
PREINDEX_ENABLED=0
```

---

#### `ENABLE_TITLE_INDEX`
**Type**: Boolean  
**Default**: `0` (disabled)  
**Purpose**: Index page titles for enhanced screenshot search

**Experimental Feature**: Not required for basic operation

**Example**:
```bash
ENABLE_TITLE_INDEX=1
```

---

### 1.8 Security & Networking

#### `WEBHOOK_SECRET`
**Type**: String  
**Default**: `secret123`  
**Purpose**: Webhook path secret

**Security**: Change default! Use strong random string

**Example**:
```bash
WEBHOOK_SECRET=$(openssl rand -hex 16)
# e.g., "a3f8d92c1e4b6f7a9d2e5c8b4f1a3d6e"
```

---

#### `PORT`
**Type**: Integer  
**Default**: `8000`  
**Purpose**: HTTP server port

**Docker**: Internal port, map with `-p` flag

**Example**:
```bash
PORT=8080
```

---

#### `HOST`
**Type**: String  
**Default**: `0.0.0.0`  
**Purpose**: Bind address

**Options**:
- `0.0.0.0` - All interfaces
- `127.0.0.1` - Localhost only (use reverse proxy)

---

### 1.9 Logging & Debug

#### `LOG_LEVEL`
**Type**: String  
**Default**: `INFO`  
**Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`  
**Purpose**: Logging verbosity

**Example**:
```bash
LOG_LEVEL=DEBUG
```

---

#### `DEBUG_PROMPTS`
**Type**: Boolean  
**Default**: `0`  
**Purpose**: Log LLM prompts (first 800 chars)

**Use**: Debugging prompt engineering

**Example**:
```bash
DEBUG_PROMPTS=1
```

---

#### `LOG_CHUNK_FILTER`
**Type**: Boolean  
**Default**: `0`  
**Purpose**: Log chunk filtering statistics

**Example**:
```bash
LOG_CHUNK_FILTER=1
```

---

### 1.10 Advanced Settings

#### `MAX_INDEX_CHUNKS`
**Type**: Integer  
**Default**: `0` (unlimited)  
**Purpose**: Limit chunks per document

**Use**: Memory constraints, testing

**Example**:
```bash
MAX_INDEX_CHUNKS=5000
```

---

#### `EMBEDDING_MODEL`
**Type**: String  
**Default**: `sentence-transformers/all-MiniLM-L6-v2`  
**Purpose**: Sentence-transformers model

**Alternatives**:
- `all-mpnet-base-v2` (better quality, slower)
- `paraphrase-MiniLM-L6-v2` (smaller)

**Example**:
```bash
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

---

#### `BATCH_SIZE`
**Type**: Integer  
**Default**: `4`  
**Purpose**: Batch size for adding chunks to ChromaDB

**Lower if memory-constrained**

---

#### `CHROMA_DISABLE_TELEMETRY`
**Type**: Boolean  
**Default**: `1`  
**Purpose**: Disable ChromaDB telemetry

**Privacy**: Keep enabled (1)

---

## 2. Configuration Files

### 2.1 `.env` Template

**Minimal Configuration**:
```bash
# Required
TELEGRAM_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.com
WEBHOOK_SECRET=change_this_secret

# LLM
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

# Optional (uncomment to customize)
# CHUNK_SIZE=800
# MAX_EXCERPTS=12
# OCR_ENABLED=0
```

**Full Configuration**:
See `.env.example` in repository

---

### 2.2 `docker-compose.yml`

**Production Template**:
```yaml
services:
  bot:
    image: telegram-pdf-bot:latest
    restart: unless-stopped
    env_file: .env
    environment:
      # Override specific vars
      MAX_UPDATE_CONCURRENCY: 20
      INDEX_CONCURRENCY: 2
    volumes:
      - ./pdfs:/app/pdfs:ro
      - ./chroma_db:/app/chroma_db
    ports:
      - "127.0.0.1:8000:8000"
    mem_limit: 12g
    cpus: "4.0"
```

---

### 2.3 Dockerfile Customization

**Custom Python Dependencies**:
```dockerfile
# Add to Dockerfile
RUN pip install --no-cache-dir     your-package==1.0.0
```

**System Packages**:
```dockerfile
# Add before pip install
RUN apt-get update && apt-get install -y     your-system-package     && rm -rf /var/lib/apt/lists/*
```

---

## 3. Performance Tuning

### 3.1 Low-Latency Configuration

**Goal**: Minimize response time

```bash
# Use smallest model
OLLAMA_MODEL=llama3.2:1b

# Reduce context
OLLAMA_NUM_CTX=1024
MAX_TOKENS=2048

# Fewer excerpts
MAX_EXCERPTS=8

# Smaller chunks
CHUNK_SIZE=600
```

**Expected Latency**: 3-8 seconds

---

### 3.2 High-Quality Configuration

**Goal**: Best answer quality

```bash
# Larger model
OLLAMA_MODEL=qwen2.5:7b-instruct

# More context
OLLAMA_NUM_CTX=4096
MAX_TOKENS=8192

# More excerpts
MAX_EXCERPTS=15

# Larger chunks
CHUNK_SIZE=1200
```

**Expected Latency**: 10-20 seconds

---

### 3.3 High-Throughput Configuration

**Goal**: Handle many concurrent users

```bash
# Increase concurrency
MAX_UPDATE_CONCURRENCY=30

# Fast indexing
INDEX_CONCURRENCY=4
EMBED_BATCH_SIZE=32

# Balanced retrieval
MAX_EXCERPTS=10
```

**Requirements**: Multi-core CPU, 16+ GB RAM

---

### 3.4 Memory-Constrained Configuration

**Goal**: Run on 4 GB RAM

```bash
# Small model
OLLAMA_MODEL=llama3.2:1b

# Low concurrency
MAX_UPDATE_CONCURRENCY=5
INDEX_CONCURRENCY=1

# Small batches
EMBED_BATCH_SIZE=8
BATCH_SIZE=2

# Limit chunks
MAX_INDEX_CHUNKS=3000
```

---

## 4. Security Configuration

### 4.1 Secrets Best Practices

**1. Use Strong Secrets**:
```bash
# Generate secure webhook secret
WEBHOOK_SECRET=$(openssl rand -hex 32)
```

**2. Never Hardcode**:
❌ Bad:
```python
TELEGRAM_TOKEN = "123456:ABC..."
```

✅ Good:
```python
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
```

**3. Use Secret Management**:
- Docker Secrets
- Kubernetes Secrets
- Cloud provider secret stores (AWS Secrets Manager, etc.)

---

### 4.2 Network Security

**Bind to Localhost** (use reverse proxy):
```yaml
ports:
  - "127.0.0.1:8000:8000"
```

**Read-Only Mounts**:
```yaml
volumes:
  - ./pdfs:/app/pdfs:ro  # Read-only
```

**Firewall Rules**: See [Deployment Guide - Security](02_DEPLOYMENT_GUIDE.md#7-security-hardening)

---

### 4.3 Content Protection

**Enable Message Protection**:
```bash
# handlers1.py sets this by default
PROTECT_CONTENT=1
```

**Prevents**:
- Screenshots by user
- Message forwarding

**Log Sanitization**:
- Automatic via `_CensorFilter` in `handlers1.py`
- Censors: tokens, URLs, secrets

---

## 5. Feature Toggles

### 5.1 Enabling OCR

**When to Use**: Scanned PDFs, images in PDFs

**Configuration**:
```bash
OCR_ENABLED=1
OCR_CONCURRENCY=2
```

**Requirements**: Tesseract installed (included in Dockerfile)

**Languages**: English + German by default

---

### 5.2 Enabling Title Index

**When to Use**: Enhanced screenshot search

**Configuration**:
```bash
ENABLE_TITLE_INDEX=1
```

**Note**: Experimental, not required for basic operation

---

### 5.3 Disabling Preindexing

**When to Use**: Large PDF collections, manual indexing

**Configuration**:
```bash
PREINDEX_ENABLED=0
```

**Manual Indexing**: Send queries to trigger on-demand indexing

---

## Appendix: Configuration Matrix

| Use Case | OLLAMA_MODEL | CHUNK_SIZE | MAX_EXCERPTS | RAM | Response Time |
|----------|--------------|------------|--------------|-----|---------------|
| **Development** | llama3.2:1b | 800 | 10 | 4 GB | 5-8s |
| **Production (Balanced)** | qwen2.5:7b | 1000 | 12 | 8 GB | 8-12s |
| **High Quality** | llama3.1:8b | 1200 | 15 | 12 GB | 12-20s |
| **Low Latency** | llama3.2:1b | 600 | 8 | 4 GB | 3-6s |
| **High Load** | qwen2.5:7b | 800 | 10 | 16 GB | 8-12s |
| **Memory Constrained** | llama3.2:1b | 600 | 8 | 4 GB | 5-8s |

---

**Document End**
