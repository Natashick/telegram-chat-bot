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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

TEMPERATURE = 0.1
TOP_P = 0.9
MAX_TOKENS = 1024
TOP_K = 40
REPEAT_PENALTY = 1.1

TIMEOUT = aiohttp.ClientTimeout(total=180)

async def ask_ollama(question: str, context: str, chunks_info: List[Dict] | None = None, target_language: str | None = None) -> str:
    try:
        system_prompt, user_prompt = _create_prompts(question, context, chunks_info, target_language)
        response = await _call_ollama_api(system_prompt, user_prompt)
        return _normalize_response(response)
    except Exception as e:
        logger.error(f"Ollama-Fehler: {e}")
        return "INFORMATION NICHT GEFUNDEN - LLM nicht erreichbar."

def _create_prompts(question: str, context: str, chunks_info: List[Dict] | None, target_language: str | None) -> Tuple[str, str]:
    lang = (target_language or "DE").upper()
    if lang not in ("DE", "EN"):
        lang = "DE"
    system = (
        ("Antworte strikt auf Deutsch. " if lang == "DE" else "Answer strictly in English. ")
        + "Liefere eine vollständige, professionelle und verständliche Antwort. "
        + "Nutze AUSSCHLIESSLICH den bereitgestellten Kontext. "
        + "Wenn der Kontext keine Antwort enthält, sage klar, dass keine relevanten Informationen gefunden wurden und schlage eine Präzisierung vor. "
        + "Nenne KEINE Quellen, Dateinamen, Seiten oder Scores. "
        + "Struktur: 1) Titel (eine Zeile) 2) Key Points (Aufzählung) 3) Ausführliche Erklärung (Absätze) 4) Kurzes Fazit."
    )
    user = (("FRAGE:\n" if lang == "DE" else "QUESTION:\n") + f"{question}\n\n"
            + ("KONTEXT:\n" if lang == "DE" else "CONTEXT:\n") + f"{context}")
    if chunks_info:
        pass  # keine Metadaten/Quellen dem Modell verraten
    return system, user

async def _call_ollama_api(system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"<<SYS>>{system_prompt}\n<</SYS>>\n{user_prompt}",
        "options": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "num_predict": MAX_TOKENS,
            "top_k": TOP_K,
            "repeat_penalty": REPEAT_PENALTY,
            "num_thread": 2
        },
        "stream": False
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("response", "")
            # Fallback: remove num_predict if server rejects options (compat across versions)
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
                    data2 = await resp2.json()
                    return data2.get("response", "")
            txt = await resp.text()
            raise RuntimeError(f"Ollama API {resp.status}: {txt}")

def _normalize_response(text: str) -> str:
    if not text or not text.strip():
        return "INFORMATION NICHT GEFUNDEN"
    t = text.strip()
    if not t.endswith(('.', '!', '?')):
        t += '.'
    return t

async def test_ollama_connection() -> bool:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{OLLAMA_URL}/api/tags") as r:
                return r.status == 200
    except Exception as e:
        logger.error(f"Ollama Verbindungstest fehlgeschlagen: {e}")
        return False
