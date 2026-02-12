# Oracle Cloud Version - Branch Information

## 🌩️ oracle-version Branch

Diese Branch enthält die **Oracle Cloud Free Tier** optimierte Version des Telegram PDF Chatbots mit Groq API Integration.

---

## 🔀 Branch-Unterschiede

### Main Branch (Lokale PC-Version)
- **LLM**: Ollama + TinyLlama-1.1B (lokal)
- **Hosting**: Windows PC mit GPU/CPU
- **Verfügbarkeit**: Nur wenn PC läuft
- **Kosten**: 0 EUR (100% lokal)
- **Antwortzeit**: 60-120 Sekunden
- **Ressourcen**: CPU-intensiv

### oracle-version Branch (Cloud-Version)
- **LLM**: Groq API + llama-3.3-70b-versatile (cloud)
- **Hosting**: Oracle Cloud Free Tier (Ubuntu 22.04, 1 core, 1GB RAM)
- **Verfügbarkeit**: 24/7
- **Kosten**: 0 EUR (Free Tier)
- **Antwortzeit**: 2-5 Sekunden
- **Ressourcen**: CPU-effizient

---

## 📦 Dateiunterschiede

### Geänderte Dateien in oracle-version:

| Datei | Änderungen |
|-------|-----------|
| `llm_client.py` | + Groq API Backend<br>+ LLM_BACKEND=groq switch<br>+ Explizite ISO/SAE 21434 Akronym-Definitionen<br>+ Verbesserte Tabellen-Formatierung<br>- Entfernt: `low_vram` Option |
| `handlers1.py` | + ACRONYM_STRICT Flag<br>+ /help und /status Registrierung<br>+ Verbesserte Fehlerbehandlung<br>+ UnboundLocalError Fix |
| `bot.py` | + Webhook empty-URL guard<br>+ MAX_UPDATE_CONCURRENCY=2<br>+ BotCommand Menu (/start, /help, /status, /screenshot) |
| `.env` | + LLM_BACKEND=groq<br>+ GROQ_API_KEY<br>+ GROQ_MODEL=llama-3.3-70b-versatile<br>+ ACRONYM_STRICT=0<br>+ MAX_UPDATE_CONCURRENCY=2 |
| `vector_store.py` | + case-insensitive keyword search retry |
| `pdf_parser.py` | + Lazy pytesseract import |
| `.gitignore` | + .env Schutz<br>+ chroma_db/ und pdfs/ ignoriert |
| `.env.example` | + Vollständiges Template mit Groq Variablen |

### Neue Dateien:

- `docs/customer/BENUTZERHANDBUCH_ORACLE.md` - Oracle-spezifische Benutzerdoku
- `README_ORACLE.md` - Diese Datei (Branch-Info)

---

## 🚀 Schnellstart für oracle-version

### Voraussetzungen:
1. **Oracle Cloud Free Tier Account** (always-free.oracle.com)
2. **Groq API Key** (console.groq.com - kostenlos)
3. **Telegram Bot Token** (@BotFather)

### Installation:

```bash
# 1. Repository klonen und Branch wechseln
git clone <your-repo-url>
cd <repo-name>
git checkout oracle-version

# 2. Environment konfigurieren
cp .env.example .env
nano .env  # Füge TELEGRAM_TOKEN und GROQ_API_KEY hinzu

# 3. Dependencies installieren
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. PDFs hinzufügen
mkdir -p pdfs
# Kopiere deine PDF-Dateien nach pdfs/

# 5. Bot starten
python bot.py
```

### Systemd Service (für 24/7 Betrieb):

```bash
sudo nano /etc/systemd/system/tgbot.service
```

```ini
[Unit]
Description=Telegram PDF RAG Bot (Oracle Cloud)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="PATH=/home/ubuntu/venv/bin"
ExecStart=/home/ubuntu/venv/bin/python /home/ubuntu/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot.service
sudo systemctl start tgbot.service
sudo journalctl -u tgbot.service -f  # Logs anzeigen
```

---

## 🔑 Wichtige Umgebungsvariablen

```bash
# .env für oracle-version
LLM_BACKEND=groq                      # ← WICHTIG: auf "groq" setzen
GROQ_API_KEY=gsk_xxxxxxxxxxxxx       # ← Dein Groq API Key
GROQ_MODEL=llama-3.3-70b-versatile   # ← Empfohlenes Modell
TELEGRAM_TOKEN=123456:ABC-DEF        # ← Von @BotFather
WEBHOOK_URL=                          # ← Leer lassen für Polling
MAX_UPDATE_CONCURRENCY=2              # ← Niedrig für 1-core VM
INDEX_CONCURRENCY=1                   # ← 1 für Oracle Free Tier
ACRONYM_STRICT=0                      # ← 0 für flexible Akronym-Erkennung
```

---

## 📊 Performance-Vergleich

| Metrik | main (lokal) | oracle-version (cloud) |
|--------|-------------|----------------------|
| Antwortzeit | 60-120s | 2-5s |
| LLM-Qualität | Basic (1.1B) | Hochwertig (70B) |
| CPU-Last | Sehr hoch (100%) | Niedrig (10-20%) |
| RAM-Nutzung | 4-8 GB | 500-800 MB |
| Gleichzeitige Nutzer | 1 | 2-3 |
| Verfügbarkeit | Nur wenn PC läuft | 24/7 |
| Monatliche Kosten | 0 EUR (lokal) | 0 EUR (Free Tier) |

---

## 🐛 Bugfixes in oracle-version

1. **UnboundLocalError** in `handlers1.py` - `all_chunks` undefined in exception handler → Fixed
2. **Webhook crash** bei leerem `WEBHOOK_URL` → Guard hinzugefügt
3. **Ollama 'low_vram' Option** nicht supported → Entfernt
4. **HTML-Sanitization** zerstörte Tags → Whitelist-basierter Ansatz
5. **OCR pytesseract Import** blockiert Start → Lazy Import implementiert
6. **Tabellen-Ausrichtung** kaputt durch Doppel-Escaping → Fixed mit _sanitize_for_telegram
7. **Kurze Akronyme** blockiert (WP, RQ, CAL) → ACRONYM_STRICT=0 für Flexibilität

---

## 🆕 Neue Features in oracle-version

### 1. Groq API Integration
- 40x schnellere Antworten (2-5s statt 60-120s)
- 70B Parameter Modell (vs. 1.1B lokal)
- Bessere Antwortqualität

### 2. Explizite Akronym-Definitionen im Prompt
```python
# In _create_prompts()
acronym_logic = (
    "Falls Abkürzungen wie WP, RQ, RC oder CAL vorkommen, interpretiere sie im Kontext der ISO/SAE 21434:\n"
    "- WP: Work Product (Arbeitsprodukt)\n"
    "- RQ: Requirement (Anforderung)\n"
    "- RC: Recommendation (Empfehlung)\n"
    "- CAL: Cybersecurity Assurance Level\n"
    "- TARA: Threat Analysis and Risk Assessment\n"
)
```

### 3. Verbesserte Tabellen-Formatierung
- Kein Doppel-Escaping mehr
- `_sanitize_for_telegram` bewahrt `<pre>`-Block-Inhalte
- Perfekte Spaltenausrichtung in Telegram

### 4. Bot-Menü
- Alle Befehle direkt sichtbar unten links
- `/start`, `/help`, `/status`, `/screenshot`

### 5. ACRONYM_STRICT Flag
- `ACRONYM_STRICT=0` (Standard): LLM darf kurze Akronyme interpretieren
- `ACRONYM_STRICT=1`: Blockiert Antwort wenn Akronym nicht in chunks

---

## 🔧 Deployment auf Oracle Cloud

### Schritt-für-Schritt:

1. **Oracle Cloud VM erstellen** (Always Free Tier):
   - Shape: VM.Standard.E2.1.Micro (1 core, 1 GB RAM)
   - Image: Ubuntu 22.04
   - Boot Volume: 50 GB

2. **SSH-Zugriff**:
   ```bash
   ssh -i your-key.pem ubuntu@<oracle-vm-ip>
   ```

3. **System-Updates**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-venv git -y
   ```

4. **Repository klonen**:
   ```bash
   cd /home/ubuntu
   git clone <your-repo> .
   git checkout oracle-version
   ```

5. **Environment setup**:
   ```bash
   cp .env.example .env
   nano .env  # Füge Secrets hinzu
   ```

6. **Python Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. **PDFs übertragen**:
   ```bash
   # Von lokalem PC:
   scp -i your-key.pem *.pdf ubuntu@<oracle-vm-ip>:/home/ubuntu/pdfs/
   ```

8. **Systemd Service** (siehe oben)

9. **Firewall** (optional für Webhook):
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 8443/tcp  # Nur wenn Webhook
   sudo ufw enable
   ```

---

## 📚 Dokumentation

### Für Endnutzer:
- **[Benutzerhandbuch Oracle Version](docs/customer/BENUTZERHANDBUCH_ORACLE.md)**

### Für Entwickler:
- **[System Architecture](docs/technical/01_SYSTEM_ARCHITECTURE.md)**
- **[Deployment Guide](docs/technical/02_DEPLOYMENT_GUIDE.md)**
- **[API Documentation](docs/technical/03_API_DOCUMENTATION.md)**

### Für Projektmanager:
- **[Lastenheft](docs/lastenheft/LASTENHEFT.md)**
- **[Pflichtenheft](docs/pflichtenheft/PFLICHTENHEFT.md)**

---

## 🔐 Sicherheitshinweise

### ⚠️ NIEMALS committen:
- `.env` (enthält Secrets)
- `chroma_db/` (lokale Datenbank)
- `pdfs/` (oft vertraulich)

### ✅ Sicher committen:
- `.env.example` (Template ohne Secrets)
- Alle `.py` Dateien
- `requirements.txt`
- Dokumentation in `docs/`

### Secrets Management:
```bash
# Prüfen ob .env in .gitignore:
cat .gitignore | grep .env

# Secrets aus Git-Historie entfernen (falls committed):
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env' \
  --prune-empty --tag-name-filter cat -- --all
```

---

## 🤝 Contribution Guidelines

### Branch-Strategie:
- `main` - Lokale PC-Version (Ollama)
- `oracle-version` - Oracle Cloud Version (Groq API)

### Änderungen einreichen:
1. Branch aus `oracle-version` erstellen:
   ```bash
   git checkout oracle-version
   git checkout -b feature/your-feature
   ```

2. Änderungen committen:
   ```bash
   git add .
   git commit -m "feat: beschreibung"
   ```

3. Push und Pull Request:
   ```bash
   git push origin feature/your-feature
   ```

4. PR gegen `oracle-version` öffnen (NICHT gegen `main`!)

---

## 📞 Support

### Bei Problemen:
1. **Logs prüfen**:
   ```bash
   sudo journalctl -u tgbot.service -f
   ```

2. **Bot-Status**:
   ```bash
   sudo systemctl status tgbot.service
   ```

3. **Groq API Limits**:
   - Free Tier: 14,400 Requests/Tag
   - Check: console.groq.com

4. **Oracle Cloud**:
   - Dashboard: cloud.oracle.com
   - VM Console → Compute → Instances

---

## 📝 Changelog

### v2.0 (12.02.2026) - Oracle Cloud Edition
- ✅ Groq API Integration
- ✅ Akronym-Definitionen in Prompts
- ✅ Tabellen-Formatierung Fix
- ✅ Bot-Menü
- ✅ ACRONYM_STRICT Flag
- ✅ Performance: 95% schneller

### v1.0 (27.01.2024) - Initial Release
- ✅ Ollama + TinyLlama lokal
- ✅ ChromaDB Indexierung
- ✅ Screenshot-Funktion
- ✅ Multi-PDF Support

---

**Happy Hacking! 🚀**

Für Fragen: Öffne ein Issue oder kontaktiere den Maintainer.
