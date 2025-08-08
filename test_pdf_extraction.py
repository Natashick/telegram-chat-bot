# test_pdf_extraction.py
# TEST-SKRIPT - Überprüft ob PDF-Extraktion funktioniert
#
# ZWECK: Entwickler-Tool zum Testen der PDF-Parser Funktion
#        Zeigt extrahierte Text-Chunks zur Qualitätskontrolle
#
# VERWENDUNG: python test_pdf_extraction.py mein_dokument.pdf
# LERNZIEL: Verstehe wie man Code testet und debuggt

# IMPORT SECTION
from pdf_parser import extract_paragraphs_from_pdf  # Unsere PDF-Funktion
import sys  # System-Funktionen (Kommandozeilen-Argumente)

# SCHRITT 1: KOMMANDOZEILEN-PARAMETER PRÜFEN
# sys.argv = Liste aller Argumente beim Programmstart
# [0] = Skriptname selbst, [1] = erstes Argument (PDF-Datei)
if len(sys.argv) < 2:
    # FEHLER: Benutzer hat keine PDF-Datei angegeben
    print("Usage: python test_pdf_extraction.py <PDF_FILE>")
    print("Beispiel: python test_pdf_extraction.py UN_Regulation155.pdf")
    sys.exit(1)  # Programm beenden mit Fehlercode 1

# SCHRITT 2: PDF-DATEINAME AUS ARGUMENTEN HOLEN
pdf_file = sys.argv[1]  # Erstes Argument nach Skriptname
print(f"Teste PDF-Extraktion für: {pdf_file}")

# SCHRITT 3: PDF VERARBEITEN UND TEXT EXTRAHIEREN
# Ruft unsere Hauptfunktion auf und bekommt Liste von Text-Chunks zurück
paragraphs = extract_paragraphs_from_pdf(pdf_file)

# SCHRITT 4: ERGEBNISSE ANZEIGEN
print(f"Gefundene Absätze: {len(paragraphs)}")
print("=" * 50)

# enumerate() gibt uns Index (i) und Inhalt (para) für jeden Absatz
for i, para in enumerate(paragraphs):
    print(f"--- Paragraph {i+1} ---")
    print(para)
    print()  # Leerzeile für bessere Lesbarkeit

print("=" * 50)
print("Test abgeschlossen!")

# WARUM IST DIESER TEST WICHTIG:
# - Überprüft ob PDF richtig gelesen wird
# - Zeigt Qualität der Text-Extraktion
# - Hilft bei Debugging von Problemen
# - Visualisiert wie Text aufgeteilt wird 