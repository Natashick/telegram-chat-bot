# pdf_parser.py
# PDF TEXT EXTRAKTOR - Wandelt PDF-Dateien in durchsuchbaren Text um
# 
# ZWECK: PDFs enthalten Text als Bilder oder verschlüsselt
#        Dieser Code macht sie für Computer lesbar
#
# LERNZIEL: Verstehe wie Computer PDF-Dateien "lesen"

# IMPORT SECTION - Externe Bibliotheken einbinden
import os           # Betriebssystem-Funktionen (Dateien, Pfade)
import re           # Regular Expressions (Text-Muster erkennen)
import PyPDF2       # PDF-Dateien lesen und analysieren
import pytesseract  # OCR = Optical Character Recognition (Bild zu Text)
from pdf2image import convert_from_path  # PDF zu Bildern konvertieren
from PIL import Image  # Bildverarbeitung (Python Imaging Library)
import asyncio      # Asynchrone Programmierung für concurrency control
import logging      # Logging für OCR tracking
import time         # Zeit-Messung für Performance-Logging

# Optional pdfminer import
try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False
    logger.info("pdfminer.six not available, using PyPDF2 only")

# OCR CONCURRENCY CONTROL - Verhindert zu viele parallele OCR-Prozesse
OCR_CONCURRENCY = int(os.getenv("OCR_CONCURRENCY", "3"))
_ocr_semaphore = asyncio.Semaphore(OCR_CONCURRENCY)

# Logging Setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PDFParser:
    """
    OPTIMIERTER PDF PARSER MIT RESOURCE CONTROL
    
    Features:
    - OCR Throttling mit asyncio.Semaphore
    - Conservative OCR defaults (PSM=6, DPI=180)
    - Early-exit für text-based PDFs
    - Async OCR calls mit asyncio.to_thread
    - Logging für OCR triggers und durations
    """
    
    def __init__(self, min_text_length=80):
        """
        Initialize PDF Parser mit konfigurierbaren Einstellungen
        
        Args:
            min_text_length: Minimum text length to skip OCR (default: 80)
        """
        self.min_text_length = int(os.getenv("MIN_TEXT_LENGTH", str(min_text_length)))
        # Conservative OCR defaults
        self.psm_modes = [6]  # Single uniform block of text
        self.default_dpi = 180  # Lower DPI for speed
        self.fallback_dpi = 240  # Fallback if first attempt fails
        self.fallback_psm = 3   # Fully automatic page segmentation
        
        logger.info(f"PDFParser initialized: min_text_length={self.min_text_length}, "
                   f"default_dpi={self.default_dpi}, ocr_concurrency={OCR_CONCURRENCY}")
    
    async def _extract_text_normal(self, file_path, page_num):
        """
        Extract text using PyPDF2 and pdfminer (no OCR)
        
        Returns: Extracted text or empty string
        """
        text = ""
        try:
            # Try PyPDF2 first
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if page_num < len(reader.pages):
                    page_text = reader.pages[page_num].extract_text() or ""
                    text = page_text.strip()
            
            # If PyPDF2 fails, try pdfminer (if available)
            if HAS_PDFMINER and len(text) < self.min_text_length:
                try:
                    full_text = await asyncio.to_thread(pdfminer_extract_text, file_path)
                    lines = full_text.split('\n')
                    # Estimate which lines belong to this page
                    if len(lines) > 0:
                        page_lines = len(lines) // max(1, self._get_page_count(file_path))
                        start = page_num * page_lines
                        end = start + page_lines
                        text = '\n'.join(lines[start:end]).strip()
                except Exception as e:
                    logger.debug(f"pdfminer extraction failed for page {page_num}: {e}")
        except Exception as e:
            logger.warning(f"Normal text extraction failed for page {page_num}: {e}")
        
        return text
    
    def _get_page_count(self, file_path):
        """Get total page count from PDF"""
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except:
            return 1
    
    async def _extract_text_ocr(self, file_path, page_num, modes=None, dpis=None):
        """
        Extract text using OCR with throttling
        
        Args:
            file_path: Path to PDF
            page_num: Page number (0-indexed)
            modes: List of PSM modes to try (default: [6])
            dpis: List of DPI values to try (default: [180])
        
        Returns: Extracted text or empty string
        """
        modes = modes or self.psm_modes
        dpis = dpis or [self.default_dpi]
        
        async with _ocr_semaphore:
            start_time = time.time()
            text = ""
            
            try:
                # Convert PDF page to image
                images = await asyncio.to_thread(
                    convert_from_path, 
                    file_path, 
                    first_page=page_num+1, 
                    last_page=page_num+1,
                    dpi=dpis[0]
                )
                
                if not images:
                    logger.warning(f"No images generated for page {page_num}")
                    return ""
                
                image = images[0]
                
                # Try OCR with specified mode
                try:
                    config = f'--psm {modes[0]}'
                    text = await asyncio.to_thread(
                        pytesseract.image_to_string, 
                        image, 
                        lang='eng',
                        config=config
                    )
                    text = text.strip()
                    
                    duration = time.time() - start_time
                    logger.info(f"OCR page {page_num+1}: mode={modes[0]}, dpi={dpis[0]}, "
                               f"duration={duration:.2f}s, text_length={len(text)}")
                    
                except Exception as e:
                    logger.error(f"OCR failed for page {page_num} with mode {modes[0]}: {e}")
                
                # Cleanup
                image.close()
                del image
                del images
                
            except Exception as e:
                logger.error(f"OCR image conversion failed for page {page_num}: {e}")
            
            return text
    
    async def _process_page_async(self, file_path, page_num):
        """
        Process a single page with early-exit logic
        
        1. Try normal text extraction (PyPDF2, pdfminer)
        2. If insufficient text, try OCR with default settings
        3. If still insufficient, try fallback OCR
        
        Returns: Extracted text
        """
        # Step 1: Try normal extraction
        text = await self._extract_text_normal(file_path, page_num)
        
        if len(text) >= self.min_text_length:
            logger.info(f"Page {page_num+1}: sufficient text without OCR ({len(text)} chars)")
            return text
        
        logger.info(f"Page {page_num+1}: insufficient text ({len(text)} chars), triggering OCR")
        
        # Step 2: Try OCR with conservative defaults
        ocr_text = await self._extract_text_ocr(
            file_path, 
            page_num,
            modes=[self.psm_modes[0]],
            dpis=[self.default_dpi]
        )
        
        if len(ocr_text) >= self.min_text_length:
            return text + "\n" + ocr_text
        
        # Step 3: Fallback OCR with higher quality
        logger.info(f"Page {page_num+1}: OCR insufficient, trying fallback "
                   f"(psm={self.fallback_psm}, dpi={self.fallback_dpi})")
        
        fallback_text = await self._extract_text_ocr(
            file_path,
            page_num,
            modes=[self.fallback_psm],
            dpis=[self.fallback_dpi]
        )
        
        duration_log = f"Fallback OCR used for page {page_num+1}"
        logger.info(duration_log)
        
        return text + "\n" + ocr_text + "\n" + fallback_text
    
    async def extract_text_async(self, file_path):
        """
        Extract text from entire PDF asynchronously
        
        Returns: Full text content
        """
        text = ""
        try:
            page_count = self._get_page_count(file_path)
            logger.info(f"Processing PDF: {file_path} ({page_count} pages)")
            
            # Process all pages
            tasks = [self._process_page_async(file_path, i) for i in range(page_count)]
            page_texts = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, page_text in enumerate(page_texts):
                if isinstance(page_text, Exception):
                    logger.error(f"Page {i+1} failed: {page_text}")
                else:
                    text += page_text + "\n"
            
            logger.info(f"PDF processing complete: {len(text)} total characters")
            
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            import traceback
            traceback.print_exc()
        
        return text


def extract_paragraphs_from_pdf(file_path, chunk_size=10):
    """
    BACKWARD COMPATIBLE WRAPPER - Converts PDF to text chunks
    
    This function maintains backward compatibility with existing code
    while using the new optimized PDFParser under the hood.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Number of sentences per chunk (default: 10)
    
    Returns:
        List of text chunks
    """
    # Create parser and extract text
    parser = PDFParser()
    
    # Run async extraction in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    text = loop.run_until_complete(parser.extract_text_async(file_path))
    
    if not text or not text.strip():
        logger.warning(f"No text extracted from {file_path}")
        return []
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Group into chunks
    chunks = []
    for i in range(0, len(sentences), chunk_size):
        chunk = ' '.join(sentences[i:i+chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    
    logger.info(f"Created {len(chunks)} chunks from {file_path}")
    return chunks