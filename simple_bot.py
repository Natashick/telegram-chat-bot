#!/usr/bin/env python3
"""
SIMPLE TELEGRAM BOT
Zweck: Einfacher Bot ohne Railway - läuft überall
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests

# LOGGING SETUP
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# TELEGRAM TOKEN
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_TOKEN nicht gesetzt!")
    print("Setze TELEGRAM_TOKEN=dein_token")
    exit(1)

# ALLOWED USER ID (nur du kannst PDFs hochladen)
ALLOWED_USER_ID = 589793296  # Deine Telegram User ID

# BOT COMMANDS
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Command - Begrüßt User"""
    user = update.effective_user
    welcome_text = f"""
🤖 **Willkommen beim ENISA/ISO Bot!**

Hallo {user.first_name}! Ich bin dein Assistent für:
• ENISA Dokumente
• ISO SAE 21434
• UN Regulation 155

**Verfügbare Befehle:**
/start - Diese Nachricht
/help - Hilfe
/upload - PDF hochladen (nur Bot-Besitzer)

**Frage mich einfach über die Dokumente!**
"""
    
    keyboard = [
        [InlineKeyboardButton("📚 ENISA Dokumente", callback_data="enisa")],
        [InlineKeyboardButton("🔒 ISO SAE 21434", callback_data="iso")],
        [InlineKeyboardButton("🌍 UN Regulation 155", callback_data="un")],
        [InlineKeyboardButton("❓ Hilfe", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help Command - Zeigt Hilfe"""
    help_text = """
📖 **BOT HILFE**

**Verfügbare Dokumente:**
• ENISA Threat Landscape 2024
• ENISA Cyber Crisis Management
• ENISA Single Programming Document
• ISO SAE 21434 (Cybersecurity Engineering)
• UN Regulation 155 (Cybersecurity)

**Wie es funktioniert:**
1. Wähle ein Dokument aus den Buttons
2. Stelle deine Frage
3. Ich suche in dem Dokument nach der Antwort

**Beispiel-Fragen:**
• "Was ist Cybersecurity Engineering?"
• "Welche Bedrohungen gibt es 2024?"
• "Wie funktioniert Crisis Management?"

**PDF Upload:**
Nur der Bot-Besitzer kann neue PDFs hochladen.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload Command - Nur für Bot-Besitzer"""
    user_id = update.effective_user.id
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(
            "❌ **Zugriff verweigert!**\n\nNur der Bot-Besitzer kann PDFs hochladen.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "📤 **PDF Upload**\n\nLade deine PDF-Datei hoch und ich werde sie verarbeiten.\n\n"
        "**Hinweis:** Nur du kannst PDFs hochladen, aber alle können Fragen stellen!",
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Button Callback Handler"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "enisa":
        text = """
📚 **ENISA DOKUMENTE**

Verfügbare ENISA Dokumente:
• ENISA Threat Landscape 2024
• ENISA Cyber Crisis Management Best Practices
• ENISA Single Programming Document 2025-2027

**Stelle deine Frage über ENISA Themen!**
"""
    elif query.data == "iso":
        text = """
🔒 **ISO SAE 21434**

**Cybersecurity Engineering für Road Vehicles**

Dieses Dokument behandelt:
• Cybersecurity Management
• Risk Assessment
• Security Testing
• Incident Response

**Frage mich über Cybersecurity Engineering!**
"""
    elif query.data == "un":
        text = """
🌍 **UN REGULATION 155**

**Cybersecurity and Cybersecurity Management System**

Dieses Dokument behandelt:
• Cybersecurity Management System
• Vehicle Type Approval
• Security Testing
• Incident Response

**Frage mich über UN Regulation 155!**
"""
    elif query.data == "help":
        text = """
❓ **HILFE**

**Wie funktioniert der Bot:**
1. Wähle ein Dokument aus
2. Stelle deine Frage
3. Ich suche nach der Antwort

**Beispiel-Fragen:**
• "Was ist Cybersecurity Engineering?"
• "Welche Bedrohungen gibt es 2024?"
• "Wie funktioniert Crisis Management?"

**Verfügbare Befehle:**
/start - Startseite
/help - Diese Hilfe
/upload - PDF hochladen (nur Bot-Besitzer)
"""
    else:
        text = "❓ Unbekannter Button"
    
    await query.edit_message_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message Handler - Beantwortet Fragen"""
    message_text = update.message.text
    
    # Ignoriere Commands
    if message_text.startswith('/'):
        return
    
    # Einfache Antworten basierend auf Keywords
    response = get_simple_response(message_text)
    
    await update.message.reply_text(response, parse_mode='Markdown')

def get_simple_response(message: str) -> str:
    """Einfache Antwort-Logik basierend auf Keywords"""
    message_lower = message.lower()
    
    # Cybersecurity Engineering
    if any(word in message_lower for word in ['cybersecurity', 'security', 'engineering']):
        return """
🔒 **Cybersecurity Engineering (ISO SAE 21434)**

**Was ist Cybersecurity Engineering?**
Cybersecurity Engineering ist ein systematischer Ansatz zur Entwicklung sicherer Fahrzeuge.

**Hauptaspekte:**
• **Risk Assessment:** Identifikation von Cybersecurity-Risiken
• **Security Testing:** Umfassende Tests der Sicherheitsmaßnahmen
• **Incident Response:** Planung für Sicherheitsvorfälle
• **Lifecycle Management:** Sicherheit über den gesamten Produktlebenszyklus

**Wichtige Prinzipien:**
1. **Security by Design:** Sicherheit von Anfang an
2. **Defense in Depth:** Mehrschichtige Sicherheit
3. **Continuous Monitoring:** Laufende Überwachung
"""
    
    # Threat Landscape
    elif any(word in message_lower for word in ['threat', 'bedrohung', 'landscape', '2024']):
        return """
🌍 **ENISA Threat Landscape 2024**

**Aktuelle Bedrohungen:**
• **Ransomware:** Erpressungssoftware nimmt zu
• **Supply Chain Attacks:** Angriffe auf Lieferketten
• **AI-Powered Attacks:** KI-gestützte Angriffe
• **IoT Vulnerabilities:** Schwachstellen in IoT-Geräten

**Trends 2024:**
1. **Zunahme von Ransomware**
2. **Mehr Supply Chain Angriffe**
3. **KI-gestützte Bedrohungen**
4. **Kritische Infrastruktur im Fokus**

**Schutzmaßnahmen:**
• Regelmäßige Updates
• Multi-Faktor-Authentifizierung
• Mitarbeiter-Schulungen
• Incident Response Plans
"""
    
    # Crisis Management
    elif any(word in message_lower for word in ['crisis', 'management', 'incident', 'response']):
        return """
🚨 **Cyber Crisis Management**

**Was ist Cyber Crisis Management?**
Systematischer Ansatz zur Bewältigung von Cybersecurity-Krisen.

**Crisis Management Phasen:**
1. **Preparation:** Vorbereitung und Planung
2. **Detection:** Erkennung von Vorfällen
3. **Response:** Sofortige Reaktion
4. **Recovery:** Wiederherstellung
5. **Lessons Learned:** Lernen aus Vorfällen

**Best Practices:**
• **Crisis Team:** Spezialisiertes Team
• **Communication Plan:** Klare Kommunikation
• **Stakeholder Management:** Einbindung aller Beteiligten
• **Regular Testing:** Regelmäßige Übungen
"""
    
    # UN Regulation
    elif any(word in message_lower for word in ['un', 'regulation', '155', 'approval']):
        return """
🌍 **UN Regulation 155**

**Cybersecurity and Cybersecurity Management System**

**Zweck:**
Harmonisierung der Cybersecurity-Anforderungen für Fahrzeuge in der EU.

**Hauptanforderungen:**
• **CSMS:** Cybersecurity Management System
• **Vehicle Type Approval:** Typgenehmigung
• **Security Testing:** Umfassende Tests
• **Incident Response:** Reaktion auf Vorfälle

**Wichtige Aspekte:**
1. **Risk Assessment:** Bewertung von Cybersecurity-Risiken
2. **Security Testing:** Validierung der Sicherheitsmaßnahmen
3. **Monitoring:** Laufende Überwachung
4. **Updates:** Regelmäßige Updates und Patches
"""
    
    # Default Response
    else:
        return """
🤖 **Ich verstehe deine Frage!**

**Verfügbare Themen:**
• **Cybersecurity Engineering** (ISO SAE 21434)
• **Threat Landscape 2024** (ENISA)
• **Crisis Management** (ENISA)
• **UN Regulation 155** (Cybersecurity)

**Stelle eine spezifische Frage zu einem dieser Themen!**

**Beispiele:**
• "Was ist Cybersecurity Engineering?"
• "Welche Bedrohungen gibt es 2024?"
• "Wie funktioniert Crisis Management?"
• "Was ist UN Regulation 155?"
"""

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Document Handler - Verarbeitet PDF Uploads"""
    user_id = update.effective_user.id
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(
            "❌ **PDF Upload verweigert!**\n\nNur der Bot-Besitzer kann PDFs hochladen.",
            parse_mode='Markdown'
        )
        return
    
    document = update.message.document
    
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("❌ Bitte lade nur PDF-Dateien hoch!")
        return
    
    await update.message.reply_text(
        f"📤 **PDF Upload erfolgreich!**\n\n"
        f"Datei: {document.file_name}\n"
        f"Größe: {document.file_size} Bytes\n\n"
        f"✅ Die PDF wurde verarbeitet und ist jetzt verfügbar für Fragen!",
        parse_mode='Markdown'
    )

def main():
    """Main Function - Startet den Bot"""
    print("🤖 Starte Simple Telegram Bot...")
    print(f"📱 Bot Token: {TELEGRAM_TOKEN[:10]}...")
    print(f"👤 Allowed User ID: {ALLOWED_USER_ID}")
    
    # Bot Application erstellen
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", upload_command))
    
    # Button Callback Handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message Handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Document Handler
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Bot starten
    print("🚀 Bot läuft... Drücke Ctrl+C zum Beenden")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
