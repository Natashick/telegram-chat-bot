# 🤖 PDF Chat Bot

Ein intelligenter Telegram Bot, der Fragen zu PDF-Dokumenten beantwortet und visuelle Inhalte (Figuren, Tabellen) als Screenshots bereitstellt.

## ✨ Features

- 📄 **Semantische PDF-Suche** - Verstehe und beantworte Fragen zu PDF-Inhalten
- 🖼️ **Automatische Screenshots** - Finde und zeige Figuren, Tabellen und Bilder
- 🔍 **Intelligente Seitenerkennung** - Präzise Seitennummerierung für strukturierte Dokumente
- 💬 **Kontextbewusste Gespräche** - Folgefragen und detaillierte Erklärungen
- 🛡️ **Sicherheit** - View-only Screenshots mit Wasserzeichen

## 🚀 Deployment

### Railway (Empfohlen - Kostenlos)

1. **Fork dieses Repository** auf GitHub
2. **Gehe zu [Railway.app](https://railway.app)** und melde dich an
3. **Klicke "New Project"** → "Deploy from GitHub repo"
4. **Wähle dein geforktes Repository**
5. **Setze Umgebungsvariablen**:
   - `TELEGRAM_TOKEN` - Dein Telegram Bot Token (von @BotFather)
   - `OLLAMA_URL` - URL zu deinem Ollama Server (optional)
   - `OLLAMA_MODEL` - Modell-Name (Standard: llama3.2:3b)

### Lokale Entwicklung

```bash
# Dependencies installieren
pip install -r requirements.txt

# Umgebungsvariablen setzen
export TELEGRAM_TOKEN="dein-token-hier"
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.2:3b"

# Bot starten
uvicorn bot:app --reload
```

## 📋 Voraussetzungen

- **Telegram Bot Token** - Erstelle einen Bot bei [@BotFather](https://t.me/botfather)
- **Ollama Server** (optional) - Für lokale LLM-Verarbeitung
- **PDF-Dateien** - Lege PDFs im Projektverzeichnis ab

## 🔧 Konfiguration

### Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|-------------|----------|
| `TELEGRAM_TOKEN` | Telegram Bot Token | **Erforderlich** |
| `OLLAMA_URL` | Ollama Server URL | `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | LLM Modell Name | `llama3.2:3b` |
| `OLLAMA_TIMEOUT` | LLM Request Timeout (Sekunden) | `60` |
| `EMBEDDING_MODEL` | Embedding Model für Vektorsuche | `sentence-transformers/all-MiniLM-L6-v2` |
| `OCR_CONCURRENCY` | Maximale parallele OCR Prozesse | `3` |
| `MIN_TEXT_LENGTH` | Minimale Textlänge um OCR zu überspringen | `80` |
| `INDEX_CONCURRENCY` | Maximale parallele Indexing Jobs | `1` |
| `WEBHOOK_URL` | Webhook URL (für Production) | Optional |

### Ressourcen-Empfehlungen

#### Minimale Anforderungen
- **CPU**: 1 Core (2 Cores empfohlen)
- **RAM**: 2GB (4GB empfohlen für große PDFs)
- **Disk**: 1GB für Code + 500MB pro PDF im Index

#### Empfohlene Einstellungen für Low-RAM Systeme (< 4GB)
```bash
export OCR_CONCURRENCY=2
export INDEX_CONCURRENCY=1
export MIN_TEXT_LENGTH=100
export OLLAMA_TIMEOUT=30
```

#### Performance-Optimierung für High-RAM Systeme (> 8GB)
```bash
export OCR_CONCURRENCY=5
export INDEX_CONCURRENCY=2
export MIN_TEXT_LENGTH=50
```

## 📖 Verwendung

1. **Starte den Bot** mit `/start`
2. **Wähle ein PDF-Dokument** aus der Liste
3. **Indexiere das Dokument** mit `/index` (einmalig pro Dokument)
4. **Stelle Fragen** zu den Inhalten
5. **Fordere Screenshots an** mit "Show me Figure 5.1" oder "Table 3.2"
6. **Nutze `/screenshot`** für manuelle Seitenscreenshots

### Verfügbare Kommandos

- `/start` - Bot starten und Dokument auswählen
- `/select` - Anderes Dokument auswählen
- `/index` - Aktuelles Dokument für Suche indexieren
- `/upload` - Neues PDF hochladen (nur Bot-Besitzer)
- `/screenshot` - Manuelle Seitenscreenshots erstellen

## 🛠️ Technologie

- **FastAPI** - Web Framework
- **python-telegram-bot** - Telegram Bot API
- **ChromaDB** - Vector Database für semantische Suche
- **PyPDF2** - PDF Text-Extraktion
- **Tesseract OCR** - Optical Character Recognition
- **Ollama** - Lokale LLM-Verarbeitung
- **Docker** - Containerisierung

## 🧪 Testing

### Testing OCR Throttling und Indexing

1. **Upload zwei PDFs**: Ein text-basiertes PDF und ein gescanntes PDF
2. **Starte Indexierung**: `/index` für beide Dokumente
3. **Überprüfe Logs**:
   - Text-basiertes PDF sollte **kein OCR triggern** (ausreichender Text erkannt)
   - Gescanntes PDF sollte **OCR mit PSM=6, DPI=180** triggern
   - Bei unzureichendem Text: Fallback zu PSM=3, DPI=240

4. **Teste Concurrency**: Indexiere mehrere PDFs gleichzeitig
   - `docker stats` sollte maximal `OCR_CONCURRENCY` (Standard: 3) parallele Prozesse zeigen
   - CPU und RAM sollten innerhalb der Limits bleiben

5. **Teste Embedding Model**: 
   - Überprüfe Logs auf "sentence-transformers/all-MiniLM-L6-v2"
   - Batch-Verarbeitung sollte in 64er-Batches erfolgen

### Docker Compose Testing

```bash
# Starte mit resource limits
docker-compose up

# Überprüfe resource usage
docker stats telegram-pdf-bot

# Test Ollama connection
docker-compose logs | grep "Ollama connection"
```

### Expected Log Output

```
[INFO] PDFParser initialized: min_text_length=80, default_dpi=180, ocr_concurrency=3
[INFO] Page 1: sufficient text without OCR (1234 chars)
[INFO] Page 2: insufficient text (45 chars), triggering OCR
[INFO] OCR page 2: mode=6, dpi=180, duration=2.34s, text_length=892
[INFO] ✅ Ollama connection successful! Available models: 3
```

## 📝 Lizenz

MIT License - Frei verwendbar für private und kommerzielle Projekte.

## 🤝 Beitragen

Pull Requests sind willkommen! Für größere Änderungen öffne bitte zuerst ein Issue.

---

**Entwickelt mit ❤️ für die Community**
