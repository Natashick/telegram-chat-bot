# Telegram PDF Chatbot - Deployment Guide

**Version:** 1.0  
**Date:** 2024-01-27  
**Status:** Final

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start](#2-quick-start)
3. [Production Deployment](#3-production-deployment)
4. [Configuration](#4-configuration)
5. [Monitoring & Maintenance](#5-monitoring--maintenance)
6. [Troubleshooting](#6-troubleshooting)
7. [Security Hardening](#7-security-hardening)
8. [Backup & Recovery](#8-backup--recovery)

---

## 1. Prerequisites

### 1.1 System Requirements

**Minimum Requirements**:
- **CPU**: 2 cores (x86_64 or ARM64)
- **RAM**: 4 GB
- **Disk**: 10 GB free space
- **OS**: Linux, macOS, Windows (with Docker)
- **Network**: Internet access for Telegram API

**Recommended Requirements**:
- **CPU**: 4+ cores (for better LLM performance)
- **RAM**: 8-16 GB
- **Disk**: 50+ GB (for large document collections)
- **GPU**: Optional (NVIDIA with CUDA for Ollama acceleration)

### 1.2 Software Dependencies

**Required**:
- Docker Engine 20.10+
- Docker Compose 2.0+
- Ollama (local or remote instance)

**Optional**:
- nginx/Caddy (reverse proxy)
- Git (for cloning repository)
- certbot (SSL certificates)

### 1.3 External Services

1. **Telegram Bot Token**:
   - Create bot via [@BotFather](https://t.me/BotFather)
   - Command: `/newbot`
   - Save the token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Public Webhook URL**:
   - Options:
     - Cloud VPS with public IP
     - ngrok/LocalTunnel (testing only)
     - Cloud platforms (Railway, Render, Fly.io)

3. **Ollama Instance**:
   - Install locally: `curl -fsSL https://ollama.ai/install.sh | sh`
   - Or use remote endpoint

---

## 2. Quick Start

### 2.1 Local Development Setup

**Step 1: Clone Repository**
```bash
git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot
```

**Step 2: Install Ollama**
```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve &

# Pull model
ollama pull qwen2.5:7b-instruct
```

**Step 3: Create `.env` File**
```bash
cat > .env << 'EOF'
# Telegram Configuration
TELEGRAM_TOKEN=your_bot_token_here
WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app
WEBHOOK_SECRET=my_secure_secret_123

# Ollama Configuration
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_NUM_CTX=2048

# Paths
PDF_DIR=/app/pdfs
CHROMA_DB_DIR=/app/chroma_db

# Performance
CHUNK_SIZE=800
CHUNK_OVERLAP=160
MAX_EXCERPTS=12
MAX_UPDATE_CONCURRENCY=10
INDEX_CONCURRENCY=1

# Features
OCR_ENABLED=0
PREINDEX_ENABLED=1
ENABLE_TITLE_INDEX=0
EOF
```

**Step 4: Add PDF Documents**
```bash
mkdir -p pdfs
cp /path/to/your/*.pdf pdfs/
```

**Step 5: Start with Docker Compose**
```bash
docker-compose up -d --build
```

**Step 6: Verify Deployment**
```bash
# Check health
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","webhook_configured":true}

# View logs
docker-compose logs -f bot
```

**Step 7: Test Bot**
1. Open Telegram
2. Search for your bot
3. Send `/start`
4. Ask a question: "What is ISO 21434?"

### 2.2 Using ngrok for Local Testing

**Install ngrok**:
```bash
# Download from https://ngrok.com/download
# Or via package manager:
brew install ngrok  # macOS
snap install ngrok  # Linux
```

**Start ngrok Tunnel**:
```bash
ngrok http 8000
```

**Update `.env` with ngrok URL**:
```bash
# Example output from ngrok:
# Forwarding: https://abc123def456.ngrok-free.app -> http://localhost:8000

# Update .env:
WEBHOOK_URL=https://abc123def456.ngrok-free.app
```

**Restart Bot**:
```bash
docker-compose restart bot
```

---

## 3. Production Deployment

### 3.1 Docker Compose Deployment (Recommended)

**docker-compose.yml** (production-ready):
```yaml
services:
  bot:
    build: .
    image: telegram-pdf-bot:latest
    restart: unless-stopped
    env_file:
      - .env
    environment:
      # Override specific settings for production
      LOG_LEVEL: INFO
      MAX_UPDATE_CONCURRENCY: 20
      INDEX_CONCURRENCY: 2
    volumes:
      - ./pdfs:/app/pdfs:ro  # Read-only for security
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs  # Optional: persist logs
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only (use reverse proxy)
    mem_limit: 12g
    cpus: "4.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - bot_network

  # Optional: Run Ollama in same stack
  ollama:
    image: ollama/ollama:latest
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "127.0.0.1:11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]  # For GPU support
    networks:
      - bot_network

volumes:
  ollama_data:

networks:
  bot_network:
    driver: bridge
```

**Deploy**:
```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Scale (if needed)
docker-compose up -d --scale bot=3  # Requires load balancer
```

### 3.2 Cloud Platform Deployment

#### 3.2.1 Railway

**railway.json**:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn bot:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Deploy Steps**:
1. Push code to GitHub
2. Create Railway project
3. Connect GitHub repository
4. Add environment variables
5. Deploy automatically

**Railway-specific `.env`**:
```bash
# Railway provides PORT automatically
WEBHOOK_URL=https://your-app.railway.app
OLLAMA_URL=https://your-ollama-instance.railway.app
```

#### 3.2.2 Fly.io

**fly.toml**:
```toml
app = "telegram-pdf-bot"
primary_region = "fra"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"
  OLLAMA_NUM_CTX = "2048"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.http_checks]]
    interval = "30s"
    timeout = "10s"
    grace_period = "60s"
    method = "GET"
    path = "/health"

[mounts]
  source = "chroma_data"
  destination = "/app/chroma_db"
```

**Deploy**:
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Create app
flyctl launch

# Set secrets
flyctl secrets set TELEGRAM_TOKEN=your_token_here
flyctl secrets set WEBHOOK_SECRET=your_secret

# Deploy
flyctl deploy
```

#### 3.2.3 DigitalOcean App Platform

**app.yaml**:
```yaml
name: telegram-pdf-bot
services:
  - name: bot
    dockerfile_path: Dockerfile
    github:
      repo: your-username/telegram-chat-bot
      branch: main
      deploy_on_push: true
    envs:
      - key: TELEGRAM_TOKEN
        scope: RUN_TIME
        type: SECRET
      - key: WEBHOOK_URL
        value: ${APP_URL}
      - key: OLLAMA_URL
        value: https://your-ollama-droplet:11434
    http_port: 8000
    instance_count: 1
    instance_size_slug: professional-xs
    routes:
      - path: /
    health_check:
      http_path: /health
```

### 3.3 Kubernetes Deployment

**k8s/deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: telegram-pdf-bot
  namespace: bots
spec:
  replicas: 2
  selector:
    matchLabels:
      app: telegram-pdf-bot
  template:
    metadata:
      labels:
        app: telegram-pdf-bot
    spec:
      containers:
      - name: bot
        image: telegram-pdf-bot:latest
        ports:
        - containerPort: 8000
        env:
        - name: TELEGRAM_TOKEN
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: telegram-token
        - name: WEBHOOK_URL
          value: "https://bot.example.com"
        - name: OLLAMA_URL
          value: "http://ollama-service:11434"
        volumeMounts:
        - name: pdfs
          mountPath: /app/pdfs
          readOnly: true
        - name: chroma-db
          mountPath: /app/chroma_db
        resources:
          requests:
            memory: "4Gi"
            cpu: "1000m"
          limits:
            memory: "12Gi"
            cpu: "4000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: pdfs
        persistentVolumeClaim:
          claimName: pdfs-pvc
      - name: chroma-db
        persistentVolumeClaim:
          claimName: chroma-db-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: telegram-pdf-bot
  namespace: bots
spec:
  selector:
    app: telegram-pdf-bot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: telegram-pdf-bot
  namespace: bots
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - bot.example.com
    secretName: bot-tls
  rules:
  - host: bot.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: telegram-pdf-bot
            port:
              number: 80
```

**Deploy**:
```bash
# Create namespace
kubectl create namespace bots

# Create secrets
kubectl create secret generic bot-secrets \
  --from-literal=telegram-token=your_token_here \
  -n bots

# Apply manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n bots
kubectl logs -f deployment/telegram-pdf-bot -n bots
```

### 3.4 Bare Metal / VPS Deployment

**System Setup** (Ubuntu 22.04):
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull model
ollama pull qwen2.5:7b-instruct
```

**Application Setup**:
```bash
# Clone repository
cd /opt
sudo git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot

# Create directories
sudo mkdir -p pdfs chroma_db logs

# Set permissions
sudo chown -R $USER:$USER .

# Copy PDFs
sudo cp /path/to/pdfs/*.pdf pdfs/

# Configure environment
sudo nano .env  # Add configuration

# Start bot
docker-compose up -d --build

# Enable auto-start
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram PDF Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/telegram-chat-bot
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### 3.5 Reverse Proxy Setup

#### nginx Configuration

**/etc/nginx/sites-available/telegram-bot**:
```nginx
upstream telegram_bot {
    server localhost:8000;
}

server {
    listen 80;
    server_name bot.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name bot.example.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/telegram-bot-access.log;
    error_log /var/log/nginx/telegram-bot-error.log;

    # Proxy Configuration
    location / {
        proxy_pass http://telegram_bot;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long LLM responses
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Health check endpoint (no auth)
    location /health {
        proxy_pass http://telegram_bot;
        access_log off;
    }
}
```

**Enable and Test**:
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d bot.example.com
```

#### Caddy Configuration

**Caddyfile**:
```caddy
bot.example.com {
    reverse_proxy localhost:8000 {
        # Long timeouts for LLM
        timeout 60s
    }
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }
    
    # Logging
    log {
        output file /var/log/caddy/telegram-bot.log
        format json
    }
}
```

**Start Caddy**:
```bash
sudo caddy run --config /etc/caddy/Caddyfile
```

---

## 4. Configuration

### 4.1 Environment Variables Reference

See [Configuration Reference](04_CONFIGURATION.md) for complete details.

**Essential Variables**:
```bash
# Required
TELEGRAM_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_URL=https://bot.example.com
WEBHOOK_SECRET=change_this_secret_123

# LLM
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_NUM_CTX=2048

# Paths
PDF_DIR=/app/pdfs
CHROMA_DB_DIR=/app/chroma_db
```

### 4.2 Production Configuration Examples

#### High Performance
```bash
# Increase concurrency
MAX_UPDATE_CONCURRENCY=30
INDEX_CONCURRENCY=4
EMBED_BATCH_SIZE=32

# Larger chunks for better context
CHUNK_SIZE=1200
CHUNK_OVERLAP=240
MAX_EXCERPTS=15

# More aggressive LLM
OLLAMA_NUM_CTX=4096
MAX_TOKENS=8192
```

#### Memory Constrained
```bash
# Reduce concurrency
MAX_UPDATE_CONCURRENCY=5
INDEX_CONCURRENCY=1
EMBED_BATCH_SIZE=8

# Smaller chunks
CHUNK_SIZE=600
CHUNK_OVERLAP=100
MAX_EXCERPTS=8

# Smaller LLM context
OLLAMA_NUM_CTX=1024
MAX_TOKENS=2048
```

#### Multi-Language Documents
```bash
# Enable OCR
OCR_ENABLED=1
OCR_CONCURRENCY=2

# Better filtering
MIN_PARA_CHARS=50
MIN_CHUNK_CHARS=80
OCR_NOISE_MAX_RATIO=0.6
```

---

## 5. Monitoring & Maintenance

### 5.1 Health Checks

**Manual Health Check**:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","webhook_configured":true}
```

**Automated Monitoring Script**:
```bash
#!/bin/bash
# health_monitor.sh

while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$STATUS" -ne 200 ]; then
        echo "$(date): Health check failed (HTTP $STATUS)"
        # Send alert (email, Slack, PagerDuty, etc.)
        docker-compose restart bot
    fi
    sleep 60
done
```

### 5.2 Logging

**View Logs**:
```bash
# Docker Compose
docker-compose logs -f bot
docker-compose logs --tail=100 bot

# Docker
docker logs -f telegram-pdf-bot

# Kubernetes
kubectl logs -f deployment/telegram-pdf-bot -n bots
```

**Log Rotation** (docker-compose.yml):
```yaml
services:
  bot:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**Centralized Logging** (optional):
```bash
# Ship logs to ELK/Loki
docker-compose logs -f bot | /opt/logstash/bin/logstash -f /etc/logstash/conf.d/bot.conf
```

### 5.3 Metrics

**Prometheus Metrics** (optional enhancement):

Add to `bot.py`:
```python
from prometheus_client import Counter, Histogram, generate_latest

queries_total = Counter('bot_queries_total', 'Total queries')
response_time = Histogram('bot_response_seconds', 'Response time')

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**Grafana Dashboard**:
- Query rate
- Response time (p50, p95, p99)
- Error rate
- Index size
- Memory/CPU usage

### 5.4 Maintenance Tasks

**Weekly**:
```bash
# Check disk space
df -h

# Review logs for errors
docker-compose logs --since 7d bot | grep ERROR

# Update Docker images
docker-compose pull
docker-compose up -d

# Clean unused Docker resources
docker system prune -f
```

**Monthly**:
```bash
# Update Ollama models
ollama pull qwen2.5:7b-instruct

# Backup ChromaDB
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/

# Review and optimize index
# (Rebuild if too fragmented)
```

**Quarterly**:
```bash
# Full system update
sudo apt update && sudo apt upgrade -y

# Review and update dependencies
pip list --outdated

# Security audit
docker scan telegram-pdf-bot:latest
```

---

## 6. Troubleshooting

### 6.1 Common Issues

#### Issue: Bot not responding

**Symptoms**: `/start` command doesn't work

**Diagnosis**:
```bash
# Check if container is running
docker ps | grep bot

# Check logs
docker-compose logs --tail=50 bot

# Check webhook status
curl http://localhost:8000/health

# Check Telegram webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

**Solutions**:
1. Verify `TELEGRAM_TOKEN` is correct
2. Ensure `WEBHOOK_URL` is publicly accessible
3. Check firewall rules (port 8000/443 open)
4. Restart bot: `docker-compose restart bot`

#### Issue: "Ollama not reachable" error

**Symptoms**: LLM calls fail

**Diagnosis**:
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# From Docker container
docker exec -it <container_id> curl http://host.docker.internal:11434/api/tags
```

**Solutions**:
1. Start Ollama: `ollama serve`
2. Fix Docker networking:
   - Linux: Use `OLLAMA_URL=http://172.17.0.1:11434`
   - macOS/Windows: Use `http://host.docker.internal:11434`
3. Pull model: `ollama pull qwen2.5:7b-instruct`

#### Issue: Slow responses (>30s)

**Symptoms**: Users complain about long wait times

**Diagnosis**:
```bash
# Check resource usage
docker stats

# Check LLM performance
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b-instruct","prompt":"Test"}'
```

**Solutions**:
1. Use smaller model: `llama3.2:1b` instead of `qwen2.5:7b`
2. Reduce context: `OLLAMA_NUM_CTX=1024`
3. Limit excerpts: `MAX_EXCERPTS=8`
4. Add GPU support for Ollama
5. Increase container resources

#### Issue: High memory usage (>12GB)

**Symptoms**: Container OOM kills

**Diagnosis**:
```bash
# Check memory
docker stats --no-stream

# Check ChromaDB size
du -sh chroma_db/
```

**Solutions**:
1. Reduce batch sizes: `EMBED_BATCH_SIZE=8`, `BATCH_SIZE=2`
2. Limit chunks: `MAX_INDEX_CHUNKS=5000`
3. Disable preindexing: `PREINDEX_ENABLED=0`
4. Use smaller embedding model
5. Increase Docker memory limit

#### Issue: PDF indexing fails

**Symptoms**: "No relevant information" for known content

**Diagnosis**:
```bash
# Check /status command in Telegram
# Look for: "Preindex: running=False, done=X/Y"

# Check logs for extraction errors
docker-compose logs bot | grep "extract\|index\|PDF"

# Test PDF extraction
docker exec -it <container> python -c "from pdf_parser import extract_paragraphs_from_pdf; print(len(extract_paragraphs_from_pdf('/app/pdfs/test.pdf')))"
```

**Solutions**:
1. Check PDF is valid: `pdfinfo pdfs/test.pdf`
2. Enable OCR: `OCR_ENABLED=1`
3. Manually trigger indexing: restart bot with `PREINDEX_ENABLED=1`
4. Check file permissions: `ls -la pdfs/`
5. Try different PDF (may be corrupted/encrypted)

### 6.2 Debug Mode

**Enable Debug Logging**:
```bash
# .env
LOG_LEVEL=DEBUG
DEBUG_PROMPTS=1
LOG_CHUNK_FILTER=1

# Restart
docker-compose restart bot
```

**Analyze Logs**:
```bash
# Search for specific errors
docker-compose logs bot | grep -i "error\|exception\|failed"

# Track user query
docker-compose logs bot | grep "Question from"

# Monitor LLM calls
docker-compose logs bot | grep "LLM"
```

### 6.3 Performance Profiling

**Measure Component Latency**:
```bash
# Add timing logs (temporary):
import time
start = time.time()
# ... operation ...
logger.info(f"Operation took {time.time() - start:.2f}s")
```

**Profile Memory**:
```python
# Add to bot.py
import psutil
import os

@app.get("/debug/memory")
async def memory_info():
    process = psutil.Process(os.getpid())
    return {
        "rss_mb": process.memory_info().rss / 1024 / 1024,
        "vms_mb": process.memory_info().vms / 1024 / 1024,
        "percent": process.memory_percent()
    }
```

---

## 7. Security Hardening

### 7.1 Secrets Management

**Never commit secrets to Git**:
```bash
# .gitignore (already included)
.env
*.pem
*.key
secrets/
```

**Use Docker Secrets** (Swarm/Kubernetes):
```yaml
# docker-compose-secrets.yml
services:
  bot:
    environment:
      TELEGRAM_TOKEN_FILE: /run/secrets/telegram_token
    secrets:
      - telegram_token

secrets:
  telegram_token:
    file: ./secrets/telegram_token.txt
```

**Use Environment Variable Services**:
- Railway: Built-in secrets
- Fly.io: `flyctl secrets set`
- Kubernetes: `kubectl create secret`

### 7.2 Network Security

**Firewall Rules** (ufw):
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**Docker Network Isolation**:
```yaml
# docker-compose.yml
services:
  bot:
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    networks:
      - internal

networks:
  internal:
    internal: true  # No external access
```

### 7.3 Container Security

**Run as Non-Root User** (Dockerfile):
```dockerfile
# Add to Dockerfile
RUN adduser --disabled-password --gecos '' botuser
USER botuser
```

**Read-Only Filesystem**:
```yaml
services:
  bot:
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./chroma_db:/app/chroma_db  # Only writable mount
```

**Security Scanning**:
```bash
# Scan image
docker scan telegram-pdf-bot:latest

# Trivy
trivy image telegram-pdf-bot:latest

# Snyk
snyk container test telegram-pdf-bot:latest
```

### 7.4 Access Control

**IP Whitelisting** (nginx):
```nginx
location / {
    # Allow only Telegram IP ranges
    # https://core.telegram.org/bots/webhooks#the-short-version
    allow 149.154.160.0/20;
    allow 91.108.4.0/22;
    deny all;
    
    proxy_pass http://telegram_bot;
}
```

**Rate Limiting** (nginx):
```nginx
limit_req_zone $binary_remote_addr zone=bot_limit:10m rate=10r/s;

location / {
    limit_req zone=bot_limit burst=20 nodelay;
    proxy_pass http://telegram_bot;
}
```

---

## 8. Backup & Recovery

### 8.1 Backup Strategy

**What to Backup**:
1. **ChromaDB** (`chroma_db/`) - Vector index
2. **PDFs** (`pdfs/`) - Source documents
3. **Configuration** (`.env`) - Settings
4. **Logs** (optional)

**Backup Script**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/telegram-bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="telegram-bot-backup-$DATE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop bot (optional, for consistency)
docker-compose stop bot

# Backup ChromaDB
tar -czf "$BACKUP_DIR/${BACKUP_NAME}-chroma.tar.gz" chroma_db/

# Backup PDFs (if they change)
tar -czf "$BACKUP_DIR/${BACKUP_NAME}-pdfs.tar.gz" pdfs/

# Backup config
cp .env "$BACKUP_DIR/${BACKUP_NAME}.env"

# Restart bot
docker-compose start bot

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_NAME"
```

**Automated Backups** (cron):
```bash
# crontab -e
0 2 * * * /opt/telegram-chat-bot/backup.sh >> /var/log/bot-backup.log 2>&1
```

### 8.2 Cloud Backup

**S3/R2 Backup**:
```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure

# Backup script
aws s3 sync chroma_db/ s3://my-bucket/telegram-bot/chroma_db/ --delete
aws s3 sync pdfs/ s3://my-bucket/telegram-bot/pdfs/ --delete
```

**Rclone to Multiple Clouds**:
```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure (interactive)
rclone config

# Backup to Google Drive, Dropbox, etc.
rclone sync chroma_db/ gdrive:telegram-bot/chroma_db/
```

### 8.3 Disaster Recovery

**Recovery Procedure**:

1. **Setup New Instance**:
```bash
# Clone repository
git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot

# Install dependencies (Docker, Ollama)
```

2. **Restore Configuration**:
```bash
# Copy backup .env
cp /backups/telegram-bot-backup-20240127.env .env
```

3. **Restore Data**:
```bash
# Extract ChromaDB
tar -xzf /backups/telegram-bot-backup-20240127-chroma.tar.gz

# Extract PDFs
tar -xzf /backups/telegram-bot-backup-20240127-pdfs.tar.gz
```

4. **Start Bot**:
```bash
docker-compose up -d --build
```

5. **Verify**:
```bash
# Health check
curl http://localhost:8000/health

# Test query
# (Send message to bot)

# Check /status for index stats
```

**Recovery Time Objective (RTO)**: 15-30 minutes  
**Recovery Point Objective (RPO)**: Last backup (daily)

---

## Appendix

### A. Deployment Checklist

**Pre-Deployment**:
- [ ] Telegram bot token obtained
- [ ] Public webhook URL secured
- [ ] Ollama installed and model pulled
- [ ] SSL certificate configured (production)
- [ ] PDFs prepared and uploaded
- [ ] `.env` file configured
- [ ] Firewall rules set

**Deployment**:
- [ ] Docker image built successfully
- [ ] Container started without errors
- [ ] Health check passes (`/health`)
- [ ] Webhook registered with Telegram
- [ ] Ollama connection verified
- [ ] Initial indexing completed
- [ ] Test query successful

**Post-Deployment**:
- [ ] Monitoring configured (logs, metrics)
- [ ] Backup script scheduled
- [ ] Documentation updated
- [ ] Team notified
- [ ] Load testing performed (if applicable)

### B. Resource Calculators

**Memory Requirements**:
```
Base: 2 GB
+ (PDFs in MB / 10) GB
+ (Concurrent users × 100 MB)
+ LLM model size
---
Example: 100 PDFs (500MB), 10 users, 7B model (4GB)
= 2 + 0.05 + 1 + 4 = ~7 GB
```

**Disk Requirements**:
```
PDFs: Original size
+ ChromaDB: ~10% of total text (embeddings)
+ Logs: ~100 MB/day
+ Docker images: ~5 GB
---
Example: 1 GB PDFs
= 1 + 0.1 + 3 (30 days logs) + 5 = ~9 GB
```

### C. Support Resources

- **Documentation**: [docs/README.md](../README.md)
- **GitHub Issues**: https://github.com/Natashick/telegram-chat-bot/issues
- **Configuration Reference**: [04_CONFIGURATION.md](04_CONFIGURATION.md)
- **Architecture**: [01_SYSTEM_ARCHITECTURE.md](01_SYSTEM_ARCHITECTURE.md)

---

**Document End**
