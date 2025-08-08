# ☁️ HEROKU DEPLOYMENT GUIDE

## WARUM HEROKU?
- ✅ Sehr etabliert und stabil
- ✅ Einfache CLI Tools
- ⚠️ Kostenpflichtig (ab $5/Monat)
- ✅ Gute Dokumentation

## VORBEREITUNG

### 1. HEROKU CLI INSTALLIEREN
```bash
# Windows:
# Downloade von: https://devcenter.heroku.com/articles/heroku-cli

# Nach Installation:
heroku login
```

### 2. PROJEKT ANPASSEN

#### A) Erstelle Procfile:
```
web: uvicorn bot:app --host 0.0.0.0 --port $PORT
```

#### B) Erstelle runtime.txt:
```
python-3.10.12
```

#### C) Erstelle .gitignore:
```
__pycache__/
*.pyc
chroma_db/
.env
screenshot.png
user_state.json
```

### 3. DEPLOYMENT
```bash
# App erstellen
heroku create dein-bot-name

# Umgebungsvariablen setzen
heroku config:set TELEGRAM_TOKEN=7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w
heroku config:set OLLAMA_URL=https://dein-ollama-server.com
heroku config:set OLLAMA_MODEL=llama3.2:3b

# Deployen
git add .
git commit -m "Deploy to Heroku"
git push heroku main

# Webhook URL setzen
heroku config:set WEBHOOK_URL=https://dein-bot-name.herokuapp.com
```

## KOSTEN
- **Eco Dyno:** $5/Monat (schläft nach 30min Inaktivität)
- **Basic Dyno:** $7/Monat (läuft 24/7)