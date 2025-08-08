# 🚀 RAILWAY DEPLOYMENT GUIDE

## WARUM RAILWAY?
- ✅ Kostenlos für Hobby-Projekte (500h/Monat)
- ✅ Automatisches Deployment bei Git Push
- ✅ Einfache Umgebungsvariablen
- ✅ Integrierte Logs
- ✅ Unterstützt Docker

## SCHRITT-FÜR-SCHRITT ANLEITUNG

### 1. RAILWAY ACCOUNT ERSTELLEN
```
1. Gehe zu: https://railway.app
2. Klicke "Login" → "Login with GitHub"
3. Autorisiere Railway mit deinem GitHub Account
```

### 2. PROJEKT VORBEREITEN

#### A) Erstelle requirements.txt (falls nicht vorhanden):
```txt
fastapi==0.104.1
uvicorn==0.24.0
python-telegram-bot==20.6
aiohttp==3.9.0
chromadb==0.4.18
sentence-transformers==2.2.2
PyPDF2==3.0.1
pdf2image==1.16.3
pytesseract==0.3.10
Pillow==10.1.0
requests==2.31.0
numpy==1.24.3
ollama==0.3.3
```

#### B) Erstelle railway.json (Railway Konfiguration):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn bot:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100
  }
}
```

#### C) Modifiziere Dockerfile für Railway:
```dockerfile
# Am Ende hinzufügen:
ENV PORT=8000
EXPOSE $PORT
CMD uvicorn bot:app --host 0.0.0.0 --port $PORT
```

### 3. GITHUB REPOSITORY ERSTELLEN
```bash
# Initialisiere Git (falls noch nicht gemacht)
git init
git add .
git commit -m "Initial bot deployment"

# Erstelle GitHub Repository und pushe
git remote add origin https://github.com/DEIN-USERNAME/telegram-bot.git
git branch -M main
git push -u origin main
```

### 4. RAILWAY DEPLOYMENT
```
1. Gehe zu Railway Dashboard
2. Klicke "New Project"
3. Wähle "Deploy from GitHub repo"
4. Wähle dein Bot Repository
5. Railway deployed automatisch!
```

### 5. UMGEBUNGSVARIABLEN SETZEN
```
Im Railway Dashboard:
1. Klicke auf dein Projekt
2. Gehe zu "Variables" Tab
3. Füge hinzu:
   - TELEGRAM_TOKEN: 7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w
   - OLLAMA_URL: https://dein-ollama-server.com/api/generate
   - OLLAMA_MODEL: llama3.2:3b
   - WEBHOOK_URL: https://dein-projekt.railway.app
```

### 6. WEBHOOK URL ERHALTEN
```
Nach Deployment bekommst du URL wie:
https://dein-projekt-name.railway.app

Diese URL verwendest du als WEBHOOK_URL
```

## KOSTEN
- **Gratis:** 500 Stunden/Monat (≈16h/Tag)
- **Pro:** $5/Monat für unlimited
- Für persönliche Projekte meist kostenlos ausreichend!