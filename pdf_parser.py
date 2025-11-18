# pdf_parser.py
import PyPDF2
import pdf2image
import pytesseract
import re
import logging
import asyncio
from typing import List, Optional
from PIL import Image
import os
from typing import Dict, Tuple
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_OCR_CONCURRENCY = int(os.getenv("OCR_CONCURRENCY", "1"))
_sema = asyncio.Semaphore(_OCR_CONCURRENCY)

class OptimizedPDFParser:
    def __init__(self):
        self.default_dpi = 180
        self.fallback_dpi = 240
        self.min_text_length = 80
        self.primary_psm = 6
        self.fallback_psm = 3
        self.languages = ['eng', 'deu']
        self.max_width = 2000
        logger.info(
            f"[PDFParser] dpi={self.default_dpi}/{self.fallback_dpi}, "
            f"min_len={self.min_text_length}, psm={self.primary_psm}->{self.fallback_psm}, "
            f"lang={'/'.join(self.languages)}, concurrency={_OCR_CONCURRENCY}"
        )

    async def extract_paragraphs_from_pdf(self, pdf_path: str) -> List[str]:
        """Открываем PdfReader один раз и обрабатываем страницы батчами."""
        try:
            logger.info(f"Starte PDF-Verarbeitung: {pdf_path}")
            # Открываем один раз
            reader = PyPDF2.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            logger.info(f"PDF hat {total_pages} Seiten")

            paragraphs: List[str] = []
            # Обрабатываем страницами пакетами, чтобы не создавать N задач сразу
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
                        paragraphs.append(res.strip())
            logger.info(f"Erfolgreich {len(paragraphs)} Absätze extrahiert")
            return paragraphs
        except Exception as e:
            logger.error(f"Fehler bei PDF-Verarbeitung: {e}")
            return []

    async def _process_page_async(self, pdf_path: str, page_num: int, total_pages: int, reader: PyPDF2.PdfReader) -> Optional[str]:
        async with _sema:
            try:
                logger.debug(f"Verarbeite Seite {page_num + 1}/{total_pages}")
                page_text = self._extract_text_normal_from_reader(reader, page_num)
                if self._is_text_sufficient(page_text):
                    return page_text

                ocr_light = await self._extract_text_ocr(pdf_path, page_num, dpi=self.default_dpi, psm=self.primary_psm)
                if self._is_text_sufficient(ocr_light):
                    return ocr_light

                ocr_fallback = await self._extract_text_ocr(pdf_path, page_num, dpi=self.fallback_dpi, psm=self.fallback_psm)
                return ocr_fallback or page_text
            except Exception as e:
                logger.error(f"Seite {page_num + 1}: {e}")
                return ""

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
                if image.width > self.max_width:
                    ratio = self.max_width / image.width
                    new_size = (int(image.width * ratio), int(image.height * ratio))
                    image = image.resize(new_size, Image.LANCZOS)
                image = image.convert("L")
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

    def _is_text_sufficient(self, text: str) -> bool:
        if not text:
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
    return asyncio.run(pdf_parser.extract_paragraphs_from_pdf(pdf_path))

# --- Zusatzfunktionen für Titel/Seiten-Screenshots ---
# Korrektes Regex (без лишних экранирований): ищет Figure/Abbildung/Table/Tabelle или номерные заголовки
TITLE_PATTERNS = re.compile(
    r'^(?:fig(?:ure)?|abbildung|table|tabelle)\s*[:\-\.]?\s+|^\d+(?:[.\d]*)\s+',
    re.I
)

def extract_titles_from_pdf(pdf_path: str) -> List[Dict]:
    """Heuristisch Titel/Überschriften/Tabellen-Abbildungen pro Seite extrahieren (synchron)."""
    out: List[Dict] = []
    try:
        reader = PyPDF2.PdfReader(pdf_path)
        total = len(reader.pages)
        for i in range(total):
            try:
                txt = reader.pages[i].extract_text() or ""
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