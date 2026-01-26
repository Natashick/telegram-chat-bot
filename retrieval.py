# retrieval.py
import re
import asyncio
import logging
from typing import List, Dict, Tuple, Optional

from vector_store import vector_store
from acronym_utils import detect_acronym  # einheitliche Logik der Akronyme

logger = logging.getLogger(__name__)

# ------------------ Definition-Filterung (beibehalten) ------------------ #

BAD_DEFN_WORDS = {
    "foreword", "vorwort", "table of contents", "inhalt", "copyright",
    "all rights reserved", "wto", "technical barriers to trade", "patent",
    "feedback", "iec", "beuth", "best beuth",
    "figure", "overview of this document", "general considerations",
    "scope of this", "introduction", "normative references"
}

# ------------------ Normalisierungshelfer ------------------ #

def _normalize_text(s: str) -> str:
    return re.sub(r"[\s\-/]+", "", s or "").casefold()


def _is_short_acronym(term: str) -> bool:
    return bool(re.fullmatch(r"[A-ZÄÖÜ]{2,5}", term or ""))


def _matches_term(term: str, text: str) -> bool:
    if not term or not text:
        return False
    if _is_short_acronym(term):
        pat = re.compile(rf"(?<![A-Za-zÄÖÜäöüß]){re.escape(term)}(?![A-Za-zÄÖÜäöüß])")
        return bool(pat.search(text))
    return _normalize_text(term) in _normalize_text(text)

# ------------------ Definitionsextraktion ------------------ #

def _defn_regex_for(term: str) -> re.Pattern:
    return re.compile(
        rf"\b{re.escape(term)}\b\s*(?:[-–—:]\s*)([^\n]{{5,200}})",
        re.IGNORECASE,
    )


def _extract_standard_title(txt: str) -> Optional[str]:
    if not txt:
        return None
    t = txt.replace("–", "—").replace("-", "—")

    m = re.search(
        r"(Road\s+vehicles\s*—\s*Cybersecurity\s+engineering)",
        t,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)

    m2 = re.search(
        r"([A-Za-z\s]+?\s*—\s*Cybersecurity\s+engineering)",
        t,
        re.IGNORECASE,
    )
    if m2 and "foreword" not in m2.group(1).casefold():
        return m2.group(1)

    return None


def find_definition_in_chunks(term: str, chunks: List[Dict]) -> List[Dict]:
    if not term or not chunks:
        return []

    defn_re = _defn_regex_for(term)
    hits: List[Tuple[Dict, int]] = []
    term_has_digits = any(ch.isdigit() for ch in term)

    for c in chunks:
        txt = (c.get("text", "") or "")
        best_line: Optional[str] = None

        # 1) standardmäßiger Titel (nur wenn Ziffern vorhanden sind)
        if term_has_digits:
            title = _extract_standard_title(txt)
            if title:
                best_line = title.strip()

        # 2) TERM - Definition
        if not best_line:
            m = defn_re.search(txt)
            if m:
                best_line = (m.group(1) or "").strip()

        if not best_line:
            continue

        low = best_line.casefold()
        if any(bad in low for bad in BAD_DEFN_WORDS):
            continue

        if len(best_line) > 220:
            best_line = best_line[:220] + "…"

        length_score = max(0, 160 - len(best_line))
        bonus = 0
        if term_has_digits and (
            "cybersecurity engineering" in low or
            "road vehicles" in low
        ):
            bonus += 60

        sim = int(c.get("similarity_score", 0) * 100)

        slim = dict(c)
        slim["text"] = best_line
        hits.append((slim, sim + length_score + bonus))

    hits.sort(key=lambda t: t[1], reverse=True)
    return [h[0] for h in hits]

# ------------------ Filterung nach Begriffspräsenz ------------------ #

def filter_chunks_by_term(term: str, chunks: List[Dict]) -> List[Dict]:
    if not term or not chunks:
        return []

    tn = _normalize_text(term)
    std_re = re.compile(r"(?i)\b(?:ISO|SAE)[\s\/-]*\d{3,6}\b")
    can_re = re.compile(r"(?i)\bCAN(?:-FD)?\b")
    gen_re = re.compile(r"(?i)\b[A-Z]{2,10}(?:[\/\-]?[A-Z0-9]{1,10})+\b")

    scored = []
    for c in chunks:
        txt = c.get("text", "") or ""
        if tn not in _normalize_text(txt):
            continue

        score = float(c.get("similarity_score", 0.0))
        if std_re.search(txt):
            score += 0.08
        if can_re.search(txt):
            score += 0.05
        if gen_re.search(txt):
            score += 0.03

        scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]

# ------------------ Haupt-Chunk-Auswahl ------------------ #

async def get_best_chunks_for_document(query: str, doc_id: str, max_chunks: int = 4):
    try:
        base = await asyncio.to_thread(
            vector_store.search_in_document,
            query,
            doc_id,
            n_results=max_chunks * 3,
        )
        chunks = base or []
    except Exception as e:
        logger.debug("Error fetching base chunks: %s", e)
        chunks = []

    if not chunks:
        return []

    term = detect_acronym(query)

    # Erweiterung des Fensters nur bei wenigen eindeutigen Ergebnissen (<5)
    try:
        seen0 = set()
        uniq0 = []
        for c in chunks:
            key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
            if key in seen0:
                continue
            seen0.add(key)
            uniq0.append(c)

        if len(uniq0) < 5:
            extra = await asyncio.to_thread(
                vector_store.search_in_document,
                query, doc_id,
                n_results=max_chunks * 10
            )
            if extra:
                chunks.extend(extra)

        # erneute Überprüfung
        seen1 = set()
        uniq1 = []
        for c in chunks:
            key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
            if key in seen1:
                continue
            seen1.add(key)
            uniq1.append(c)

        if len(uniq1) < 5:
            extra = await asyncio.to_thread(
                vector_store.search_in_document,
                query, doc_id,
                n_results=max_chunks * 30
            )
            if extra:
                chunks.extend(extra)

        # erneute Überprüfung
        seen = set()
        uniq = []
        for c in chunks:
            key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)

        chunks = sorted(uniq, key=lambda x: x["similarity_score"], reverse=True)

    except Exception:
        pass

    if term:
        defs = find_definition_in_chunks(term, chunks)
        if defs:
            return defs[:max_chunks]

        hits = filter_chunks_by_term(term, chunks)
        if hits:
            return hits[:max_chunks]

    return chunks[:max_chunks]

# ------------------ globale Chunk-Auswahl ------------------ #

async def get_best_chunks_global(query: str, max_chunks: int = 12) -> List[Dict]:
    try:
        # Initialer Durchgang
        base = await asyncio.to_thread(
            vector_store.search_global,
            query,
            n_results=max_chunks * 6,
        )
        chunks = base or []

        # Progressives Widening für große Korpora
        def _uniq_len(items: List[Dict]) -> int:
            seen = set()
            for c in items:
                key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
                if key not in seen:
                    seen.add(key)
            return len(seen)

        if _uniq_len(chunks) < max_chunks * 3:
            extra1 = await asyncio.to_thread(
                vector_store.search_global,
                query,
                n_results=max(max_chunks * 20, 200),
            )
            if extra1:
                chunks.extend(extra1)

        if _uniq_len(chunks) < max_chunks * 3:
            extra2 = await asyncio.to_thread(
                vector_store.search_global,
                query,
                n_results=max(max_chunks * 40, 400),
            )
            if extra2:
                chunks.extend(extra2)

    except Exception as e:
        logger.debug("Error fetching global chunks: %s", e)
        chunks = []

    if not chunks:
        return []

    # Duplizieren nach chunk_id + führendem Text entfernen
    seen = set()
    uniq: List[Dict] = []
    for c in chunks:
        key = f"{c.get('chunk_id')}|{(c.get('text') or '')[:64]}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(c)

    chunks = sorted(uniq, key=lambda x: x.get("similarity_score", 0.0), reverse=True)

    term = detect_acronym(query)
    if term:
        defs = find_definition_in_chunks(term, chunks)
        if defs:
            return defs[:max_chunks]
        hits = filter_chunks_by_term(term, chunks)
        if hits:
            return hits[:max_chunks]

    return chunks[:max_chunks]

# ------------------ LLM Ausschnitte ------------------ #

def build_combined_excerpts(chunks: List[Dict]) -> str:
    if not chunks:
        return ""

    def _sanitize(t: str) -> str:
        if not t:
            return ""
        lines = []
        for raw in t.splitlines():
            s = raw.strip()
            if not s:
                continue

            # skip "figure/clause/annex/overview", but NOT table/tabelle
            if re.match(r"^(figure|clause|overview|annex)\b", s, re.IGNORECASE):
                continue
            # If this is a table row in Markdown or similar, save it.
            if "|" in s or re.match(r"^(table|tabelle)\b", s, re.IGNORECASE):
                lines.append(s)
                continue
            #
            if (
                re.search(r"\b(ISO|SAE)\b", s, re.IGNORECASE)
                or re.search(r"\b[A-Z]{2,10}\b", s)
                or re.search(r"\d", s)
            ):
                lines.append(s)
                continue

            if re.match(r"^\d+(\.\d+)*\s+[A-Z]", s):
                continue
            if len(s.split()) <= 2:
                continue

            lines.append(s)


        out = []
        seen = set()
        for s in lines:
            key = s.casefold()
            if key not in seen:
                seen.add(key)
                out.append(s)

        text = " ".join(out)
        return text[:800] + "…" if len(text) > 800 else text

    cleaned = [_sanitize(c.get("text", "")) for c in chunks]
    cleaned = [x for x in cleaned if x]

    # Fallback: wenn die Bereinigung alles entfernt hat, verwenden Sie rohe, getrimmte Texte
    if not cleaned:
        raw = []
        for c in chunks[:6]:
            t = (c.get("text") or "").strip()
            if not t:
                continue
            raw.append(t[:600] + ("…" if len(t) > 600 else ""))
        cleaned = raw

    return "\n---\n".join(
        f"EXCERPT {i}:\n{t}" for i, t in enumerate(cleaned, 1)
    )

# ------------------ genaue Zeilen-/Satzfinder ------------------ #

def find_chunk_with_term(term: str, chunks: List[Dict]) -> Optional[str]:
    """
    Gibt ein prägnantes Zitat (einzelne Zeile oder Satz) aus dem ersten Chunk zurück, der
    den Begriff enthält. Verwendet _matches_term für eine robuste Erkennung.
    """
    if not term or not chunks:
        return None
    for c in chunks:
        txt = (c.get("text") or "").strip()
        if not txt:
            continue
        if not _matches_term(term, txt):
            continue
        for line in txt.splitlines():
            s = line.strip()
            if not s:
                continue
            if _matches_term(term, s) and 20 <= len(s) <= 220:
                return s
        parts = re.split(r"(?<=[\.\!\?])\s+", txt)
        for sent in parts:
            s = sent.strip()
            if _matches_term(term, s) and 20 <= len(s) <= 220:
                return s
        return (txt[:220] + "…") if len(txt) > 220 else txt
    return None