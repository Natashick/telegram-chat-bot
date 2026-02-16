# llm_client.py
import aiohttp
import re
import os
import logging
import html 
import json
from typing import Dict, List, Tuple
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM backend selection
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()

# OLLAMA_URL: in Containern NICHT 'localhost' verwenden, sondern Host-Gateway!
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")
OLLAMA_STREAM = os.getenv("OLLAMA_STREAM", "0") == "1"
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "1024"))

# Groq (OpenAI-compatible) settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

_ALLOWED_LOCAL_OLLAMA_HOSTS = {
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
}

_ALLOW_REMOTE_OLLAMA = os.getenv("ALLOW_REMOTE_OLLAMA", "0") == "1"

if LLM_BACKEND == "ollama":
    _parsed_ollama = urlparse(OLLAMA_URL)
    if _parsed_ollama.scheme not in ("http", "https") or not _parsed_ollama.hostname:
        raise ValueError(f"Unsupported OLLAMA_URL={OLLAMA_URL!r}. Please use http/https with a valid hostname.")
    if not _ALLOW_REMOTE_OLLAMA and _parsed_ollama.hostname not in _ALLOWED_LOCAL_OLLAMA_HOSTS:
        raise ValueError(
            f"Unsupported OLLAMA_URL host={_parsed_ollama.hostname!r}. Set ALLOW_REMOTE_OLLAMA=1 to allow remote hosts."
        )

TEMPERATURE = 0.1
TOP_P = 0.4
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "512"))
TOP_K = 20
REPEAT_PENALTY = 1.1

TIMEOUT = aiohttp.ClientTimeout(total=360)
DEBUG_PROMPTS = os.getenv("DEBUG_PROMPTS", "0") == "1"

def _is_truncated(text: str) -> bool:
    """A crude response break detector (HTML/Markdown features)."""
    if not text:
        return False
    t = str(text).rstrip()
    if not t.endswith(('.', '!', '?', '"', ')', '>', '`', ':')):
        return True
    open_tags = len(re.findall(r'<(b|i|pre|code|strong|em)>', t))
    close_tags = len(re.findall(r'</(b|i|pre|code|strong|em)>', t))
    if open_tags != close_tags:
        return True
    if t.count('```') % 2 != 0:
        return True
    if t.count('**') % 2 != 0:
        return True
    return False

def _wants_long_answer(q: str) -> bool:
    if not q:
        return False
    ql = q.casefold()
    long_keys = (
        "ausführlich","ausfuehrlich","erklaere","erkläre","erläutere",
        "liste","schritte","begruendung","begründung","beispiele",
        "detailliert","worum geht es","worum geht es in","worum handelt es sich",
        "was ist","was bedeutet","beschreibe","beschreibung",
        "explain","detailed","steps","list","why","how",
        "what is","what's","whats","what does","overview","overview of","describe","description"
    )
    if len(q) > 100:
        return True
    if any(k in ql for k in long_keys):
        return True
    if re.search(r'\b(ISO|SAE|UNR|standard|norm)\s*[\d/\-]+', q, re.IGNORECASE):
        return True
    return False

async def ask_ollama(question: str, context: str, chunks_info: List[Dict] | None = None, target_language: str | None = None) -> str:
    try:
        system_prompt, user_prompt = _create_prompts(question, context, chunks_info, target_language)
        want_long = _wants_long_answer(question)

        try:
            if LLM_BACKEND == "groq":
                response = await _call_groq_chat(system_prompt, user_prompt, want_long=want_long)
            else:
                response = await _call_ollama_chat(system_prompt, user_prompt, want_long=want_long)
        except Exception as chat_err:
            if LLM_BACKEND == "groq":
                raise
            logger.debug("chat API failed: %s; fallback to generate", chat_err)
            response = await _call_ollama_api(system_prompt, user_prompt, want_long=want_long)

        response = _strip_noinfo_sections(response)

        if response:
            _ood = ("wordpress", "instagram", "facebook", "tiktok", "twitter", "github", "stackoverflow")
            low_resp = response.lower()
            low_ctx = (context or "").lower()
            if any(tok in low_resp for tok in _ood) and not any(tok in low_ctx for tok in _ood):
                return "Keine relevanten Informationen im Kontext."

        if _is_truncated(response):
            is_german = any(word in (response or "").lower() for word in ['die', 'der', 'das', 'und', 'ist', 'werden'])
            warning = "\n\n<i>Hinweis: Antwort möglicherweise unvollständig.</i>" if is_german else "\n\n<i>Note: Answer might be incomplete.</i>"
            response = (response or "").rstrip() + warning

        response = normalize_to_html(response)
        response = _sanitize_for_telegram(response)
        return _normalize_response(response)

    except Exception as e:
        logger.error(f"Ollama-Fehler: {e}")
        return "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."

def _estimate_tokens(_prompt: str, *, want_long: bool = False) -> int:
    return 512 if want_long else 256

def _create_prompts(question: str, context: str, chunks_info: List[Dict] | None, target_language: str | None) -> Tuple[str, str]:
    lang = (target_language or "DE").upper()
    if lang not in ("DE", "EN"):
        lang = "DE"
    
    # Explicit acronym definitions for ISO/SAE 21434
    acronym_logic = (
        "Falls Abkürzungen wie WP, RQ, RC oder CAL vorkommen, interpretiere sie im Kontext der ISO/SAE 21434:\n"
        "- WP: Work Product (Arbeitsprodukt)\n"
        "- RQ: Requirement (Anforderung)\n"
        "- RC: Recommendation (Empfehlung)\n"
        "- CAL: Cybersecurity Assurance Level\n"
        "- TARA: Threat Analysis and Risk Assessment\n"
    )
    
    if lang == "DE":
        system = (
            "Du bist ein Experte für ISO/SAE 21434. Antworte AUSSCHLIESSLICH auf Basis der EXCERPTS.\n"
            f"{acronym_logic}"
            "Toleranz für Schreibvarianten (Groß/Klein, Bindestrich, Slash).\n"
            "Wenn die EXCERPTS nicht ausreichen, um eine präzise Antwort zu geben, nutze dein Wissen über die Struktur des Standards, um die Fundstellen zu erklären.\n"
            "Ausgabeformat NUR als HTML (<b> für Titel, <pre> für Tabellen).\n"
        )
        user = f"FRAGE:\n{question}\n\nEXCERPTS:\n{context}\n\nGib eine strukturierte, ausführliche HTML-Antwort."
    else:
        acronym_logic_en = (
            "If abbreviations like WP, RQ, RC, or CAL appear, interpret them in the ISO/SAE 21434 context:\n"
            "- WP: Work Product\n"
            "- RQ: Requirement\n"
            "- RC: Recommendation\n"
            "- CAL: Cybersecurity Assurance Level\n"
            "- TARA: Threat Analysis and Risk Assessment\n"
        )
        system = (
            "You are an ISO/SAE 21434 expert. Answer ONLY based on the EXCERPTS provided.\n"
            f"{acronym_logic_en}"
            "If the EXCERPTS are insufficient for a full definition, use your knowledge of the standard's structure to explain the findings.\n"
            "Output format MUST be HTML (<b> for headings, <pre> for tables).\n"
        )
        user = f"QUESTION:\n{question}\n\nEXCERPTS:\n{context}\n\nReturn a structured, detailed HTML answer."

    return system, user

async def _call_ollama_api(system_prompt: str, user_prompt: str, *, want_long: bool = False) -> str:
    def _extract_text(data) -> str:
        if not data: return ""
        if isinstance(data, dict):
            txt = data.get("response") or data.get("output") or data.get("message") or ""
            if isinstance(txt, dict): txt = txt.get("content", "")
            return txt if isinstance(txt, str) else ""
        return str(data)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"<<SYS>>{system_prompt}\n<</SYS>>\n{user_prompt}",
        "options": {
            "temperature": 0.1,
            "top_p": 0.2,
            "num_predict": min(MAX_TOKENS, 512 if want_long else 256),  # Limit answer length for speed
            "top_k": 10,
            "repeat_penalty": 1.2,
            "num_ctx": OLLAMA_NUM_CTX,    # Use configured context size
            "num_thread": 1,
        },
        "stream": False
    }

    async with aiohttp.ClientSession(timeout=TIMEOUT, trust_env=True) as session:
        async with session.post(f"{OLLAMA_URL}/api/generate", json=payload, allow_redirects=False) as resp:
            if resp.status == 200:
                if not OLLAMA_STREAM:
                    data = await resp.json()
                    return _extract_text(data)
                
                acc = []
                async for chunk in resp.content.iter_any():
                    try:
                        s = chunk.decode("utf-8", errors="ignore")
                        for line in s.splitlines():
                            if line.strip().startswith("{"):
                                d = json.loads(line)
                                t = d.get("response") or ""
                                if t: acc.append(t)
                    except Exception:
                        continue
                return "".join(acc)
            
            # Fallback for 400/422 (compatibility)
            if resp.status in (400, 422):
                fallback = payload.copy()
                fallback["options"].pop("num_predict", None)
                async with session.post(f"{OLLAMA_URL}/api/generate", json=fallback) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.json()
                        return _extract_text(data2)

            err_text = await resp.text()
            raise RuntimeError(f"Ollama API {resp.status}: {err_text}")

async def _call_ollama_chat(system_prompt: str, user_prompt: str, *, want_long: bool = False) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "options": {
            "temperature": 0.1,
            "num_predict": min(MAX_TOKENS, 512 if want_long else 256), # Limit answer length for speed
            "num_ctx": OLLAMA_NUM_CTX,    # Use configured context size
            "num_thread": 1,    # Keep one thread if CPU is very weak
        },
        "stream": False
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT, trust_env=False) as session:
        async with session.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            if resp.status != 200:
                txt = await resp.text()
                raise RuntimeError(f"Ollama chat {resp.status}: {txt}")
            data = await resp.json()
            return data.get("message", {}).get("content", "")

async def _call_groq_chat(system_prompt: str, user_prompt: str, *, want_long: bool = False) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set")
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "top_p": 0.2,
        "max_tokens": MAX_TOKENS if MAX_TOKENS > 512 else 1024,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT, trust_env=True) as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers) as resp:
            if resp.status != 200:
                txt = await resp.text()
                raise RuntimeError(f"Groq chat {resp.status}: {txt}")
            data = await resp.json()
            return (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")

def _md_bold_to_html_block(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text or "")

def _md_headings_to_bold_block(text: str) -> str:
    out_lines = []
    for raw in (text or "").splitlines():
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", raw)
        if m:
            out_lines.append(f"<b>{html.escape(m.group(2).strip())}</b>")
        else:
            out_lines.append(raw)
    return "\n".join(out_lines)

def _md_tables_to_pre_block(text: str) -> str:
    if not text: return ""
    lines = text.splitlines()
    out, buf = [], []

    def flush():
        nonlocal buf
        if not buf: return
        
        # Filter out separator lines (|---|---|) and parse cells
        rows = []
        for r in buf:
            if "|" not in r: continue
            # Skip separator lines (contain only |, -, :, and spaces)
            if re.match(r'^[\s|:\-]+$', r): continue
            
            # Split by | and strip empty edges
            cells = r.split("|")
            if cells and not cells[0].strip(): cells = cells[1:]
            if cells and not cells[-1].strip(): cells = cells[:-1]
            
            # Strip cells (escape happens later in normalize_to_html)
            cells = [c.strip() for c in cells]
            rows.append(cells)
        
        if not rows: return
        
        # Calculate column widths
        max_cols = max(len(r) for r in rows)
        widths = [0] * max_cols
        for cells in rows:
            for i in range(len(cells)):
                widths[i] = max(widths[i], len(cells[i]))
        
        # Format table with proper alignment
        box = []
        for cells in rows:
            padded = " | ".join(
                (cells[i] if i < len(cells) else "").ljust(widths[i]) 
                for i in range(max_cols)
            )
            box.append(padded)
        
        out.append("<pre>\n" + "\n".join(box) + "\n</pre>")
        buf.clear()

    for L in lines:
        if L.count("|") >= 2: buf.append(L)
        else:
            flush()
            out.append(L)
    flush()
    return "\n".join(out)

def normalize_to_html(text: str) -> str:
    if not text: return ""
    segments = re.split(r'(?i)(<pre[\s\S]*?</pre>)', text)
    out = []
    for seg in segments:
        if re.match(r'(?i)^<pre[\s\S]*?</pre>$', seg.strip()):
            m = re.match(r'(?is)<pre\b[^>]*>([\s\S]*?)</pre>', seg)
            inner = html.escape(m.group(1)) if m else seg
            out.append(f"<pre>{inner}</pre>")
        else:
            block = _md_headings_to_bold_block(seg)
            block = _md_bold_to_html_block(block)
            block = _md_tables_to_pre_block(block)
            out.append(block)
    return "\n".join(out)

def _sanitize_for_telegram(text: str) -> str:
    """Escape everything except content inside <pre> tags, then allow only <b> and <pre> tags back."""
    if not text:
        return ""
    
    # Extract <pre> blocks to prevent double-escaping
    pre_blocks = []
    def save_pre(match):
        pre_blocks.append(match.group(0))
        return f"__PRE_BLOCK_{len(pre_blocks)-1}__"
    
    text_with_placeholders = re.sub(r'(?i)<pre[^>]*>[\s\S]*?</pre>', save_pre, text)
    
    # Escape the text without <pre> content
    escaped = html.escape(text_with_placeholders)
    
    # Unescape allowed tags
    for tag in ("b", "pre"):
        escaped = re.sub(rf"&lt;{tag}&gt;", f"<{tag}>", escaped, flags=re.IGNORECASE)
        escaped = re.sub(rf"&lt;/{tag}&gt;", f"</{tag}>", escaped, flags=re.IGNORECASE)
    
    # Restore <pre> blocks
    for i, block in enumerate(pre_blocks):
        escaped = escaped.replace(f"__PRE_BLOCK_{i}__", block)
    
    return escaped

def _strip_noinfo_sections(text: str) -> str:
    if not text: return ""
    _NOINFO_RE = re.compile(r"(?im)^\s*(kommentare?|comments?)\s*:.*$|^\s*keine\s+relevanten\s+informationen.*$")
    lines = [L for L in text.splitlines() if not _NOINFO_RE.match(L)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

def _normalize_response(text: str) -> str:
    return text.strip() if text and text.strip() else "Keine relevanten Informationen im Kontext."

async def test_ollama_connection() -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_URL}/api/tags") as r:
                return r.status == 200
    except:
        return False