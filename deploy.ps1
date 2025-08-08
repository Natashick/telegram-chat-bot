# deploy.ps1
# AUTOMATISCHES DEPLOYMENT SCRIPT

Write-Host "🚀 TELEGRAM BOT DEPLOYMENT SCRIPT" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# 1. Git Repository check
if (!(Test-Path ".git")) {
    Write-Host "❌ Kein Git Repository gefunden!" -ForegroundColor Red
    Write-Host "Initialisiere Git..." -ForegroundColor Yellow
    git init
    git add .
    git commit -m "Initial commit for deployment"
    Write-Host "✅ Git Repository erstellt" -ForegroundColor Green
}

# 2. Erstelle Railway-Konfiguration
Write-Host "📄 Erstelle Railway Konfiguration..." -ForegroundColor Yellow

$railwayConfig = @"
{
  "`$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn bot:app --host 0.0.0.0 --port `$PORT",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100
  }
}
"@

$railwayConfig | Out-File -FilePath "railway.json" -Encoding UTF8
Write-Host "✅ railway.json erstellt" -ForegroundColor Green

# 3. Erstelle .gitignore
$gitignore = @"
__pycache__/
*.pyc
*.pyo
chroma_db/
.env
screenshot.png
user_state.json
*.log
.DS_Store
"@

$gitignore | Out-File -FilePath ".gitignore" -Encoding UTF8
Write-Host "✅ .gitignore erstellt" -ForegroundColor Green

# 4. Modifiziere Dockerfile für Cloud Deployment
Write-Host "🐳 Passe Dockerfile für Cloud an..." -ForegroundColor Yellow

$dockerfileContent = Get-Content "Dockerfile" -Raw
if ($dockerfileContent -notlike "*ENV PORT*") {
    $newDockerfile = $dockerfileContent -replace 'CMD \["uvicorn".*\]', @"
# Cloud deployment configuration
ENV PORT=8000
EXPOSE `$PORT
CMD ["sh", "-c", "uvicorn bot:app --host 0.0.0.0 --port `$PORT"]
"@
    $newDockerfile | Out-File -FilePath "Dockerfile" -Encoding UTF8 -NoNewline
    Write-Host "✅ Dockerfile für Cloud angepasst" -ForegroundColor Green
}

# 5. Nächste Schritte anzeigen
Write-Host ""
Write-Host "🎯 NÄCHSTE SCHRITTE:" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  GITHUB REPOSITORY ERSTELLEN:" -ForegroundColor Yellow
Write-Host "   - Gehe zu: https://github.com/new"
Write-Host "   - Repository Name: telegram-bot"
Write-Host "   - Dann ausführen:"
Write-Host "     git remote add origin https://github.com/DEIN-USERNAME/telegram-bot.git"
Write-Host "     git branch -M main"
Write-Host "     git push -u origin main"
Write-Host ""

Write-Host "2️⃣  RAILWAY DEPLOYMENT:" -ForegroundColor Yellow
Write-Host "   - Gehe zu: https://railway.app"
Write-Host "   - Login with GitHub"
Write-Host "   - New Project → Deploy from GitHub repo"
Write-Host "   - Wähle dein telegram-bot Repository"
Write-Host ""

Write-Host "3️⃣  UMGEBUNGSVARIABLEN SETZEN:" -ForegroundColor Yellow
Write-Host "   Im Railway Dashboard → Variables:"
Write-Host "   - TELEGRAM_TOKEN: 7724790025:AAE-a0iLKSuIDNct2volaJdncylmOp_L17w"
Write-Host "   - OLLAMA_URL: http://DEINE-EXTERNE-IP:11434/api/generate"
Write-Host "   - OLLAMA_MODEL: llama3.2:3b"
Write-Host "   - WEBHOOK_URL: https://dein-projekt.railway.app"
Write-Host ""

Write-Host "4️⃣  OLLAMA ÖFFENTLICH MACHEN:" -ForegroundColor Yellow
Write-Host "   Auf deinem PC:"
Write-Host "   `$env:OLLAMA_HOST='0.0.0.0:11434'"
Write-Host "   ollama serve"
Write-Host "   Router Port 11434 forwarding einrichten"
Write-Host ""

Write-Host "✅ DEPLOYMENT VORBEREITUNG ABGESCHLOSSEN!" -ForegroundColor Green
Write-Host "📝 Weitere Details in: railway-deployment.md" -ForegroundColor Cyan