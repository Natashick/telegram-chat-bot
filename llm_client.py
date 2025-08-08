# llm_client.py

import aiohttp
import asyncio
import os

# Flexible URL configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

print(f"[INFO] LLM URL: {OLLAMA_URL}")
print(f"[INFO] LLM Model: {OLLAMA_MODEL}")

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
                timeout=aiohttp.ClientTimeout(total=60)  # 60 Sekunden für llama3.2:3b
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data.get("response", "").strip()
                    return answer if answer else f"Found info about '{question}' but no clear answer."
                else:
                    return f"[Ollama Error {response.status}] Cannot connect to LLM."
    except asyncio.TimeoutError:
        # TIMEOUT HANDLING (nach 60s)
        return f"Antwort zu '{question}' gefunden, aber LLM antwortet zu langsam (>60s). Versuche es erneut oder verwende kürzere Fragen."
    except aiohttp.ClientError as e:
        return f"Verbindungsfehler zum LLM Server: {str(e)[:80]}..."
    except Exception as e:
        return f"LLM Fehler: {str(e)[:80]}..."