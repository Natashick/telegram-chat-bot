# LASTENHEFT
## Telegram PDF Chatbot - Anforderungsspezifikation

**Projekt**: Telegram PDF Chatbot für Automotive Cybersecurity  
**Version**: 1.0  
**Datum**: 27.01.2024  
**Status**: Finalisiert

---

## Inhaltsverzeichnis

1. [Zielbestimmung](#1-zielbestimmung)
2. [Produkteinsatz](#2-produkteinsatz)
3. [Stakeholder](#3-stakeholder)
4. [Funktionale Anforderungen](#4-funktionale-anforderungen)
5. [Nicht-funktionale Anforderungen](#5-nicht-funktionale-anforderungen)
6. [Systemschnittstellen](#6-systemschnittstellen)
7. [Qualitätsanforderungen](#7-qualitätsanforderungen)
8. [Technische Randbedingungen](#8-technische-randbedingungen)
9. [Abnahmekriterien](#9-abnahmekriterien)

---

## 1. Zielbestimmung

### 1.1 Musskriterien

#### M1: Semantische PDF-Dokumentensuche
Das System **MUSS** eine semantische Suche über mehrere PDF-Dokumente ermöglichen, die bedeutungsbasiert (nicht nur schlüsselwortbasiert) relevante Informationen findet.

**Begründung**: Kernfunktionalität für intelligente Dokumentenabfrage

---

#### M2: Telegram-Integration
Das System **MUSS** über eine Telegram-Bot-Schnittstelle bedienbar sein.

**Begründung**: Nutzerfreundlicher Zugang über etablierte Messaging-Plattform

---

#### M3: Lokale LLM-Verarbeitung
Das System **MUSS** ein lokal betriebenes Large Language Model (Ollama) nutzen, ohne externe Cloud-API-Aufrufe.

**Begründung**: Datenschutz, Vertraulichkeit sensibler Automotive-Dokumente

---

#### M4: Mehrsprachigkeit (DE/EN)
Das System **MUSS** Anfragen in Deutsch und Englisch verarbeiten und in der erkannten Sprache antworten.

**Begründung**: Internationale Nutzerschaft in Automotive-Branche

---

#### M5: Akronym-Erkennung
Das System **MUSS** technische Akronyme (z.B. TARA, CAN, ISO 21434) erkennen und deren Definitionen priorisieren.

**Begründung**: Zentral für technische Automotive-Cybersecurity-Dokumentation

---

### 1.2 Wunschkriterien

#### W1: OCR-Unterstützung
Das System **SOLLTE** gescannte PDFs via OCR verarbeiten können.

**Priorität**: Mittel

---

#### W2: Screenshot-Funktion
Das System **SOLLTE** einzelne PDF-Seiten, Tabellen und Abbildungen als Bild rendern können.

**Priorität**: Hoch (bereits implementiert)

---

#### W3: Multi-User-Support
Das System **SOLLTE** mehrere gleichzeitige Nutzer unterstützen (10-50 concurrent).

**Priorität**: Hoch

---

#### W4: Antwort-Paginierung
Das System **SOLLTE** lange Antworten auf mehrere Telegram-Nachrichten aufteilen.

**Priorität**: Hoch (bereits implementiert)

---

### 1.3 Abgrenzungskriterien

#### A1: Dokumenten-Upload
Das System wird **NICHT** Dokumente via Telegram hochladen können.  
**Grund**: Sicherheitsrisiko, Komplexität

---

#### A2: Benutzer-Authentifizierung
Das System wird **NICHT** Telegram-übergreifende Nutzerauthentifizierung implementieren.  
**Grund**: Telegram Bot API bietet bereits User-IDs

---

#### A3: Graphische Oberfläche
Das System wird **NICHT** eine Web-GUI bereitstellen.  
**Grund**: Telegram als UI, keine zusätzliche Oberfläche nötig

---

## 2. Produkteinsatz

### 2.1 Anwendungsbereiche

**Primär**:
- Automotive Cybersecurity Engineering
- ISO/SAE 21434 Compliance
- UN R155/R156 Dokumentation
- Technische Standards-Recherche

**Sekundär**:
- Interne Schulungen
- Wissensdatenbank-Abfragen
- Technische Dokumentation (allgemein)

---

### 2.2 Zielgruppen

| Gruppe | Profil | Nutzungshäufigkeit |
|--------|--------|-------------------|
| **Cybersecurity Engineers** | Technische Fachkräfte, vertraut mit ISO 21434 | Täglich |
| **Compliance Officers** | Regulatorische Experten | 2-3x/Woche |
| **Software Engineers** | Automotive-Software-Entwickler | Wöchentlich |
| **Projektmanager** | Technisches Management | Gelegentlich |

---

### 2.3 Betriebsbedingungen

**Umgebung**:
- Cloud-VPS oder On-Premise-Server
- Kontinuierlicher Betrieb (24/7)
- Netzwerkzugriff zu Telegram-Servern erforderlich

**Lastprofil**:
- Durchschnitt: 10-20 gleichzeitige Nutzer
- Spitzenlast: 50 Nutzer
- Antwortzeit: <15 Sekunden (95. Perzentil)

---

## 3. Stakeholder

### 3.1 Auftraggeber
**Automotive Cybersecurity Team**

**Erwartungen**:
- Schnelle Recherche in technischen Standards
- Datenschutz-konforme Lösung
- Minimale Betriebskosten

---

### 3.2 Entwickler
**DevOps/ML-Engineers**

**Verantwortlichkeiten**:
- Implementierung
- Deployment
- Wartung

---

### 3.3 Endnutzer
**Technische Mitarbeiter**

**Erwartungen**:
- Einfache Bedienung (Telegram)
- Präzise Antworten
- Schnelle Response

---

## 4. Funktionale Anforderungen

### FA-001: Dokumentenindexierung
**Priorität**: Muss  
**Beschreibung**: Das System muss PDF-Dokumente automatisch beim Start indexieren.

**Akzeptanzkriterien**:
- Automatische Indexierung aller PDFs im konfigurierten Verzeichnis
- Fortschrittsanzeige über `/status`-Befehl
- Versionserkennung (Re-Indexierung bei Änderung)

---

### FA-002: Semantische Suche
**Priorität**: Muss  
**Beschreibung**: Bedeutungsbasierte Suche, nicht nur Keyword-Matching.

**Akzeptanzkriterien**:
- Ähnliche Begriffe finden (z.B. "Threat" → "Bedrohung")
- Synonyme erkennen
- Cosine-Similarity ≥ 0.15 als Schwellwert

---

### FA-003: Telegram-Befehle
**Priorität**: Muss

| Befehl | Funktion |
|--------|----------|
| `/start` | Bot initialisieren |
| `/help` | Hilfe anzeigen |
| `/status` | Systemstatus abfragen |
| `/screenshot` | Seite/Tabelle/Abbildung rendern |

---

### FA-004: Freitextanfragen
**Priorität**: Muss  
**Beschreibung**: Nutzer können Fragen in natürlicher Sprache stellen.

**Beispiele**:
- "Was ist TARA in ISO 21434?"
- "Erkläre die CAL-Stufen"
- "Wie funktioniert eine Bedrohungsanalyse?"

---

### FA-005: Spracherkennung
**Priorität**: Muss  
**Beschreibung**: Automatische Erkennung Deutsch/Englisch basierend auf Anfrage.

**Kriterien**:
- Deutsche Keywords: `was`, `ist`, `wie`, `ä`, `ö`, `ü`
- Englisch: Fallback wenn keine deutschen Marker

---

### FA-006: Akronym-Priorisierung
**Priorität**: Muss  
**Beschreibung**: Definitionen für Akronyme bevorzugt anzeigen.

**Akronyme (Beispiele)**:
- TARA, CAN, ECU, OEM, CAL, RASIC
- ISO 21434, SAE J3061, UNR 155

**Mechanismus**:
- Regex-Pattern: `TERM - Definition`, `TERM: ...`, `TERM (...)`
- Scoring-Bonus für Treffer

---

### FA-007: Screenshot-Funktion
**Priorität**: Soll  
**Beschreibung**: Rendern von PDF-Seiten als Bild.

**Workflow**:
1. `/screenshot` → Dokumentenauswahl
2. Nutzer wählt Dokument
3. Nutzer gibt Ziel an ("Seite 10", "Tabelle 3")
4. Bot sendet Bild

---

### FA-008: Paginierung langer Antworten
**Priorität**: Soll  
**Beschreibung**: Antworten >3600 Zeichen werden auf mehrere Nachrichten aufgeteilt.

**Navigation**: Inline-Keyboard mit [◀️ Prev] [▶️ Next]

---

### FA-009: Hintergrund-Indexierung
**Priorität**: Soll  
**Beschreibung**: Indexierung läuft asynchron, blockiert nicht den Betrieb.

**Anforderung**: Concurrency-Control via Semaphore

---

### FA-010: Gesundheitscheck-Endpoint
**Priorität**: Muss  
**Beschreibung**: HTTP-Endpoint für Monitoring.

**Endpoint**: `GET /health`  
**Response**: `{"status": "healthy", "webhook_configured": true}`

---

## 5. Nicht-funktionale Anforderungen

### NFA-001: Performance - Antwortzeit
**Priorität**: Hoch  
**Anforderung**: 95% der Anfragen innerhalb von 15 Sekunden beantwortet.

**Messbar via**: Response-Time-Logs, Monitoring

---

### NFA-002: Performance - Durchsatz
**Priorität**: Mittel  
**Anforderung**: 10-50 gleichzeitige Nutzer unterstützen.

**Konfiguration**: `MAX_UPDATE_CONCURRENCY=20` (default)

---

### NFA-003: Zuverlässigkeit - Verfügbarkeit
**Priorität**: Hoch  
**Anforderung**: 99% Uptime (außer geplante Wartung).

**Maßnahmen**: Docker Restart-Policy, Health Checks

---

### NFA-004: Skalierbarkeit - Dokumentenanzahl
**Priorität**: Mittel  
**Anforderung**: 100-1000 PDFs, 10.000-100.000 Seiten unterstützen.

**Technologie**: ChromaDB HNSW-Index skaliert gut

---

### NFA-005: Sicherheit - Datenschutz
**Priorität**: Kritisch  
**Anforderung**: 100% lokale Verarbeitung, keine externen API-Aufrufe (außer Telegram).

**Maßnahmen**:
- Ollama lokal
- Embeddings lokal (sentence-transformers)
- ChromaDB lokal persistiert

---

### NFA-006: Sicherheit - Secrets-Management
**Priorität**: Hoch  
**Anforderung**: Telegram-Token, Webhook-Secret niemals hartkodiert oder geloggt.

**Maßnahmen**:
- Umgebungsvariablen
- `_CensorFilter` in Logs
- `.gitignore` für `.env`

---

### NFA-007: Sicherheit - Content-Protection
**Priorität**: Mittel  
**Anforderung**: Telegram-Nachrichten vor Screenshots/Weiterleitung schützen.

**Maßnahme**: `protect_content=True` auf Nachrichten

---

### NFA-008: Wartbarkeit - Modularität
**Priorität**: Hoch  
**Anforderung**: Klare Trennung der Komponenten.

**Module**:
- `bot.py` (Entry Point)
- `handlers1.py` (Message Handling)
- `llm_client.py` (LLM)
- `vector_store.py` (Vector DB)
- `pdf_parser.py` (PDF Extraction)
- `retrieval.py` (Search Logic)
- `indexer.py` (Indexing)
- `acronym_utils.py` (Utilities)

---

### NFA-009: Wartbarkeit - Konfigurierbarkeit
**Priorität**: Hoch  
**Anforderung**: Alle relevanten Parameter via Umgebungsvariablen steuerbar.

**Beispiele**: `CHUNK_SIZE`, `MAX_EXCERPTS`, `OLLAMA_MODEL`

---

### NFA-010: Benutzerfreundlichkeit - Einfachheit
**Priorität**: Hoch  
**Anforderung**: Intuitive Bedienung ohne Schulung.

**Maßnahmen**:
- Reply-Keyboard mit Haupt-Befehlen
- Klare Hilfetexte
- Beispiel-Fragen in `/start`

---

### NFA-011: Portabilität - Deployment
**Priorität**: Hoch  
**Anforderung**: Docker-basiertes Deployment auf Linux/macOS/Windows.

**Technologie**: Docker + Docker Compose

---

### NFA-012: Portabilität - Cloud-Plattformen
**Priorität**: Mittel  
**Anforderung**: Deployment auf Railway, Fly.io, DigitalOcean, AWS/Azure/GCP möglich.

**Status**: Dokumentiert in Deployment Guide

---

### NFA-013: Ressourcen - Memory
**Priorität**: Mittel  
**Anforderung**: ≤12 GB RAM im Normalbetrieb.

**Konfiguration**: Docker `mem_limit: 12g`

---

### NFA-014: Ressourcen - CPU
**Priorität**: Mittel  
**Anforderung**: 2-4 CPU-Kerne für performanten Betrieb.

**Konfiguration**: Docker `cpus: "2.0"`

---

### NFA-015: Erweiterbarkeit - Neue Modelle
**Priorität**: Mittel  
**Anforderung**: Einfacher Wechsel des LLM-Modells.

**Maßnahme**: `OLLAMA_MODEL` Umgebungsvariable

---

### NFA-016: Erweiterbarkeit - Neue Sprachen
**Priorität**: Niedrig  
**Anforderung**: Erweiterung um weitere Sprachen (FR, ES, IT) möglich.

**Architektur**: Language-Detection-Logik modular in `handlers1.py`

---

### NFA-017: Dokumentation
**Priorität**: Hoch  
**Anforderung**: Vollständige technische und Benutzer-Dokumentation.

**Umfang**:
- System Architecture
- Deployment Guide
- API Documentation
- Configuration Reference
- Lastenheft/Pflichtenheft
- Benutzerhandbuch

---

## 6. Systemschnittstellen

### 6.1 Telegram Bot API
**Typ**: Externe REST-API (HTTPS)  
**Protokoll**: Webhook (POST) + Polling (fallback)  
**Endpoints**: `/sendMessage`, `/sendPhoto`, `/setWebhook`, etc.

---

### 6.2 Ollama API
**Typ**: Lokale REST-API (HTTP)  
**Protokoll**: HTTP POST  
**Endpoints**: `/api/chat`, `/api/generate`, `/api/tags`

---

### 6.3 ChromaDB
**Typ**: Eingebettete Bibliothek (Python)  
**Speicher**: SQLite + Parquet-Dateien  
**Persistenz**: Lokales Dateisystem

---

### 6.4 Tesseract OCR
**Typ**: Lokales Binary  
**Interface**: `pytesseract` Python-Wrapper  
**Sprachen**: Englisch, Deutsch

---

## 7. Qualitätsanforderungen

### 7.1 Funktionale Eignung
**Ziel**: System löst die gestellten Aufgaben korrekt.

**Metriken**:
- Retrieval Precision: ≥80% relevante Chunks
- LLM Accuracy: ≥90% korrekte Antworten (manuelles Review)

---

### 7.2 Zuverlässigkeit
**Ziel**: System arbeitet stabil und fehlerfrei.

**Metriken**:
- Uptime: ≥99%
- Fehlerrate: <1% der Anfragen
- Crash-Rate: <1/Woche

---

### 7.3 Effizienz
**Ziel**: Schnelle Antworten bei akzeptablem Ressourcenverbrauch.

**Metriken**:
- P50 Latency: <10s
- P95 Latency: <15s
- Memory: <12 GB
- CPU: <80% Auslastung (Durchschnitt)

---

### 7.4 Benutzbarkeit
**Ziel**: Einfache Bedienung für technische Nutzer.

**Metriken**:
- Time-to-First-Answer: <30 Sekunden (inkl. Onboarding)
- Support-Anfragen: <5% der Nutzer
- User Satisfaction: ≥4/5 Sterne

---

## 8. Technische Randbedingungen

### 8.1 Hardware
**Minimum**: 2 CPU-Kerne, 4 GB RAM, 10 GB Disk  
**Empfohlen**: 4 CPU-Kerne, 8-16 GB RAM, 50 GB Disk

---

### 8.2 Software
**OS**: Linux (Ubuntu 22.04+), macOS 12+, Windows 10+ (via Docker)  
**Docker**: Engine 20.10+, Compose 2.0+  
**Ollama**: Latest stable version  
**Python**: 3.11+ (in Container)

---

### 8.3 Netzwerk
**Bandbreite**: ≥10 Mbit/s (Up/Down)  
**Latenz**: <100ms zu Telegram-Servern  
**Firewall**: Port 80/443 (Webhook), Port 11434 (Ollama, lokal)

---

### 8.4 Externe Dienste
**Telegram**: Verfügbarkeit abhängig von Telegram-Infrastruktur  
**Domain/SSL**: HTTPS-Endpoint erforderlich (ngrok für Testing ok)

---

## 9. Abnahmekriterien

### 9.1 Funktionale Tests

#### Test 1: Basis-Q&A
**Eingabe**: "Was ist TARA?"  
**Erwartung**: Definition von TARA (Threat Analysis and Risk Assessment)  
**Status**: ✅ Bestanden

---

#### Test 2: Mehrsprachigkeit
**Eingabe**: "What is ISO 21434?" (Englisch)  
**Erwartung**: Englische Antwort  
**Status**: ✅ Bestanden

---

#### Test 3: Screenshot
**Eingabe**: `/screenshot` → Dokument auswählen → "Seite 10"  
**Erwartung**: PNG-Bild von Seite 10  
**Status**: ✅ Bestanden

---

#### Test 4: Paginierung
**Eingabe**: "Erkläre ISO 21434 ausführlich"  
**Erwartung**: Lange Antwort mit [Prev/Next]-Buttons  
**Status**: ✅ Bestanden

---

#### Test 5: Status-Abfrage
**Eingabe**: `/status`  
**Erwartung**: Chunk-Anzahl, Indexierungs-Fortschritt  
**Status**: ✅ Bestanden

---

### 9.2 Nicht-funktionale Tests

#### Test 6: Performance
**Szenario**: 10 gleichzeitige Anfragen  
**Erwartung**: Alle Antworten innerhalb 20 Sekunden  
**Status**: ✅ Bestanden

---

#### Test 7: Datenschutz
**Test**: Wireshark-Analyse während Anfrage  
**Erwartung**: Nur Traffic zu Telegram, kein Cloud-LLM-Aufruf  
**Status**: ✅ Bestanden

---

#### Test 8: Ressourcen
**Szenario**: 1 Stunde Dauerbetrieb, 20 Anfragen  
**Erwartung**: Memory <12 GB, CPU <90%  
**Status**: ✅ Bestanden

---

#### Test 9: Verfügbarkeit
**Szenario**: 7 Tage Betrieb  
**Erwartung**: <1 Ausfall, Health-Check immer 200 OK  
**Status**: ⏳ In Produktion zu testen

---

### 9.3 Abnahme-Checkliste

- [x] Alle Musskriterien erfüllt (M1-M5)
- [x] Wunschkriterien erfüllt (W2, W3, W4)
- [x] Funktionale Tests bestanden (Test 1-5)
- [x] Nicht-funktionale Tests bestanden (Test 6-8)
- [x] Dokumentation vollständig
- [ ] Produktions-Deployment erfolgreich (7-Tage-Test ausstehend)

**Abnahmedatum**: TBD (nach 7-Tage-Produktionstest)

---

## Anhang

### A. Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Akronym** | Abkürzung (z.B. TARA, CAN, ISO) |
| **Chunk** | Textabschnitt für Vektorsuche (Standard: 800 Wörter) |
| **Embedding** | Vektordarstellung von Text (384-dimensional) |
| **Semantic Search** | Bedeutungsbasierte Suche (vs. Keyword-Matching) |
| **LLM** | Large Language Model (z.B. Llama 3.2, Qwen 2.5) |
| **Ollama** | Lokales LLM-Framework (GPU/CPU-Support) |
| **ChromaDB** | Open-Source Vector Database |
| **Webhook** | HTTP-Callback für Telegram-Updates |

---

### B. Referenzen

- ISO/IEC 25010: Qualitätsmodell für Software
- DIN 69901: Projektmanagement
- IEEE 830: Software Requirements Specification
- ISO 21434: Automotive Cybersecurity
- Telegram Bot API: https://core.telegram.org/bots/api

---

**Dokument-Ende**
