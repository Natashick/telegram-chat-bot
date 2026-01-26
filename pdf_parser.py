# pdf_parser.py
import PyPDF2                 # Text-Extraktion und Seitenzugriff aus PDFs (ohne OCR)
import pdf2image              # Rendert PDF-Seiten als Bilder (für OCR & Screenshots)
import pytesseract            # OCR: extrahiert Text aus gerenderten Bildern
import re
import logging
import asyncio
from typing import List, Optional, Dict
from PIL import Image         # Bildverarbeitung (Resize, Grayscale) vor OCR & PNG-Ausgabe
import os
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OCR_ENABLED = int(os.getenv("OCR_ENABLED", "0"))  # 0 = off, 1 = on
_OCR_CONCURRENCY = int(os.getenv("OCR_CONCURRENCY", "1"))
_sema = asyncio.Semaphore(_OCR_CONCURRENCY)

# Heuristiken zur Verkürzung der Definitionszeilen (z. B. „TARA – Bedrohungsanalyse und Risikobewertung“)
DEFN_RE = re.compile(r"\b([A-ZÄÖÜ]{2,10})\b\s*(?:[-–—:]\s*|\()", re.IGNORECASE)

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
        logger.info(
            f"[PDFParser] dpi={self.default_dpi}/{self.fallback_dpi}, "
            f"min_len={self.min_text_length}, psm={self.primary_psm}->{self.fallback_psm}, "
            f"lang={'/'.join(self.languages)}, concurrency={_OCR_CONCURRENCY}, OCR_ENABLED={OCR_ENABLED}"
        )

    async def extract_paragraphs_from_pdf(self, pdf_path: str) -> List[str]:
        """Route by OCR_ENABLED: 0 = simple (PyPDF2 only), 1 = OCR pipeline."""
        if not OCR_ENABLED:
            return await self._extract_text_only(pdf_path)
        return await self._extract_with_ocr(pdf_path)

    async def _extract_text_only(self, pdf_path: str) -> List[str]:
        """Lightweight path: extract text using PyPDF2 only (no OCR)."""
        try:
            logger.info(f"Starte PDF-Verarbeitung (simple): {pdf_path}")
            paragraphs: List[str] = []
            with open(pdf_path, "rb") as f:  # PDF-Datei öffnen
                reader = PyPDF2.PdfReader(f)  # PyPDF2: PDF-Struktur laden
                total_pages = len(reader.pages)  # Seiten zählen
                logger.info(f"PDF hat {total_pages} Seiten")
                for i in range(total_pages):
                    try:
                        page = reader.pages[i]  # Seite abrufen
                        raw = page.extract_text() or ""  # PyPDF2: reinen Text der Seite extrahieren
                        # Normalisiere Zeilenumbrüche und Silbentrennung vor der Absatzaufteilung
                        text = raw.replace("\r", "")
                        # Worttrennungen über Zeilenumbrüche hinweg korrigieren: "threat-\nanalysis" -> "threatanalysis"
                        text = re.sub(r"([A-Za-zÄÖÜäöüß0-9])-\n([A-Za-zÄÖÜäöüß0-9])", r"\1\2", text)
                        # Einzelne Zeilenumbrüche in Leerzeichen umwandeln, Absatzumbrüche beibehalten
                        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
                        # Mehrfache Leerzeichen normalisieren
                        text = re.sub(r"[ \t]{2,}", " ", text)
                    except Exception as e:
                        logger.debug(f"Text-Extrakt Fehler Seite {i+1}: {e}")
                        text = ""
                    # Aufteilen in Absätze anhand von Leerzeilen
                    for para in re.split(r"\n\s*\n", text):
                        p = (para or "").strip()
                        if self._is_usable_para(p):
                            paragraphs.append(p)
            logger.info(f"Erfolgreich {len(paragraphs)} Absätze extrahiert (simple)")
            return paragraphs
        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung (simple): {e}")
            return []

    async def _extract_with_ocr(self, pdf_path: str) -> List[str]:
        """Open PdfReader once and process pages in batches with OCR fallback."""
        try:
            logger.info(f"Starte PDF-Verarbeitung: {pdf_path}")
            # Datei sicher öffnen und bis zum Abschluss der Seitenverarbeitung geöffnet halten
            with open(pdf_path, "rb") as f:  # PDF öffnen
                reader = PyPDF2.PdfReader(f)  # PyPDF2: Leser für direkten Textzugriff
                total_pages = len(reader.pages)  # Seitenzahl ermitteln
                logger.info(f"PDF hat {total_pages} Seiten")

                paragraphs: List[str] = []
                # Verarbeite Seiten in Batches, um nicht sofort N Tasks zu erstellen
                page_batch_size = max(1, _OCR_CONCURRENCY * 2)
                for start in range(0, total_pages, page_batch_size):
                    batch_pages = list(range(start, min(start + page_batch_size, total_pages)))
                    tasks = [self._process_page_async(pdf_path, p, total_pages, reader) for p in batch_pages]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for i, res in enumerate(results):
                        if isinstance(res, Exception):
                            logger.error(f"Fehler bei Seite {batch_pages[i]+1}: {res}")
                            continue
                        if res and res.strip():
                            candidate = res.strip()
                            if self._is_usable_para(candidate):
                                paragraphs.append(candidate)
                logger.info(f"Erfolgreich {len(paragraphs)} Absätze extrahiert")
                return paragraphs
        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung: {e}")
            return []

    async def _process_page_async(self, pdf_path: str, page_num: int, total_pages: int, reader: PyPDF2.PdfReader) -> Optional[str]:
        async with _sema:
            try:
                logger.debug(f"Verarbeite Seite {page_num + 1}/{total_pages}")
                page_text = self._extract_text_normal_from_reader(reader, page_num)  # 1) PyPDF2: direkter Textversuch
                if self._is_text_sufficient(page_text):
                    return page_text

                # 2) OCR (leicht): Seite rendern und mit Tesseract lesen
                ocr_light = await self._extract_text_ocr(pdf_path, page_num, dpi=self.default_dpi, psm=self.primary_psm)
                if self._is_text_sufficient(ocr_light):
                    return ocr_light

                # 3) OCR (Fallback): höhere DPI/angepasster PSM als zweite Chance
                ocr_fallback = await self._extract_text_ocr(pdf_path, page_num, dpi=self.fallback_dpi, psm=self.fallback_psm)
                return ocr_fallback or page_text
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
        try:
            images = await asyncio.to_thread(  # pdf2image in Thread: PDF-Seite -> PIL.Image Liste
                pdf2image.convert_from_path,
                pdf_path,
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=dpi,
                fmt='PNG'
            )
            if not images:
                return ""
            image = images[0]  # Erste (und einzige) gerenderte Seite
            try:
                if image.width > self.max_width:  # Optionales Downscaling zur Reduktion von OCR-Laufzeit
                    ratio = self.max_width / image.width
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.LANCZOS)  # PIL: hochwertiges Resize
                image = image.convert("L")  # PIL: in Graustufen konvertieren (robusteres OCR)
                text = await asyncio.to_thread(  # Tesseract OCR auf dem Bild
                    pytesseract.image_to_string,
                    image,
                    lang='+'.join(self.languages),
                    config=f'--psm {psm}'
                )
                return text or ""
            finally:
                try:
                    image.close()  # PIL-Ressourcen freigeben
                except Exception:
                    pass
                del images
        except Exception as e:
            logger.debug(f"OCR fehlgeschlagen (dpi={dpi}, psm={psm}) auf Seite {page_num+1}: {e}")
            return ""

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

# Globale Instanz
pdf_parser = OptimizedPDFParser()

def extract_paragraphs_from_pdf(pdf_path: str) -> List[str]:
    """
    Synchrone Wrapper-Funktion für CLI/Skripte OHNE aktiven Event-Loop.
    Wenn bereits ein Event-Loop läuft (z.B. innerhalb eines Webhooks), wird ein verständlicher Fehler ausgelöst.
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
    """Heuristisch Titel/Überschriften/Tabellen-Abbildungen pro Seite extrahieren (synchron)."""
    out: List[Dict] = []
    try:
        reader = PyPDF2.PdfReader(pdf_path)  # PyPDF2: Datei laden
        total = len(reader.pages)  # Anzahl Seiten
        for i in range(total):
            try:
                txt = reader.pages[i].extract_text() or ""  # PyPDF2: Seitentext
            except Exception:
                txt = ""
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            for line in lines:
                if TITLE_PATTERNS.match(line):
                    title = re.sub(r'\s+', ' ', line)[:200]
                    out.append({"title": title, "page": i + 1, "type": "title"})
    except Exception as e:
        logger.debug(f"extract_titles_from_pdf Fehler: {e}")
    return out

def get_page_image_bytes(pdf_path: str, page_num: int, dpi: int = 180) -> bytes:
    """Rendert eine einzelne Seite als PNG-Bytes."""
    try:
        images = pdf2image.convert_from_path(  # pdf2image: PDF-Seite -> PIL Image(s)
            pdf_path, first_page=page_num, last_page=page_num, dpi=dpi, fmt='PNG'
        )
        if not images:
            return b""
        buf = io.BytesIO()
        images[0].save(buf, format="PNG")  # PIL: als PNG in Speicher schreiben
        images[0].close()  # Ressourcen freigeben
        return buf.getvalue()
    except Exception as e:
        logger.debug(f"get_page_image_bytes Fehler: {e}")
        return b""