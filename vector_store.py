# vector_store.py
import chromadb
from chromadb.config import Settings
import os
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
import requests
import threading

# Limit parallel embedding HTTP calls to reduce load
EMBED_CONCURRENCY = int(os.getenv("EMBED_CONCURRENCY", "1"))
_embed_sema = threading.Semaphore(EMBED_CONCURRENCY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self,
                 persist_directory: str = None,
                 chunk_size: int = 800,
                 chunk_overlap: int = 160,
                 batch_size: int = 4):
        if persist_directory is None:
            env_dir = os.getenv("CHROMA_DB_DIR")
            if env_dir:
                self.persist_directory = env_dir
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                self.persist_directory = os.path.join(script_dir, "chroma_db")
        else:
            self.persist_directory = persist_directory
        # allow tuning via environment variables to control memory/CPU pressure
        try:
            self.chunk_size = int(os.getenv("CHUNK_SIZE", str(chunk_size)))
        except Exception:
            self.chunk_size = chunk_size
        try:
            self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", str(chunk_overlap)))
        except Exception:
            self.chunk_overlap = chunk_overlap
        try:
            self.batch_size = int(os.getenv("BATCH_SIZE", str(batch_size)))
        except Exception:
            self.batch_size = batch_size
        self.seen_hashes = set()

        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    persist_directory=self.persist_directory,
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            ollama_embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

            class OllamaEmbeddingFunction:
                def __init__(self, base_url: str, model: str):
                    self.base_url = base_url.rstrip("/")
                    self.model = model
                    self.session = requests.Session()

                def __call__(self, input: List[str]) -> List[List[float]]:
                    texts = input or []
                    if not texts:
                        return []
                    embeddings: List[List[float]] = []

                    def _is_valid_embedding_list(e: List[List[float]]) -> bool:
                        return (
                            isinstance(e, list)
                            and len(e) == len(texts)
                            and all(isinstance(v, list) and len(v) > 0 for v in e)
                        )

                    # 1) Попытка батча с "input" (некоторые версии API поддерживают)
                    try:
                        if len(texts) > 1:
                            with _embed_sema:
                                resp = self.session.post(
                                    f"{self.base_url}/api/embeddings",
                                    json={"model": self.model, "input": texts},
                                    timeout=60
                                )
                            resp.raise_for_status()
                            data = resp.json()
                            if isinstance(data, dict):
                                if data.get("embeddings") and _is_valid_embedding_list(data["embeddings"]):
                                    return data["embeddings"]
                                if data.get("data"):
                                    tmp = [item.get("embedding") for item in data.get("data", [])]
                                    if _is_valid_embedding_list(tmp):
                                        return tmp
                    except Exception:
                        # игнорируем и переходим к поштучным вызовам
                        pass

                    # 2) Поштучный фоллбек: сначала пробуем с "input", если пусто/невалидно → с "prompt"
                    for text in texts:
                        emb: Optional[List[float]] = None

                        # 2a) per-item с input
                        try:
                            with _embed_sema:
                                r1 = self.session.post(
                                    f"{self.base_url}/api/embeddings",
                                    json={"model": self.model, "input": text},
                                    timeout=60
                                )
                            r1.raise_for_status()
                            d1 = r1.json()
                            if isinstance(d1, dict):
                                emb = d1.get("embedding")
                                if not emb and d1.get("data"):
                                    emb = (d1.get("data", [{}])[0] or {}).get("embedding")
                                if not emb and d1.get("embeddings"):
                                    emb = (d1.get("embeddings") or [None])[0]
                        except Exception:
                            emb = None

                        # 2b) если пусто/нет валидного — per-item с prompt (совместимо с текущей Ollama)
                        if not isinstance(emb, list) or len(emb) == 0:
                            try:
                                with _embed_sema:
                                    r2 = self.session.post(
                                        f"{self.base_url}/api/embeddings",
                                        json={"model": self.model, "prompt": text},
                                        timeout=60
                                    )
                                r2.raise_for_status()
                                d2 = r2.json()
                                if isinstance(d2, dict):
                                    emb = d2.get("embedding")
                            except Exception:
                                emb = None

                        if not isinstance(emb, list) or len(emb) == 0:
                            raise ValueError("Invalid embedding response (empty)")
                        embeddings.append(emb)

                    return embeddings

                def __del__(self):
                    try:
                        self.session.close()
                    except Exception:
                        pass

            embedding_fn = OllamaEmbeddingFunction(ollama_url, ollama_embed_model)

            self.collection = self.client.get_or_create_collection(
                name="pdf_chunks",
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_fn
            )
            self.titles = self.client.get_or_create_collection(
                name="page_titles",
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_fn
            )
            logger.info(f"Vector Store init @ {self.persist_directory} | chunk={self.chunk_size} overlap={self.chunk_overlap} batch={self.batch_size}")
        except Exception as e:
            logger.error(f"Init-Fehler Vector Store: {e}")
            raise

    def _get_any_metadata_for_doc(self, doc_id: str) -> Optional[Dict]:
        try:
            result = self.collection.get(where={"doc_id": doc_id}, limit=1, include=["metadatas"])
            metas = (result or {}).get("metadatas") or []
            if metas and metas[0]:
                return metas[0]
            return None
        except Exception as e:
            logger.error(f"_get_any_metadata_for_doc Fehler ({doc_id}): {e}")
            return None

    def get_document_version(self, doc_id: str) -> Optional[str]:
        """Gibt die gespeicherte doc_version (falls vorhanden) zurück."""
        meta = self._get_any_metadata_for_doc(doc_id)
        try:
            return (meta or {}).get("doc_version")
        except Exception:
            return None

    def _split_text_into_chunks(self, text: str) -> List[str]:
        words = text.split()
        if len(words) <= self.chunk_size:
            return [text]
        chunks, start = [], 0
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start = end - self.chunk_overlap
            if start >= len(words):
                break
        return chunks

    def _calculate_chunk_hash(self, chunk: str) -> str:
        return hashlib.sha1(chunk.encode('utf-8')).hexdigest()

    def _generate_unique_id(self, doc_id: str, chunk_index: int) -> str:
        try:
            full_path = os.path.abspath(doc_id)
            path_hash = hashlib.sha1(full_path.encode()).hexdigest()[:8]
            return f"{path_hash}_chunk_{chunk_index}"
        except Exception:
            return f"{doc_id}_chunk_{chunk_index}"

    def _passes_quality_check(self, chunk: str) -> bool:
        if not chunk or not chunk.strip():
            return False
        s = chunk.strip()
        if len(s) < 100:
            return False
        words = s.split()
        if len(words) < 10:
            return False
        alpha = sum(c.isalpha() for c in s)
        if alpha / max(1, len(s)) < 0.3:
            return False
        return True

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict] = None) -> bool:
        try:
            chunks = self._split_text_into_chunks(text)
            total_added = 0
            # собираем батчи меньшего размера и добавляем
            for i in range(0, len(chunks), self.batch_size):
                batch_chunks = chunks[i:i + self.batch_size]
                doc_batch, meta_batch, id_batch = [], [], []
                for j, chunk in enumerate(batch_chunks):
                    if not self._passes_quality_check(chunk):
                        continue
                    chunk_hash = self._calculate_chunk_hash(chunk)
                    if chunk_hash in self.seen_hashes:
                        continue
                    uid = self._generate_unique_id(doc_id, i + j)
                    doc_batch.append(chunk)
                    meta_batch.append({
                        "doc_id": doc_id,
                        "chunk_id": uid,
                        "chunk_index": i + j,
                        "total_chunks": len(chunks),
                        "chunk_hash": chunk_hash,
                        **(metadata or {})
                    })
                    id_batch.append(uid)
                    self.seen_hashes.add(chunk_hash)
                if doc_batch:
                    # call may be blocking (embedding fn will call Ollama) - this method is usually called from thread
                    self._add_batch(doc_batch, meta_batch, id_batch)
                    total_added += len(doc_batch)
            logger.info(f"{doc_id}: {total_added} Chunks hinzugefügt")
            return total_added > 0
        except Exception as e:
            logger.error(f"add_document Fehler: {e}")
            return False

    def _add_batch(self, docs: List[str], metas: List[Dict], ids: List[str]) -> None:
        self.collection.add(
            documents=docs,
            metadatas=metas,
            ids=ids
        )

    def has_document(self, doc_id: str) -> bool:
        try:
            result = self.collection.get(where={"doc_id": doc_id}, limit=1, include=["metadatas"])
            return bool(result and result.get("ids"))
        except Exception as e:
            logger.error(f"has_document Fehler ({doc_id}): {e}")
            return False

    def search_in_document(self, query: str, doc_id: str, n_results: int = 5, similarity_threshold: float = 0.15) -> List[Dict]:
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results * 2,
                where={"doc_id": doc_id},
                include=["metadatas", "distances", "documents"]
            )
            filtered = []
            for metadata, distance, document in zip(
                results.get('metadatas', [[]])[0],
                results.get('distances', [[]])[0],
                results.get('documents', [[]])[0]
            ):
                similarity = 1.0 / (1.0 + distance)
                if similarity >= similarity_threshold:
                    filtered.append({
                        "doc_id": metadata.get("doc_id", ""),
                        "chunk_id": metadata.get("chunk_id", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "text": document,
                        "similarity_score": similarity,
                        "metadata": metadata
                    })
            filtered.sort(key=lambda x: x["similarity_score"], reverse=True)
            return filtered[:n_results]
        except Exception as e:
            logger.error(f"Dokument-Suche Fehler ({doc_id}): {e}")
            return []

    def get_combined_context_for_document(self, query: str, doc_id: str, max_chunks: int = 4) -> Tuple[str, List[Dict]]:
        chunks = self.search_in_document(query, doc_id, n_results=max_chunks)
        if not chunks:
            return "Keine relevanten Informationen gefunden.", []
        context = "\n\n".join(
            f"--- CHUNK_START (Score: {c['similarity_score']:.3f}) ---\n{c['text']}\n--- CHUNK_END ---"
            for c in chunks
        )
        return context, chunks

    def get_document_info(self) -> Dict:
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "persist_directory": self.persist_directory,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "batch_size": self.batch_size,
                "unique_hashes": len(self.seen_hashes)
            }
        except Exception as e:
            logger.error(f"get_document_info Fehler: {e}")
            return {}

    def clear_all(self) -> bool:
        try:
            self.client.reset()
            self.seen_hashes.clear()
            logger.info("Vector Store geleert")
            return True
        except Exception as e:
            logger.error(f"clear_all Fehler: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """Löscht alle Chunks eines Dokuments anhand doc_id."""
        try:
            self.collection.delete(where={"doc_id": doc_id})
            logger.info(f"Dokument gelöscht: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"delete_document Fehler ({doc_id}): {e}")
            return False
    def delete_titles_for_doc(self, doc_id: str) -> bool:
        """Löscht alle Titel/Überschriften-Einträge für ein Dokument."""
        try:
            self.titles.delete(where={"doc_id": doc_id})
            return True
        except Exception as e:
            logger.error(f"delete_titles_for_doc Fehler ({doc_id}): {e}")
            return False

    # --- Titles indexing/search (leichtgewichtiger Index) ---
    def index_page_titles(self, doc_id: str, titles: List[Dict]) -> int:
        """titles: List[{ 'title': str, 'page': int, 'type': str }]"""
        try:
            # hard guard by env to prevent accidental indexing
            if os.getenv("ENABLE_TITLE_INDEX", "0") != "1":
                return 0
            docs, metas, ids = [], [], []
            for i, t in enumerate(titles):
                title_text = (t.get("title") or "").strip()
                page_num = int(t.get("page", 0))
                t_type = (t.get("type") or "title")
                if not title_text:
                    continue
                uid = self._generate_unique_id(doc_id, page_num) + f"_title_{i}"
                docs.append(title_text)
                metas.append({"doc_id": doc_id, "page": page_num, "type": t_type, "title": title_text})
                ids.append(uid)
            if not docs:
                return 0
            # skip ids that already exist in titles collection
            existing_ids = set()
            try:
                res = self.titles.get(ids=ids, include=["ids"])
                if res and res.get("ids"):
                    existing_ids = set(res.get("ids"))
            except Exception:
                existing_ids = set()
            to_add_docs, to_add_metas, to_add_ids = [], [], []
            for d, m, i in zip(docs, metas, ids):
                if i in existing_ids:
                    continue
                to_add_docs.append(d)
                to_add_metas.append(m)
                to_add_ids.append(i)
            if not to_add_ids:
                return 0
            # chunked add to reduce memory/CPU spikes
            chunk = int(os.getenv("TITLE_BATCH_SIZE", "32"))
            if chunk <= 0:
                chunk = 32
            total = 0
            for i in range(0, len(to_add_docs), chunk):
                j = i + chunk
                self.titles.add(
                    documents=to_add_docs[i:j],
                    metadatas=to_add_metas[i:j],
                    ids=to_add_ids[i:j]
                )
                total += (j - i)
            return total
        except Exception as e:
            logger.error(f"index_page_titles Fehler ({doc_id}): {e}")
            return 0

    def search_titles(self, query: str, n_results: int = 5) -> List[Dict]:
        try:
            results = self.titles.query(
                query_texts=[query],
                n_results=n_results,
                include=["metadatas", "distances", "documents"]
            )
            out = []
            for metadata, distance, document in zip(
                results.get('metadatas', [[]])[0],
                results.get('distances', [[]])[0],
                results.get('documents', [[]])[0]
            ):
                similarity = 1.0 / (1.0 + distance)
                out.append({
                    "doc_id": metadata.get("doc_id", ""),
                    "page": metadata.get("page", 1),
                    "type": metadata.get("type", "title"),
                    "title": metadata.get("title", document),
                    "similarity_score": similarity
                })
            out.sort(key=lambda x: x["similarity_score"], reverse=True)
            return out[:n_results]
        except Exception as e:
            logger.error(f"search_titles Fehler: {e}")
            return []

# Globale Instanz
vector_store = VectorStore()