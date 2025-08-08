# 💻 POWERSHELL KOMMANDOS FÜR DEN BOT

## 🚀 BOT STARTEN (PowerShell Syntax)

cd "C:\Users\Student\OneDrive - orhunsuzer.com\Desktop\Praktikum\Mein Praktikum\chat_bot"

### **Methode 1: Einzelne Kommandos**
```powershell
# Environment Variables setzen (PowerShell Syntax!)
$env:TELEGRAM_TOKEN="7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w"
$env:WEBHOOK_URL="https://99a39f39ee0d.ngrok-free.app"
$env:OLLAMA_URL="http://localhost:11434"
$env:OLLAMA_MODEL="llama3.2:3b"

# Bot starten
python -m uvicorn bot:app --host 0.0.0.0 --port 8000 --reload
```

### **Methode 2: Ein-Zeilen Kommando (PowerShell)**
```powershell
$env:TELEGRAM_TOKEN="7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w"; $env:WEBHOOK_URL="https://99a39f39ee0d.ngrok-free.app"; $env:OLLAMA_URL="http://localhost:11434"; $env:OLLAMA_MODEL="llama3.2:3b"; python -m uvicorn bot:app --host 0.0.0.0 --port 8000 --reload
```

### **WARUM ANDERE SYNTAX ALS LINUX/MAC:**
- **Linux/Mac:** `export VAR=value && command`
- **PowerShell:** `$env:VAR="value"; command`
- **CMD:** `set VAR=value && command`

---

## 🔧 OLLAMA KOMMANDOS

```powershell
# Ollama Server starten (in separatem Terminal)
ollama serve

# Modelle herunterladen
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Verfügbare Modelle anzeigen
ollama list

# Testen ob Ollama läuft
curl http://localhost:11434/api/tags
```

---

## 🐳 DOCKER KOMMANDOS

```powershell
# Docker Image bauen
docker build -t mein-bot .

# Laufende Container anzeigen
docker ps

# Container starten (lokal)
docker run -p 8000:8000 -e TELEGRAM_TOKEN="7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w" -e WEBHOOK_URL="https://d40087949776.ngrok-free.app" -e OLLAMA_URL="http://host.docker.internal:11434" -e OLLAMA_MODEL="llama3.2:3b" mein-bot

# Container stoppen
docker stop CONTAINER_ID

# Container Logs anzeigen
docker logs CONTAINER_ID
```

---

## 🧪 TEST KOMMANDOS

```powershell
# PDF Extraktion testen
python test_pdf_extraction.py UN_Regulation155.pdf

# Bot Health Check
curl http://localhost:8000/

# Requirements installieren
pip install -r requirements.txt

# Python Dependencies anzeigen
pip list
```

---

## 🛠️ DEBUGGING KOMMANDOS

```powershell
# Prozesse finden die Port blockieren
netstat -ano | findstr :8000

# Python Prozesse beenden
taskkill /F /IM python.exe

# Alle Docker Container stoppen
docker stop $(docker ps -q)

# Chroma Datenbank löschen (Neustart)
Remove-Item -Recurse -Force chroma_db
```

---

## 📁 DATEI-OPERATIONEN

```powershell
# Verzeichnis wechseln
cd "C:\Users\Student\OneDrive - orhunsuzer.com\Desktop\Praktikum\Mein Praktikum\chat_bot"

# Dateien auflisten
Get-ChildItem

# PDF-Dateien finden
Get-ChildItem *.pdf

# Logs anzeigen (wenn vorhanden)
Get-Content bot.log -Tail 20
```

---

## 🌐 NGROK KOMMANDOS

```powershell
# Ngrok Tunnel starten (in separatem Terminal)
ngrok http 8000

# Ngrok Status prüfen
curl http://127.0.0.1:4040/api/tunnels
```

---

## ⚠️ HÄUFIGE POWERSHELL FEHLER

### **Problem: "&&" funktioniert nicht**
```powershell
# FALSCH (Linux Syntax):
set TELEGRAM_TOKEN=xyz && python bot.py

# RICHTIG (PowerShell):
$env:TELEGRAM_TOKEN="xyz"; python bot.py
```

### **Problem: "Ausführungsrichtlinie"**
```powershell
# Falls Scripts blockiert werden:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Problem: "python nicht gefunden"**
```powershell
# Python Pfad prüfen:
where python
python --version

# Falls nicht installiert:
# Python von python.org herunterladen
```

---

## 🎯 NÜTZLICHE ALIASE (Optional)

```powershell
# Diese in PowerShell Profile einfügen ($PROFILE)
function Start-Bot {
    $env:TELEGRAM_TOKEN="7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w"
    $env:WEBHOOK_URL="https://d40087949776.ngrok-free.app"
    $env:OLLAMA_URL="http://localhost:11434"
    $env:OLLAMA_MODEL="llama3.2:3b"
    python -m uvicorn bot:app --host 0.0.0.0 --port 8000 --reload
}

# Dann einfach aufrufen mit:
Start-Bot
```

---

## 📊 MONITORING KOMMANDOS

```powershell
# CPU/Memory Usage
Get-Process python

# Netzwerk Connections
netstat -an | Select-String 8000

# Disk Space
Get-PSDrive C

# Bot Performance Log (falls implementiert)
Get-Content -Path "bot_performance.log" -Wait
```

---

**💡 TIPP:** Speichere dir die häufig verwendeten Kommandos in einer `.ps1` Datei für schnellen Zugriff!