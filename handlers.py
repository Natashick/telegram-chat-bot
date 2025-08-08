# handlers.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from vector_store import semantic_search, get_combined_context, index_pdfs
from llm_client import ask_ollama
import json
from telegram.ext import ChatMemberHandler
import logging
from pdf2image import convert_from_path
from PIL import Image
import asyncio
import shutil

USER_STATE_FILE = "user_state.json"

def load_user_state():
    try:
        with open(USER_STATE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_state(state):
    with open(USER_STATE_FILE, "w") as f:
        json.dump(state, f)

# User-zu-Dokument-Mapping
user_selected_doc = load_user_state()

user_screenshot_state = {}
user_last_context = {}

async def show_typing_while_processing(update, duration_seconds=25):
    """
    ZEIGT KONTINUIERLICHES "TIPPT..." WÄHREND LLM ARBEITET
    
    Zweck: Hält "Bot tippt..." Animation während der gesamten Verarbeitung aktiv
    
    Parameter:
    - update: Telegram Update Objekt
    - duration_seconds: Wie lange die Animation maximal läuft
    
    Technisch: Sendet alle 4 Sekunden erneut typing action (Telegram Limit: 5s)
    """
    try:
        for _ in range(duration_seconds // 4):  # Alle 4 Sekunden erneuern
            await update.message.reply_chat_action(action="typing")
            await asyncio.sleep(4)
    except:
        pass  # Ignoriere Fehler falls Chat geschlossen wurde

# Hilfsfunktion: Erkenne typische Folgefragen
FOLLOW_UP_KEYWORDS = [
    "more details", "explain this", "tell me more", "erkläre das", "mehr details", "explain", "details"
]

# NEUE FUNKTION: Erkenne Figure/Table/Image Anfragen
VISUAL_CONTENT_KEYWORDS = [
    "figure", "table", "image", "chart", "diagram", "graph", "bild", "abbildung", "tabelle", "grafik"
]

def extract_figure_table_request(user_question):
    """
    ERKENNT ANFRAGEN FÜR VISUELLE INHALTE
    
    Beispiele:
    - "i need figure H.1" -> ("figure", "H.1")
    - "show me table 5.2" -> ("table", "5.2") 
    - "can you send figure 3" -> ("figure", "3")
    """
    text = user_question.lower()
    
    # Suche nach Mustern wie "figure X.Y", "table A.B", etc.
    import re
    
    # Pattern für Figure/Table mit Nummern
    patterns = [
        r'(?:figure|fig\.?)\s+([a-z]*\.?\d+(?:\.\d+)?)',  # figure H.1, fig 3.2
        r'(?:table|tab\.?)\s+([a-z]*\.?\d+(?:\.\d+)?)',   # table H.8, tab 5.1
        r'(?:image|img)\s+([a-z]*\.?\d+(?:\.\d+)?)',      # image 1.2
        r'(?:abbildung|abb\.?)\s+([a-z]*\.?\d+(?:\.\d+)?)', # abbildung 2.1
        r'(?:tabelle)\s+([a-z]*\.?\d+(?:\.\d+)?)'         # tabelle 3.4
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Bestimme den Typ
            if any(word in text for word in ['figure', 'fig', 'abbildung', 'abb']):
                return ("figure", match.group(1))
            elif any(word in text for word in ['table', 'tab', 'tabelle']):
                return ("table", match.group(1))
            elif any(word in text for word in ['image', 'img', 'bild']):
                return ("image", match.group(1))
    
    return None
def is_follow_up(update, user_question):
    # Antwort auf Bot-Nachricht?
    if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
        return True
    # Enthält typische Schlüsselwörter?
    uq = user_question.lower()
    return any(kw in uq for kw in FOLLOW_UP_KEYWORDS)

def get_pdf_files():
    return [f for f in os.listdir() if f.lower().endswith('.pdf')]

def get_file_display_name(fname):
    return os.path.splitext(os.path.basename(fname))[0]

def get_callback_maps(pdf_files):
    callback_to_file = {f"doc{i}": fname for i, fname in enumerate(pdf_files)}
    file_to_callback = {fname: cb for cb, fname in callback_to_file.items()}
    file_display_name = {fname: get_file_display_name(fname) for fname in pdf_files}
    return callback_to_file, file_to_callback, file_display_name

async def greet_on_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.my_chat_member and update.my_chat_member.new_chat_member.status == "member":
        chat = update.effective_chat
        if chat.type == "private":
            pass  # Begrüßungsnachricht entfernt

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start handler called!")
    print("update:", update)
    print("update.message:", update.message)
    pdf_files = get_pdf_files()
    print("PDF files found:", pdf_files)
    _, file_to_callback, file_display_name = get_callback_maps(pdf_files)
    user_name = update.effective_user.first_name if update.effective_user else "User"
    greeting = f"Hey, {user_name}! Please select a document to ask questions about."
    # Begrüßung und Hinweis auf /start
    keyboard = [
        [InlineKeyboardButton(file_display_name[fname], callback_data=file_to_callback[fname])]
        for fname in pdf_files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(greeting, reply_markup=reply_markup)

async def select_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pdf_files = get_pdf_files()
    _, file_to_callback, file_display_name = get_callback_maps(pdf_files)
    keyboard = [
        [InlineKeyboardButton(file_display_name[fname], callback_data=file_to_callback[fname])]
        for fname in pdf_files
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Select document:", reply_markup=reply_markup)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text("Select document:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pdf_files = get_pdf_files()
    callback_to_file, _, _ = get_callback_maps(pdf_files)
    query = update.callback_query
    if not query or not query.data or query.data not in callback_to_file:
        await query.edit_message_text("Invalid document selection.")  # type: ignore
        return
    await query.answer()
    user_id = query.from_user.id
    selected_doc = callback_to_file[query.data]
    user_selected_doc[user_id] = selected_doc
    save_user_state(user_selected_doc)
    await query.edit_message_text(text=f"Selected document: {get_file_display_name(selected_doc)}\nNow ask your question!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        user_question = update.message.text or ""
        selected_doc = user_selected_doc.get(user_id)
        if not selected_doc:
            await select_document(update, context)
            return
        # BEST PRACTICE: Optimierte semantische Suche
        logging.debug(f"[DEBUG] Starte semantic_search für: {user_question}")
        results = semantic_search(user_question, selected_doc, n_results=3)
        logging.debug(f"[DEBUG] Semantic search abgeschlossen")
        
        # BEST PRACTICE: Verwende die neue kombinierte Kontext-Funktion
        context = get_combined_context(results)
        
        if context and context != "No relevant information found.":
            print(f"[INFO] Found relevant context: {len(context)} characters")
            
            # 💬 STARTE KONTINUIERLICHE "BOT TIPPT..." ANIMATION
            typing_task = asyncio.create_task(show_typing_while_processing(update, 25))
            
            try:
                answer = await ask_ollama(user_question, context)
                user_last_context[user_id] = context
            finally:
                # Stoppe typing animation
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
        else:
            answer = "No relevant content found in the selected document."
        max_length = 4096
        for i in range(0, len(answer), max_length):
            await update.message.reply_text(answer[i:i+max_length])
    except Exception as e:
        print(f"[DEBUG] Fehler im handle_message: {e}")
        import traceback
        traceback.print_exc()

async def upload_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PDF UPLOAD FUNKTION
    Nur der Bot-Besitzer kann PDFs hochladen
    """
    user_id = update.effective_user.id
    print(f"[DEBUG] /upload aufgerufen von User {user_id}")
    
    # PRIVAT PDF UPLOAD: Nur du kannst PDFs hochladen
    ALLOWED_USER_ID = 123456789  # Ersetze mit deiner Telegram User ID
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ **PDF Upload verweigert!**\n\nNur der Bot-Besitzer kann PDFs hochladen. Du kannst aber Fragen zu den vorhandenen Dokumenten stellen!")
        return
    
    await update.message.reply_text("📄 Sende mir eine PDF-Datei und ich werde sie für Fragen verfügbar machen!")

async def handle_pdf_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    VERARBEITET HOCHGELADENE PDF-DATEIEN
    """
    user_id = update.effective_user.id
    
    # PRIVAT PDF UPLOAD: Nur du kannst PDFs hochladen
    ALLOWED_USER_ID = 123456789  # Ersetze mit deiner Telegram User ID
    
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ **PDF Upload verweigert!**\n\nNur der Bot-Besitzer kann PDFs hochladen. Du kannst aber Fragen zu den vorhandenen Dokumenten stellen!")
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ Das ist keine PDF-Datei. Bitte sende eine PDF.")
        return
    
    document = update.message.document
    
    if not document.file_name.lower().endswith('.pdf'):
        await update.message.reply_text("❌ Bitte sende nur PDF-Dateien.")
        return
    
    try:
        # PDF herunterladen
        file = await context.bot.get_file(document.file_id)
        pdf_path = f"uploaded_{user_id}_{document.file_name}"
        
        # Datei speichern
        await file.download_to_drive(pdf_path)
        
        # PDF indexieren für semantische Suche
        index_pdfs([pdf_path])
        
        # User-Dokument setzen
        user_selected_doc[user_id] = pdf_path
        save_user_state(user_selected_doc)
        
        await update.message.reply_text(
            f"✅ PDF '{document.file_name}' erfolgreich hochgeladen und indexiert!\n\n"
            f"Du kannst jetzt Fragen zu diesem Dokument stellen."
        )
        
        print(f"[DEBUG] PDF {pdf_path} von User {user_id} hochgeladen und indexiert")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Fehler beim Hochladen: {str(e)}")
        print(f"[DEBUG] PDF Upload Fehler: {e}")

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    SCREENSHOT FUNKTION - VIEW-ONLY (nicht speicherbar)
    User können Screenshots sehen aber nicht speichern
    """
    user_id = update.effective_user.id
    print(f"[DEBUG] /screenshot aufgerufen von User {user_id}")
    user_screenshot_state[user_id] = {'step': 'awaiting_page'}
    await update.message.reply_text("Enter page number for view-only screenshot (e.g., 12):")

async def handle_screenshot_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"[DEBUG] handle_screenshot_dialog aufgerufen von User {user_id}")
    state = user_screenshot_state.get(user_id)
    print(f"[DEBUG] Aktueller Screenshot-State: {state}")
    if not state:
        return
    if state['step'] == 'awaiting_page':
        try:
            page = int(update.message.text.strip())
            state['page'] = page
            state['step'] = 'awaiting_crop'
            await update.message.reply_text("Optional: Enter crop box as left,upper,right,lower (e.g., 100,200,400,600) or 'no' for full page:")
        except Exception:
            await update.message.reply_text("Invalid page number. Please enter a valid number:")
    elif state['step'] == 'awaiting_crop':
        crop_input = update.message.text.strip().lower()
        crop_box = None
        if crop_input != 'no':
            try:
                # VERBESSERTE CROP BOX PARSING
                # Entferne Leerzeichen und teile bei Komma
                coords = [x.strip() for x in crop_input.split(',')]
                if len(coords) != 4:
                    raise ValueError("Need exactly 4 coordinates")
                crop_box = tuple(map(int, coords))
                print(f"[DEBUG] Parsed crop_box: {crop_box}")
            except Exception as e:
                print(f"[DEBUG] Crop parsing error: {e}")
                await update.message.reply_text("Invalid crop box. Please enter as left,upper,right,lower (e.g., 100,200,400,600) or 'no':")
                return
        # Screenshot erzeugen
        pdf_files = get_pdf_files()
        selected_doc = user_selected_doc.get(user_id, pdf_files[0] if pdf_files else None)
        if not selected_doc:
            await update.message.reply_text("No document selected or available.")
            user_screenshot_state.pop(user_id, None)
            return
        try:
            images = convert_from_path(selected_doc, first_page=state['page'], last_page=state['page'])
            img = images[0]
            if crop_box:
                img = img.crop(crop_box)
            
            # SICHERHEIT: Als PHOTO senden aber mit SCHUTZ-OPTIONEN
            import io
            from telegram import InputMediaPhoto
            
            # WASSERZEICHEN HINZUFÜGEN (diskret aber sichtbar)
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Kleines Wasserzeichen unten rechts
            watermark_text = "VIEW ONLY"
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Position unten rechts
            img_width, img_height = img.size
            text_width = draw.textlength(watermark_text, font=font)
            
            # Halbtransparenter Hintergrund
            draw.rectangle(
                [(img_width - text_width - 10, img_height - 35), (img_width - 5, img_height - 5)],
                fill=(0, 0, 0, 100)
            )
            
            # Weißer Text auf dunklem Hintergrund
            draw.text(
                (img_width - text_width - 8, img_height - 30),
                watermark_text,
                fill=(255, 255, 255, 200),
                font=font
            )
            
            # Als JPEG speichern (verhindert einfaches Kopieren)
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=85)
            img_buffer.seek(0)
            
            # Als PHOTO senden mit SCHUTZ-EINSTELLUNGEN
            await update.message.reply_photo(
                photo=img_buffer,
                caption="Page screenshot - View only",
                has_spoiler=True,  # SPOILER-SCHUTZ: User muss klicken um zu sehen
                protect_content=True  # VERHINDERT Weiterleitung und Screenshots in Telegram
            )
            print(f"[DEBUG] Screenshot gesendet für Seite {state['page']} und crop_box {crop_box}")
        except Exception as e:
            await update.message.reply_text(f"Error creating screenshot: {e}")
            print(f"[DEBUG] Fehler beim Screenshot: {e}")
        user_screenshot_state.pop(user_id, None)

async def find_and_send_visual_content(update: Update, content_type: str, content_id: str):
    """
    SUCHT UND SENDET FIGURE/TABLE ALS SCREENSHOT
    
    Parameter:
    - content_type: "figure", "table", "image"
    - content_id: "H.1", "5.2", etc.
    """
    user_id = update.effective_user.id
    selected_doc = user_selected_doc.get(user_id)
    
    if not selected_doc:
        await update.message.reply_text("Please select a document first using /start")
        return
    
    # Typing animation während Suche
    await update.message.reply_chat_action(action="typing")
    
    try:
        # SUCHE NACH VISUAL CONTENT IN PDF
        print(f"[DEBUG] Suche nach {content_type} {content_id} in {selected_doc}")
        
        # Durchsuche PDF nach dem spezifischen Content
        from pdf_parser import extract_paragraphs_from_pdf
        import re
        
        chunks = extract_paragraphs_from_pdf(selected_doc, chunk_size=5)
        found_page = None
        found_context = ""
        
        # Verschiedene Suchmuster für Figure/Table
        escaped_id = content_id.replace('.', r'\.')  # Escape dots außerhalb f-string
        search_patterns = [
            f"{content_type}\\s*{content_id}",  # "Figure H.1"
            f"{content_type}\\s*{escaped_id}",  # Escaped dots
            f"{content_id}",  # Nur die Nummer
            f"{content_type.capitalize()}\\s*{content_id}",  # "Figure H.1"
        ]
        
        # VERBESSERTE SEITENSCHÄTZUNG durch PyPDF2
        import PyPDF2
        total_pages = 0
        try:
            with open(selected_doc, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
        except:
            total_pages = 100  # Fallback
        
        for i, chunk in enumerate(chunks):
            for pattern in search_patterns:
                if re.search(pattern, chunk, re.IGNORECASE):
                    # BESSERE Seitenschätzung basierend auf Chunk-Position
                    estimated_page = max(1, min(total_pages, int((i / len(chunks)) * total_pages) + 1))
                    found_page = estimated_page
                    found_context = chunk[:300] + "..."
                    print(f"[DEBUG] Found {content_type} {content_id} in chunk {i}, estimated page {estimated_page}")
                    break
            if found_page:
                break
        
        if found_page:
            # ERSTELLE AUTOMATISCHEN SCREENSHOT
            await update.message.reply_text(f"Found {content_type} {content_id} on page {found_page}. Generating screenshot...")
            
            # Screenshot ohne Dialog - direkt erstellen
            from pdf2image import convert_from_path
            from PIL import ImageDraw, ImageFont
            import io
            
            images = convert_from_path(selected_doc, first_page=found_page, last_page=found_page)
            img = images[0]
            
            # Wasserzeichen hinzufügen
            draw = ImageDraw.Draw(img)
            watermark_text = f"{content_type.upper()} {content_id} - VIEW ONLY"
            
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # Position unten rechts
            img_width, img_height = img.size
            text_width = draw.textlength(watermark_text, font=font)
            
            # Halbtransparenter Hintergrund
            draw.rectangle(
                [(img_width - text_width - 10, img_height - 30), (img_width - 5, img_height - 5)],
                fill=(0, 0, 0, 120)
            )
            
            # Weißer Text
            draw.text(
                (img_width - text_width - 8, img_height - 25),
                watermark_text,
                fill=(255, 255, 255, 200),
                font=font
            )
            
            # Als JPEG speichern
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=90)
            img_buffer.seek(0)
            
            # Als geschütztes Photo senden
            await update.message.reply_photo(
                photo=img_buffer,
                caption=f"{content_type.capitalize()} {content_id} from page {found_page}\n\n{found_context}",
                has_spoiler=True,
                protect_content=True
            )
            
            print(f"[DEBUG] {content_type} {content_id} Screenshot gesendet von Seite {found_page}")
            
        else:
            await update.message.reply_text(f"Sorry, I couldn't find {content_type} {content_id} in the selected document. Try using /screenshot to manually browse pages.")
            
    except Exception as e:
        print(f"[DEBUG] Fehler bei Visual Content Suche: {e}")
        await update.message.reply_text(f"Error searching for {content_type} {content_id}: {e}")

async def main_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_question = update.message.text or ""
    
    # NEUE FUNKTION: Erkenne Figure/Table Anfragen
    visual_request = extract_figure_table_request(user_question)
    if visual_request:
        content_type, content_id = visual_request
        print(f"[DEBUG] Visual content request: {content_type} {content_id}")
        await find_and_send_visual_content(update, content_type, content_id)
        return
    
    # NEUE FUNKTION: Erkenne PDF Uploads
    if update.message.document:
        await handle_pdf_upload(update, context)
        return
    
    if user_id in user_screenshot_state:
        print(f"[DEBUG] Router: Screenshot-Dialog für User {user_id}")
        await handle_screenshot_dialog(update, context)
    elif is_follow_up(update, user_question):
        print(f"[DEBUG] Router: Folgefrage für User {user_id}")
        last_context = user_last_context.get(user_id)
        print(f"[DEBUG] Letzter Kontext für User {user_id}: {last_context}")
        if last_context:
            # STARTE KONTINUIERLICHE "BOT TIPPT..." FÜR FOLLOW-UP FRAGEN
            typing_task = asyncio.create_task(show_typing_while_processing(update, 25))
            
            try:
                answer = await ask_ollama(user_question, last_context)
            finally:
                # Stoppe typing animation
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
                    
            max_length = 4096
            for i in range(0, len(answer), max_length):
                await update.message.reply_text(answer[i:i+max_length])
        else:
            await handle_message(update, context)
    else:
        print(f"[DEBUG] Router: Normale Frage für User {user_id}")
        await handle_message(update, context)