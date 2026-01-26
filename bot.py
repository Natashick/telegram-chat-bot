# bot.py
import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import asyncio
from contextlib import asynccontextmanager
from llm_client import test_ollama_connection

# Konfiguration aus Umgebungsvariablen (kein hartkodiertes Token!)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Please set it in your environment (e.g. via .env).")

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret123")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL is required. Polling mode is not supported in this deployment.")

# Logging konfigurieren
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Hier Anwendung erstellen
application = Application.builder().token(TELEGRAM_TOKEN).build()
# Um eine Aufgabenexplosion zu vermeiden, muss die parallele Hintergrundverarbeitung von Aktualisierungen begrenzt werden.
_UPDATE_SEMA = asyncio.Semaphore(int(os.getenv("MAX_UPDATE_CONCURRENCY", "10")))

async def _process_update_bg(update: Update):
    async with _UPDATE_SEMA:
        try:
            await application.process_update(update)
        except Exception as e:
            logger.exception(f"Fehler in background update processing: {e}")

# Handler registrieren (bevorzugt schlanke handlers1, falls vorhanden)
try:
    from handlers1 import (
        start_command,
        handle_message,
        button_callback,
        help_command,
        status_command,
        screenshot_command
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("screenshot", screenshot_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
except Exception as e:
    logger.exception(f"Failed to register handlers: {e}")
    raise

async def setup_webhook(application: Application):
    try:
        webhook_url = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"
        await application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )
        logger.info(f"Webhook eingerichtet: {webhook_url}")
        # Menü-Befehle leeren, чтобы не дублировать с ReplyKeyboard (/start, /screenshot)
        try:
            await application.bot.set_my_commands([])
        except Exception as ce:
            logger.debug(f"set_my_commands warn: {ce}")
    except Exception as e:
        logger.error(f"Durch das Einrichten des Webhooks ist ein Fehler aufgetreten: {e}")
        raise

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # startup
    logger.info("Starting application...")
    await application.initialize()
    await application.start()
    await setup_webhook(application)
    # Ollama availability check
    try:
        ok = await test_ollama_connection()
        if not ok:
            logger.error("Ollama ist nicht erreichbar – bitte prüfen (URL/Port/Modell).")
        else:
            logger.info("Ollama-Verbindung OK.")
    except Exception as e:
        logger.error(f"Ollama-Check Fehler: {e}")
    try:
        # Запуск прединдексации только если явно включено
        pre_enabled = os.getenv("PREINDEX_ENABLED", "1") != "0"
        if pre_enabled:
            # gather pdf list from handlers1 and schedule via indexer
            from handlers1 import get_pdf_files
            from indexer import preindex_all_pdfs as _preindex
            pdfs = get_pdf_files()
            asyncio.create_task(_preindex(pdfs))
            logger.info("Preindex task started in background (flag).")
        else:
            logger.info("Preindex disabled (set PREINDEX_ENABLED=1 to enable).")
    except Exception as e:
        logger.debug(f"Preindex task could not be started: {e}")
    yield
    # shutdown
    logger.info("Stopping application...")
    try:
        await application.stop()
        await application.shutdown()
    except Exception as e:
        logger.exception(f"Fehler beim Stoppen des Bots: {e}")

# FastAPI App (mit Lifespan-Handler statt on_event)
app = FastAPI(title="Telegram Bot API", version="1.0.0", lifespan=lifespan)

@app.post(f"/webhook/{WEBHOOK_SECRET}")
async def webhook_handler(request: Request):
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, application.bot)
        # Non-blocking processing so webhook returns 200 immediately
        asyncio.create_task(_process_update_bg(update))
        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.exception(f"Fehler im Webhook: {e}")
        return Response(content="Error", status_code=500)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "webhook_configured": bool(WEBHOOK_URL),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
