#!/bin/bash
# START-SCRIPT FÜR RAILWAY DEPLOYMENT
# Zweck: Korrekte Behandlung der PORT Umgebungsvariable

# PORT Variable setzen (Railway gibt diese automatisch)
export PORT=${PORT:-8000}

echo "=== BOT STARTUP ==="
echo "Port: $PORT"
echo "Working directory: $(pwd)"
echo "Files in directory:"
ls -la

# Python Environment prüfen
echo "Python version: $(python --version)"
echo "Pip packages:"
pip list

# Bot starten mit Debug-Info
echo "Starting bot..."
exec uvicorn bot:app --host 0.0.0.0 --port $PORT --log-level debug
