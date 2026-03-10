# README
# Telegram PDF Chatbot
## Intelligente Dokumentensuche mit lokaler KI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

Ein datenschutzfreundlicher Telegram-Bot für **semantische Suche und Frage-Antwort** über PDF-Dokumente. Nutzt lokales LLM (Ollama) und ChromaDB für vollständig lokale, KI-gestützte Dokumentenanalyse.

---

##  Highlights

-  **Semantische Suche**: Bedeutungsbasiertes Verständnis, nicht nur Keywords
-  **Lokales LLM**: Vollständige Datenkontrolle, keine externen APIs
-  **Multi-Dokument**: Durchsucht mehrere PDFs gleichzeitig
-  **Mehrsprachig**: Deutsch & Englisch
-  **Datenschutz**: 100% lokale Verarbeitung
-  **Telegram-Integration**: Nutzen Sie Ihre gewohnte App
-  **Docker-Ready**: Einfaches Deployment

---

##  Dokumentation

**Vollständige Dokumentation verfügbar in `/docs/`**

### Schnellstart nach Zielgruppe:

| Sie sind... | Starten Sie hier |
|-------------|------------------|
|  **Endnutzer** | [Benutzerhandbuch (Deutsch)](docs/customer/BENUTZERHANDBUCH.md) |
|  **Administrator** | [Deployment Guide](docs/technical/02_DEPLOYMENT_GUIDE.md) |
|  **Entwickler** | [System Architecture](docs/technical/01_SYSTEM_ARCHITECTURE.md) |
|  **Projektmanager** | [Lastenheft](docs/lastenheft/LASTENHEFT.md) |

### Dokumentationsübersicht:

- **[ Dokumentations-Index](docs/README.md)** - Kompletter Überblick
- **[ System Architecture](docs/technical/01_SYSTEM_ARCHITECTURE.md)** - Technisches Design
- **[ Deployment Guide](docs/technical/02_DEPLOYMENT_GUIDE.md)** - Installation & Betrieb
- **[ API Documentation](docs/technical/03_API_DOCUMENTATION.md)** - Schnittstellen-Referenz
- **[ Configuration Reference](docs/technical/04_CONFIGURATION.md)** - Alle Konfigurationsoptionen
- **[ Lastenheft](docs/lastenheft/LASTENHEFT.md)** - Anforderungsspezifikation
- **[ Pflichtenheft](docs/pflichtenheft/PFLICHTENHEFT.md)** - Funktionale Spezifikation
- **[ Benutzerhandbuch](docs/customer/BENUTZERHANDBUCH.md)** - Anleitung für Endnutzer

---

##  Quick Start

### Voraussetzungen
- Docker & Docker Compose
- Telegram Bot Token (von [@BotFather](https://t.me/BotFather))
- Ollama (lokal oder remote)

### 1. Repository klonen
```bash
git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot
```

### 2. Umgebung konfigurieren
```bash
cat > .env << 'EOF'
TELEGRAM_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-domain.com/
OLLAMA_URL="your URL"
OLLAMA_MODEL="your Modell"
EOF
```

### 3. PDFs hinzufügen
```bash
mkdir -p pdfs
cp /path/to/your/documents/*.pdf pdfs/
```

### 4. Ollama starten
```bash
ollama pull "your Modell"
ollama serve
```

### 5. Bot starten
```bash
docker-compose up -d --build
```

### 6. Überprüfen
```bash
# Health check
curl http://localhost:8000/health

# Logs ansehen
docker-compose logs -f bot
```

### 7. Bot testen
1. Öffnen Sie Telegram
2. Suchen Sie Ihren Bot
3. Senden Sie `/start`
4. Stellen Sie eine Frage!

**Detaillierte Anleitung**: Siehe [Deployment Guide](docs/technical/02_DEPLOYMENT_GUIDE.md)

---

##  Features im Detail

### Kernfunktionen

 **Fragen in natürlicher Sprache**
- Stellen Sie Fragen wie "Was ist ISO 21434?"
- Automatische Spracherkennung (DE/EN)
- Kontextbasierte Antworten

 **Intelligente Dokumentensuche**
- Semantische Suche über alle PDFs
- Akronym-Erkennung (TARA, CAN, ECU, etc.)
- Glossar-Priorisierung
- Multi-Dokument-Retrieval

 **Erweiterte Funktionen**
- `/screenshot <doc> <page>` - Seite als Bild
- `/page <doc> <page>` - Textextraktion
- `/status` - Systemstatus & Indexierung
- Automatische Pagination bei langen Antworten

 **Datenschutz & Sicherheit**
- 100% lokale LLM-Verarbeitung (Ollama)
- Keine externen API-Aufrufe (außer Telegram)
- Telemetrie deaktiviert
- Log-Sanitization für sensible Daten

---

##  Architektur

```
Telegram User
    │
    ▼
FastAPI Webhook
    │
    ├─► Message Handlers ──► Retrieval System ──► Vector Store (ChromaDB)
    │                                 │
    │                                 ▼
    └─► LLM Client (Ollama) ◄─── PDF Parser
                                      │
                                      ▼
                                  PDF Files
```

**Technologie-Stack**:
- **Backend**: Python 3.11, FastAPI, python-telegram-bot
- **LLM**: Ollama (lokal, GPU-optional)
- **Vector DB**: ChromaDB (persistent)
- **Embeddings**: sentence-transformers (CPU)
- **PDF Processing**: PyPDF2, pdfplumber, Tesseract OCR
- **Deployment**: Docker + Docker Compose

**Details**: Siehe [System Architecture](docs/technical/01_SYSTEM_ARCHITECTURE.md)

---

##  Konfiguration

Alle Konfigurationsoptionen sind über Umgebungsvariablen steuerbar:

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `TELEGRAM_TOKEN` | - | Bot Token (erforderlich) |
| `WEBHOOK_URL` | - | Webhook URL (erforderlich) |
| `OLLAMA_URL` | `your URL` | Ollama Endpoint |
| `OLLAMA_MODEL` | `your modell` | LLM Modell |
| `CHUNK_SIZE` | `800` | Wörter pro Chunk |
| `MAX_EXCERPTS` | `12` | Max. Chunks an LLM |
| `OCR_ENABLED` | `0` | OCR aktivieren (1/0) |

**Vollständige Referenz**: [Configuration Guide](docs/technical/04_CONFIGURATION.md)

---

##  Deployment-Optionen

### Option 1: Docker Compose (Empfohlen)
```bash
docker-compose up -d --build
```

### Option 2: Kubernetes
```bash
kubectl apply -f k8s/
```

### Option 3: Bare Metal
```bash
pip install -r requirements.txt
python -m uvicorn bot:app --host 0.0.0.0 --port 8000
```

**Detaillierte Anleitungen**: [Deployment Guide](docs/technical/02_DEPLOYMENT_GUIDE.md)

---

##  Performance

| Metrik | Wert | Bedingung |
|--------|------|-----------|
| Antwortzeit | 5-15s | Durchschnitt |
| Indexierung | 100-500 Seiten/min | Ohne OCR |
| Vector Search | 50-200ms | 1000s Chunks |
| Concurrent Users | 10-50 | Konfigurierbar |
| Memory | 4-12 GB | Abhängig vom Modell |

**Tuning**: Siehe [Configuration Guide - Performance](docs/technical/04_CONFIGURATION.md#4-performance-tuning)

---

##  Sicherheit & Datenschutz

 **Keine externe Datenübertragung**
- LLM läuft lokal (Ollama)
- Embeddings lokal generiert
- Keine Cloud-API-Aufrufe

 **Datenschutz-Features**
- ChromaDB-Telemetrie deaktiviert
- Token-Zensierung in Logs
- Webhook-Secret-Validierung
- Message Protection aktiviert

 **DSGVO-konform**
- Lokale Speicherung
- Keine Nutzerprofile
- Keine Tracking-Mechanismen

**Details**: Siehe [Benutzerhandbuch - Datenschutz](docs/customer/BENUTZERHANDBUCH.md#9-datenschutz--sicherheit)

---

##  Nutzung

### Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `/start` | Bot starten |
| `/help` | Hilfe anzeigen |
| `/status` | Systemstatus prüfen |
| `/screenshot <doc> <page>` | Seite als Bild |
| `/page <doc> <page>` | Text extrahieren |

### Beispiel-Fragen

```
"Was ist TARA in ISO 21434?"
"Erkläre den Unterschied zwischen CAL 1 und CAL 4"
"Wie führe ich eine Risikoanalyse durch?"
"Was bedeutet ECU im Automotive-Kontext?"
```

**Vollständige Anleitung**: [Benutzerhandbuch](docs/customer/BENUTZERHANDBUCH.md)

---
## Deployment auf Railway (Cloud)

**Kurzanleitung:**

1. Forke oder klone dieses Repo und pushe es zu Railway.
2. Lege [Environment Variables](.env.example) im Railway Dashboard an — setze echte Werte für deine Secrets!  
   Genaue Beschreibung aller Optionen siehe [.env.example](./.env.example).
3. **PDF-Dateien:**
   - Empfohlen: Halte PDF in einem privaten (nicht öffentlichen!) Repository
   - Nutze ein Download-Script (siehe [fetch_pdfs_github.py](#)) mit GITHUB_TOKEN, 
      ODER
   - Lade PDF einmalig auf ein Railway Volume und passe CHROMA_DB_PATH/Storage-Pfad an.
4. Klicke auf "Deploy" – Railway baut und startet alles automatisch.
5. Stelle sicher, dass dein FastAPI/Uvicorn-Server auf `os.environ['PORT']` lauscht.
6. Nutze die öffentliche URL von Railway als deinen Telegram `WEBHOOK_URL`.

> **Achtung:** Railway setzt den Port per Umgebungsvariable `$PORT`. Stelle sicher, dass dein Webserver diese Variable nutzt!
>
> Beispiel in Python:
> ```python
> import os
> port = int(os.environ.get("PORT", 8000))
> app.run(host="0.0.0.0", port=port)
> ```


"!!! Achtung !!!" 
$PORT:
import os
port = int(os.environ.get("PORT", 8000))
app.run(host="0.0.0.0", port=port)


Dockerfile CMD
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "bot:app", "--bind", "0.0.0.0:${PORT:-8000}"]


##  Testing

```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/ -m integration

# E2E tests
pytest tests/ -m e2e

# Coverage
pytest --cov=. --cov-report=html
```

**Test-Konzept**: Siehe [Pflichtenheft - Testkonzept](docs/pflichtenheft/PFLICHTENHEFT.md#7-testkonzept)

---

##  Beitragen

Beiträge sind willkommen! Bitte beachten Sie:

1. Fork das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Commit Ihre Änderungen (`git commit -m 'Add AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

**Contribution Guidelines**: Siehe [CONTRIBUTING.md](CONTRIBUTING.md) (falls vorhanden)

---

##  Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

---

##  Danksagungen

- **Ollama** - Lokales LLM Framework
- **ChromaDB** - Vector Database
- **python-telegram-bot** - Telegram Bot Framework
- **sentence-transformers** - Embedding Models
- **FastAPI** - Web Framework

---

##  Support & Kontakt

- **Dokumentation**: [docs/](docs/README.md)
- **Issues**: [GitHub Issues](https://github.com/Natashick/telegram-chat-bot/issues)
- **Repository**: [github.com/Natashick/telegram-chat-bot](https://github.com/Natashick/telegram-chat-bot)

---

##  Roadmap

### Geplante Features
- [ ] Multi-User Support mit Dokumenten-Isolation
- [ ] Admin-Panel für Dokumentenverwaltung
- [ ] Export von Konversationen
- [ ] Erweiterte Filter-Optionen
- [ ] GPU-Beschleunigung für Embeddings
- [ ] Weitere Sprachen (FR, ES, IT)

**Details**: Siehe [Lastenheft - Wunschkriterien](docs/lastenheft/LASTENHEFT.md#12-wunschkriterien)

---

##  Changelog

### Version 1.0 (2026-01-27)
-  Initiale Veröffentlichung
-  Vollständige Dokumentation (Lastenheft, Pflichtenheft, Benutzerhandbuch)
-  Semantische PDF-Suche
-  Ollama LLM Integration
-  Docker Deployment
-  Deutsch/Englisch Support

