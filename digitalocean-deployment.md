# 🌊 DIGITALOCEAN APP PLATFORM GUIDE

## WARUM DIGITALOCEAN?
- ✅ $5/Monat für Basic App
- ✅ Sehr gute Performance
- ✅ Einfaches Docker Deployment
- ✅ Integrierte Database Optionen

## DEPLOYMENT SCHRITTE

### 1. DIGITALOCEAN ACCOUNT
```
1. Gehe zu: https://www.digitalocean.com
2. Erstelle Account (GitHub Login möglich)
3. Gehe zu "Apps" → "Create App"
```

### 2. APP KONFIGURATION
```
Source: GitHub Repository
Branch: main
Autodeploy: Enabled

Build Command: (leer lassen - Docker wird automatisch erkannt)
Run Command: uvicorn bot:app --host 0.0.0.0 --port 8080
```

### 3. UMGEBUNGSVARIABLEN
```
Im App Settings → Environment Variables:
- TELEGRAM_TOKEN: 7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w
- OLLAMA_URL: https://dein-ollama-server.com
- OLLAMA_MODEL: llama3.2:3b
- WEBHOOK_URL: https://deine-app.ondigitalocean.app
- PORT: 8080
```

### 4. DOCKERFILE ANPASSEN
```dockerfile
# Port für DigitalOcean
ENV PORT=8080
EXPOSE $PORT
CMD ["uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8080"]
```

## KOSTEN
- **Basic:** $5/Monat (512MB RAM, 1 vCPU)
- **Professional:** $12/Monat (1GB RAM, 1 vCPU)