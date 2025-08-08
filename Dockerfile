# Dockerfile
# DOCKER CONTAINER BAUANLEITUNG - Erstellt isolierte Bot-Umgebung
#
# ZWECK: Verpackt Bot mit allen Dependencies in ein Container
#        Läuft identisch auf jedem System (Windows, Linux, Mac)
#
# VERWENDUNG: 
#   docker build -t mein-bot .
#   docker run -p 8000:8000 mein-bot
#
# LERNZIEL: Verstehe Docker Container und Deployment

# SCHRITT 1: BASIS-IMAGE WÄHLEN
# python:3.10-slim = Python 3.10 + minimales Linux System
# "slim" = klein aber funktional (vs "alpine" = sehr klein, "full" = groß)
FROM python:3.10-slim

# SCHRITT 2: SYSTEM-DEPENDENCIES INSTALLIEREN (OPTIMIERT)
# Nur die wichtigsten Dependencies für kleinere Image-Größe
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# WARUM DIESE PAKETE (MINIMAL):
# - tesseract-ocr: pytesseract braucht das
# - poppler-utils: pdf2image braucht das  
# - curl: Für Health Checks

# SCHRITT 3: ARBEITSVERZEICHNIS SETZEN
# Alle folgenden Kommandos laufen in /app
WORKDIR /app

# SCHRITT 4: PYTHON-DEPENDENCIES INSTALLIEREN
# COPY requirements.txt zuerst (Docker Layer Caching!)
# Wenn sich Code ändert aber requirements.txt nicht,
# muss dieser Layer nicht neu gebaut werden
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --no-cache-dir = Spart Speicherplatz (kein pip cache)

# SCHRITT 5: APPLICATION CODE KOPIEREN
# Kopiert alle Dateien (außer .dockerignore) ins Container
COPY . .

# SCHRITT 6: PORT FREIGEBEN
# Teilt Docker mit dass Container Port 8000 verwendet
# Tatsächliche Weiterleitung erfolgt mit -p beim docker run
EXPOSE 8000

# SCHRITT 7: ALTE DATENBANK LÖSCHEN
# Verhindert Konflikte mit alter lokaler ChromaDB
# Container erstellt neue, saubere Datenbank
RUN rm -rf /app/chroma_db

# SCHRITT 8: START-KOMMANDO DEFINIEREN
# CMD = Was passiert wenn Container startet
# uvicorn = ASGI Server für FastAPI
# --host 0.0.0.0 = Akzeptiere Verbindungen von außerhalb
# --port 8000 = Verwende Port 8000
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8000"]

# DOCKER LAYER OPTIMIERUNG:
# 1. BASIS IMAGE (ändert sich selten)
# 2. SYSTEM PAKETE (ändert sich selten) 
# 3. PYTHON REQUIREMENTS (ändert sich manchmal)
# 4. APPLICATION CODE (ändert sich oft)
#
# Wenn nur Code ändert, werden nur Layer 4 neu gebaut = SCHNELL! 