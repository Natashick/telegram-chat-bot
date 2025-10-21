# vector_store.py

import os
import glob
import chromadb
from pdf_parser import extract_paragraphs_from_pdf
from chromadb.config import Settings
import logging

CHROMA_DIR = "./chroma_db"

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# OPTIMIZED DEFAULTS FOR MEMORY EFFICIENCY
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_BATCH_SIZE = 64

# ChromaDB Konfiguration für Railway
def get_chroma_client():
    """Erstellt ChromaDB Client mit Railway-optimierter Konfiguration"""
    try:
        # Versuche persistente ChromaDB
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        print(f"[INFO] Using persistent ChromaDB at {CHROMA_DIR}")
        return client
    except Exception as e:
        print(f"[WARNING] Persistent ChromaDB failed: {e}")
        # Fallback zu In-Memory ChromaDB
        client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=None
        ))
        print("[INFO] Using in-memory ChromaDB")
        return client

# Ollama Embedding mit echtem Embedding-Model
class OllamaEmbeddingFunction:
    def __init__(self, embedding_model=None, url=None, batch_size=DEFAULT_BATCH_SIZE):
        # Use optimized default model
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        self.url = url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.batch_size = batch_size
        logger.info(f"Ollama Embedding Model: {self.embedding_model}")
        logger.info(f"Ollama Embedding URL: {self.url}")
        logger.info(f"Batch size: {self.batch_size}")
        
    def __call__(self, input):
        # BATCHED EMBEDDING PROCESSING FOR MEMORY EFFICIENCY
        import requests
        embeddings = []
        texts = input if isinstance(input, list) else [input]
        
        # Process in batches to reduce memory usage
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            logger.debug(f"Processing embedding batch {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1}")
            
            for text in batch:
                try:
                    base_url = self.url.rstrip("/")
                    response = requests.post(f"{base_url}/api/embeddings", 
                        json={"model": self.embedding_model, "prompt": text[:500]}, timeout=5)
                    if response.status_code == 200:
                        embedding = response.json().get("embedding", [0.0] * 768)
                        embeddings.append(embedding)
                    else:
                        # Fallback zu einfachen Embeddings
                        logger.warning(f"Ollama embedding failed: {response.status_code}")
                        embeddings.append([0.1] * 768)
                except Exception as e:
                    logger.warning(f"Ollama embedding error: {e}")
                    # Fallback zu einfachen Embeddings
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

# ChromaDB Client mit Railway-Fallback
try:
    chroma_client = get_chroma_client()
    collection = chroma_client.get_or_create_collection(
        name="pdf_paragraphs",
        embedding_function=embedding_func
    )
    print("[INFO] ChromaDB initialized successfully")
except Exception as e:
    print(f"[ERROR] ChromaDB initialization failed: {e}")
    # Fallback zu In-Memory
    chroma_client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=None
    ))
    collection = chroma_client.get_or_create_collection(
        name="pdf_paragraphs",
        embedding_function=embedding_func
    )
    print("[INFO] Using in-memory ChromaDB fallback")

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


def has_document(pdf_file):
    """
    CHECK IF DOCUMENT IS INDEXED
    
    Args:
        pdf_file: Path or filename of PDF
    
    Returns:
        bool: True if document has indexed chunks
    """
    try:
        basename = os.path.basename(pdf_file)
        # Query for any document with this source
        results = collection.get(
            where={"source": pdf_file},
            limit=1
        )
        
        # Also check with basename
        if not results['ids']:
            results = collection.get(
                where={"source": basename},
                limit=1
            )
        
        is_indexed = len(results['ids']) > 0
        logger.debug(f"Document {basename} indexed: {is_indexed}")
        return is_indexed
    except Exception as e:
        logger.error(f"Error checking if document indexed: {e}")
        return False


def index_document(pdf_file, progress_callback=None):
    """
    INDEX A SINGLE DOCUMENT
    
    Args:
        pdf_file: Path to PDF file
        progress_callback: Optional callback function(message: str)
    
    Returns:
        bool: True if successful
    """
    try:
        if progress_callback:
            progress_callback(f"Starting indexing: {os.path.basename(pdf_file)}")
        
        logger.info(f"Indexing document: {pdf_file}")
        paras = extract_paragraphs_from_pdf(pdf_file)
        
        if not paras:
            logger.warning(f"No paragraphs extracted from {pdf_file}")
            if progress_callback:
                progress_callback(f"⚠️ No text extracted from {os.path.basename(pdf_file)}")
            return False
        
        if progress_callback:
            progress_callback(f"Extracted {len(paras)} paragraphs, adding to index...")
        
        # Add paragraphs in batches
        batch_size = DEFAULT_BATCH_SIZE
        for i in range(0, len(paras), batch_size):
            batch = paras[i:i+batch_size]
            batch_ids = [f"{os.path.basename(pdf_file)}_{i+j}" for j in range(len(batch))]
            batch_metadata = [{"source": pdf_file} for _ in batch]
            
            collection.add(
                documents=batch,
                metadatas=batch_metadata,
                ids=batch_ids
            )
            
            if progress_callback:
                progress = min(100, int((i + len(batch)) / len(paras) * 100))
                progress_callback(f"Progress: {progress}% ({i + len(batch)}/{len(paras)} paragraphs)")
        
        logger.info(f"Successfully indexed {pdf_file} with {len(paras)} paragraphs")
        if progress_callback:
            progress_callback(f"✅ Indexing complete: {os.path.basename(pdf_file)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error indexing document {pdf_file}: {e}")
        if progress_callback:
            progress_callback(f"❌ Error indexing: {str(e)}")
        return False