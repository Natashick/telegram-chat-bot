# pdf_parser.py
import PyPDF2                 # Primär: Text-Extraktion und Seitenzugriff aus PDFs (ohne OCR)
import pdfplumber             # Zusätzlich: robuste Tabellen- und Text-Extraktion für komplexe Layouts
import pdf2image              # Rendert PDF-Seiten als Bilder (für OCR & Screenshots)
import pytesseract            # OCR: extrahiert Text aus gerenderten Bildern (Pipeline vorbereitet)
import re
import logging
import asyncio
from typing import List, Optional, Dict, Tuple
from PIL import Image         # Bildverarbeitung (Resize, Grayscale, OCR-Vorbereitung)
import os
import io
import unicodedata            # Text-Normalisierung
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OCR_ENABLED = int(os.getenv("OCR_ENABLED", "0"))  # 0 = off, 1 = on
_OCR_CONCURRENCY = int(os.getenv("OCR_CONCURRENCY", "1"))
_sema = asyncio.Semaphore(_OCR_CONCURRENCY)

# Heuristiken zur Verkürzung der Definitionszeilen (z. B. „TARA – Bedrohungsanalyse und Risikobewertung“)
DEFN_RE = re.compile(r"\b([A-ZÄÖÜ]{2,10})\b\s*(?:[-–—:]\s*|\()", re.IGNORECASE)
# ============================================================================
# TEXT NORMALIZATION & PREPROCESSING
# ============================================================================

class TextNormalizer:
    """Robuste Normalisierung für saubere Absätze: Zeilenumbrüche, Silbentrennung, Unicode."""
    
    @staticmethod
    def normalize_text(raw_text: str) -> str:
        """
        Normalisiert PDF-Text durch mehrere Passes:
        1. Unicode-Normalisierung (Sonderzeichen)
        2. Zeilenumbruch-Behandlung (Silbentrennung, Absätze)
        3. Whitespace-Bereinigung
        4. Ligatur-Ersetzung
        """
        if not raw_text:
            return ""
        
        text = str(raw_text)
        
        # 1) Unicode NFD-Normalisierung (z.B. é → e + Akzent kombiniert)
        text = unicodedata.normalize("NFKC", text)
        
        # 2) Zeilenumbruchbehandlung
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # 2a) Silbentrennung über Zeilenumbrüche:
        # "threat-\nanalysis" → "threatanalysis"
        # "confi-\ndential" → "confidential"
        text = re.sub(
            r"([A-Za-zÄÖÜäöüß0-9])-\n+([A-Za-zÄÖÜäöüß0-9])",
            r"\1\2",
            text
        )
        
        # 2b) Einfache Zeilenumbrüche in Leerzeichen umwandeln
        # (aber Absatzumbrüche \n\n → \n beibehalten)
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
        
        # 2c) Mehrfache Absatzumbrüche auf max. 2 reduzieren
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # 3) Ligatur-Ersetzung (ﬁ→fi, ﬂ→fl, etc.)
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = text.replace("ﬀ", "ff").replace("ﬂ", "fl")
        text = text.replace("ﬃ", "ffi").replace("ﬄ", "ffl")
        
        # 4) Whitespace-Bereinigung
        # Mehrfache Leerzeichen → einfaches Leerzeichen
        text = re.sub(r"[ \t]{2,}", " ", text)
        
        # Leerzeichen vor Satzzeichen entfernen
        text = re.sub(r"\s+([.,:;!?])", r"\1", text)
        
        # 5) Führende/abschließende Whitespaces trimmen
        text = text.strip()
        
        return text
    
    @staticmethod
    def split_into_paragraphs(text: str) -> List[str]:
        """
        Teilt normalisierten Text in saubere Absätze auf.
        Respektiert Absatzumbrüche (\n\n) und entfernt leere Zeilen.
        """
        if not text:
            return []
        
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r"\n\s*\n", text)
        
        # Clean each paragraph
        result = []
        for para in paragraphs:
            cleaned = para.strip()
            if cleaned:
                # Restore single newlines within paragraph (for structured text)
                cleaned = re.sub(r"\n+", " ", cleaned)
                result.append(cleaned)
        
        return result


# ============================================================================
# ROBUST PDF EXTRACTION WITH pdfplumber FALLBACK
# ============================================================================
class OptimizedPDFParser:
    def __init__(self):
        self.default_dpi = 180
        self.fallback_dpi = 240
        # Ermöglicht das Überschreiben zum Beibehalten kurzer Glossar-ähnlicher Zeilen (0 zum Deaktivieren des Längenfilters)
        self.min_text_length = int(os.getenv("MIN_PARA_CHARS", "30"))
        self.noise_max_ratio = float(os.getenv("OCR_NOISE_MAX_RATIO", "0.7"))
        self.primary_psm = 6
        self.fallback_psm = 3
        self.languages = ['eng', 'deu']
        self.max_width = 2000
        self.normalizer = TextNormalizer()
        logger.info(
            f"[PDFParser] dpi={self.default_dpi}/{self.fallback_dpi}, "
            f"min_len={self.min_text_length}, psm={self.primary_psm}->{self.fallback_psm}, "
            f"lang={'/'.join(self.languages)}, concurrency={_OCR_CONCURRENCY}, OCR_ENABLED={OCR_ENABLED}"
        )

    async def extract_paragraphs_from_pdf(self, pdf_path: str) -> List[str]:
        """Route by OCR_ENABLED: 0 = simple (PyPDF2+pdfplumber), 1 = OCR pipeline."""
        if not OCR_ENABLED:
            return await self._extract_text_only(pdf_path)
        return await self._extract_with_ocr(pdf_path)

    async def _extract_text_only(self, pdf_path: str) -> List[str]:
        """Lightweight path: extract text using PyPDF2 + pdfplumber fallback (no OCR)."""
        try:
            logger.info(f"Starte PDF-Verarbeitung (Text-only, PyPDF2+pdfplumber): {pdf_path}")
            paragraphs: List[str] = []
            
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                logger.info(f"PDF hat {total_pages} Seiten")
                
                for i in range(total_pages):
                    try:
                        page = reader.pages[i]
                        
                        # Primär: PyPDF2
                        raw_text = page.extract_text() or ""
                        
                        # Fallback: pdfplumber für komplexere Layouts
                        if not self._is_text_sufficient(raw_text):
                            logger.debug(f"PyPDF2 Seite {i+1} unzureichend, versuche pdfplumber...")
                            raw_text = await self._extract_with_pdfplumber(pdf_path, i)
                        
                        if not raw_text:
                            continue
                        
                        # Normalisiere Text
                        normalized = self.normalizer.normalize_text(raw_text)
                        
                        # Teile in Absätze und filtere
                        for para in self.normalizer.split_into_paragraphs(normalized):
                            if self._is_usable_para(para):
                                paragraphs.append(para)
                    
                    except Exception as e:
                        logger.debug(f"Fehler Seite {i+1}: {e}")
                        continue
            
            logger.info(f"Erfolgreich {len(paragraphs)} Absätze extrahiert (Text-only)")
            return paragraphs
        
        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung (Text-only): {e}")
            return []

    async def _extract_with_pdfplumber(self, pdf_path: str, page_num: int) -> str:
        """pdfplumber für robuste Extraktion aus komplexen Layouts."""
        try:
            text = await asyncio.to_thread(
                self._pdfplumber_extract,
                pdf_path,
                page_num
            )
            return text or ""
        except Exception as e:
            logger.debug(f"pdfplumber Seite {page_num+1} Fehler: {e}")
            return ""
    
    def _pdfplumber_extract(self, pdf_path: str, page_num: int) -> str:
        """Synchrone pdfplumber-Extraktion (in Thread aufgerufen)."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num >= len(pdf.pages):
                    return ""
                page = pdf.pages[page_num]
                
                # 1) Reiner Text
                text = page.extract_text() or ""
                
                # 2) Tabellen aus dieser Seite (falls vorhanden)
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                row_text = " | ".join([str(cell or "") for cell in row])
                                text += "\n" + row_text
                except Exception:
                    pass
                
                return text.strip()
        except Exception as e:
            logger.debug(f"_pdfplumber_extract Fehler: {e}")
            return ""

    async def _extract_with_ocr(self, pdf_path: str) -> List[str]:
        """
        OCR Pipeline: mit Fallback-Strategie und Normalisierung.
        1. Versuche PyPDF2 + pdfplumber
        2. Falls unzureichend: OCR mit light/fallback DPI
        3. Normalisiere alle Ergebnisse
        """
        try:
            logger.info(f"Starte PDF-Verarbeitung (OCR-Pipeline): {pdf_path}")
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                logger.info(f"PDF hat {total_pages} Seiten, OCR-Pipeline aktiv")

                paragraphs: List[str] = []
                page_batch_size = max(1, _OCR_CONCURRENCY * 2)
                
                for start in range(0, total_pages, page_batch_size):
                    batch_pages = list(range(start, min(start + page_batch_size, total_pages)))
                    tasks = [
                        self._process_page_async_ocr(pdf_path, p, total_pages, reader)
                        for p in batch_pages
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for i, res in enumerate(results):
                        if isinstance(res, Exception):
                            logger.error(f"Fehler bei Seite {batch_pages[i]+1}: {res}")
                            continue
                        if res and isinstance(res, str) and res.strip():
                            # Normalisiere extrahierten Text
                            normalized = self.normalizer.normalize_text(res.strip())
                            if normalized:
                                for para in self.normalizer.split_into_paragraphs(normalized):
                                    if self._is_usable_para(para):
                                        paragraphs.append(para)
                
                logger.info(f"Erfolgreich {len(paragraphs)} Absätze extrahiert (OCR-Pipeline)")
                return paragraphs
        
        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung (OCR): {e}")
            return []

    async def _process_page_async_ocr(
        self,
        pdf_path: str,
        page_num: int,
        total_pages: int,
        reader: PyPDF2.PdfReader
    ) -> Optional[str]:
        """
        OCR-Verarbeitungspipeline pro Seite mit Fallbacks:
        1. PyPDF2 direkt
        2. pdfplumber (für komplexe Layouts)
        3. OCR mit standard DPI
        4. OCR mit höherer DPI (Fallback)
        """
        async with _sema:
            try:
                logger.debug(f"Verarbeite Seite {page_num + 1}/{total_pages} (OCR-Pipeline)")
                
                # 1) PyPDF2 direkt
                page_text = self._extract_text_normal_from_reader(reader, page_num)
                if self._is_text_sufficient(page_text):
                    logger.debug(f"Seite {page_num+1}: PyPDF2 ausreichend")
                    return page_text

                # 2) pdfplumber als zweiter Versuch
                plumber_text = await self._extract_with_pdfplumber(pdf_path, page_num)
                if self._is_text_sufficient(plumber_text):
                    logger.debug(f"Seite {page_num+1}: pdfplumber ausreichend")
                    return plumber_text

                # 3) OCR leicht: Standard DPI + PSM
                logger.debug(f"Seite {page_num+1}: starte OCR (leicht)...")
                ocr_light = await self._extract_text_ocr(
                    pdf_path, page_num,
                    dpi=self.default_dpi,
                    psm=self.primary_psm
                )
                if self._is_text_sufficient(ocr_light):
                    logger.debug(f"Seite {page_num+1}: OCR (leicht) ausreichend")
                    return ocr_light

                # 4) OCR Fallback: höhere DPI + anderer PSM
                logger.debug(f"Seite {page_num+1}: starte OCR (Fallback mit höherer DPI)...")
                ocr_fallback = await self._extract_text_ocr(
                    pdf_path, page_num,
                    dpi=self.fallback_dpi,
                    psm=self.fallback_psm
                )
                
                if ocr_fallback:
                    logger.debug(f"Seite {page_num+1}: OCR (Fallback) verwendet")
                    return ocr_fallback
                
                # Letzte Option: kombiniere was verfügbar ist
                combined = (page_text or "") + "\n" + (plumber_text or "")
                if combined.strip():
                    logger.debug(f"Seite {page_num+1}: kombinierte Extraction")
                    return combined
                
                logger.debug(f"Seite {page_num+1}: keine Extraktion erfolgreich")
                return ""
            
            except Exception as e:
                logger.error(f"Seite {page_num + 1}: {e}")
                return ""

    def _is_noisy(self, text: str) -> bool:
        if not text:
            return True
        s = str(text)
        s2 = re.sub(r"\s+", "", s)
        if not s2:
            return True
        non_word = sum(1 for ch in s2 if not ch.isalnum())
        ratio = non_word / max(1, len(s2))
        return ratio >= self.noise_max_ratio

    def _is_usable_para(self, p: str) -> bool:
        if not p:
            return False
        # Табличные строки (markdown/ASCII) оставляем сразу, чтобы не отбрасывать полезные ячейки
        if p.count("|") >= 2:
            return True
        cleaned = re.sub(r'\s+', '', p)
        # Behalten Sie kurze, prägnante Linien bei, auch wenn die Länge gering ist.
        if DEFN_RE.search(p):
            return not self._is_noisy(p)
        # Length threshold (0 disables length filter)
        if self.min_text_length > 0 and len(cleaned) < self.min_text_length:
            return False
        # Rauschfilter
        if self._is_noisy(p):
            return False
        return True

    def _extract_text_normal_from_reader(self, reader: PyPDF2.PdfReader, page_num: int) -> str:
        try:
            page = reader.pages[page_num]
            text = page.extract_text()
            return text or ""
        except Exception as e:
            logger.debug(f"Fehler beim normalen Text-Extrakt: {e}")
            return ""

    async def _extract_text_ocr(self, pdf_path: str, page_num: int, dpi: int, psm: int) -> str:
        """
        OCR-Extraktion mit Bildvorbereitung:
        1. Render PDF-Seite als Bild
        2. Preprocessing: Resize, Grayscale, Contrast-Enhancement
        3. Tesseract OCR mit angepassten PSM-Parametern
        """
        try:
            images = await asyncio.to_thread(
                pdf2image.convert_from_path,
                pdf_path,
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=dpi,
                fmt='PNG'
            )
            if not images:
                return ""
            
            image = images[0]
            try:
                # Bildvorbereitung für robusteres OCR
                image = self._preprocess_image_for_ocr(image)
                
                # Tesseract OCR mit Language + PSM Config
                text = await asyncio.to_thread(
                    pytesseract.image_to_string,
                    image,
                    lang='+'.join(self.languages),
                    config=f'--psm {psm}'
                )
                return text or ""
            finally:
                try:
                    image.close()
                except Exception:
                    pass
                del images
        except Exception as e:
            logger.debug(f"OCR fehlgeschlagen (dpi={dpi}, psm={psm}) auf Seite {page_num+1}: {e}")
            return ""

    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Bildvorbereitung für OCR-Pipeline:
        1. Optional Resize (Downscaling für Geschwindigkeit)
        2. Grayscale-Konvertierung
        3. Contrast-Enhancement (optional)
        """
        try:
            # 1) Optional Downscaling zur Reduktion der OCR-Laufzeit
            if image.width > self.max_width:
                ratio = self.max_width / image.width
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # 2) In Grayscale konvertieren (robuster für OCR)
            image = image.convert("L")
            
            # 3) Optional: Contrast Enhancement via Bildoperation
            # (Kann die OCR-Genauigkeit bei schlecht gedruckten Dokumenten verbessern)
            # ImageEnhance import nur bei Bedarf
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.2)  # +20% Kontrast
            except Exception:
                pass  # Falls ImageEnhance nicht verfügbar, weitermachen
            
            return image
        except Exception as e:
            logger.debug(f"Bildvorbereitung OCR Fehler: {e}")
            return image

    def _is_text_sufficient(self, text: str) -> bool:
        if not text:
            return False
        if self._is_noisy(text):
            return False
        cleaned = re.sub(r'\s+', '', text)
        if len(cleaned) < self.min_text_length:
            return False
        alnum = re.sub(r'[^A-Za-z0-9ÄÖÜäöüß]', '', cleaned)
        if len(alnum) < self.min_text_length * 0.5:
            return False
        words = text.split()
        if len(words) < 12:
            return False
        return True

# Globальный экземпляр парсера
pdf_parser = OptimizedPDFParser()

# ============================================================================
# UTILITY FUNCTIONS FOR TITLES & SCREENSHOTS
# ============================================================================

def extract_paragraphs_from_pdf(pdf_path: str) -> List[str]:
    """
    Synchrone Wrapper-Funktion für CLI/Skripte OHNE aktiven Event-Loop.
    Wenn bereits ein Event-Loop läuft (z.B. innerhalb eines Webhooks), wird ein verständlicher Fehler ausgelöst.
    
    Nutzt die komplette OCR-Pipeline (wenn OCR_ENABLED=1) oder schnelle Text-Extraktion (PyPDF2+pdfplumber).
    """
    try:
        _loop = asyncio.get_running_loop()
    except RuntimeError:
        # Kein aktiver Loop — synchron mit asyncio.run ausführen
        return asyncio.run(pdf_parser.extract_paragraphs_from_pdf(pdf_path))
    # Aktiver Loop vorhanden → blockierendes run() nicht erlaubt
    raise RuntimeError("extract_paragraphs_from_pdf cannot be used inside an active event loop; use async API")


# --- Zusatzfunktionen für Titel/Seiten-Screenshots ---
# Regex (ohne überflüssige Escape-Zeichen): sucht nach Figure/Abbildung/Table/Tabelle oder nummerierten Überschriften
TITLE_PATTERNS = re.compile(
    r'^(?:fig(?:ure)?|abbildung|table|tabelle)\s*[:\-\.]?\s+|^\d+(?:[.\d]*)\s+',
    re.I
)

def extract_titles_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Heuristisch Titel/Überschriften/Tabellen-Abbildungen pro Seite extrahieren (synchron).
    Nutzt PyPDF2 + pdfplumber-Fallback für bessere Erkennung.
    """
    out: List[Dict] = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for i in range(total):
                try:
                    page = pdf.pages[i]
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                
                if not txt:
                    continue
                
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                for line in lines:
                    if TITLE_PATTERNS.match(line):
                        # Normalisiere und kürze
                        title = re.sub(r'\s+', ' ', line)[:200]
                        # Normalisiere auch den Titel
                        normalizer = TextNormalizer()
                        title = normalizer.normalize_text(title)
                        out.append({"title": title, "page": i + 1, "type": "title"})
    except Exception as e:
        logger.debug(f"extract_titles_from_pdf Fehler (pdfplumber): {e}")
        # Fallback auf PyPDF2
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            total = len(reader.pages)
            for i in range(total):
                try:
                    txt = reader.pages[i].extract_text() or ""
                except Exception:
                    txt = ""
                
                if not txt:
                    continue
                
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                for line in lines:
                    if TITLE_PATTERNS.match(line):
                        title = re.sub(r'\s+', ' ', line)[:200]
                        out.append({"title": title, "page": i + 1, "type": "title"})
        except Exception as e2:
            logger.debug(f"extract_titles_from_pdf Fallback-Fehler: {e2}")
    
    return out

def get_page_image_bytes(pdf_path: str, page_num: int, dpi: int = 180) -> bytes:
    """Rendert eine einzelne Seite als PNG-Bytes für Screenshots."""
    try:
        images = pdf2image.convert_from_path(
            pdf_path, first_page=page_num, last_page=page_num, dpi=dpi, fmt='PNG'
        )
        if not images:
            return b""
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")
        images[0].close()
        return buf.getvalue()
    except Exception as e:
        logger.debug(f"get_page_image_bytes Fehler: {e}")
        return b""


# ============================================================================
# PAGE LABELS (sichtbare Seitenbezeichnungen) → PDF-Seitenindex
# ============================================================================

_LABEL_CACHE: Dict[str, Dict[str, int]] = {}

def _int_to_roman(n: int, upper: bool) -> str:
    if n <= 0:
        return ""
    vals = [
        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
    ]
    out = []
    for v, sym in vals:
        while n >= v:
            out.append(sym)
            n -= v
    s = "".join(out)
    return s if upper else s.lower()

def _make_label(number: int, style: str | None, prefix: str | None) -> str:
    # style: '/D' decimal, '/r' roman lower, '/R' roman upper, '/A' '/a' (alphabetic) – wir unterstützen D/r/R
    if style in ("/r", "r"):
        num = _int_to_roman(number, upper=False)
    elif style in ("/R", "R"):
        num = _int_to_roman(number, upper=True)
    else:
        num = str(number)
    pre = prefix or ""
    return f"{pre}{num}"

def _extract_page_labels(reader: PyPDF2.PdfReader) -> Dict[str, int]:
    """
    Parst /PageLabels NumberTree und baut Mapping: sichtbare Bezeichnung -> 1-basierter PDF‑Seitenindex.
    Nur häufige Styles (D, r, R) werden unterstützt; Rest fällt auf Dezimal zurück.
    """
    try:
        root = reader.trailer.get("/Root")
        if root is None:
            return {}
        page_labels = root.get("/PageLabels")
        if page_labels is None:
            return {}
        try:
            labels_dict = page_labels.get_object()
        except Exception:
            labels_dict = page_labels
        nums = labels_dict.get("/Nums")
        if not nums:
            return {}
        try:
            nums = list(nums)
        except Exception:
            return {}
        # nums ist eine Liste: [page_index0, dict0, page_index1, dict1, ...]
        total = len(reader.pages)
        runs: List[Tuple[int, dict]] = []
        i = 0
        while i + 1 < len(nums):
            try:
                idx_obj = nums[i]
                spec_obj = nums[i+1]
                try:
                    idx = int(idx_obj)
                except Exception:
                    idx = int(getattr(idx_obj, "value", 0))
                try:
                    spec = spec_obj.get_object()
                except Exception:
                    spec = spec_obj
                if not isinstance(spec, dict):
                    spec = {}
                runs.append((max(0, idx), spec))
            except Exception:
                pass
            i += 2
        runs.sort(key=lambda t: t[0])
        # Build mapping
        mapping: Dict[str, int] = {}
        for j, (start, spec) in enumerate(runs):
            end = runs[j+1][0] - 1 if j + 1 < len(runs) else total - 1
            style = spec.get("/S")
            prefix = spec.get("/P")
            start_num = int(spec.get("/St", 1))
            cur = start_num
            for p in range(start, min(end, total - 1) + 1):
                label = _make_label(cur, style, prefix)
                # 1-basierter PDF‑Index
                mapping[str(label).strip()] = p + 1
                # zusätzlich: reine Zahl ohne Präfix, falls vorhanden
                try:
                    mapping[str(cur)] = p + 1
                except Exception:
                    pass
                # auch römische/arabische Varianten ohne Präфикс зарезервируем
                if style in ("/r", "r", "/R", "R"):
                    mapping[_int_to_roman(cur, upper=(style in ("/R", "R")))] = p + 1
                    mapping[_int_to_roman(cur, upper=False)] = p + 1
                    mapping[_int_to_roman(cur, upper=True)] = p + 1
                cur += 1
        return mapping
    except Exception as e:
        logger.debug(f"PageLabels parsing failed: {e}")
        return {}

def _fallback_offset_map(pdf_path: str, total_pages: int) -> Dict[str, int]:
    """
    Запасной оффсет для известных файлов: титульные без номера + римские i…vi, затем арабские 1…
    Для других документов возвращает пустую карту.
    """
    name = os.path.basename(pdf_path)
    # Значения по задаче: ISO SAE 21434: титульная (без метки) + i..vi = 7 страниц, затем 1..81
    if name == "ISO SAE 21434.pdf":
        title_pages = 1
        roman_pages = 6
        start_pdf = title_pages + roman_pages  # 1‑based индекс страницы, после которой начинается печатная "1"
        mapping: Dict[str, int] = {}
        # На практике в данном файле пользователи вводят "ii", "iii", … — устраним систематическое смещение +1.
        # Маппим: ii→2, iii→3, …, vi→(title_pages + 5) = 6, а при наличии "i" — считаем его как страницу 2.
        romans = ["i", "ii", "iii", "iv", "v", "vi"]
        for k, r in enumerate(romans, start=0):
            # титул = 1, желаемое: ii→2 (k=1 ⇒ 1+1=2), …; i (если попросят) тоже даём 2
            pdf_index = max(2, title_pages + k)
            mapping[r] = pdf_index
            mapping[r.upper()] = pdf_index
        # Арабские 1.. до конца. Ранее был систематический сдвиг +1, убираем его:
        printed = 1
        p = start_pdf  # 1‑based PDF‑индекс первой арабской страницы (без +1)
        while p <= total_pages and printed <= 200:
            mapping[str(printed)] = p
            printed += 1
            p += 1
        return mapping
    return {}

def get_page_label_map(pdf_path: str) -> Dict[str, int]:
    """
    Возвращает кэшированную карту: sichtbare Seitenbezeichnung ('i','vi','1','10', ggf. mit Präfix) → 1‑basierter PDF‑Index.
    """
    try:
        cached = _LABEL_CACHE.get(pdf_path)
        if cached is not None:
            return cached
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total = len(reader.pages)
            mapping = _extract_page_labels(reader)
            if not mapping:
                mapping = _fallback_offset_map(pdf_path, total)
            _LABEL_CACHE[pdf_path] = mapping or {}
            return mapping or {}
    except Exception as e:
        logger.debug(f"get_page_label_map failed: {e}")
        return {}

# ============================================================================
# IMPLEMENTATION SUMMARY
# ============================================================================
# 
# Primär: PyPDF2 (Text-PDFs)
# ├─ Robuste Text-Extraktion aus standardisierten PDF-Strukturen
# ├─ Direkter Zugriff auf Seiten
# └─ Optimiert für schnelle Verarbeitung
#
# Zusätzlich: pdfplumber für robuste Extraktion
# ├─ Komplexe Layouts und Tabellen
# ├─ Fallback wenn PyPDF2 unzureichend ist
# └─ Tabellen-Extraktion + Text
#
# OCR-Pipeline vorbereitet (pytesseract + pdf2image)
# ├─ Nur wenn OCR_ENABLED=1
# ├─ Multi-Strategy: Standard DPI → Fallback (höhere DPI + angepasster PSM)
# ├─ Sperrsemaphor für Concurrency-Kontrolle
# └─ Async-Processing für Skalierbarkeit
#
# Normalisierung: Zeilenumbrüche, Silbentrennung, saubere Absätze
# ├─ TextNormalizer-Klasse für Unicode-Normalisierung (NFD→NFKC)
# ├─ Behandlung von Silbentrennung über Zeilenumbrüche ("threat-\nanalysis"→"threatanalysis")
# ├─ Absatz-intelligente Aufteilung (\n\n Respekt)
# ├─ Ligatur-Ersetzung (ﬁ→fi, ﬂ→fl)
# └─ Whitespace-Bereinigung (mehrfache Leerzeichen, Satzzeichen)
#
# ============================================================================