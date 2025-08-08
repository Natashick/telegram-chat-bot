# bot.py
# HAUPT-BOT-DATEI - Zentrale FastAPI-Anwendung für Telegram Bot
# Zweck: Verbindet Telegram Bot mit FastAPI Webhook-Server und startet alle Services
# Verwendet: FastAPI für Webhooks, python-telegram-bot für Bot-Funktionalität

import os
from fastapi import FastAPI, Request, Response
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ChatMemberHandler
from handlers import start, select_document, button, handle_message, greet_on_new_chat, screenshot_command, upload_pdf_command, main_message_router
from vector_store import index_pdfs
from contextlib import asynccontextmanager
import asyncio

# UMGEBUNGSVARIABLEN LADEN UND VALIDIEREN
# Zweck: Überprüft ob alle notwendigen Konfigurationsvariablen gesetzt sind
# Warum wichtig: Bot funktioniert nicht ohne Token und Ollama-Konfiguration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    print("FEHLER: TELEGRAM_TOKEN ist nicht gesetzt!")
    print("Lösung: $env:TELEGRAM_TOKEN=\"DEIN-TOKEN-HIER\"")
    raise ValueError("TELEGRAM_TOKEN Umgebungsvariable ist nicht gesetzt.")

# Webhook URL für Telegram (optional für lokale Tests)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# Ollama Server URL (Standard: localhost:11434)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# LLM Model das verwendet werden soll (Standard: llama3.2:3b)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# KONFIGURATION ANZEIGEN
# Zweck: Debug-Informationen für einfacheres Troubleshooting
print(f"Telegram Bot startet...")
print(f"Webhook URL: {WEBHOOK_URL or 'NICHT GESETZT (nur für lokale Tests)'}")
print(f"Ollama URL: {OLLAMA_URL}")
print(f"LLM Model: {OLLAMA_MODEL}")

# Webhook-Pfad generieren (einzigartig durch Token)
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"

# TELEGRAM BOT ERSTELLEN
# Zweck: Initialisiert den Bot mit dem Token aus den Umgebungsvariablen
app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


# FASTAPI LIFESPAN MANAGER
# Zweck: Verwaltet Startup und Shutdown des Bots während FastAPI läuft
# Warum nötig: Bot muss vor ersten Requests initialisiert werden
@asynccontextmanager
async def lifespan(app: FastAPI):
    # BOT STARTUP PHASE
    # Bot initialisieren (Verbindung zu Telegram herstellen)
    await app_bot.initialize()
    # HANDLER REGISTRIEREN
    # Zweck: Definiert welche Funktionen auf welche Telegram-Events reagieren
    app_bot.add_handler(CommandHandler("start", start))  # /start Kommando
    app_bot.add_handler(CommandHandler("select", select_document))  # /select Kommando
    app_bot.add_handler(CommandHandler("upload", upload_pdf_command))  # /upload Kommando
    app_bot.add_handler(CallbackQueryHandler(button))  # Inline-Button Klicks
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_message_router))  # Text-Nachrichten
    app_bot.add_handler(MessageHandler(filters.Document.ALL, main_message_router))  # PDF Uploads
    app_bot.add_handler(ChatMemberHandler(greet_on_new_chat, chat_member_types=["my_chat_member"]))  # Bot zu Chat hinzugefügt
    app_bot.add_handler(CommandHandler("screenshot", screenshot_command))  # /screenshot Kommando (VIEW-ONLY)
    # Bot starten (Polling/Webhook Modus aktivieren)
    await app_bot.start()
    print("Telegram-Bot gestartet.")
    
    # PDF INDEXIERUNG
    # Zweck: Alle PDF-Dateien im Verzeichnis für semantische Suche vorbereiten
    # Warum wichtig: Ohne Indexierung kann der Bot keine Fragen zu PDFs beantworten
    pdfs = [f for f in os.listdir() if f.lower().endswith(".pdf")]
    if pdfs:
        index_pdfs(pdfs)  # Erstellt Embeddings und speichert in ChromaDB
        print(f"{len(pdfs)} PDFs indexiert.")
    else:
        print("Keine PDFs gefunden zum Indexieren.")
    # WEBHOOK KONFIGURATION
    # Zweck: Teilt Telegram mit, wo Updates hingesendet werden sollen
    # Webhook vs Polling: Webhook = Push, Polling = Pull
    if WEBHOOK_URL:
        webhook = WEBHOOK_URL + WEBHOOK_PATH
        try:
            await app_bot.bot.setWebhook(webhook)
            print(f"Webhook gesetzt auf {webhook}")
        except Exception as e:
            print(f"Fehler beim Setzen des Webhooks: {e}")
    else:
        print("Kein WEBHOOK_URL gesetzt. Webhook wird nicht aktiviert.")
    yield  # Hier läuft die FastAPI Anwendung
    
    # SHUTDOWN PHASE
    # Zweck: Sauberes Herunterfahren ohne Datenverlust
    await app_bot.stop()
    await app_bot.shutdown()
    print("Telegram-Bot gestoppt.")

# FASTAPI ANWENDUNG ERSTELLEN
# Zweck: Haupt-Webserver der die Webhook-Endpoints bereitstellt
app = FastAPI(lifespan=lifespan)

# HEALTH CHECK ENDPOINT FÜR RAILWAY
@app.get("/health")
async def health_check():
    """
    HEALTH CHECK ENDPOINT
    Zweck: Railway überprüft ob Bot läuft
    """
    return {"status": "healthy", "bot": "running"}

# WEBHOOK ENDPOINT
# Zweck: Empfängt Updates von Telegram und leitet sie an den Bot weiter
# HTTP POST wird von Telegram bei jeder Nachricht/Aktion aufgerufen
@app.post(WEBHOOK_PATH)
async def telegram_webhook(req: Request):
    """Verarbeitet eingehende Telegram Updates via Webhook
    
    Flow: Telegram -> ngrok -> FastAPI -> python-telegram-bot -> handlers
    """
    print("Webhook called!")
    try:
        # JSON Daten von Telegram parsen
        data = await req.json()
        print("Update received:", data)
        
        # Telegram Update Objekt erstellen
        update = Update.de_json(data, app_bot.bot)
        print("Update object:", update)
        
        # Update an Bot-Handler weiterleiten
        await app_bot.process_update(update)
        return Response(status_code=200)  # Telegram bestätigen
    except Exception as e:
        print(f"FEHLER bei der Webhook-Verarbeitung: {e}")
        import traceback
        traceback.print_exc()
        return Response(status_code=200)  # Immer 200 zurückgeben, sonst sendet Telegram erneut
