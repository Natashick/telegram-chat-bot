# vector_store.py
from __future__ import annotations

import os
import gc
import hashlib
import logging
import re
import threading
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from acronym_utils import detect_acronym  # gemeinsame Logik mit retrieval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vector_store")

# Rauschen in Chroma-Telemetrieprotokollen unterdrücken
try:
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.ERROR)
except Exception:
    pass


class VectorStore:
    def __init__(
        self,
        *,
        persist_directory: Optional[str] = None,
                 chunk_size: int = 800,
                 chunk_overlap: int = 160,
        batch_size: int = 4,
    ) -> None:
        # Persistenzort
        self.persist_directory = (
            persist_directory
            if persist_directory
            else os.getenv(
                "CHROMA_DB_DIR",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db"),
            )
        )

        # Chunking / Batching Einstellungen
        self.chunk_size = int(os.getenv("CHUNK_SIZE", str(chunk_size)))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", str(chunk_overlap)))
        self.batch_size = int(os.getenv("BATCH_SIZE", str(batch_size)))
        self.embed_batch_size = int(os.getenv("EMBED_BATCH_SIZE", "16"))
        self._lock = threading.Lock()

        # Chunk-Filter Einstellungen
        self.min_chunk_chars = int(os.getenv("MIN_CHUNK_CHARS", "60"))
        self.min_chunk_words = int(os.getenv("MIN_CHUNK_WORDS", "8"))
        self.disable_chunk_filter = os.getenv("DISABLE_CHUNK_FILTER", "0") == "1"

        # Retrieval-Schwelle (tolerant für kurze Definitionen)
        self.min_sim_threshold = float(os.getenv("MIN_SIM_THRESHOLD", "0.15"))

        # Chroma-Client ohne serverseitige Einbettung (wir übergeben Einbettungen explizit)
        settings = Settings(
            persist_directory=self.persist_directory,
            anonymized_telemetry=False,
            allow_reset=True,
        )
        self.client = chromadb.PersistentClient(
            path=self.persist_directory, settings=settings
        )
        self.collection = self.client.get_or_create_collection(
            name="pdf_chunks",
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        # Optionale Titelsammlung (nur verwendet, wenn über env aktiviert)
        self.titles = self.client.get_or_create_collection(
            name="page_titles",
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

        # Lokaler CPU-Encoder (sentence-transformers)
        model_name = os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        logger.info("Loading embedding model: %s", model_name)
        self.embedder = SentenceTransformer(model_name, device="cpu")

        logger.info(
            "Vector Store ready @ %s | chunk=%s overlap=%s batch=%s embed_bs=%s",
            self.persist_directory,
            self.chunk_size,
            self.chunk_overlap,
            self.batch_size,
            self.embed_batch_size,
        )

    # ---- interne Hilfsfunktionen -------------------------------------------------
    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.detail_encode(texts)

    def detail_encode(self, texts: List[str]) -> List[List[float]]:  # Liefert Embeddings (Vektoren) für die übergebenen Texte
        return (  # Rückgabe als verschachtelte Liste von Floats (Kompatibilität zu Chroma)
            self.embedder.encode(  # sentence-transformers Aufruf mit initialisiertem Modell (CPU)
                texts,  # Liste der zu embedden Texte
                batch_size=self.embed_batch_size,  # Batchgröße: kontrolliert Speicher/Nebenläufigkeit
                convert_to_numpy=True,  # Ergebnis als NumPy-Array (schneller, konsistent)
                normalize_embeddings=True,  # L2-Normalisierung für Cosine-Similarity
                show_progress_bar=False,  # Keine Progress-Bar (saubere Logs/kein Overhead)
            ).tolist()  # NumPy-Array -> Python-Listen für die Übergabe an Chroma
        )

    @staticmethod
    def _hash_path(path: str) -> str:
        try:
            return hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:8]
        except Exception:
            return "doc"

    def _split_text_into_chunks(self, text: str) -> List[str]:
        words = (text or "").split()
        if not words:
            return []
        if len(words) <= self.chunk_size:
            return [" ".join(words)]
        chunks: List[str] = []
        start = 0
        while start < len(words):
            end = min(len(words), start + self.chunk_size)
            chunks.append(" ".join(words[start:end]))
            # slide with overlap but never go backwards
            nxt = end - self.chunk_overlap
            start = end if nxt <= start else nxt
        return [c for c in chunks if c.strip()]

    def _passes_quality(self, chunk: str) -> bool:
        if not chunk:
            return False
        s = " ".join(chunk.split())
        if self.disable_chunk_filter:
            return bool(s.strip())
        # Erlaube kürzere Definitionen (behalte prägnante Glossar-ähnliche Zeilen bei)
        if s.count("|") >= 2:
            return True
        if re.search(fr"\b[A-ZÄÖÜ]{2,10}\b\s*(?:[---:]\s|\()", s, re.IGNORECASE):
            return True
        if len(s) < self.min_chunk_chars:
            return False
        alpha = sum(ch.isalpha() for ch in s)
        return (alpha / max(1, len(s))) >= 0.25

    # ---- public API -------------------------------------------------------

    def add_chunks(
        self, doc_id: str, chunks: List[str], metadata: Optional[Dict] = None
    ) -> bool:
        """Add pre-split chunks using local embeddings (CPU)."""
        if not chunks:
            return True

        meta_base = metadata or {}
        max_chunks = int(os.getenv("MAX_INDEX_CHUNKS", "0")) or 0
        reasons_dropped = {"short": 0, "empty": 0, "other": 0}
        to_use: List[str] = []

        for c in chunks or []:
            if not c or not str(c).strip():
                reasons_dropped["empty"] += 1
                if self.disable_chunk_filter:
                    # selbst wenn deaktiviert, reine Leereinträge überspringen
                    continue
            if self._passes_quality(c):
                to_use.append(c)
            else:
                reasons_dropped["short"] += 1

        dropped = len(chunks or []) - len(to_use)
        if dropped and os.getenv("LOG_CHUNK_FILTER", "0") == "1":
            logger.info(
                "Chunk filter dropped=%s (short=%s, empty=%s)",
                dropped,
                reasons_dropped["short"],
                reasons_dropped["empty"],
            )

        if max_chunks and len(to_use) > max_chunks:
            to_use = to_use[:max_chunks]

        ids = [f"{self._hash_path(doc_id)}_chunk_{i}" for i in range(len(to_use))]
        metadatas: List[Dict] = [
            {
                "doc_id": doc_id,
                "source": doc_id,
                "chunk_id": ids[i],
                "chunk_index": i,
                "total_chunks": len(to_use),
                **meta_base,
            }
            for i in range(len(to_use))
        ]

        # Embed + die Daten fügen in kleinen Mengen unter Kontrolle hinzu, um Speicherspitzen zu vermeiden.
        with self._lock:
            embeddings: List[List[float]] = []
            for i in range(0, len(to_use), self.embed_batch_size):
                batch = to_use[i : i + self.embed_batch_size]
                embeddings.extend(self._embed(batch))

            total_added = 0
            for i in range(0, len(to_use), self.batch_size):
                d = to_use[i : i + self.batch_size]
                m = metadatas[i : i + self.batch_size]
                e = embeddings[i : i + self.batch_size]
                ids_slice = ids[i : i + self.batch_size]
                try:
                    self.collection.add(
                        documents=d,
                        metadatas=m,
                        embeddings=e,
                        ids=ids_slice,
                    )
                    total_added += len(d)
                except Exception as ex:
                    logger.warning("collection.add failed @%s: %s", i, ex)
                finally:
                    try:
                        # touch storage & persist
                        self.collection.count()
                        self.client.persist()
                    except Exception:
                        pass
                    gc.collect()

            logger.info("Added %s chunks for %s", total_added, doc_id)
        return True

    def add_document(
        self, doc_id: str, text: str, metadata: Optional[Dict] = None
    ) -> bool:
        chunks = self._split_text_into_chunks(text or "")
        return self.add_chunks(doc_id, chunks, metadata)

    # --- Abfragehilfen (kompatibel mit alten Handlern) ----------------------
    def has_document(self, doc_id: str) -> bool:
        try:
            res = self.collection.get(where={"source": doc_id}, limit=1)
            return bool(res and res.get("ids"))
        except Exception as e:
            logger.error("has_document error (%s): %s", doc_id, e)
            return False

    def _get_any_metadata_for_doc(self, doc_id: str) -> Optional[Dict]:
        try:
            res = self.collection.get(
                where={"source": doc_id}, limit=1, include=["metadatas"]
            )
            metas = (res or {}).get("metadatas") or []
            return metas[0] if metas else None
        except Exception as e:
            logger.error("_get_any_metadata_for_doc error (%s): %s", doc_id, e)
            return None

    def get_document_version(self, doc_id: str) -> Optional[str]:
        meta = self._get_any_metadata_for_doc(doc_id)
        try:
            return (meta or {}).get("doc_version")
        except Exception:
            return None

    def search_in_document(
        self,
        query: str,
        doc_id: str,
        n_results: int = 5,
        *,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict]:
        """
        Semantische Suche in einem einzelnen Dokument mit Fokus auf Akronyme/Begriffe:
        - Basis Chroma-Suche
        - Boost, wenn ein Begriff gefunden wird und im Chunk vorkommt
        - Bei Vorhandensein eines Begriffs — Neuordnung, um mögliche Definitionen nach vorne zu bringen
        """
        try:
            if not query:
                return []

            q_emb = self._embed([query])[0]

            # Einheitliche Logik: gemeinsame Funktion detect_acronym (aus acronym_utils)
            acr = detect_acronym(query)
            acr_cf = acr.casefold() if acr else None

            # Mehr für die Nachfilterung abrufen
            top_k = max(50, n_results * 6)
            thr = (
                self.min_sim_threshold
                if similarity_threshold is None
                else float(similarity_threshold)
            )

            res = self.collection.query(
                query_embeddings=[q_emb],
                n_results=top_k,
                where={"source": doc_id},
                include=["documents", "metadatas", "distances"],
            )

            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]

            out: List[Dict] = []
            for doc, meta, dist in zip(docs, metas, dists):
                base_sim = 1.0 / (1.0 + float(dist if isinstance(dist, (int, float)) else 0.0))
                sim = base_sim

                # Boost, wenn ein Akronym tatsächlich im Text vorkommt
                if acr_cf and doc:
                    doc_cf = (doc or "").casefold()
                    if acr_cf in doc_cf:
                        sim = min(1.0, base_sim + 0.30)

                if sim >= thr:
                    out.append(
                        {
                            "doc_id": meta.get("source", meta.get("doc_id", "")),
                            "chunk_id": meta.get("chunk_id", ""),
                            "chunk_index": meta.get("chunk_index", 0),
                            "text": doc,
                            "similarity_score": sim,
                            "metadata": meta,
                        }
                    )

            if not out:
                return []

            out.sort(key=lambda x: x["similarity_score"], reverse=True)

            # Zusätzliche Neuordnung nach "Definition zuerst"
            if acr_cf:
                def is_defn(txt: str) -> bool:
                    t = (txt or "").casefold()
                    return (
                        f"{acr_cf} -" in t
                        or f"{acr_cf}:" in t
                        or f"{acr_cf} (" in t
                    )

                preferred = [
                    c for c in out if acr_cf in ((c.get("text") or "").casefold())
                ]
                if preferred:
                    preferred.sort(
                        key=lambda c: (
                            1 if is_defn(c.get("text", "")) else 0,
                            float(c.get("similarity_score", 0.0)),
                        ),
                        reverse=True,
                    )
                    tail = [c for c in out if c not in preferred]
                    out = preferred + tail
                else:
                    # Keine eindeutigen Treffer für das Akronym — erweitern wir das Fenster und versuchen es erneut
                    res2 = self.collection.query(
                        query_embeddings=[q_emb],
                        n_results=max(top_k * 2, 20),
                        where={"source": doc_id},
                        include=["documents", "metadatas", "distances"],
                    )
                    docs2 = res2.get("documents", [[]])[0]
                    metas2 = res2.get("metadatas", [[]])[0]
                    dists2 = res2.get("distances", [[]])[0]
                    out2: List[Dict] = []
                    for doc, meta, dist in zip(docs2, metas2, dists2):
                        base_sim2 = 1.0 / (
                            1.0
                            + float(dist if isinstance(dist, (int, float)) else 0.0)
                        )
                        sim2 = base_sim2
                        if acr_cf and doc:
                            if acr_cf in ((doc or "").casefold()):
                                sim2 = min(1.0, base_sim2 + 0.30)
                        if sim2 >= thr:
                            out2.append(
                                {
                                    "doc_id": meta.get(
                                        "source", meta.get("doc_id", "")
                                    ),
                                    "chunk_id": meta.get("chunk_id", ""),
                                    "chunk_index": meta.get("chunk_index", 0),
                                    "text": doc,
                                    "similarity_score": sim2,
                                    "metadata": meta,
                                }
                            )
                    if out2:
                        out2.sort(
                            key=lambda x: x["similarity_score"], reverse=True
                        )
                        preferred2 = [
                            c
                            for c in out2
                            if acr_cf in ((c.get("text") or "").casefold())
                        ]
                        if preferred2:
                            preferred2.sort(
                                key=lambda c: (
                                    1 if is_defn(c.get("text", "")) else 0,
                                    float(c.get("similarity_score", 0.0)),
                                ),
                                reverse=True,
                            )
                            tail2 = [c for c in out2 if c not in preferred2]
                            out = preferred2 + tail2
                        else:
                            out = out2

            return out[:n_results]
        except Exception as e:
            logger.error("search_in_document error (%s): %s", doc_id, e)
            return []

    def search_global(  # Globale semantische Suche über alle Dokumente
        self,
        query: str,                        # Freitext‑Suchanfrage
        n_results: int = 5,                # gewünschte Anzahl Top‑Ergebnisse
        *,
        similarity_threshold: Optional[float] = None,  # optionale Mindestähnlichkeit
    ) -> List[Dict]:
        """
        Globale semantische Suche über alle Dokumente mit akronymbewusstem Boosting.
        Gibt eine Liste von Dicts zurück, ähnlich wie search_in_document.
        """
        try:
            if not query:                  # wenn es eine Leere Anfrage gibt dann keine Resultate
                return []

            q_emb = self._embed([query])[0]     # Embedding der Anfrage erzeugen
            acr = detect_acronym(query)         # Akronym erkennen (z. B. "TARA", "CAN, "CAL")
            acr_cf = acr.casefold() if acr else None  # casefolded Vergleichsform

            top_k = max(50, n_results * 6)      # Erst großzügig viele Kandidaten holen
            thr = (                              # Schwellwert für Ähnlichkeit bestimmen
                self.min_sim_threshold
                if similarity_threshold is None
                else float(similarity_threshold)
            )

            res = self.collection.query(         # Chroma: Vektorabfrage
                query_embeddings=[q_emb],        # Anfrage‑Embedding
                n_results=top_k,                 # Anzahl roher Kandidaten
                include=["documents", "metadatas", "distances"],  # Texte, Metadaten, Distanzen
            )

            docs = res.get("documents", [[]])[0]   # Top‑Dokumenttexte
            metas = res.get("metadatas", [[]])[0]  # Metadaten je Chunk
            dists = res.get("distances", [[]])[0]  # Distanzwerte

            out: List[Dict] = []  # gesammelte, gefilterte Ergebnisse
            for doc, meta, dist in zip(docs, metas, dists):
                base_sim = 1.0 / (1.0 + float(dist if isinstance(dist, (int, float)) else 0.0))  # Distanz→Ähnlichkeit
                sim = base_sim  # Startwert
                if acr_cf and doc:  # Akronym‑Boost, falls Akronym im Chunktext auftaucht
                    if acr_cf in ((doc or "").casefold()):
                        sim = min(1.0, base_sim + 0.30)  # Bonus, gedeckelt bei 1.0
                if sim >= thr:  # nur ausreichend ähnliche behalten
                    out.append(
                        {
                            "doc_id": meta.get("source", meta.get("doc_id", "")),  # Dokumentkennung
                            "chunk_id": meta.get("chunk_id", ""),                  # Chunk‑ID
                            "chunk_index": meta.get("chunk_index", 0),             # Position im Dokument
                            "text": doc,                                           # gefundener Text
                            "similarity_score": sim,                                # berechnete Ähnlichkeit
                            "metadata": meta,                                       # weitere Metadaten
                        }
                    )

            if not out:  # keine Treffer nach Filter
                return []

            out.sort(key=lambda x: x["similarity_score"], reverse=True)

            if acr_cf:
                def is_defn(txt: str) -> bool:
                    t = (txt or "").casefold()
                    return (
                        f"{acr_cf} -" in t
                        or f"{acr_cf}:" in t
                        or f"{acr_cf} (" in t
                    )

                preferred = [c for c in out if acr_cf in ((c.get("text") or "").casefold())]
                if preferred:
                    preferred.sort(
                        key=lambda c: (
                            1 if is_defn(c.get("text", "")) else 0,
                            float(c.get("similarity_score", 0.0)),
                        ),
                        reverse=True,
                    )
                    tail = [c for c in out if c not in preferred]
                    out = preferred + tail
                else:
                    # widen if nothing contains acronym explicitly
                    res2 = self.collection.query(
                        query_embeddings=[q_emb],
                        n_results=max(top_k * 2, 20),
                        include=["documents", "metadatas", "distances"],
                    )
                    docs2 = res2.get("documents", [[]])[0]
                    metas2 = res2.get("metadatas", [[]])[0]
                    dists2 = res2.get("distances", [[]])[0]
                    out2: List[Dict] = []
                    for doc, meta, dist in zip(docs2, metas2, dists2):
                        base_sim2 = 1.0 / (1.0 + float(dist if isinstance(dist, (int, float)) else 0.0))
                        sim2 = base_sim2
                        if acr_cf and doc and acr_cf in ((doc or "").casefold()):
                            sim2 = min(1.0, base_sim2 + 0.30)
                        if sim2 >= thr:
                            out2.append(
                                {
                                    "doc_id": meta.get("source", meta.get("doc_id", "")),
                                    "chunk_id": meta.get("chunk_id", ""),
                                    "chunk_index": meta.get("chunk_index", 0),
                                    "text": doc,
                                    "similarity_score": sim2,
                                    "metadata": meta,
                                }
                            )
                    if out2:
                        out2.sort(key=lambda x: x["similarity_score"], reverse=True)
                        preferred2 = [c for c in out2 if acr_cf in ((c.get("text") or "").casefold())]
                        if preferred2:
                            preferred2.sort(
                                key=lambda c: (
                                    1 if is_defn(c.get("text", "")) else 0,
                                    float(c.get("similarity_score", 0.0)),
                                ),
                                reverse=True,
                            )
                            tail2 = [c for c in out2 if c not in preferred2]
                            out = preferred2 + tail2
                        else:
                            out = out2

            return out[:n_results]
        except Exception as e:
            logger.error("search_global error: %s", e)
            return []
    def get_combined_context_for_document(
        self, query: str, doc_id: str, max_chunks: int = 4
    ) -> Tuple[str, List[Dict]]:
        """
        Kompatibilität mit altem Code:
        Gibt (Kontexttext, Chunks-Liste) zurück.
        Aktuell erfolgt der Abruf direkt über search_in_document,
        aber das soll so bleiben.
        """
        chunks = self.search_in_document(query, doc_id, n_results=max_chunks)
        if not chunks:
            return ("Keine relevanten Informationen gefunden.", [])

        context = "\n\n".join(
            f"--- CHUNK ---\n{c['text']}\n--- END ---" for c in chunks
        )
        return (context, chunks)

    def query(self, question: str, top_k: int = 5) -> Tuple[List[str], List[Dict]]:
        """Globale semantische Suche über alle Dokumente."""
        if not question:
            return ([], [])
        q_emb = self._embed([question])[0]
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        return (docs, metas)

    def get_document_info(self) -> Dict:
        try:
            return {
                "total_chunks": self.collection.count(),
                "persist_directory": self.persist_directory,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "batch_size": self.batch_size,
            }
        except Exception as e:
            logger.error("get_document_info error: %s", e)
            return {}

    def delete_document(self, doc_id: str) -> bool:
        try:
            self.collection.delete(where={"source": doc_id})
            logger.info("Deleted document: %s", doc_id)
            return True
        except Exception as e:
            logger.error("delete_document error (%s): %s", doc_id, e)
            return False

    def clear_all(self) -> bool:
        try:
            self.client.reset()
            logger.info("Vector store cleared")
            return True
        except Exception as e:
            logger.error("clear_all error: %s", e)
            return False

    # ---- Titel-Hilfen (optional) ----------------------------------------
    def delete_titles_for_doc(self, doc_id: str) -> bool:
        try:
            self.titles.delete(where={"source": doc_id})
            return True
        except Exception:
            return False

    def index_page_titles(self, doc_id: str, titles: List[Dict]) -> int:
        if os.getenv("ENABLE_TITLE_INDEX", "0") != "1":
            return 0
        if not titles:
            return 0
        texts: List[str] = []
        metas: List[Dict] = []
        ids: List[str] = []

        for i, t in enumerate(titles):
            title_text = (t.get("title") or "").strip()
            if not title_text:
                continue
            page = int(t.get("page", 0))
            t_type = t.get("type", "title")
            uid = f"{self._hash_path(doc_id)}_title_{page}_{i}"
            texts.append(title_text)
            metas.append(
                {
                    "source": doc_id,
                    "page": page,
                    "type": t_type,
                    "title": title_text,
                }
            )
            ids.append(uid)

        if not texts:
            return 0

        embs = self._embed(texts)
        added = 0
        with self._lock:
            try:
                self.titles.add(
                    documents=texts, metadatas=metas, ids=ids, embeddings=embs
                )
                added = len(texts)
                self.client.persist()
            except Exception as e:
                logger.warning("titles add failed: %s", e)
        return added

    def search_titles(self, query: str, n_results: int = 5) -> List[Dict]:
        if os.getenv("ENABLE_TITLE_INDEX", "0") != "1":
            return []
        if not query:
            return []
        try:
            q_emb = self._embed([query])[0]
            res = self.titles.query(
                query_embeddings=[q_emb],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            out: List[Dict] = []
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, dists):
                sim = 1.0 / (
                    1.0 + float(dist if isinstance(dist, (int, float)) else 0.0)
                )
                out.append(
                    {
                        "doc_id": meta.get("source", ""),
                        "page": meta.get("page", 1),
                        "type": meta.get("type", "title"),
                        "title": meta.get("title", doc),
                        "similarity_score": sim,
                    }
                )
            out.sort(key=lambda x: x["similarity_score"], reverse=True)
            return out
        except Exception as e:
            logger.error("search_titles error: %s", e)
            return []

    # kleine Hilfestellung für das Logging
    def indicator(self) -> str:
        return self.persist_directory


# Globale Instanz
vector_store = VectorStore()
