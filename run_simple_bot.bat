@echo off
echo ========================================
echo    SIMPLE TELEGRAM BOT STARTER
echo ========================================
echo.

REM Check if TELEGRAM_TOKEN is set
if "%TELEGRAM_TOKEN%"=="" (
    echo ❌ TELEGRAM_TOKEN ist nicht gesetzt!
    echo.
    echo Setze deinen Token:
    set /p TELEGRAM_TOKEN="Gib deinen Telegram Bot Token ein: "
    echo.
)

echo 🤖 Starte Simple Bot...
echo 📱 Token: %TELEGRAM_TOKEN:~0,10%...
echo.

REM Install dependencies if needed
echo 📦 Installiere Dependencies...
pip install -r simple_requirements.txt

echo.
echo 🚀 Starte Bot...
python simple_bot.py

pause
