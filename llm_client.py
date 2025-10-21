# llm_client.py

import aiohttp
import asyncio
import os
import logging

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Flexible URL configuration with Docker-friendly default
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

logger.info(f"LLM URL: {OLLAMA_URL}")
logger.info(f"LLM Model: {OLLAMA_MODEL}")
logger.info(f"LLM Timeout: {OLLAMA_TIMEOUT}s")


async def test_ollama_connection():
    """
    TEST OLLAMA CONNECTION AT STARTUP
    
    Checks if Ollama server is reachable and logs clear warning if not.
    This helps diagnose connectivity issues early.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        logger.info("Testing Ollama connection...")
        
        async with aiohttp.ClientSession() as session:
            # Try to list models endpoint
            models_url = f"{OLLAMA_BASE_URL}/api/tags"
            
            try:
                async with session.get(
                    models_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get('models', [])
                        logger.info(f"✅ Ollama connection successful! Available models: {len(models)}")
                        
                        # Check if configured model is available
                        model_names = [m.get('name', '') for m in models]
                        if OLLAMA_MODEL in model_names:
                            logger.info(f"✅ Configured model '{OLLAMA_MODEL}' is available")
                        else:
                            logger.warning(f"⚠️ Configured model '{OLLAMA_MODEL}' not found in available models: {model_names}")
                        
                        return True
                    else:
                        logger.warning(f"⚠️ Ollama returned status {response.status}")
                        return False
                        
            except asyncio.TimeoutError:
                logger.error(f"❌ Ollama connection timeout after 10s")
                logger.error(f"   URL: {OLLAMA_BASE_URL}")
                logger.error(f"   Make sure Ollama is running and accessible")
                return False
                
    except aiohttp.ClientError as e:
        logger.error(f"❌ Ollama connection failed: {e}")
        logger.error(f"   URL: {OLLAMA_BASE_URL}")
        logger.error(f"   Check that OLLAMA_URL environment variable is set correctly")
        logger.error(f"   If using Docker, ensure host.docker.internal is accessible")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error testing Ollama connection: {e}")
        return False


def ensure_ollama_on_startup():
    """
    SYNCHRONOUS WRAPPER FOR STARTUP CONNECTION TEST
    
    Call this from application initialization to verify Ollama connectivity.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(test_ollama_connection())


async def ask_ollama(question, context):
    """ FRAGT OLLAMA LLM
    
    Zweck: Sendet Frage + Kontext an Ollama und bekommt Antwort zurück
    
    Parameter:
    - question (str): Die Benutzerfrage
    - context (str): Relevante PDF-Textstücke aus Vektorsuche
    
    Rückgabe: 
    - str: Antwort vom LLM oder Fehlermeldung
    
    Performance-Optimierungen:
    - Kurzer, präziser Prompt (weniger Tokens)
    - Reduzierte Antwortlänge für Geschwindigkeit
    - Aggressives Timeout (8s statt 30s)
    """
    
    # PROMPT FÜR VOLLSTÄNDIGE ANTWORTEN
    # Erkennt ob Liste/Aufzählung gefragt ist und gibt vollständige Antworten
    prompt = f"""Based on this context, answer the question comprehensively:

CONTEXT:
{context[:2000]}

QUESTION: {question}

INSTRUCTIONS:
- If the question asks for a list, enumerate ALL items completely
- For "how many" questions, provide the exact count and list all items
- Use bullet points (•) for lists and numbered points (1., 2., 3.) for sequences  
- Include ALL relevant details found in the context
- If asking about multiple points/steps/items, list them ALL
- Don't cut off lists - provide complete information

ANSWER:"""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,     # Weniger Kreativität = schneller
                        "top_p": 0.8,           # Fokussierter für Speed
                        "top_k": 20,            # Weniger Vielfalt = schneller
                        "num_predict": 300,     # Kürzere Antworten = schneller
                        "repeat_penalty": 1.1,  # Keine Wiederholungen
                        "num_ctx": 2048         # Weniger Kontext = schneller
                    }
                },
                timeout=aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("response", "").strip()
                    return answer if answer else f"Found info about '{question}' but no clear answer."
                else:
                    return f"[Ollama Error {response.status}] Cannot connect to LLM."
    except asyncio.TimeoutError:
        # TIMEOUT HANDLING
        return f"Antwort zu '{question}' gefunden, aber LLM antwortet zu langsam (>{OLLAMA_TIMEOUT}s). Versuche es erneut oder verwende kürzere Fragen."
    except aiohttp.ClientError as e:
        return f"Verbindungsfehler zum LLM Server: {str(e)[:80]}..."
    except Exception as e:
        return f"LLM Fehler: {str(e)[:80]}..."