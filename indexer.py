# indexer.py
import asyncio
import logging
from typing import List
import os

from pdf_parser import pdf_parser, extract_titles_from_pdf
from vector_store import vector_store

logger = logging.getLogger(__name__)

INDEX_CONCURRENCY = int(os.getenv("INDEX_CONCURRENCY", "1"))
_index_sema = asyncio.Semaphore(INDEX_CONCURRENCY)

# Global preindex bookkeeping (module-level)
preindex_inflight = 0
preindex_total = 0
preindex_done = 0
preindex_running = False

# Simple per-document locks to avoid double-indexing same file concurrently
_doc_locks: dict[str, asyncio.Lock] = {}

def _doc_lock(path: str) -> asyncio.Lock:
    lock = _doc_locks.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _doc_locks[path] = lock
    return lock

def schedule_index(document_name: str):
    """
    Schedule background indexing for a document. Returns immediately.
    """
    global preindex_inflight, preindex_running
    try:
        logger.info("Schedule index task: %s", document_name)
        preindex_inflight += 1
        preindex_running = True
        task = asyncio.create_task(_index_worker(document_name))
        task.add_done_callback(_index_task_done)
    except Exception as e:
        logger.exception("Failed to schedule index for %s: %s", document_name, e)

def _index_task_done(task: asyncio.Task):
    """
    Called when a background index task finishes.
    Decrements inflight counter and increments done counter.
    """
    global preindex_inflight, preindex_done, preindex_running
    try:
        exc = task.exception()
        if exc:
            logger.exception("Index task raised exception: %s", exc)
    except asyncio.CancelledException:
        logger.warning("Index task cancelled")
    except Exception as e:
        logger.exception("Index task inspection failed: %s", e)
    finally:
        try:
            preindex_inflight = max(0, preindex_inflight - 1)
            preindex_done += 1
            logger.info("Index task completed. inflight=%d done=%d", preindex_inflight, preindex_done)
        finally:
            if preindex_inflight == 0:
                preindex_running = False
                logger.info("All preindex tasks finished.")

async def _index_worker(document_name: str):
    async with _index_sema:
        try:
            logger.info("Index worker running for %s", document_name)
            await ensure_document_indexed(document_name)
        except Exception as e:
            logger.exception("Background indexing failed for %s: %s", document_name, e)

def _compute_doc_version(file_path: str) -> str:
    try:
        st = os.stat(file_path)
        return f"{st.st_size}-{int(st.st_mtime)}"
    except Exception:
        return "unknown"

async def ensure_document_indexed(document_name: str):
    """
    Ensure a single document is indexed. Thread-safe per-document.
    Uses pdf_parser to extract paragraphs and vector_store to add chunks.
    """
    async with _doc_lock(document_name):
        try:
            current_version = _compute_doc_version(document_name)
            existing_version = await asyncio.to_thread(vector_store.get_document_version, document_name)
            # If version changed, delete old index
            if existing_version and existing_version != current_version:
                logger.info("Document version changed, deleting previous index for %s", document_name)
                await asyncio.to_thread(vector_store.delete_document, document_name)
                # titles deletion is optional inside vector_store implementation
                try:
                    await asyncio.to_thread(vector_store.delete_titles_for_doc, document_name)
                except Exception:
                    # optional, ignore if not implemented
                    pass

            # If already indexed with same version, skip
            if existing_version == current_version and await asyncio.to_thread(vector_store.has_document, document_name):
                logger.info("Document already indexed (same version): %s", document_name)
                return

            logger.info("Indexing document: %s", document_name)
            paragraphs = await pdf_parser.extract_paragraphs_from_pdf(document_name)
            if not paragraphs:
                logger.warning("No paragraphs extracted for %s", document_name)
                return

            # Index page titles if vector_store supports it and env flag is set
            if os.getenv("ENABLE_TITLE_INDEX", "0") == "1":
                try:
                    titles = await asyncio.to_thread(extract_titles_from_pdf, document_name)
                    if isinstance(titles, list) and titles:
                        try:
                            await asyncio.to_thread(vector_store.delete_titles_for_doc, document_name)
                        except Exception:
                            pass
                        await asyncio.to_thread(vector_store.index_page_titles, document_name, titles)
                except Exception as e:
                    logger.debug("Title indexing skipped/warn: %s", e)

            success = await asyncio.to_thread(
                vector_store.add_chunks,
                document_name,
                paragraphs,
                {"source": document_name, "type": "pdf", "doc_version": current_version},
            )
            if success:
                logger.info("Indexed %s: %d paragraphs", document_name, len(paragraphs))
            else:
                logger.error("Indexing reported failure for %s", document_name)
        except Exception as e:
            logger.exception("Error indexing document %s: %s", document_name, e)

async def preindex_all_pdfs(pdf_paths: List[str]):
    """
    Schedule indexing for a list of pdf paths.
    This function only schedules tasks and returns quickly.
    """
    global preindex_total, preindex_done, preindex_running
    try:
        preindex_total = len(pdf_paths)
        preindex_done = 0
        if preindex_total == 0:
            preindex_running = False
            logger.info("No PDFs to preindex.")
            return
        preindex_running = True
        for p in pdf_paths:
            schedule_index(p)
            await asyncio.sleep(0.05)
        logger.info("All preindex tasks scheduled: %d", preindex_total)
    except Exception as e:
        logger.exception("preindex_all_pdfs error: %s", e)
        preindex_running = False