# llm_client.py
import aiohttp
import re
import os
import logging
import html 
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OLLAMA_URL: in Containern NICHT 'localhost' verwenden, sondern Host-Gateway!
# Windows/Mac Docker: export OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_STREAM = os.getenv("OLLAMA_STREAM", "0") == "1"
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "1024"))

TEMPERATURE = 0.1
TOP_P = 0.9
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))  # obere Grenze für die Generierung
TOP_K = 40
REPEAT_PENALTY = 1.1

TIMEOUT = aiohttp.ClientTimeout(total=180)
DEBUG_PROMPTS = os.getenv("DEBUG_PROMPTS", "0") == "1"

def _is_truncated(text: str) -> bool:
    """Грубый детектор обрыва ответа (HTML/Markdown признаки)."""
    if not text:
        return False
    t = str(text).rstrip()
    # незавершённое предложение/блок
    if not t.endswith(('.', '!', '?', '"', ')', '>', '`', ':')):
        return True
    # незакрытые HTML‑теги
    open_tags = len(re.findall(r'<(b|i|pre|code|strong|em)>', t))
    close_tags = len(re.findall(r'</(b|i|pre|code|strong|em)>', t))
    if open_tags != close_tags:
        return True
    # незакрытые markdown‑блоки
    if t.count('```') % 2 != 0:
        return True
    if t.count('**') % 2 != 0:
        return True
    return False

def _wants_long_answer(q: str) -> bool:
    """ Returns True if the question is long and requires a long answer.
    Args: q: str - The question to check.
    Returns: bool - True if the question is long and requires a long answer, False otherwise.
    """
    # Protektionsmodus: wenn keine Frage, keine lange Antwort
    if not q:
        return False
    ql = q.casefold()
    # Deutsche und Englische Schlüsselwörter für lange Antworten
    long_keys = (
        # Deutsche Intents
        "ausführlich","ausfuehrlich","erklaere","erkläre","erläutere",
        "liste","schritte","begruendung","begründung","beispiele",
        "detailliert","worum geht es","worum geht es in","worum handelt es sich",
        "was ist","was bedeutet","beschreibe","beschreibung",
        # Englische Intents
        "explain","detailed","steps","list","why","how",
        "what is","what's","whats","what does","overview","overview of","describe","description"
    )
    # Kriterium 1: Eine lange frage (>100 Zeichnen) erfordert in der Regel eine ausführliche Antwort
    if len(q) > 100:
        return True
    # Kriterium 2: DIe Frage enthält klare Merkmale einer "erwiterten" Anfrage
    if any(k in ql for k in long_keys):
        return True
    # Kriterium 3: Informationsanfrage zu einer bestimmten Form/einem bestimmten Dokument
    # Beispiele: "Iso 21434", "UNR 155", "ISO/SAE 21434", "UNR 155"
    if re.search(r'\b(ISO|SAE|UNR|standard|norm)\s*[\d/\-]+', q, re.IGNORECASE):
        return True
    # Standard: kurze Antwort
    return False

async def ask_ollama(question: str, context: str, chunks_info: List[Dict] | None = None, target_language: str | None = None) -> str:
    try:
        system_prompt, user_prompt = _create_prompts(question, context, chunks_info, target_language)
        if DEBUG_PROMPTS:
            logger.debug("LLM system: %s", system_prompt[:800])
            logger.debug("LLM user: %s", user_prompt[:800])
        # Dynamische Länge je nach Absicht der Frage
        want_long = _wants_long_answer(question)
        # Основной вызов — chat; при ошибке fallback на generate
        try:
            response = await _call_ollama_chat(system_prompt, user_prompt, want_long=want_long)
        except Exception as chat_err:
            logger.debug("chat API failed: %s; fallback to generate", chat_err)
            response = await _call_ollama_api(system_prompt, user_prompt, want_long=want_long)

        # «Продолжение» при вероятном обрыве (до 2 раз)
        max_cont = 2
        cont = 0
        while _is_truncated(response) and cont < max_cont:
            tail = (response or "")[-200:]
            continuation_prompt = (
                "Fahre mit der HTML‑Antwort fort ab:\n"
                f"{tail}\n"
                "Nur die Fortsetzung (keine Wiederholung), HTML mit <b> und <pre>."
            )
            try:
                more = await _call_ollama_chat(system_prompt, continuation_prompt, want_long=True)
            except Exception as chat_err2:
                logger.debug("chat continuation failed: %s; stop continuation", chat_err2)
                break
            response = (response or "") + ("\n" if response else "") + (more or "")
            cont += 1

        # Мягкое предупреждение, если всё ещё выглядит обрезанным
        if _is_truncated(response):
            is_german = any(word in (response or "").lower() for word in ['die', 'der', 'das', 'und', 'ist', 'werden'])
            warning = "\n\n<i>Hinweis: Antwort möglicherweise unvollständig.</i>" if is_german else "\n\n<i>Note: Answer might be incomplete.</i>"
            response = (response or "").rstrip() + warning

        # Markdown → HTML Normalisierung (жирный/таблицы) для единого HTML-конвейера
        response = normalize_to_html(response)
        return _normalize_response(response)

    except Exception as e:
        logger.error(f"Ollama-Fehler: {e}")
        return "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."

def _estimate_tokens(_prompt: str, *, want_long: bool = False) -> int:
    """
    Fixed safe budgets:
    - long (security_mode): up to 3500 tokens (capped by MAX_TOKENS)
    - short: up to 1500 tokens (capped by MAX_TOKENS)
    """
    return min(3500 if want_long else 1500, MAX_TOKENS)

def _create_prompts(question: str, context: str, chunks_info: List[Dict] | None, target_language: str | None) -> Tuple[str, str]:
    lang = (target_language or "DE").upper()
    if lang not in ("DE", "EN"):
        lang = "DE"
    # Sicherheitsmodus: strukturiert, HTML-Überschriften (fett), Quellen nur wenn in Ausschnitten vorhanden
    if lang == "DE":
        system = (
            "Antworte AUSSCHLIESSLICH auf Basis der EXCERPTS.\n"
            "Toleranz für Schreibvarianten (Groß/Klein, Bindestrich, Slash, Leerzeichen).\n"
            "Keine Exploit-/Angriffsanleitungen.\n"
            "Wenn die EXCERPTS nicht ausreichen, gib GENAU EINMAL: \"Keine relevanten Informationen im Kontext.\".\n"
            "Ausgabeformat NUR als HTML:\n"
            "- Überschriften in <b>...</b>\n"
            "- Tabellen als ASCII in <pre>...</pre>\n"
            "- Keine Markdown-Syntax, kein Codeblock-Markdown.\n"
        )
        user = (
            f"FRAGE:\n{question}\n\n"
            f"EXCERPTS (nur diese verwenden):\n{context}\n\n"
            "Gib eine strukturierte, sachliche HTML-Antwort mit <b>-Überschriften. "
            "Wenn Tabellen sinnvoll sind, nutze ein ASCII-Raster in <pre>."

        )
    else:
        system = (
            "Answer ONLY from the EXCERPTS.\n"
            "Be tolerant to minor spelling variations (case, hyphens, slashes, spaces).\n"
            "No exploit/attack instructions.\n"
            "If the EXCERPTS are insufficient, output EXACTLY ONCE: \"No relevant information in the context.\".\n"
            "Output format MUST be HTML:\n"
            "- Headings in <b>...</b>\n"
            "- Tables as ASCII in <pre>...</pre>\n"
            "- No Markdown syntax, no code-block Markdown.\n"
        )

        user = (
            f"QUESTION:\n{question}\n\n"
            f"EXCERPTS (use only these):\n{context}\n\n"
            "Return a structured, factual HTML answer with <b> headings. "
            "If a table is suitable, use an ASCII grid in <pre>."
        )

    if chunks_info:
        # rohe Metadaten nicht preisgeben; das Modell schließt aus dem Ausschnittstext
        pass
    return system, user

async def _call_ollama_api(system_prompt: str, user_prompt: str, *, want_long: bool = False) -> str:
    def _extract_text(data) -> str:
        if data is None:
            return ""
        if isinstance(data, dict):
            # Gemeinsame Felder in allen Ollama-Versionen/Adaptern
            txt = (
                data.get("response")
                or data.get("output")
                or data.get("message")
                or ""
            )
            if isinstance(txt, dict):
                # e.g. {"message":{"content":"..."}}
                txt = txt.get("content", "") or txt.get("text", "")
            if isinstance(txt, list):
                # e.g. [{"content":"..."}, {"content":"..."}]
                parts = []
                for item in txt:
                    if isinstance(item, dict):
                        parts.append(item.get("content") or item.get("text") or "")
                    elif isinstance(item, str):
                        parts.append(item)
                txt = "\n".join([p for p in parts if p])
            if isinstance(txt, str):
                return txt
            return ""
        if isinstance(data, str):
            return data
        return ""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"<<SYS>>{system_prompt}\n<</SYS>>\n{user_prompt}",
        "options": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "num_predict": _estimate_tokens(user_prompt, want_long=want_long),
            "top_k": TOP_K,
            "repeat_penalty": REPEAT_PENALTY,
            "num_thread": 2,
            "num_ctx": OLLAMA_NUM_CTX,
        },
        "stream": OLLAMA_STREAM
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
            if resp.status == 200:
                # Einige Versionen können text/plain oder unterschiedliche JSON-Formate zurückgeben
                ctype = resp.headers.get("Content-Type", "")
                if "application/json" in ctype and not OLLAMA_STREAM:
                    data = await resp.json()
                    return _extract_text(data)
                if OLLAMA_STREAM:
                    # Streaming-Chunks lesen und Text zusammenfügen
                    acc = []
                    async for chunk in resp.content.iter_any():
                        try:
                            s = chunk.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                        # Ollama streamt JSON-Zeilen; versuche 'response' zu extrahieren
                        for line in s.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("{") and line.endswith("}"):
                                try:
                                    import json
                                    d = json.loads(line)
                                    t = d.get("response") or d.get("output") or ""
                                    if isinstance(t, str) and t:
                                        acc.append(t)
                                except Exception:
                                    pass
                    return "".join(acc)
                txt = await resp.text()
                return txt or ""
            # Fallback: entferne num_predict, wenn der Server Optionen ablehnt (Kompatibilität über Versionen hinweg)
            if resp.status in (400, 422):
                try:
                    txt1 = await resp.text()
                except Exception:
                    txt1 = ""
                fallback = payload.copy()
                opts = dict(fallback.get("options", {}))
                opts.pop("num_predict", None)
                fallback["options"] = opts
                async with session.post(f"{OLLAMA_URL}/api/generate", json=fallback) as resp2:
                    if resp2.status != 200:
                        txt2 = await resp2.text()
                        raise RuntimeError(f"Ollama API {resp.status}: {txt1} | fallback {resp2.status}: {txt2}")
                    ctype2 = resp2.headers.get("Content-Type", "")
                    if "application/json" in ctype2:
                        data2 = await resp2.json()
                        return _extract_text(data2)
                    txt2 = await resp2.text()
                    return txt2 or ""
            txt = await resp.text()
            raise RuntimeError(f"Ollama API {resp.status}: {txt}")

async def _call_ollama_chat(system_prompt: str, user_prompt: str, *, want_long: bool = False) -> str:
    """Предпочтительный вызов — chat API с ролями system/user."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "num_predict": _estimate_tokens(user_prompt, want_long=want_long),
            "top_k": TOP_K,
            "repeat_penalty": REPEAT_PENALTY,
            "num_ctx": OLLAMA_NUM_CTX,
        },
        "stream": False
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            txt = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Ollama chat {resp.status}: {txt}")
            try:
                data = await resp.json()
                msg = (data.get("message") or {}).get("content") or data.get("response") or data.get("output") or txt
                return msg
            except Exception:
                return txt

def _md_bold_to_html(text: str) -> str:
    # **bold** → <b>bold</b>
    try:
        return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text or "")
    except Exception:
        return text or ""

def _md_table_to_pre(text: str) -> str:
    # Преобразование markdown-таблиц в моноширинный <pre>
    if not text:
        return ""
    lines = (text or "").splitlines()
    out: list[str] = []
    buf: list[str] = []

    def flush():
        nonlocal out, buf
        if not buf:
            return
        # Подгон ширины столбцов
        rows = [r for r in buf if "|" in r]
        cols_lists = [row.split("|") for row in rows]
        # выравнивание по количеству столбцов в первой строке
        max_cols = max(len(r) for r in cols_lists) if cols_lists else 0
        widths = [0] * max_cols
        for cells in cols_lists:
            for i in range(max_cols):
                cell = cells[i] if i < len(cells) else ""
                widths[i] = max(widths[i], len(cell.strip()))
        box = []
        for cells in cols_lists:
            padded = " | ".join(
                (cells[i].strip() if i < len(cells) else "").ljust(widths[i])
                for i in range(max_cols)
            )
            box.append(padded)
        out.append("<pre>\n" + "\n".join(box) + "\n</pre>")
        buf = []

    for L in lines:
        if L.count("|") >= 2:
            buf.append(L)
        else:
            flush()
            out.append(L)
    flush()
    return "\n".join(out)

def normalize_to_html(text: str) -> str:
    """Лёгкая нормализация: **…**→<b>…</b>, markdown-таблицы → <pre>…</pre>"""
    if not text:
        return ""
    t = _md_bold_to_html(text)
    t = _md_table_to_pre(t)
    return t

def _normalize_response(text: str) -> str:
    t = "" if text is None else str(text).strip()
    if t:
        return t
    # Standard kann an die Sprache gebunden werden
    # Man kann Englisch beibehalten oder eine neutrale Nachricht verwenden.
    return "Keine relevanten Informationen im Kontext."

async def test_ollama_connection() -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_URL}/api/tags") as r:
                return r.status == 200
    except Exception as e:
        logger.error(f"Ollama Verbindungstest fehlgeschlagen: {e}")
        return False
