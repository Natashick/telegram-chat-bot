# bot.py
# HAUPT-BOT-DATEI - Zentrale FastAPI-Anwendung für Telegram Bot
# Zweck: Verbindet Telegram Bot mit FastAPI Webhook-Server und startet alle Services
# Verwendet: FastAPI für Webhooks, python-telegram-bot für Bot-Funktionalität

import os
from fastapi import FastAPI, Request, Response
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ChatMemberHandler
from handlers import start, select_document, button, handle_message, greet_on_new_chat, screenshot_command, upload_pdf_command, main_message_router
from contextlib import asynccontextmanager
import asyncio

# UMGEBUNGSVARIABLEN LADEN UND VALIDIEREN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w")
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "dummy_token_for_health_check":
    print("FEHLER: TELEGRAM_TOKEN ist nicht gesetzt!")
    print("Lösung: Setze TELEGRAM_TOKEN in Railway Variables")
    print("WARNING: Bot wird ohne Telegram Token gestartet (nur Health Check verfügbar)")
    TELEGRAM_TOKEN = "7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w"

# Webhook URL für Telegram (optional für lokale Tests)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# Ollama Server URL (Standard: localhost:11434)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
# LLM Model das verwendet werden soll (Standard: llama3.2:3b)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# KONFIGURATION ANZEIGEN
print(f"Telegram Bot startet...")
print(f"Webhook URL: {WEBHOOK_URL or 'NICHT GESETZT (nur für lokale Tests)'}")
print(f"Ollama URL: {OLLAMA_URL}")
print(f"LLM Model: {OLLAMA_MODEL}")

# Webhook-Pfad generieren (einzigartig durch Token)
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"

# TELEGRAM BOT ERSTELLEN
try:
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    print("[INFO] Telegram Bot Application erstellt")
except Exception as e:
    print(f"[ERROR] Telegram Bot Application failed: {e}")
    app_bot = None

# FASTAPI LIFESPAN MANAGER
@asynccontextmanager
async def lifespan(app: FastAPI):
    # BOT STARTUP PHASE
    if app_bot:
        try:
            # Bot initialisieren (Verbindung zu Telegram herstellen)
            await app_bot.initialize()
            # HANDLER REGISTRIEREN
            app_bot.add_handler(CommandHandler("start", start))  # /start Kommando
            app_bot.add_handler(CommandHandler("select", select_document))  # /select Kommando
            app_bot.add_handler(CommandHandler("upload", upload_pdf_command))  # /upload Kommando
            app_bot.add_handler(CallbackQueryHandler(button))  # Inline-Button Klicks
            app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_message_router))  # Text-Nachrichten
            app_bot.add_handler(MessageHandler(filters.Document.ALL, main_message_router))  # PDF Uploads
            app_bot.add_handler(ChatMemberHandler(greet_on_new_chat, chat_member_types=["my_chat_member"]))  # Bot zu Chat hinzugefügt
            app_bot.add_handler(CommandHandler("screenshot", screenshot_command))  # /screenshot Kommando (VIEW-ONLY)
            
            # POLLING MODUS FÜR RAILWAY - KEIN WEBHOOK
            print("🚀 Starte Bot im Polling-Modus für Railway...")
            await app_bot.start()
            print("✅ Telegram-Bot gestartet im Polling-Modus!")
            
        except Exception as e:
            print(f"[ERROR] Bot startup failed: {e}")
    else:
        print("[WARNING] Bot Application nicht verfügbar - nur Health Check verfügbar")
    
    # KEINE PDF INDEXIERUNG BEIM START - verursacht Crashes
    print("PDF Indexierung übersprungen - wird bei Bedarf gemacht")
    
    yield  # Hier läuft die FastAPI Anwendung
    
    # SHUTDOWN PHASE
    if app_bot:
        try:
            await app_bot.stop()
            await app_bot.shutdown()
            print("Telegram-Bot gestoppt.")
        except Exception as e:
            print(f"[ERROR] Bot shutdown failed: {e}")

# FASTAPI ANWENDUNG ERSTELLEN
app = FastAPI(lifespan=lifespan)

# HEALTH CHECK ENDPOINT FÜR RAILWAY
@app.get("/health")
async def health_check():
    """
    HEALTH CHECK ENDPOINT
    Zweck: Railway überprüft ob Bot läuft
    """
    return {"status": "healthy", "bot": "running"}

# ROOT ENDPOINT
@app.get("/")
async def root():
    """
    ROOT ENDPOINT
    Zweck: Zeigt Bot Status
    """
    return {
        "message": "ENISA/ISO Telegram Bot läuft!",
        "status": "active",
        "mode": "polling",
        "health": "/health"
    }
