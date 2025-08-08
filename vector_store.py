# vector_store.py

import os
import glob
import chromadb
from pdf_parser import extract_paragraphs_from_pdf
from chromadb.config import Settings

CHROMA_DIR = "./chroma_db"

# Ollama Embedding mit echtem Embedding-Model
class OllamaEmbeddingFunction:
    def __init__(self, embedding_model="nomic-embed-text", url=None):
        self.embedding_model = embedding_model  # Echtes Embedding-Model
        self.url = url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        print(f"[INFO] Ollama Embedding Model: {self.embedding_model}")
        print(f"[INFO] Ollama Embedding URL: {self.url}")
    
    def __call__(self, input):
        import requests
        embeddings = []
        texts = input if isinstance(input, list) else [input]
        for text in texts:
            try:
                base_url = self.url.rstrip("/")
                response = requests.post(f"{base_url}/api/embeddings", 
                    json={"model": self.embedding_model, "prompt": text[:500]}, timeout=10)
                if response.status_code == 200:
                    embedding = response.json().get("embedding", [0.0] * 768)
                    embeddings.append(embedding)
                else:
                    # Fallback zu Standard wenn Ollama nicht verfügbar
                    print(f"[WARNING] Ollama embedding failed: {response.status_code}")
                    embeddings.append([0.1] * 768)
            except Exception as e:
                print(f"[WARNING] Ollama embedding error: {e}")
                embeddings.append([0.1] * 768)
        return embeddings

# Versuche Ollama Embeddings, sonst Standard
try:
    embedding_func = OllamaEmbeddingFunction()
    print("[INFO] Using Ollama embeddings with nomic-embed-text")
except Exception as e:
    print(f"[WARNING] Ollama embeddings failed: {e}")
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        embedding_func = DefaultEmbeddingFunction()
        print("[INFO] Fallback to ChromaDB default embeddings")
    except Exception as e2:
        print(f"[ERROR] All embeddings failed: {e2}")
        embedding_func = None

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR,
    settings=Settings(anonymized_telemetry=False)
)

collection = chroma_client.get_or_create_collection(
    name="pdf_paragraphs",
    embedding_function=embedding_func
)

def index_pdfs(pdf_files):
    if collection.count() > 0:
        print("Collection already indexed.")
        return
    for pdf in pdf_files:
        paras = extract_paragraphs_from_pdf(pdf)
        for pid, para in enumerate(paras):
            collection.add(
                documents=[para],
                metadatas=[{"source": pdf}],
                ids=[f"{os.path.basename(pdf)}_{pid}"]
            )

def semantic_search(question, selected_doc, n_results=3):
    """
    BEST PRACTICE: Hole mehrere relevante Textabschnitte für besseren Kontext
    """
    results = collection.query(
        query_texts=[question],
        n_results=n_results,  # 3 beste Ergebnisse
        where={"source": selected_doc},
        include=["documents", "metadatas", "distances"]
    )
    return results

def get_combined_context(results):
    """
    BEST PRACTICE: Kombiniere mehrere Suchergebnisse zu einem besseren Kontext
    """
    if not results['documents'] or not results['documents'][0]:
        return "No relevant information found."
    
    documents = results['documents'][0]
    distances = results['distances'][0] if results['distances'] else [0] * len(documents)
    
    # Sortiere nach Relevanz (niedrigere Distanz = relevanter)
    sorted_docs = sorted(zip(documents, distances), key=lambda x: x[1])
    
    # Kombiniere die besten Abschnitte
    combined = []
    for i, (doc, distance) in enumerate(sorted_docs[:3]):  # Top 3
        combined.append(f"[Section {i+1}] {doc}")
    
    return "\n\n".join(combined)


# HILFSFUNKTIONEN

def get_collection_stats():
    """
    SAMMLE STATISTIKEN Über die Vektordatenbank
    
    Zweck: Debug-Informationen für Performance-Analyse
    Rückgabe: Dictionary mit Count, Modell-Info, etc.
    """
    try:
        count = collection.count()
        return {
            "total_paragraphs": count,
            "embedding_model": embedding_func.embedding_model if hasattr(embedding_func, 'embedding_model') else "unknown",
            "database_path": CHROMA_DIR
        }
    except Exception as e:
        return {"error": str(e)}


def clear_index():
    """
    LÖSCHE ALLE INDIZIERTEN DATEN
    
    Zweck: Neustart der Indexierung (für Entwicklung/Tests)
    VORSICHT: Alle Daten gehen verloren!
    """
    try:
        # Lösche Collection
        chroma_client.delete_collection("pdf_paragraphs")
        print("Index erfolgreich gelöscht.")
        return True
    except Exception as e:
        print(f"Fehler beim Löschen: {e}")
        return False