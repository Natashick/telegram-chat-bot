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

def extract_paragraphs_from_pdf(file_path, chunk_size=10):
    """
    HAUPTFUNKTION: PDF zu Text-Chunks konvertieren
    
    WAS PASSIERT HIER:
    1. PDF-Datei öffnen und Seite für Seite lesen
    2. Text extrahieren (direkt oder per OCR wenn nötig)
    3. Text in sinnvolle Abschnitte aufteilen
    4. Liste von Text-Chunks zurückgeben
    
    PARAMETER:
    - file_path: Pfad zur PDF-Datei (z.B. "document.pdf")
    - chunk_size: Wie viele Sätze pro Abschnitt (Standard: 10)
    
    RÜCKGABE:
    - Liste von Text-Strings ["Absatz 1...", "Absatz 2...", ...]
    
    WARUM CHUNKS: 
    - Lange Texte sind schwer zu durchsuchen
    - Kleine Stücke = bessere Suchergebnisse
    """
    
    # SCHRITT 1: VARIABLE FÜR GESAMTEN TEXT VORBEREITEN
    text = ""  # Hier sammeln wir allen extrahierten Text
    
    try:
        # SCHRITT 2: PDF-DATEI ÖFFNEN UND LESEN
        # "rb" = read binary (PDF ist binäre Datei, nicht Text)
        with open(file_path, "rb") as f:
            # PyPDF2 Reader erstellen - das ist unser PDF-Leser
            reader = PyPDF2.PdfReader(f)
            
            # SCHRITT 3: JEDE SEITE EINZELN VERARBEITEN
            # enumerate() gibt uns Seitennummer (i) und Seite selbst
            for i, page in enumerate(reader.pages):
                # VERSUCH 1: DIREKTER TEXT-EXTRAKT
                # Manche PDFs haben eingebauten Text
                page_text = page.extract_text() or ""
                
                if page_text.strip():  # strip() entfernt Leerzeichen
                    # ERFOLG: Text gefunden, zur Sammlung hinzufügen
                    text += page_text
                else:
                    # PROBLEM: Keine Text gefunden (wahrscheinlich Scan/Bild)
                    print(f"WARNUNG: Seite {i+1} in {file_path} hat keinen extrahierbaren Text. Versuche OCR.")
                    
                    # VERSUCH 2: OCR (OPTICAL CHARACTER RECOGNITION)
                    # PDF-Seite zu Bild konvertieren
                    images = convert_from_path(file_path, first_page=i+1, last_page=i+1)
                    
                    # Jedes Bild durch OCR verarbeiten
                    for image in images:
                        # Tesseract OCR: Erkennt Text in Bildern
                        ocr_text = pytesseract.image_to_string(image, lang='eng')
                        text += ocr_text
                        
    except PyPDF2.errors.PdfReadError as e:
        # FEHLERBEHANDLUNG: PDF beschädigt oder passwortgeschützt
        print(f"FEHLER: Konnte PDF-Datei '{file_path}' nicht lesen. Möglicherweise beschädigt oder passwortgeschützt. {e}")
        return []  # Leere Liste zurückgeben
        
    except Exception as e:
        # FEHLERBEHANDLUNG: Unerwarteter Fehler
        print(f"FEHLER beim Extrahieren von Text aus '{file_path}': {e}")
        import traceback
        traceback.print_exc()  # Detaillierte Fehlermeldung
        return []

    # SCHRITT 4: TEXT IN SINNVOLLE ABSCHNITTE AUFTEILEN
    # Regular Expression: Teile Text bei Satzende (.!?) + Leerzeichen
    # (?<=[.!?]) = "Schaue zurück nach Punkt/Ausrufe/Fragezeichen"
    # \s+ = "Ein oder mehr Leerzeichen"
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # SCHRITT 5: SÄTZE ZU CHUNKS GRUPPIEREN
    chunks = []  # Liste für fertige Text-Abschnitte
    
    # range(start, stop, step) = von 0 bis Satzanzahl, in chunk_size Schritten
    for i in range(0, len(sentences), chunk_size):
        # Nimm chunk_size Sätze und verbinde sie mit Leerzeichen
        chunk = ' '.join(sentences[i:i+chunk_size]).strip()
        
        if chunk:  # Nur nicht-leere Chunks hinzufügen
            chunks.append(chunk)
    
    # FERTIG: Liste von Text-Abschnitten zurückgeben
    return chunks