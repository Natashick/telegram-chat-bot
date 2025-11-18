# README
# Telegram PDF Chatbot (mit ChromaDB & Ollama)

## Features
- Fragt PDFs im Ordner per Telegram-Bot ab (semantische Suche)
- Inline-Buttons für Dokumentauswahl
- Lokale LLM-Antworten (Ollama, z.B. Mistral)
- OCR für gescannte PDFs
- Persistente Vektor-Datenbank (ChromaDB)
- Webhook-Deployment (FastAPI)

## Setup (Docker Compose empfohlen)

1. PDFs in den Ordner `./pdfs` legen (nur Lesen im Container).
2. `.env` neben `docker-compose.yml` erstellen:
   ```env
   TELEGRAM_TOKEN=DEIN_TELEGRAM_TOKEN
   # Für Webhook (ngrok o.ä.). Leer lassen für Polling.
   WEBHOOK_URL=https://<dein>.ngrok-free.app
   # Optional:
   WEBHOOK_SECRET=secret123
   OLLAMA_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=llama3.2:3b
   OLLAMA_EMBED_MODEL=nomic-embed-text
   OCR_CONCURRENCY=1
   PDF_DIR=/app/pdfs
   ```
3. Starten
   ```bash
   docker compose up -d --build
   ```
4. Healthcheck
   ```bash
   curl http://localhost:8000/health
   ```
5. Webhook prüfen (optional)
   ```bash
   curl "https://api.telegram.org/bot$TELEGRAM_TOKEN/getWebhookInfo"
   ```

## Alternativ: Lokale Entwicklung

1. **Python-Pakete installieren**
   ```
   pip install -r requirements.txt
   ```

2. **Poppler & Tesseract installieren**
   - Poppler: [Download für Windows](http://blog.alivate.com.au/poppler-windows/)
   - Tesseract: [Download für Windows](https://github.com/tesseract-ocr/tesseract)

3. **Ollama installieren & Modell laden**
   ```
   ollama pull mistral
   ollama serve
   ```

4. **Umgebungsvariablen setzen**
   - `TELEGRAM_TOKEN` (dein Bot-Token)
   - `WEBHOOK_URL` (z.B. von ngrok oder deinem Server)

5. **Bot starten**
   ```
   python -m uvicorn bot:app --host 0.0.0.0 --port 8000
   ```

6. **Webhook setzen**
   - Stelle sicher, dass dein Server/PC von Telegram erreichbar ist (z.B. mit ngrok).

## Hinweise
- PDFs in `./pdfs` legen; im Container sind sie unter `/app/pdfs` (nur Lesen).
- Der Bot indexiert beim Start alle PDFs (Vor-Indexierung, sequentiell, ressourcenschonend) und aktualisiert geänderte Dateien automatisch.
- UI: Start/Language (EN/DE), automatische Paginierung langer Antworten (◀️ Prev / ▶️ Next), Screenshots nach Titel/Stichwort.
- Antworten kommen vom lokalen LLM (Ollama, standardmäßig `llama3.2:3b`). Embeddings via `nomic-embed-text`.

## Fehlerbehebung
- Bei OCR-Problemen: Poppler- und Tesseract-Pfade prüfen.
- Bei LLM-Problemen: Läuft Ollama? Modell geladen?
- Bei Webhook-Problemen: Ist der Server von Telegram erreichbar?
