# handlers.py
import os
import re
import logging
import asyncio
from typing import Dict, List
import io
import contextlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from indexer import schedule_index, preindex_running, preindex_done, preindex_total  # import scheduling helper
from retrieval import (
    get_best_chunks_for_document,
    get_best_chunks_global,
    build_combined_excerpts,
    detect_acronym,
    find_definition_in_chunks,
    find_chunk_with_term,
)
from vector_store import vector_store
from llm_client import ask_ollama

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Protokollierungsfilter (Schutz sensibler Informationen in Protokollen) ---
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # Geheimnis aus ENV für Webhook‑Pfad
_PDF_DIR_ENV = os.getenv("PDF_DIR", "")  # Optionaler PDF‑Stammpfad aus ENV

def _censor(text: str) -> str:
    # Ersetzt sensible Muster (Tokens, Secrets, Pfade) durch in Logstrings
    if not text:  # Leere Eingabe unverändert zurückgeben
        return text
    s = str(text)  # Robustheit: beliebigen Typ in String wandeln
    # Liste zensierbarer Muster
    patterns = [
        r"\b\d{8,}:[A-Za-z0-9_\-]{20,}\b",                  # Telegram‑Bot‑Token‑ähnliches Muster
        r"(?:https?://)?[a-z0-9\-]+\.ngrok-free\.app[^\s]*", # ngrok‑URL (inkl. Pfad/Query)
        re.escape(_WEBHOOK_SECRET) if _WEBHOOK_SECRET else None,  # konkretes Webhook‑Secret
        r"[A-Za-z]:\\[^\s]+",                                # absolute Windows‑Pfade
        r"/app/pdfs/[^\s]+",                                 # Container‑PDF‑Pfad
    ]
    for pat in filter(None, patterns):  # None auslassen, falls optionales Muster fehlt
        s = re.sub(pat, "[CENSORED]", s, flags=re.IGNORECASE)  # fallunabhängige Ersetzung
    return s  # zensierter String

class _CensorFilter(logging.Filter):
    # Logging‑Filter: erzwingt Zensur auf der fertigen Lognachricht und typischen Zusatzfeldern
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()          # formatierten Nachrichtentext erzeugen
            record.msg = _censor(msg)          # sensiblen Inhalt durch Platzhalter ersetzen
            record.args = ()                   # weitere %-Formatierung verhindern
        except Exception:
            pass                               # Logging darf nie durch Zensurfehler brechen
        # Bestmögliche Bemühungen: Zensur gängiger benutzerdefinierter Attribute
        for attr in ("text", "data"):
            if hasattr(record, attr):          # nur vorhandene Attribute prüfen
                try:
                    val = getattr(record, attr)
                    setattr(record, attr, _censor(val))  # Attributinhalt zensieren
                except Exception:
                    pass
        return True  # Logeintrag weiterreichen (nie blockieren)

logger.addFilter(_CensorFilter())

MAX_EXCERPTS = int(os.getenv("MAX_EXCERPTS", "12"))
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "1") == "1"

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.getenv('PDF_DIR', _SCRIPT_DIR)
if PDF_DIR == _SCRIPT_DIR:
    PDF_DIR = os.path.join(_SCRIPT_DIR, "pdfs")

# Minimaler lokaler Zustand für die Paginierung
user_pages_state: Dict[int, Dict] = {}
# Einfacher Screenshot-Zustand pro Benutzer
SCREENSHOT_STATE: Dict[int, Dict] = {}

async def _typing_loop(bot, chat_id: int, stop_evt: asyncio.Event, period: float = 4.0) -> None:
    """Periodically send 'typing…' action until stop_evt is set."""
    try:
        while not stop_evt.is_set():
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                # Never propagate typing errors
                pass
            try:
                await asyncio.wait_for(stop_evt.wait(), timeout=period)
            except asyncio.TimeoutError:
                continue
    except Exception:
        # Swallow any unexpected errors to not break the main flow
        pass

def _is_screenshot_target_query(text: str) -> bool:
    """Return True if text looks like a page/table/figure reference."""
    if not text:
        return False
    t = text.strip()
    # Accept arabic numbers and roman numerals (i, ii, iii, iv, v, vi, ...)
    if re.search(r"(?i)\b(seite|page)\s*([ivxlcdm]+|\d+)\b", t):
        return True
    # akzeptiere numerisch (3) und alphanumerisch wie H.3 / H-3 / H3
    if re.search(r"(?i)\b(tab(?:elle)?|table)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", t):
        return True
    if re.search(r"(?i)\b(fig(?:ure)?|abbildung)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)\b", t):
        return True
    return False
def _build_docs_keyboard(pdfs: List[str]) -> InlineKeyboardMarkup:
    buttons = []
    row: List[InlineKeyboardButton] = []
    for idx, p in enumerate(pdfs):
        label = os.path.basename(p)[:30]
        row.append(InlineKeyboardButton(label, callback_data=f"shot_doc:{idx}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
 

def get_pdf_files() -> List[str]:
    try:
        entries = os.listdir(PDF_DIR)
    except Exception:
        entries = []
    return [os.path.join(PDF_DIR, f) for f in entries if f.lower().endswith('.pdf')]

# --- Befehle (dünne Wrapper) ---

async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    pdfs = get_pdf_files()
    if not pdfs:
        await update.message.reply_text("Keine PDFs gefunden. Bitte lade zuerst PDFs hoch.", disable_web_page_preview=True)
        return
    main_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("/start"), KeyboardButton("/screenshot")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True
    )
    await update.message.reply_text(
        "Willkommen beim Automotive-Cybersecurity-Bot.\n\n"
        "So funktioniert es:\n"
        "1️⃣ Drücke /Start.\n"
        "2️⃣ Stelle deine Frage oder nutze /screenshot für Seiten/Bilder/Tabellen.\n"
        "⚠️ Hinweis: Die Dokumenteninhalte sind vertraulich. Bitte keine Screenshots speichern oder weitergeben.",
        reply_markup=main_kb,
        disable_web_page_preview=True,
    )

async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    main_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("/start"), KeyboardButton("/screenshot")]],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True
    )
    await update.message.reply_text(
        "Hilfe: /start (Startmenü) • /status (Index) • /screenshot (Seite/Bild/Tabelle).",
        reply_markup=main_kb,
        disable_web_page_preview=True
    )

async def status_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    info = await asyncio.to_thread(vector_store.get_document_info)
    text = (
        f"VectorStore chunks: {info.get('total_chunks', 'unknown')}\n"
        f"Persist dir: {info.get('persist_directory', 'unknown')}\n"
        f"Preindex: running={preindex_running}, done={preindex_done}/{preindex_total}\n"
    )
    await update.message.reply_text(text, disable_web_page_preview=True)

async def button_callback(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except Exception:
        pass
    # Paginierung für lange Antworten
    if q.data in ("page_prev", "page_next"):
        st = user_pages_state.get(q.from_user.id) or {}
        pages = st.get("pages") or []
        use_html = bool(st.get("html"))
        parse_mode = ParseMode.HTML if use_html else None
        if not pages:
            return
        old_idx = st.get("idx", 0)
        idx = old_idx
        if q.data == "page_prev":
            idx = max(0, idx - 1)
        else:
            idx = min(len(pages) - 1, idx + 1)
        # Vermeide Telegram BadRequest "Message is not modified"
        if idx == old_idx:
            return
        st["idx"] = idx
        user_pages_state[q.from_user.id] = st
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
                                    InlineKeyboardButton("▶️ Next", callback_data="page_next")]])
        try:
            await q.edit_message_text(pages[idx] + f"\n\n📄 {idx+1}/{len(pages)}",
                                      reply_markup=kb,
                                      disable_web_page_preview=True,
                                      parse_mode=parse_mode)
        except Exception as e:
            logger.warning(f"Edit failed, fallback to plain: {e}")
            await q.edit_message_text(pages[idx] + f"\n\n📄 {idx+1}/{len(pages)}",
                                      reply_markup=kb,
                                      disable_web_page_preview=True)
        return
    if q.data == "shot_start":
        # start document selection
        pdfs = get_pdf_files()
        SCREENSHOT_STATE[q.from_user.id] = {"mode": "pick_doc"}
        kb = _build_docs_keyboard(pdfs)
        await q.edit_message_text(
            "📄 Bitte wählen Sie ein Dokument für den Screenshot:",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        return
    if q.data.startswith("shot_doc:"):
        try:
            _, idx_s = q.data.split(":", 1)
            idx = int(idx_s)
        except Exception:
            await q.answer("Ungültige Auswahl")
            return
        pdfs = get_pdf_files()
        if not (0 <= idx < len(pdfs)):
            await q.answer("Dokument nicht gefunden")
            return
        doc_path = pdfs[idx]
        SCREENSHOT_STATE[q.from_user.id] = {"mode": "awaiting_target", "doc": doc_path}
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Dokument wählen", callback_data="shot_start")]])
        # Kurze, klare Instruktion mit Seitenspezifika
        name = os.path.basename(doc_path)
        instr = (
            "Geben Sie ein, was gerendert werden soll, z.B.:\n"
            "• „Seite 10“ oder „Page 10“\n"
            "• „Tabelle 3“ / „Table 3“ oder „Abbildung 2“ / „Figure 2“\n"
            "• oder einen Titel-/Kapiteltext\n\n"
        )
        # Spezielle Hinweise je Dokument
        if name == "Interpretation Document.pdf":
            extra = "Hinweis: In „Interpretation Document.pdf“ gibt es 40 Seiten, nummeriert 1–40."
        elif name == "UNR 155.pdf":
            extra = "Hinweis: In „UNR 155.pdf“ gibt es 30 Seiten, nummeriert 1–30."
        elif name == "ISO SAE 21434.pdf":
            extra = ("Hinweis: In „ISO SAE 21434.pdf“ gibt es 82 Seiten. "
                     "Die ersten 6 Seiten sind römisch i–vi (die Titelseite ohne Kennzeichnung), "
                     "danach 1–81. Sie können z. B. „Seite iv“ oder „Seite 10“ eingeben.")
        else:
            extra = ""
        await q.edit_message_text(
            f"Ausgewählt: {os.path.basename(doc_path)}\n{instr}{extra}",
            reply_markup=back_kb,
            disable_web_page_preview=True
        )
        return
    if q.data.startswith("shot_goto:"):
        # syntax: shot_goto:<idx>:<page>
        try:
            _, idx_s, page_s = q.data.split(":", 2)
            idx = int(idx_s); page = int(page_s)
        except Exception:
            await q.answer("Ungültige Auswahl")
            return
        pdfs = get_pdf_files()
        if not (0 <= idx < len(pdfs)):
            await q.answer("Dokument nicht gefunden")
            return
        from pdf_parser import get_page_image_bytes
        img = get_page_image_bytes(pdfs[idx], page)
        if not img:
            await q.edit_message_text("Seite konnte nicht gerendert werden.", disable_web_page_preview=True)
            return
        await _context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=io.BytesIO(img),
            caption=f"📄 {os.path.basename(pdfs[idx])} – Seite {page}",
            protect_content=PROTECT_CONTENT,
        )
        return
    if q.data == "start_query":
        await q.edit_message_text("Stelle deine Frage:", disable_web_page_preview=True)
        return

# --- Paginierungshilfen (klein) ---

def _split_pages(text: str, max_len: int = 3600) -> List[str]:
    """Умная пагинация: по абзацам/предложениям, чтобы не резать теги/блоки."""
    if len(text) <= max_len:
        return [text]
    pages: List[str] = []
    current = ""
    paragraphs = text.split("\n\n")
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= max_len:
            current = (current + "\n\n" + para) if current else para
            continue
        if current:
            pages.append(current)
            current = ""
        if len(para) > max_len:
            sentences = re.split(r"(?<=[\.\!\?])\s+", para)
            buf = ""
            for s in sentences:
                if len(buf) + len(s) + 1 <= max_len:
                    buf = (buf + " " + s) if buf else s
                else:
                    if buf:
                        pages.append(buf)
                    buf = s
            current = buf
        else:
            current = para
    if current:
        pages.append(current)
    return pages

async def _send_paginated(update: Update, _context: ContextTypes.DEFAULT_TYPE, text: str):
    user_id = update.effective_user.id
    # автоопределение режима
    use_html = ("<pre>" in (text or "")) or ("<b>" in (text or ""))
    parse_mode = ParseMode.HTML if use_html else None
    pages = _split_pages(text)
    try:
        if len(pages) == 1:
            await update.message.reply_text(
                pages[0],
                disable_web_page_preview=True,
                parse_mode=parse_mode,
                protect_content=PROTECT_CONTENT,
            )
            return
        user_pages_state[user_id] = {'pages': pages, 'idx': 0, 'html': use_html}
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
                    InlineKeyboardButton("▶️ Next", callback_data="page_next"),
                ]
            ]
        )
        msg = await update.message.reply_text(
            pages[0] + f"\n\n📄 1/{len(pages)}",
            reply_markup=kb,
            disable_web_page_preview=True,
            parse_mode=parse_mode,
            protect_content=PROTECT_CONTENT,
        )
        user_pages_state[user_id]['last_message_id'] = msg.message_id
    except Exception as e:
        logger.warning(f"Send failed: {e}")
        if len(pages) == 1:
            await update.message.reply_text(
                pages[0],
                parse_mode=None,
                disable_web_page_preview=True,
                protect_content=PROTECT_CONTENT,
            )
            return
        user_pages_state[user_id] = {'pages': pages, 'idx': 0, 'html': False}
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("◀️ Prev", callback_data="page_prev"),
                    InlineKeyboardButton("▶️ Next", callback_data="page_next"),
                ]
            ]
        )
        msg = await update.message.reply_text(
            pages[0] + f"\n\n📄 1/{len(pages)}",
            reply_markup=kb,
            parse_mode=None,
            disable_web_page_preview=True,
            protect_content=PROTECT_CONTENT,
        )
        user_pages_state[user_id]['last_message_id'] = msg.message_id

# --- Kernnachrichten-Handler (dünn, verwendet Retrieval/Indexer) ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_question = (update.message.text or "").strip()
    if not user_question:
        return
    user_id = update.effective_user.id
    logger.info("Question from %s: %s", user_id, user_question)

    # --- Screenshot-Modus (frühe Verarbeitung) ---
    _shot = SCREENSHOT_STATE.get(user_id, {})
    # Nur abfangen, wenn der Benutzer sich im Screenshot-Zielmodus befindet UND der Text wie eine Zielabfrage aussieht.
    if _shot.get("mode") in ("awaiting_target",) and _is_screenshot_target_query(user_question):
        from pdf_parser import get_page_image_bytes, extract_titles_from_pdf, get_page_label_map
        doc_path = _shot.get("doc")
        if not doc_path or not os.path.exists(doc_path):
            SCREENSHOT_STATE[user_id] = {"mode": "pick_doc"}
            kb = _build_docs_keyboard(get_pdf_files())
            await update.message.reply_text("Bitte wählen Sie ein Dokument:", reply_markup=kb, disable_web_page_preview=True)
            return
        txt = user_question.strip()
        # 1) explizite Seitenzahl
        # Akzeptiere "Seite 10" oder "Page 10" (Groß-/Kleinschreibung ignorieren)
        # Zusätzlich: akzeptiere römische Zahlen (i, ii, iii, iv, v, vi ...)
        m = re.search(r"(?i)\b(seite|page)\s*([ivxlcdm]+|\d+)\b", txt)
        if m:
            label = m.group(2)
            lbl_norm = label.strip()
            label_map = {}
            try:
                label_map = get_page_label_map(doc_path) or {}
            except Exception:
                label_map = {}
            page = None
            if label_map:
                # zuerst versuchen, прямой ключ
                page = label_map.get(lbl_norm)
                # потом попробовать нормализованные варианты
                if page is None:
                    page = label_map.get(lbl_norm.lower()) or label_map.get(lbl_norm.upper())
                # если всё ещё None и это арабское число
                if page is None and lbl_norm.isdigit():
                    page = label_map.get(str(int(lbl_norm)))
            # Если мапы нет/не нашли — простой числовой fallback
            if page is None:
                try:
                    page = int(lbl_norm)  # если это было арабское число
                except Exception:
                    # простая римская конверсия на случай отсутствия PageLabels
                    roman = lbl_norm.upper()
                    roman_vals = {'M':1000,'CM':900,'D':500,'CD':400,'C':100,'XC':90,'L':50,'XL':40,'X':10,'IX':9,'V':5,'IV':4,'I':1}
                    i = 0; total = 0
                    while i < len(roman):
                        if i+1 < len(roman) and roman[i:i+2] in roman_vals:
                            total += roman_vals[roman[i:i+2]]; i += 2
                        elif roman[i] in roman_vals:
                            total += roman_vals[roman[i]]; i += 1
                        else:
                            total = 0; break
                    page = total if total > 0 else None
            if not page or page <= 0:
                await update.message.reply_text("Seite nicht gefunden.", disable_web_page_preview=True)
                return
            try:
                img = get_page_image_bytes(doc_path, page)
            except Exception as e:
                logger.debug("get_page_image_bytes error: %s", e)
                img = b""
            if not img:
                await update.message.reply_text("Seite konnte nicht gerendert werden.", disable_web_page_preview=True)
                return
            SCREENSHOT_STATE.pop(user_id, None)
            # Caption: show both the requested printed label and the actual PDF index to avoid confusion
            printed = lbl_norm
            await context.bot.send_photo(
                update.effective_chat.id,
                io.BytesIO(img),
                caption=(
                    f"📄 {os.path.basename(doc_path)} – "
                    f"Seite {printed} (gedruckt) → PDF {page}"
                ),
                protect_content=PROTECT_CONTENT,
            )
            return
        # 2) Tabelle / Abbildung nach Nummer
        titles = []
        try:
            titles = extract_titles_from_pdf(doc_path)
        except Exception:
            titles = []
        m_tbl = re.search(r"(?i)\b(tab(?:elle)?|table)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)", txt)
        m_fig = re.search(r"(?i)\b(fig(?:ure)?|abbildung)\s*([A-Za-z]\s*[\.\-]?\s*\d+|\d+)", txt)
        if m_tbl:
            num = m_tbl.group(2)
            def _norm(s: str) -> str:
                return re.sub(r"[\\s\\.\\-]+", "", (s or "").lower())
            num_n = _norm(num)
            cand = next((t for t in titles if t.get('type','').lower() in ('table','tabelle') and num_n in _norm(t.get('title',''))), None)
            if cand:
                page = int(cand.get('page', 1))
                img = get_page_image_bytes(doc_path, page)
                if not img:
                    await update.message.reply_text("Seite konnte nicht gerendert werden.", disable_web_page_preview=True)
                    return
                SCREENSHOT_STATE.pop(user_id, None)
                await context.bot.send_photo(
                    update.effective_chat.id,
                    io.BytesIO(img),
                    caption=f"📄 {os.path.basename(doc_path)} – Seite {page}: {cand.get('title','')}",
                    protect_content=PROTECT_CONTENT,
                )
                return
        if m_fig:
            num = m_fig.group(2)
            def _norm2(s: str) -> str:
                return re.sub(r"[\\s\\.\\-]+", "", (s or "").lower())
            num_n = _norm2(num)
            cand = next((t for t in titles if t.get('type','').lower() in ('figure','abbildung') and num_n in _norm2(t.get('title',''))), None)
            if cand:
                page = int(cand.get('page', 1))
                img = get_page_image_bytes(doc_path, page)
                if not img:
                    await update.message.reply_text("Seite konnte nicht gerendert werden.", disable_web_page_preview=True)
                    return
                SCREENSHOT_STATE.pop(user_id, None)
                await context.bot.send_photo(
                    update.effective_chat.id,
                    io.BytesIO(img),
                    caption=f"📄 {os.path.basename(doc_path)} – Seite {page}: {cand.get('title','')}",
                    protect_content=PROTECT_CONTENT,
                )
                return
        # 3) Stichwortsuche in Titeln
        kw = txt.lower()
        hits = [t for t in titles if kw and kw in (t.get('title','').lower())]
        if not hits:
            await update.message.reply_text("Kein Treffer. Beispiele: „Seite 10“, „Tabelle 3“, „Figure 2“ oder ein Stichwort aus dem Titel.", disable_web_page_preview=True)
            return
        if len(hits) == 1:
            page = int(hits[0].get('page', 1))
            img = get_page_image_bytes(doc_path, page)
            if not img:
                await update.message.reply_text("Seite konnte nicht gerendert werden.", disable_web_page_preview=True)
                return
            SCREENSHOT_STATE.pop(user_id, None)
            await context.bot.send_photo(
                update.effective_chat.id,
                io.BytesIO(img),
                caption=f"📄 {os.path.basename(doc_path)} – Seite {page}: {hits[0].get('title','')}",
                protect_content=PROTECT_CONTENT,
            )
            return
        # Auswahl anbieten
        pdfs = get_pdf_files()
        try:
            doc_idx = pdfs.index(doc_path)
        except ValueError:
            doc_idx = 0
        rows = [[InlineKeyboardButton(f"S.{int(h.get('page',1))}: {h.get('title','')[:40]}", callback_data=f"shot_goto:{doc_idx}:{int(h.get('page',1))}")] for h in hits[:10]]
        kb = InlineKeyboardMarkup(rows + [[InlineKeyboardButton("◀️ Dokument wählen", callback_data="shot_start")]])
        await update.message.reply_text("Mehrere Treffer – bitte wählen:", reply_markup=kb, disable_web_page_preview=True)
        return
    # Wenn der Benutzer sich im Screenshot-Fluss befindet, aber eine normale Frage eingibt, den Screenshot-Modus verlassen und mit Q/A fortfahren.
    if _shot.get("mode") in ("awaiting_target","pick_doc") and not user_question.startswith("/screenshot"):
        SCREENSHOT_STATE.pop(user_id, None)

    # Sprachrichtlinie: Standard EN; wenn die Frage wie Deutsch aussieht, antworte DE
    t = f" {(user_question or '').casefold()} "
    is_german = any(w in t for w in (
        " was ", " ist ", " sind ", " sollte ", " wie ", " wann ", " warum ",
        " worum ", " worauf ", " inwiefern ", " der ", " die ", " das ", " über ", " und "
    )) or any(ch in user_question for ch in ("ä","ö","ü","Ä","Ö","Ü","ß"))
    context.user_data["lang"] = "DE" if is_german else "EN"

    # Schneller Check: Wenn keine PDFs indexiert sind, Indexierung planen und Benutzer informieren
    pdfs = get_pdf_files()
    if not pdfs:
        await update.message.reply_text("Keine PDFs vorhanden.")
        return

    # Sicherstellen, dass mindestens ein Dokument indexiert ist; falls nicht, Indexierung planen und Benutzer auffordern, es später erneut zu versuchen
    has_any = await asyncio.to_thread(lambda: any(vector_store.has_document(p) for p in pdfs))
    if not has_any:
        # Indexierung für alle PDFs planen und Benutzer auffordern, es später erneut zu versuchen
        for p in pdfs:
            schedule_index(p)
        await update.message.reply_text(
            "Indexierung gestartet im Hintergrund. Prüfe den Fortschritt mit /status und versuche es danach erneut.",
            disable_web_page_preview=True,
        )
        return

    # Global beste Abschnitte über alle Dokumente hinweg, um Präzision und Recall zu maximieren
    try:
        all_chunks = await get_best_chunks_global(user_question, max_chunks=MAX_EXCERPTS)
    except Exception as e:
        logger.debug("Global retrieval error: %s", e)


    # Fallback: wenn zu wenige globale Ergebnisse vorliegen, pro Dokument parallel abfragen
    if not all_chunks or len(all_chunks) < max(4, MAX_EXCERPTS // 2):
        try:
            tasks = [
                get_best_chunks_for_document(user_question, p, max_chunks=max(4, MAX_EXCERPTS // 2))
                for p in pdfs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            combined: List[dict] = []
            for res in results:
                if isinstance(res, Exception):
                    logger.debug("Error fetching chunks: %s", res)
                    continue
                if res:
                    combined.extend(res)
            # Duplikate entfernen + sortieren
            seen = set()
            uniq = []
            for c in combined:
                key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(c)
            all_chunks = sorted(uniq, key=lambda c: c.get("similarity_score", 0), reverse=True)[:MAX_EXCERPTS]
        except Exception as e:
            logger.debug("Parallel per-doc retrieval error: %s", e)

    if not all_chunks:
        await update.message.reply_text("Keine relevanten Informationen gefunden.")
        return

    # Versuch deterministisches 'Definition zuerst' Verhalten
    term = detect_acronym(user_question)
    if term:
        defs = find_definition_in_chunks(term, all_chunks)
        if defs:
            # Gefundene Definitionen über LLM umformulieren (ohne rohe Zitate)
            combined_context = "\n\n".join([(d.get("text") or "").strip() for d in defs[:3]])
            stop_evt = asyncio.Event()
            task = asyncio.create_task(_typing_loop(context.bot, update.effective_chat.id, stop_evt))
            try:
                answer = await ask_ollama(
                    user_question,
                    combined_context,
                    defs[:3],
                    target_language=(context.user_data.get("lang", "DE") if hasattr(context, "user_data") else "DE"),
                )
                await _send_paginated(update, context, answer)
            except Exception as e:
                logger.exception("LLM paraphrase error: %s", e)
                await update.message.reply_text("Fehler beim Generieren der Antwort.")
            finally:
                stop_evt.set()
                with contextlib.suppress(Exception):
                    await task
            return
        # Wenn eine genaue Zitat mit dem Begriff gefunden wird
        exact = find_chunk_with_term(term, all_chunks)
        if exact:
            stop_evt2 = asyncio.Event()
            task2 = asyncio.create_task(_typing_loop(context.bot, update.effective_chat.id, stop_evt2))
            try:
                answer = await ask_ollama(
                    user_question, exact, [{"text": exact}], target_language=context.user_data.get("lang", "DE")
                )
                await _send_paginated(update, context, answer)
            except Exception as e:
                logger.exception("LLM paraphrase error for exact chunk: %s", e)
                await update.message.reply_text("Fehler beim Generieren der Antwort.")
            finally:
                stop_evt2.set()
                with contextlib.suppress(Exception):
                    await task2
            return

    # Fallback: kombinierte Auszüge vorbereiten und LLM mit strengem Prompt aufrufen
    # Anzahl der gesendeten Auszüge begrenzen
    final_chunks = sorted(all_chunks, key=lambda c: c.get("similarity_score", 0), reverse=True)[:MAX_EXCERPTS]

    # Hinweis statt harter Blockade: Wenn das Akronym eindeutig nicht gefunden wird, versuchen wir trotzdem, die Frage zu beantworten.
    if term and re.fullmatch(r"[A-ZÄÖÜ]{2,5}", term or ""):
        joined = " ".join((c.get("text") or "") for c in final_chunks) or ""
        if not re.search(rf"(?<![A-Za-zÄÖÜäöüß]){re.escape(term)}(?![A-Za-zÄÖÜäöüß])", joined):
            # keine Unterbrechung der Antwort; das Modell kann trotzdem eine nützliche kurze Erklärung geben
            pass
    combined = build_combined_excerpts(final_chunks)
    stop_evt3 = asyncio.Event()
    task3 = asyncio.create_task(_typing_loop(context.bot, update.effective_chat.id, stop_evt3))
    try:
        answer = await ask_ollama(
            user_question,
            combined,
            final_chunks,
            target_language=(context.user_data.get("lang", "DE") if hasattr(context, "user_data") else "DE"),
        )
        await _send_paginated(update, context, answer)
    except Exception as e:
        logger.exception("Llm call failed: %s", e)
        await update.message.reply_text("Fehler beim Generieren der Antwort.")
    finally:
        stop_evt3.set()
        with contextlib.suppress(Exception):
            await task3

# --- Einfacher Screenshot-Befehl Platzhalter ---

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Beginnen Sie mit der Dokumentauswahl
    SCREENSHOT_STATE[update.effective_user.id] = {"mode": "pick_doc"}
    kb = _build_docs_keyboard(get_pdf_files())
    await update.message.reply_text(
        "Screenshot-Modus aktiviert.\n"
        "📄 Bitte wählen Sie ein Dokument für den Screenshot.",
        reply_markup=kb,
        disable_web_page_preview=True,
    )