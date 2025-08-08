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
| `OLLAMA_URL` | Ollama Server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM Modell Name | `llama3.2:3b` |
| `WEBHOOK_URL` | Webhook URL (für Production) | Optional |

## 📖 Verwendung

1. **Starte den Bot** mit `/start`
2. **Wähle ein PDF-Dokument** aus der Liste
3. **Stelle Fragen** zu den Inhalten
4. **Fordere Screenshots an** mit "Show me Figure 5.1" oder "Table 3.2"
5. **Nutze `/screenshot`** für manuelle Seitenscreenshots

## 🛠️ Technologie


- **FastAPI** - Web Framework
- **python-telegram-bot** - Telegram Bot API
- **ChromaDB** - Vector Database für semantische Suche
- **PyPDF2** - PDF Text-Extraktion
- **Ollama** - Lokale LLM-Verarbeitung
- **Docker** - Containerisierung

## 📝 Lizenz

MIT License - Frei verwendbar für private und kommerzielle Projekte.

## 🤝 Beitragen

Pull Requests sind willkommen! Für größere Änderungen öffne bitte zuerst ein Issue.

---

**Entwickelt mit ❤️ für die Community**
