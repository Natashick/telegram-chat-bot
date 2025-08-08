#!/bin/bash
# START-SCRIPT FÜR RAILWAY DEPLOYMENT
# Zweck: Korrekte Behandlung der PORT Umgebungsvariable

# PORT Variable setzen (Railway gibt diese automatisch)
export PORT=${PORT:-8000}

echo "Starting bot on port: $PORT"

# Bot starten
exec uvicorn bot:app --host 0.0.0.0 --port $PORT
