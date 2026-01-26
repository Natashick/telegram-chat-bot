# llm_client.py
import aiohttp
import os
import logging
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

def _wants_long_answer(q: str) -> bool:
    if not q:
        return False
    ql = q.casefold()
    keys = (
        # Deutsche Intents
        "ausführlich","ausfuehrlich","erklaere","erkläre","erläutere",
        "liste","schritte","begruendung","begründung","beispiele",
        "detailliert","worum geht es","worum geht es in","worum handelt es sich",
        "was ist","was bedeutet","beschreibe","beschreibung",
        # Englische Intents
        "explain","detailed","steps","list","why","how",
        "what is","what's","whats","what does","overview","overview of","describe","description"
    )
    return any(k in ql for k in keys)

async def ask_ollama(question: str, context: str, chunks_info: List[Dict] | None = None, target_language: str | None = None) -> str:
    try:
        system_prompt, user_prompt = _create_prompts(question, context, chunks_info, target_language)
        if DEBUG_PROMPTS:
            logger.debug("LLM system: %s", system_prompt[:800])
            logger.debug("LLM user: %s", user_prompt[:800])
        # Dynamische Länge je nach Absicht der Frage
        want_long = _wants_long_answer(question)
        response = await _call_ollama_api(system_prompt, user_prompt, want_long=want_long)
        return _normalize_response(response)
    except Exception as e:
        logger.error(f"Ollama-Fehler: {e}")
        return "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."

def _estimate_tokens(_prompt: str, *, want_long: bool = False) -> int:
    """
    Fixed safe budgets:
    - long (security_mode): up to 1600 tokens (capped by MAX_TOKENS)
    - short: up to 384 tokens (capped by MAX_TOKENS)
    """
    return min(2800 if want_long else 512, MAX_TOKENS)

def _create_prompts(question: str, context: str, chunks_info: List[Dict] | None, target_language: str | None) -> Tuple[str, str]:
    lang = (target_language or "DE").upper()
    if lang not in ("DE", "EN"):
        lang = "DE"
    # Sicherheitsmodus: strukturiert, HTML-Überschriften (fett), Quellen nur wenn in Ausschnitten vorhanden
    if lang == "DE":
        system = (
            "Antworte NUR auf Basis der folgenden EXCERPTS.\n"
            "Behandle geringfügige Schreibvarianten (Groß-/Kleinschreibung, Bindestrich, Slash, Leerzeichen) als identisch.\n"
            "Keine Exploits oder Angriffsanleitungen. Falls Anfrage riskant ist, freundlich ablehnen und sichere Alternativen (Patching, Monitoring, Incident Response) vorschlagen.\n"
            "Wenn Information nicht ausreichend durch EXCERPTS gestützt ist, gib GENAU EINMAL aus: \"Keine relevanten Informationen im Kontext.\".\n"
            "Ausgabeformat (nur Text, HTML‑Fettdruck für Überschriften, ohne Aufzählungszeichen):\n"
            "Vollständige hilfreiche Informationen.\n"
            "<b>Kurzfazit:</b>\n"
            "<b>Quellen:</b> (nur wenn der Dokumentname explizit in den EXCERPTS steht)\n"
        )
        user = (
            f"FRAGE:\n{question}\n\n"
            f"EXCERPTS (nur diese verwenden):\n{context}\n\n"
            "AUFGABE: Gib eine strukturierte, sachliche Antwort mit den genannten Überschriften. "
            "Quellen nennen nur, wenn sie explizit in den EXCERPTS vorkommen ('Interpretation Document', 'ISO/SAE 21434', 'UNR 155'). "
            "Keine Halluzinationen."
        )
    else:
        system = (
            "Answer ONLY based on the following EXCERPTS.\n"
            "Treat minor spelling variations (capitalization, hyphens, slashes, spaces) as identical.\n"
            "No exploits or attack instructions. If the request is risky, politely refuse and suggest safe alternatives (patching, monitoring, incident response).\n"
            "If information is not sufficiently supported by the EXCERPTS, output EXACTLY ONCE: \"No relevant information in the context.\".\n"
            "Output format (plain text, use HTML-bold for headings, no bullets):\n"
            "Full useful information.\n"
            "<b>Summary:</b>\n"
            "<b>Sources:</b> (only if the EXCERPTS explicitly contain a document name)\n"
        )
        user = (
            f"QUESTION:\n{question}\n\n"
            f"EXCERPTS (use only these):\n{context}\n\n"
            "TASK: Provide a structured, factual answer with the specified headings. "
            "List sources only if they explicitly appear in the EXCERPTS ('Interpretation Document', 'ISO/SAE 21434', 'UNR 155'). "
            "No hallucinations."
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
