# handlers.py
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pdf_parser import pdf_parser
from pdf_parser import extract_titles_from_pdf, get_page_image_bytes
from io import BytesIO
from vector_store import vector_store
from llm_client import ask_ollama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-Memory Zustände
pdf_files = []
user_selected_doc = {}
user_screenshot_state = {}
preindex_total = 0
preindex_done = 0
preindex_running = False
user_pages_state = {}  # user_id -> { 'pages': List[str], 'idx': int, 'last_message_id': int }
user_lang_state = {}   # user_id -> "DE"/"EN"
user_shot_candidates = {}  # user_id -> List[Dict]

USER_STATE_FILE = "user_state.json"

def save_user_state(state: dict):
    try:
        import json
        with open(USER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Konnte {USER_STATE_FILE} nicht speichern: {e}")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.getenv('PDF_DIR', _SCRIPT_DIR)

def get_pdf_files():
    try:
        entries = os.listdir(PDF_DIR)
    except Exception:
        entries = []
    return [os.path.join(PDF_DIR, f) for f in entries if f.lower().endswith('.pdf')]

# --- Helpers for thread-wrapping blocking vector_store calls ---

async def _has_document_async(doc_id: str) -> bool:
    return await asyncio.to_thread(vector_store.has_document, doc_id)

async def _add_document_async(doc_id: str, text: str, metadata: dict) -> bool:
    return await asyncio.to_thread(vector_store.add_document, doc_id, text, metadata)

async def _get_combined_context_async(query: str, doc_id: str, max_chunks: int = 4):
    return await asyncio.to_thread(vector_store.get_combined_context_for_document, query, doc_id, max_chunks)

async def _get_document_info_async():
    return await asyncio.to_thread(vector_store.get_document_info)

async def _get_document_version_async(doc_id: str) -> str | None:
    return await asyncio.to_thread(vector_store.get_document_version, doc_id)

async def _delete_document_async(doc_id: str) -> bool:
    return await asyncio.to_thread(vector_store.delete_document, doc_id)

async def _delete_titles_async(doc_id: str) -> bool:
    try:
        return await asyncio.to_thread(vector_store.delete_titles_for_doc, doc_id)
    except Exception:
        return False

# --- Versioning helpers ---

def _compute_doc_version(file_path: str) -> str:
    try:
        st = os.stat(file_path)
        return f"{st.st_size}-{int(st.st_mtime)}"
    except Exception:
        return "unknown"

# --- Commands ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pdf_files
    pdf_files = get_pdf_files()
    context.bot_data['pdf_files'] = pdf_files[:]
    if not pdf_files:
        await update.message.reply_text("Keine PDF-Dateien gefunden. Bitte lade zuerst PDFs hoch.")
        return
    keyboard = [
        [InlineKeyboardButton("🟢 Start", callback_data="start_dialog")],
        [InlineKeyboardButton("🌐 Language: EN/DE", callback_data="lang_toggle")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hallo! Drücke „🟢 Start“, um eine Frage zu stellen. Sprache mit „🌐 Language: EN/DE“ wählen.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "HILFE\n\n"
        "• /start – Menü öffnen\n"
        "• /status – Status des Vector Stores\n\n"
        "Tipps:\n"
        "• Verwende spezifische Suchbegriffe\n"
        "• Frage nach Abschnitten, Tabellen, Nummern\n"
        "• Ich antworte in deiner Sprache"
    )
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    store_info = await _get_document_info_async()
    user_id = update.effective_user.id
    mode_text = "Bereit"
    global preindex_total, preindex_done, preindex_running
    status_text = (
        "BOT-STATUS\n\n"
        f"Aktueller Modus: {mode_text}\n"
        f"Verfügbare PDFs: {len(get_pdf_files())}\n"
        f"Indexierte Chunks: {store_info.get('total_chunks', 0)}\n"
        f"Vector Store: {store_info.get('persist_directory', 'Unbekannt')}\n"
        f"Batch-Größe: {store_info.get('batch_size', 'Unbekannt')}\n"
        f"Preindex: {'laufend' if preindex_running else 'fertig'} "
        f"({preindex_done}/{preindex_total})\n"
    )
    await update.message.reply_text(status_text)

# --- Callback Buttons ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pdf_files
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    # Pagination callbacks
    if query.data in ("page_prev", "page_next"):
        await _handle_pagination_callback(query, context)
        return
    # Screenshot pick/cancel
    if query.data.startswith("shot_pick_"):
        await _handle_screenshot_pick(query, context)
        return
    if query.data == "shot_cancel":
        await query.edit_message_text("Abgebrochen.")
        return

    if query.data == "start_dialog":
        await query.edit_message_text("Stellen Sie Ihre Frage. Ich antworte in der gewählten Sprache.")
        return
    if query.data == "lang_toggle":
        # simple toggle placeholder (persist per user in memory)
        user_id = update.effective_user.id
        lang = context.user_data.get("lang", "DE")
        context.user_data["lang"] = "EN" if lang == "DE" else "DE"
        new_lang = context.user_data["lang"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Start", callback_data="start_dialog")],
            [InlineKeyboardButton("🌐 Language: EN/DE", callback_data="lang_toggle")]
        ])
        greet = "Hallo, {name}! Ich bin TALIA = Threat Analysis & Learning Intelligence Agent – Ihr Assistent für Automotive Cybersecurity.".format(
            name=(update.effective_user.first_name or update.effective_user.username or "User")
        )
        if new_lang == "EN":
            greet = "Hello, {name}! I am TALIA = Threat Analysis & Learning Intelligence Agent – your Automotive Cybersecurity assistant.".format(
                name=(update.effective_user.first_name or update.effective_user.username or "User")
            )
        await query.edit_message_text(
            greet + "\n\n"
            "1) Sprache/Language mit „🌐 Language: EN/DE“ wählen\n"
            "2) „🟢 Start“ drücken und Frage stellen\n"
            "3) Lange Antworten mit „◀️ Prev / ▶️ Next“ blättern\n"
            "4) „🖼 Page screenshot“: Titel/Schlagwort eingeben und Seite als Bild erhalten",
            reply_markup=kb
        )
        return

async def _send_menu(query):
    keyboard = [
        [InlineKeyboardButton("🟢 Start", callback_data="start_dialog")],
        [InlineKeyboardButton("🌐 Language: EN/DE", callback_data="lang_toggle")]
    ]
    await query.message.reply_text("Optionen:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Indexierung ---

async def _ensure_document_indexed(document_name: str):
    """Indexiert ein Dokument (einmalig), mit robustem Logging."""
    try:
        current_version = _compute_doc_version(document_name)
        existing_version = await _get_document_version_async(document_name)
        if existing_version == current_version and await _has_document_async(document_name):
            logger.info(f"Dokument bereits indexiert (Version unverändert): {document_name}")
            return
        if existing_version and existing_version != current_version:
            await _delete_document_async(document_name)
            await _delete_titles_async(document_name)
        logger.info(f"Indexiere Dokument: {document_name}")
        paragraphs = await pdf_parser.extract_paragraphs_from_pdf(document_name)
        if not paragraphs:
            logger.warning(f"Keine Paragraphen extrahiert: {document_name}")
            return
        # zusätzlich: Titel/Überschriften extrahieren und leichtgewichtig indexieren
        try:
            # default is OFF unless explicitly enabled
            if os.getenv("ENABLE_TITLE_INDEX", "0") == "1":
                titles = await asyncio.to_thread(extract_titles_from_pdf, document_name)
                if isinstance(titles, list) and titles:
                    # при полной переиндексации очистим старые записи, затем добавим заново
                    await _delete_titles_async(document_name)
                    await asyncio.to_thread(vector_store.index_page_titles, document_name, titles)
            else:
                logger.debug("Title indexing disabled by ENABLE_TITLE_INDEX=0")
        except Exception as e:
            logger.debug(f"Title-Index warn ({document_name}): {e}")
        full_text = "\n\n".join(paragraphs)
        # Add document in thread to avoid blocking event loop
        success = await _add_document_async(
            doc_id=document_name,
            text=full_text,
            metadata={"source": document_name, "type": "pdf", "doc_version": current_version}
        )
        if success:
            logger.info(f"Dokument {document_name} erfolgreich indexiert: {len(paragraphs)} Absätze")
        else:
            logger.error(f"Fehler beim Indexieren von {document_name}")
    except Exception as e:
        logger.error(f"Fehler beim Indexieren: {e}")

# --- Preindex all PDFs on startup (sequential, non-blocking for webhook) ---

async def preindex_all_pdfs():
    """Preindexiert alle PDFs in PDF_DIR nacheinander, ohne das Event-Loop zu blockieren."""
    global preindex_total, preindex_done, preindex_running, pdf_files
    try:
        pdf_files = get_pdf_files()
        preindex_total = len(pdf_files)
        preindex_done = 0
        preindex_running = True
        for pdf_path in pdf_files:
            await _ensure_document_indexed(pdf_path)
            preindex_done += 1
            # kleine Pause, чтобы не перегружать систему
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"Preindex Fehler: {e}")
    finally:
        preindex_running = False

# --- Nachrichten ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Frage von User {user_id}: {user_question}")
    # Screenshot title mode
    if context.user_data.get("shot_mode") == "awaiting_title":
        try:
            results = await asyncio.to_thread(vector_store.search_titles, user_question, 5)
            if not results:
                await update.message.reply_text("Nichts gefunden. Bitte anderen Titel/Begriff versuchen.")
                return
            user_shot_candidates[user_id] = results
            kb = [[InlineKeyboardButton(f"{r.get('type','')} {r.get('title','')[:40]} (S.{r.get('page',1)})",
                                        callback_data=f"shot_pick_{i}")] for i, r in enumerate(results)]
            kb.append([InlineKeyboardButton("Abbrechen", callback_data="shot_cancel")])
            await update.message.reply_text("Bitte auswählen:", reply_markup=InlineKeyboardMarkup(kb))
            context.user_data["shot_mode"] = None
            return
        except Exception as e:
            logger.warning(f"Screenshotsuche Fehler: {e}")
            await update.message.reply_text("Fehler bei der Suche. Bitte erneut versuchen.")
            context.user_data["shot_mode"] = None
            return
    try:
        selected = user_selected_doc.get(str(user_id))
        if selected:
            await _handle_specific_search(update, context, user_question, selected)
        else:
            await _handle_global_search(update, context, user_question)
    except Exception as e:
        logger.error(f"Fehler bei der Nachrichtenverarbeitung: {e}")
        await update.message.reply_text("Ein Fehler ist aufgetreten. Bitte noch einmal versuchen.")

def _split_pages(text: str, max_len: int = 3600) -> list[str]:
    if len(text) <= max_len:
        return [text]
    pages = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        pages.append(text[start:end])
        start = end
    return pages

async def _send_paginated(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    pages = _split_pages(text)
    if len(pages) == 1:
        await update.message.reply_text(pages[0])
        return
    user_pages_state[user_id] = {'pages': pages, 'idx': 0}
    nav = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
         InlineKeyboardButton("▶️ Next", callback_data="page_next")]
    ])
    content = pages[0] + f"\n\n📄 1/{len(pages)}"
    msg = await update.message.reply_text(content, reply_markup=nav)
    user_pages_state[user_id]['last_message_id'] = msg.message_id

async def _handle_specific_search(update: Update, context: ContextTypes.DEFAULT_TYPE, user_question: str, doc_name: str):
    try:
        if not await _has_document_async(doc_name):
            await update.message.reply_text(
                "Dieses Dokument wird noch indexiert. Bitte stelle deine Frage gleich erneut."
            )
            return
        context_text, chunks_info = await _get_combined_context_async(user_question, doc_name, max_chunks=3)
        lang = context.user_data.get("lang", "DE")
        answer = await ask_ollama(user_question, context_text, chunks_info, target_language=lang)
        await _send_paginated(update, context, answer)
    except Exception as e:
        logger.warning(f"Fehler bei spezifischer Suche in {doc_name}: {e}")
        await update.message.reply_text("Ich konnte dazu nichts finden.")

async def _handle_global_search(update: Update, context: ContextTypes.DEFAULT_TYPE, user_question: str):
    """Globale Suche mit automatischer Indexierung fehlender PDFs vor der Suche."""
    try:
        all_results = []
        docs = get_pdf_files()
        # Fehlende zunächst indexieren (prüfen параллельно, но non-blocking)
        has_tasks = [asyncio.to_thread(vector_store.has_document, d) for d in docs]
        has_results = await asyncio.gather(*has_tasks, return_exceptions=False)
        missing = [d for d, has in zip(docs, has_results) if not has]

        if missing:
            try:
                await update.message.reply_text(f"Indexiere {len(missing)} Dokument(e) für die globale Suche – bitte warten…")
            except Exception:
                pass
            for pdf_file in missing:
                # индексировать последовательно, чтобы не перегружать машину
                await _ensure_document_indexed(pdf_file)

        # Danach alle durchsuchen
        for pdf_file in docs:
            if not await _has_document_async(pdf_file):
                # Falls Indexierung fehlgeschlagen ist
                logger.info(f"Überspringe nicht indexiertes PDF: {pdf_file}")
                continue
            _, chunks_info = await _get_combined_context_async(user_question, pdf_file, max_chunks=2)
            if chunks_info:
                for chunk in chunks_info[:2]:
                    # Не раскрывать источники в сообщениях
                    all_results.append(chunk)

        if not all_results:
            await update.message.reply_text(
                "Keine relevanten Informationen gefunden. Versuche andere Suchbegriffe oder wähle ein Dokument aus."
            )
            return

        combined = "\n\n".join(c.get('text') for c in all_results[:4])
        lang = context.user_data.get("lang", "DE")
        answer = await ask_ollama(user_question, combined, all_results[:4], target_language=lang)
        await _send_paginated(update, context, answer)
    except Exception as e:
        logger.warning(f"Fehler bei globaler Suche: {e}")
        await update.message.reply_text("Bei der globalen Suche ist ein Problem aufgetreten.")

# --- Screenshot-Dialog (unverändert, ggf. abgespeckt für Kürze) ---

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data["shot_mode"] = "awaiting_title"
    await update.message.reply_text("Bitte geben Sie Titel/Schlagwort ein (z. B. 'Tabelle Cybersecurity Prozess'):")

async def handle_screenshot_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass  # Logik in handle_message integriert (awaiting_title)

async def _handle_pagination_callback(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    state = user_pages_state.get(user_id) or {}
    pages = state.get('pages') or []
    if not pages:
        await query.answer()
        return
    idx = state.get('idx', 0)
    if query.data == "page_prev":
        idx = max(0, idx - 1)
    elif query.data == "page_next":
        idx = min(len(pages) - 1, idx + 1)
    user_pages_state[user_id]['idx'] = idx
    nav = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
         InlineKeyboardButton("▶️ Next", callback_data="page_next")]
    ])
    content = pages[idx] + f"\n\n📄 {idx+1}/{len(pages)}"
    try:
        await query.edit_message_text(content, reply_markup=nav)
    except Exception as e:
        logger.debug(f"Pagination edit failed: {e}")

async def _handle_screenshot_pick(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    try:
        idx = int(query.data.split("_")[-1])
    except Exception:
        await query.answer()
        return
    candidates = user_shot_candidates.get(user_id) or []
    if not (0 <= idx < len(candidates)):
        await query.answer()
        return
    cand = candidates[idx]
    pdf = cand.get("doc_id", "")
    page = int(cand.get("page", 1))
    img_bytes = await asyncio.to_thread(get_page_image_bytes, pdf, page, 180)
    if not img_bytes:
        await query.message.reply_text("Konnte Seite nicht rendern.")
        return
    await context.bot.send_photo(chat_id=query.message.chat_id, photo=BytesIO(img_bytes))
    await query.answer()