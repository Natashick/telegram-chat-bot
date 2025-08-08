# 📚 KOMPLETTER GUIDE: BIBLIOTHEKEN, TOOLS & ORDNER

## 🎯 WAS IST DIESER GUIDE?
Dieser Guide erklärt **JEDE** Bibliothek, **JEDES** Tool und **JEDEN** Ordner in dem Telegram Bot Projekt.
**LERNZIEL:** Du verstehst warum wir was verwenden und wie alles zusammenarbeitet.

---

## 📦 PYTHON BIBLIOTHEKEN (requirements.txt)

### 1. **TELEGRAM BOT BIBLIOTHEKEN**

#### `python-telegram-bot==20.6`
- **WAS:** Offizielle Python-Bibliothek für Telegram Bots
- **WARUM:** Macht Telegram API einfach benutzbar
- **OHNE DAS:** Müsstest du HTTP-Requests manuell schreiben
- **VERWENDET IN:** `bot.py`, `handlers.py`
- **BEISPIEL:** `await update.message.reply_text("Hallo!")`

---

### 2. **WEB-SERVER BIBLIOTHEKEN**

#### `fastapi==0.104.1`
- **WAS:** Modernes Python Web-Framework
- **WARUM:** Erstellt HTTP-Server für Telegram Webhooks
- **OHNE DAS:** Bot könnte nur Polling (langsam), nicht Webhooks (schnell)
- **VERWENDET IN:** `bot.py`
- **ALTERNATIVE:** Flask, Django (komplizierter)

#### `uvicorn==0.24.0`
- **WAS:** ASGI Server (läuft FastAPI)
- **WARUM:** FastAPI braucht einen Server um zu laufen
- **OHNE DAS:** FastAPI kann nicht starten
- **KOMMANDO:** `uvicorn bot:app --host 0.0.0.0 --port 8000`

#### `aiohttp==3.9.0`
- **WAS:** Asynchroner HTTP Client
- **WARUM:** Für HTTP-Requests an Ollama LLM Server
- **OHNE DAS:** Bot kann nicht mit Ollama kommunizieren
- **VERWENDET IN:** `llm_client.py`, `vector_store.py`
- **VORTEIL:** Async = non-blocking (bot hängt nicht)

---

### 3. **KI/LLM BIBLIOTHEKEN**

#### `ollama==0.3.3`
- **WAS:** Python Client für Ollama Server
- **WARUM:** Vereinfacht Kommunikation mit lokalen LLMs
- **OHNE DAS:** Müsstest HTTP-Requests manuell machen
- **VERWENDET IN:** Optional (wir benutzen aiohttp direkt)
- **MODELS:** llama3.2:3b, nomic-embed-text

---

### 4. **VEKTORDATENBANK BIBLIOTHEKEN**

#### `chromadb==0.4.18`
- **WAS:** Vektordatenbank für semantische Suche
- **WARUM:** Speichert Text als Vektoren für ähnlichkeitsbasierte Suche
- **OHNE DAS:** Keine intelligente Suche, nur exakte Textsuche
- **VERWENDET IN:** `vector_store.py`
- **ERSTELLT:** `chroma_db/` Ordner

#### `sentence-transformers==2.2.2`
- **WAS:** Erstellt Text-Embeddings (Text zu Vektoren)
- **WARUM:** Fallback falls Ollama Embeddings nicht funktionieren
- **OHNE DAS:** Nur Ollama Embeddings verfügbar
- **VERWENDET IN:** `vector_store.py` (Fallback)

---

### 5. **PDF VERARBEITUNG BIBLIOTHEKEN**

#### `PyPDF2==3.0.1`
- **WAS:** PDF-Dateien lesen und Text extrahieren
- **WARUM:** Macht PDF-Inhalte für Computer lesbar
- **OHNE DAS:** PDFs bleiben unlesbar für Bot
- **VERWENDET IN:** `pdf_parser.py`
- **LIMITATION:** Funktioniert nur bei Text-PDFs (nicht Scans)

#### `pdf2image==1.16.3`
- **WAS:** Konvertiert PDF-Seiten zu Bildern
- **WARUM:** Für OCR bei gescannten PDFs
- **OHNE DAS:** Gescannte PDFs nicht lesbar
- **VERWENDET IN:** `pdf_parser.py`, `handlers.py` (Screenshots)
- **BENÖTIGT:** Poppler (System-Tool)

#### `pytesseract==0.3.10`
- **WAS:** OCR (Optical Character Recognition) - Text aus Bildern extrahieren
- **WARUM:** Gescannte PDF-Seiten haben Text als Bilder
- **OHNE DAS:** Scans bleiben unlesbar
- **VERWENDET IN:** `pdf_parser.py`
- **BENÖTIGT:** Tesseract (System-Tool)

#### `Pillow==10.1.0`
- **WAS:** Bildverarbeitung (Python Imaging Library)
- **WARUM:** Bilder bearbeiten (zuschneiden, konvertieren)
- **OHNE DAS:** Screenshot-Funktion funktioniert nicht
- **VERWENDET IN:** `handlers.py` (Screenshots)

---

### 6. **HILFSBIBLIOTHEKEN**

#### `requests==2.31.0`
- **WAS:** Einfache HTTP-Requests
- **WARUM:** Synchrone HTTP-Calls (für Embeddings)
- **OHNE DAS:** Embedding-Requests komplizierter
- **VERWENDET IN:** `vector_store.py`
- **UNTERSCHIED zu aiohttp:** Synchron vs Asynchron

#### `numpy==1.24.3`
- **WAS:** Numerische Berechnungen (Arrays, Matrizen)
- **WARUM:** ChromaDB und Embeddings verwenden Arrays
- **OHNE DAS:** Vektordatenbank funktioniert nicht
- **AUTOMATISCH:** Wird von ChromaDB mitinstalliert

---

## 🛠️ SYSTEM-TOOLS (müssen separat installiert werden)

### **Ollama**
- **WAS:** Lokaler LLM Server
- **INSTALLATION:** [ollama.ai](https://ollama.ai)
- **WARUM:** Läuft KI-Modelle lokal (kein Internet nötig)
- **KOMMANDOS:**
  ```bash
  ollama pull llama3.2:3b        # LLM Model herunterladen
  ollama pull nomic-embed-text   # Embedding Model herunterladen
  ollama serve                   # Server starten
  ```

### **Docker**
- **WAS:** Containerisierung-Platform
- **INSTALLATION:** [docker.com](https://docker.com)
- **WARUM:** Bot in isolierter Umgebung laufen lassen
- **KOMMANDOS:**
  ```bash
  docker build -t mein-bot .     # Image erstellen
  docker run -p 8000:8000 mein-bot  # Container starten
  ```

### **Tesseract OCR**
- **WAS:** Open-Source OCR Engine
- **INSTALLATION:** 
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt install tesseract-ocr`
- **WARUM:** pytesseract braucht diese Engine
- **SPRACHEN:** Deutsch, Englisch, etc.

### **Poppler**
- **WAS:** PDF-Utilities
- **INSTALLATION:**
  - Windows: https://blog.alivate.com.au/poppler-windows/
  - Linux: `sudo apt install poppler-utils`
- **WARUM:** pdf2image braucht diese Tools
- **ENTHÄLT:** pdftoppm, pdfinfo, etc.

---

## 📁 PROJEKT-ORDNER ERKLÄRT

### **`chroma_db/`**
- **WAS:** Vektordatenbank-Speicher
- **INHALT:** 
  - Embeddings (Text als Vektoren)
  - Index-Dateien
  - Metadaten
- **WARUM:** Persistente Speicherung der Vektoren
- **KANN GELÖSCHT WERDEN:** Ja, wird neu erstellt
- **GRÖßE:** Wächst mit Anzahl der PDFs

### **`__pycache__/`**
- **WAS:** Python Bytecode Cache
- **INHALT:** Kompilierte .pyc Dateien
- **WARUM:** Python-Optimierung (schnellere Starts)
- **AUTOMATISCH:** Wird von Python erstellt
- **KANN GELÖSCHT WERDEN:** Ja, wird automatisch neu erstellt
- **IM GIT:** Sollte ignoriert werden (.gitignore)

### **`.dockerignore`**
- **WAS:** Docker Ignore-Datei
- **ZWECK:** Definiert was NICHT ins Docker Image kommt
- **ENTHÄLT:** __pycache__, .git, chroma_db, etc.
- **WARUM:** Kleinere, sauberere Docker Images

### **`Dockerfile`**
- **WAS:** Docker Image Bauanleitung
- **ZWECK:** Definiert wie Bot-Container erstellt wird
- **ENTHÄLT:** 
  - Python Installation
  - System-Dependencies (Tesseract, Poppler)
  - Python-Bibliotheken
  - App-Code

### **`requirements.txt`**
- **WAS:** Python Dependencies Liste
- **ZWECK:** Definiert alle benötigten Bibliotheken
- **FORMAT:** `bibliothek==version`
- **INSTALLATION:** `pip install -r requirements.txt`

---

## 🔄 WIE ALLES ZUSAMMENARBEITET

### **DATENFLUSS:**
1. **PDF** → pdf_parser.py → **Text-Chunks**
2. **Text-Chunks** → vector_store.py → **Embeddings**
3. **Embeddings** → ChromaDB → **Vektordatenbank**
4. **User-Frage** → Telegram → bot.py → handlers.py
5. **Frage** → vector_store.py → **Ähnliche Chunks**
6. **Chunks** → llm_client.py → Ollama → **Antwort**
7. **Antwort** → handlers.py → Telegram → **User**

### **ARCHITEKTUR:**
```
User (Telegram) 
    ↕ 
ngrok (Tunnel)
    ↕
FastAPI (bot.py) 
    ↕
Handlers (handlers.py)
    ↕
Vector Search (vector_store.py) ← ChromaDB
    ↕
LLM Client (llm_client.py) 
    ↕
Ollama Server (llama3.2:3b)
```

---

## 🚀 WARUM DIESE TECHNOLOGIE-AUSWAHL?

### **Warum Python?**
- Einfache Syntax
- Viele KI-Bibliotheken
- Große Community

### **Warum FastAPI?**
- Schnell und modern
- Automatische Dokumentation
- Async Support

### **Warum ChromaDB?**
- Einfach zu verwenden
- Gute Performance
- Lokaler Betrieb

### **Warum Ollama?**
- Lokale KI (keine Cloud)
- Einfache Installation
- Viele Modelle

### **Warum Docker?**
- Reproduzierbare Umgebung
- Einfache Deployment
- Isolation

---

## 🎓 LERNEMPFEHLUNGEN

### **Reihenfolge zum Lernen:**
1. **Python Grundlagen** (if/for/functions)
2. **HTTP/APIs verstehen** (GET/POST Requests)
3. **Async/Await Konzept** (asynchrone Programmierung)
4. **Vector Databases** (Embeddings, Similarity Search)
5. **LLM Concepts** (Prompts, Tokens, Context)
6. **Docker Basics** (Images, Containers)

### **Praktische Übungen:**
1. Test einzelne Funktionen (test_pdf_extraction.py)
2. Ändere Prompts in llm_client.py
3. Experimentiere mit chunk_size
4. Probiere andere Ollama Models
5. Baue eigene Handler

---

## 🆘 TROUBLESHOOTING

### **Häufige Probleme:**
1. **"Ollama not found"** → Ollama installieren und starten
2. **"Tesseract not found"** → Tesseract installieren
3. **"pdf2image error"** → Poppler installieren
4. **"Port already in use"** → Anderen Port verwenden
5. **"ChromaDB error"** → chroma_db/ Ordner löschen

### **Debug-Tipps:**
1. Prüfe Logs in Terminal
2. Teste einzelne Komponenten
3. Verwende print() Statements
4. Prüfe Environment Variables
5. Teste mit curl

---

**🎯 FAZIT:** Jede Bibliothek hat einen spezifischen Zweck. Zusammen ergeben sie einen vollständigen, intelligenten Telegram Bot der PDFs verstehen und Fragen beantworten kann!