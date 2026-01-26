# handlers.py
import os
import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from pdf_parser import pdf_parser
from pdf_parser import extract_titles_from_pdf, get_page_image_bytes
from io import BytesIO
from vector_store import vector_store
from llm_client import ask_ollama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
MAX_EXCERPTS = int(os.getenv("MAX_EXCERPTS", "10"))
DEBUG_RAG = os.getenv("DEBUG_RAG", "0") == "1"

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

# Index concurrency/semaphore for background indexing (prevent OOM)
INDEX_CONCURRENCY = int(os.getenv("INDEX_CONCURRENCY", "1"))
_index_sema = asyncio.Semaphore(INDEX_CONCURRENCY)
# Track inflight indexing tasks for clearer status
preindex_inflight = 0

# Helper to schedule indexing with concurrency control
def schedule_index(document_name: str):
    """
    Schedule background indexing of a document. This returns immediately.
    The actual indexing runs in a limited background worker to avoid OOM.
    """
    global preindex_inflight, preindex_running
    try:
        logger.info("Schedule index task: %s", document_name)
        preindex_inflight += 1
        preindex_running = True
        task = asyncio.create_task(_index_worker(document_name))
        task.add_done_callback(_index_task_done)
    except Exception as e:
        logger.exception(f"Failed to schedule index for {document_name}: {e}")

def _index_task_done(task: asyncio.Task):
    """Log exceptions and decrement inflight counter when a background index task completes."""
    global preindex_inflight, preindex_running
    try:
        exc = task.exception()
        if exc:
            logger.exception("Index task raised: %s", exc)
    except asyncio.CancelledException:
        logger.warning("Index task cancelled")
    except Exception as e:
        logger.exception("Index task inspection failed: %s", e)
    finally:
        try:
            preindex_inflight = max(0, preindex_inflight - 1)
        finally:
            if preindex_inflight == 0:
                preindex_running = False

async def _index_worker(document_name: str):
    """
    Worker that ensures only INDEX_CONCURRENCY jobs run simultaneously.
    """
    global preindex_running
    async with _index_sema:
        try:
            logger.info("Index worker started: %s", document_name)
            await _ensure_document_indexed(document_name)
            logger.info("Index worker finished: %s", document_name)
        except Exception as e:
            logger.exception(f"Background indexing failed for {document_name}: {e}")


def _load_user_state() -> dict:
    try:
        import json
        if not os.path.exists(USER_STATE_FILE):
            return {}
        with open(USER_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _persist_user_state():
    """Persist current in-memory selections (doc, lang) to USER_STATE_FILE."""
    try:
        import json
        data = {
            "selected_doc": user_selected_doc,
            "lang": user_lang_state,
        }
        with open(USER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Konnte {USER_STATE_FILE} nicht speichern: {e}")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# init persisted state (best-effort)
_state = _load_user_state()
if isinstance(_state, dict):
    try:
        sel = _state.get("selected_doc") or {}
        if isinstance(sel, dict):
            user_selected_doc.update({str(k): v for k, v in sel.items()})
        langs = _state.get("lang") or {}
        if isinstance(langs, dict):
            user_lang_state.update({str(k): v for k, v in langs.items()})
    except Exception:
        pass
PDF_DIR = os.getenv('PDF_DIR', _SCRIPT_DIR)

# Default to the local "pdfs" directory if PDF_DIR is not explicitly provided via environment
if PDF_DIR == _SCRIPT_DIR:
    PDF_DIR = os.path.join(_SCRIPT_DIR, "pdfs")

def get_pdf_files():
    try:
        entries = os.listdir(PDF_DIR)
    except Exception:
        entries = []
    return [os.path.join(PDF_DIR, f) for f in entries if f.lower().endswith('.pdf')]

# --- Helpers for thread-wrapping blocking vector_store calls ---
_doc_locks: dict[str, asyncio.Lock] = {}

def _doc_lock(path: str) -> asyncio.Lock:
    lock = _doc_locks.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _doc_locks[path] = lock
    return lock

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

# --- Acronym helper (guards hallucinations) ---
def _detect_acronym(text: str) -> str | None:
    """
    Detect a likely key term/acronym from the user query.
    Accepts lower/upper case; excludes trivial stopwords.
    Returns the term uppercased for matching.
    """
    try:
        if not text:
            return None
        stop = {
            "was","ist","das","der","die","und","ein","eine","mit","im","in","de","en","the","and","for","to","of","or","an","von"
        }
        tokens = re.findall(r"\b[A-Za-zÄÖÜäöüß]{2,12}\b", text)
        # prefer last significant token
        for tok in reversed(tokens):
            low = tok.lower()
            if low not in stop:
                return tok.upper()
        return None
    except Exception:
        return None

def _build_term_regex(term: str) -> re.Pattern:
    return re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)

def _build_defn_regex(term: str) -> re.Pattern:
    # matches "TERM - ..." or "TERM: ..." or "TERM (..."
    return re.compile(rf"\b{re.escape(term)}\b\s*(?:[-–—:]\s*|\()", re.IGNORECASE)

# --- Commands ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pdf_files
    pdf_files = get_pdf_files()
    context.bot_data['pdf_files'] = pdf_files[:]
    if not pdf_files:
        await update.message.reply_text("Keine PDF-Dateien gefunden. Bitte lade zuerst PDFs hoch.")
        return
    # restore preferred language if present
    uid = str(update.effective_user.id)
    if uid in user_lang_state:
        context.user_data["lang"] = user_lang_state[uid]
    keyboard = [
        [InlineKeyboardButton("🟢 Start", callback_data="start_dialog")],
        [InlineKeyboardButton("🌐 Language: EN/DE", callback_data="lang_toggle")],
        [InlineKeyboardButton("🖼 Page screenshot", callback_data="shot_start")]
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
    if query.data == "shot_start":
        user_id = update.effective_user.id
        lang = context.user_data.get("lang", user_lang_state.get(str(user_id), "DE"))
        context.user_data["shot_mode"] = "awaiting_title"
        prompt_de = "Bitte geben Sie Titel/Schlagwort ein (z. B. 'Tabelle Cybersecurity Prozess'): "
        prompt_en = "Please enter a title/keyword (e.g., 'Table Cybersecurity process'): "
        try:
            await query.edit_message_text(prompt_en if lang == "EN" else prompt_de)
        except Exception:
            # fallback to replying without editing
            await query.message.reply_text(prompt_en if lang == "EN" else prompt_de)
        return

    if query.data == "start_dialog":
        # ensure screenshot mode is cleared when starting dialog
        try:
            context.user_data["shot_mode"] = None
        except Exception:
            pass
        await query.edit_message_text("Stellen Sie Ihre Frage. Ich antworte in der gewählten Sprache.")
        return
    if query.data == "lang_toggle":
        # simple toggle placeholder (persist per user in memory)
        user_id = update.effective_user.id
        lang = context.user_data.get("lang", user_lang_state.get(str(user_id), "DE"))
        new_lang = "EN" if lang == "DE" else "DE"
        context.user_data["lang"] = new_lang
        user_lang_state[str(user_id)] = new_lang
        _persist_user_state()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Start", callback_data="start_dialog")],
            [InlineKeyboardButton("🌐 Language: EN/DE", callback_data="lang_toggle")],
            [InlineKeyboardButton("🖼 Page screenshot", callback_data="shot_start")]
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

# (removed _send_menu helper; not used)

# --- Indexierung ---

async def _ensure_document_indexed(document_name: str):
    """Indexiert ein Dokument (einmalig) с внутримутексной защитой. Параллельность управляется в _index_worker."""
    async with _doc_lock(document_name):
        try:
            current_version = _compute_doc_version(document_name)
            # Re-check unter Lock, чтобы не дублировать работу
            existing_version = await _get_document_version_async(document_name)
            if existing_version == current_version and await _has_document_async(document_name):
                logger.info(f"Dokument bereits indexiert (Version unverändert): {document_name}")
                return
            if existing_version and existing_version != current_version:
                await _delete_document_async(document_name)
                if os.getenv("ENABLE_TITLE_INDEX", "0") == "1":
                    await _delete_titles_async(document_name)
            logger.info(f"Indexiere Dokument: {document_name}")
            paragraphs = await pdf_parser.extract_paragraphs_from_pdf(document_name)
            if not paragraphs:
                logger.warning(f"Keine Paragraphen extrahiert: {document_name}")
                return
            # Titel/Überschriften индексируем только при включённом флаге
            if os.getenv("ENABLE_TITLE_INDEX", "0") == "1":
                try:
                    titles = await asyncio.to_thread(extract_titles_from_pdf, document_name)
                    if isinstance(titles, list) and titles:
                        # bei Neuindexierung: alte Titel löschen und neu hinzufügen
                        await _delete_titles_async(document_name)
                        await asyncio.to_thread(vector_store.index_page_titles, document_name, titles)
                except Exception as e:
                    logger.debug(f"Title-Index warn ({document_name}): {e}")
            # Добавляем чанки напрямую, без склейки большого текста
            success = await asyncio.to_thread(
                vector_store.add_chunks,
                document_name,
                paragraphs,
                {"source": document_name, "type": "pdf", "doc_version": current_version},
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
            # schedule background indexing with concurrency limit
            schedule_index(pdf_path)
            preindex_done += 1
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
                # clear mode so normal Q&A continues
                context.user_data["shot_mode"] = None
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
    # show typing before sending potentially long, paginated response
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    except Exception:
        pass
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
    return msg

async def _handle_specific_search(update: Update, context: ContextTypes.DEFAULT_TYPE, user_question: str, doc_name: str):
    try:
        if not await _has_document_async(doc_name):
            await update.message.reply_text(
                "Dieses Dokument wird noch indexiert. Bitte stelle deine Frage gleich erneut."
            )
            return
        wait_msg = await update.message.reply_text("bitte warte kurz auf die Antwort")
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            logger.info("Hole Kontext… (spezifische Suche)")
            _, chunks_info = await _get_combined_context_async(user_question, doc_name, max_chunks=MAX_EXCERPTS)
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            lang = context.user_data.get("lang", "DE")
            logger.info("Rufe LLM…")
            # Prefer definition-sized chunks containing the queried term
            acr = _detect_acronym(user_question)
            use_chunks = (chunks_info or [])
            if acr:
                term_re = _build_term_regex(acr)
                defn_re = _build_defn_regex(acr)
                with_term = [c for c in use_chunks if term_re.search((c.get("text") or ""))]
                with_defn = [c for c in with_term if defn_re.search((c.get("text") or ""))]
                if with_defn:
                    use_chunks = with_defn
                elif with_term:
                    use_chunks = with_term
                else:
                    # try an extra pull directly on the term
                    extra = await asyncio.to_thread(vector_store.search_in_document, acr, doc_name, MAX_EXCERPTS * 3)
                    regex_def = _build_defn_regex(acr)
                    extra_defn = [c for c in (extra or []) if regex_def.search((c.get("text") or ""))] if extra else []
                    use_chunks = (extra_defn or extra or [])
            use_chunks = use_chunks[:MAX_EXCERPTS]
            excerpts = [f"EXCERPT {i}:\n{c.get('text','')}" for i, c in enumerate(use_chunks, 1)]
            combined_for_llm = "\n---\n".join(excerpts)
            logger.info("Combined context length=%d, excerpts=%d", len(combined_for_llm), len(excerpts))
            answer = await ask_ollama(user_question, combined_for_llm, use_chunks, target_language=lang)
            logger.info("LLM Antwort empfangen…")
            await _send_paginated(update, context, answer)
        finally:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=wait_msg.message_id)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Fehler bei spezifischer Suche in {doc_name}: {e}")
        await update.message.reply_text("Ich konnte dazu nichts finden.")

async def _handle_global_search(update: Update, context: ContextTypes.DEFAULT_TYPE, user_question: str):
    """Globale Suche: если чего‑то нет в индексе — индексируем СЕЙЧАС (под локом) и сразу отвечаем."""
    try:
        docs = get_pdf_files()
        if not docs:
            await update.message.reply_text("Keine PDFs gefunden.")
            return

        user_lang = context.user_data.get("lang", "DE").upper()
        wait_text = "Bitte warte kurz auf die Antwort…" if user_lang == "DE" else "Please wait a moment for the answer…"
        nores_text = "Keine relevanten Informationen gefunden. Versuche andere Suchbegriffe." if user_lang == "DE" else "No relevant information found. Try different keywords."
        idx_started_text = "Indexierung gestartet im Hintergrund — bitte wiederholen Sie Ihre Anfrage in ein paar Minuten." if user_lang == "DE" else "Indexing started in the background — please repeat your query in a few minutes."

        wait_msg = await update.message.reply_text(wait_text)
        try:
            logger.info("Hole Kontext… (globale Suche)")
            # 1) Выявить и доиндексировать отсутствующие PDF синхронно
            has_results = await asyncio.gather(
                *[asyncio.to_thread(vector_store.has_document, d) for d in docs],
                return_exceptions=False
            )
            missing = [d for d, ok in zip(docs, has_results) if not ok]
            logger.info("Dokumente: %s, fehlend: %s", len(docs), len(missing))
            if missing:
                # Планируем индексирование в фоне и НЕ ждём — чтобы не блокировать ответ
                for pdf_file in sorted(set(missing)):
                    try:
                        logger.info("Fehlend -> plane Hintergrund-Indexierung: %s", pdf_file)
                        schedule_index(pdf_file)
                    except Exception as e:
                        logger.warning(f"Schedule index failed for {pdf_file}: {e}")
                # сообщаем пользователю и завершаем обработку
                await update.message.reply_text(idx_started_text)
                return

            # 2) Собрать контекст из всех проиндексированных документов
            all_results = []
            for pdf_file in docs:
                if not await _has_document_async(pdf_file):
                    logger.info("Überspringe nicht indexiertes Dokument: %s", pdf_file)
                    continue
                logger.info("Suche Kontext im Dokument: %s", pdf_file)
                _, chunks_info = await _get_combined_context_async(user_question, pdf_file, max_chunks=MAX_EXCERPTS)
                if isinstance(chunks_info, list) and chunks_info:
                    all_results.extend(chunks_info)
                    logger.info("Gefundene Chunks in %s: %s", pdf_file, len(chunks_info))
                else:
                    logger.info("Keine Chunks gefunden in %s", pdf_file)

            if not all_results:
                logger.info("Keine dokumentspezifischen Treffer. Starte Fallback‑Suche…")
                # Fallback: глобальный поиск по всей коллекции (без фильтра по документу)
                try:
                    docs, metas = await asyncio.to_thread(vector_store.query, user_question, 5)
                    fallback_chunks = []
                    for d, m in zip(docs or [], metas or []):
                        if not d or not isinstance(m, dict):
                            continue
                        fallback_chunks.append({"text": d, "metadata": m, "similarity_score": 0.0})
                        if len(fallback_chunks) >= 4:
                            break
                    if not fallback_chunks:
                        logger.info("Fallback‑Suche ergab 0 Treffer.")
                        await update.message.reply_text(nores_text)
                        return
                    logger.info("Fallback‑Treffer: %s", len(fallback_chunks))
                    combined = "\n\n".join(c.get("text", "") for c in fallback_chunks)
                    lang = context.user_data.get("lang", "DE")
                    logger.info("Rufe LLM… (Fallback)")
                    answer = await ask_ollama(user_question, combined, fallback_chunks, target_language=lang)
                    logger.info("LLM Antwort empfangen… (Fallback)")
                    await _send_paginated(update, context, answer)
                    return
                except Exception:
                    logger.info("Fallback‑Suche fehlgeschlagen (Exception).")
                    await update.message.reply_text(nores_text)
                    return

            selected = all_results[:MAX_EXCERPTS]
            # Prefer definition-sized chunks containing the queried term
            acr = _detect_acronym(user_question)
            final_chunks = selected
            if acr:
                term_re = _build_term_regex(acr)
                defn_re = _build_defn_regex(acr)
                with_term = [c for c in selected if term_re.search((c.get('text') or ''))]
                with_defn = [c for c in with_term if defn_re.search((c.get('text') or ''))]
                if with_defn:
                    final_chunks = with_defn[:MAX_EXCERPTS]
                elif with_term:
                    final_chunks = with_term[:MAX_EXCERPTS]
                else:
                    # No term present in top selected chunks → do an extra targeted pull
                    # 1) Try per‑document acronym search to surface short definitions
                    extra_hits = []
                    try:
                        for pdf_file in docs:
                            try:
                                hits = await asyncio.to_thread(
                                    vector_store.search_in_document, acr, pdf_file, MAX_EXCERPTS * 3
                                )
                            except Exception:
                                hits = []
                            if hits:
                                extra_hits.extend(hits)
                        # Prefer definition‑like matches, then anything with the term
                        if extra_hits:
                            defn_only = [c for c in extra_hits if defn_re.search((c.get('text') or ''))]
                            term_only = [c for c in extra_hits if term_re.search((c.get('text') or ''))]
                            final_chunks = (defn_only or term_only or extra_hits)[:MAX_EXCERPTS]
                    except Exception:
                        pass
                    # 2) Special case: queries about ISO/SAE standards (ensure the code "21434" presence)
                    if not final_chunks:
                        try:
                            m = re.search(r"(ISO\s*/?\s*SAE\s*)?(\d{4,6})", user_question, re.IGNORECASE)
                            if m:
                                code = m.group(2)
                                if code:
                                    extra_all = []
                                    for pdf_file in docs:
                                        try:
                                            hits = await asyncio.to_thread(
                                                vector_store.search_in_document, code, pdf_file, MAX_EXCERPTS * 3
                                            )
                                        except Exception:
                                            hits = []
                                        if hits:
                                            extra_all.extend(hits)
                                    if extra_all:
                                        final_chunks = extra_all[:MAX_EXCERPTS]
                        except Exception:
                            pass
            excerpts = [f"EXCERPT {i}:\n{c.get('text','')}" for i, c in enumerate(final_chunks, 1)]
            combined = "\n---\n".join(excerpts)
            lang = context.user_data.get("lang", "DE")
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            logger.info("Rufe LLM… (global)")
            if DEBUG_RAG:
                try:
                    for i, c in enumerate(final_chunks[:min(5, len(final_chunks))], 1):
                        txt = (c.get("text", "") or "").strip().replace("\n", " ")
                        logger.debug("EXCERPT %d: %s", i, txt[:240])
                except Exception:
                    pass
            logger.info("Combined context length=%d, excerpts=%d", len(combined), len(excerpts))
            answer = await ask_ollama(user_question, combined, final_chunks, target_language=lang)
            logger.info("LLM Antwort empfangen… (global)")
            await _send_paginated(update, context, answer)
        except Exception as e:
            logger.warning(f"Globale Suche Fehler: {e}")
        finally:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=wait_msg.message_id)
                logger.info("Warte‑Nachricht entfernt.")
            except Exception:
                pass
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