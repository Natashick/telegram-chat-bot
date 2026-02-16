# BENUTZERHANDBUCH - ORACLE CLOUD VERSION
## Telegram PDF Chatbot für ISO/SAE 21434 Automotive Cybersecurity

**Version**: 2.0 (Oracle Cloud Edition)  
**Datum**: 12.02.2026  
**Zielgruppe**: Endnutzer (Cybersecurity Engineers, Compliance Officers, Software Engineers)  
**Plattform**: Oracle Cloud Free Tier + Groq API

---

## Inhaltsverzeichnis

1. [Was ist neu in der Oracle Version?](#1-was-ist-neu-in-der-oracle-version)
2. [Erste Schritte](#2-erste-schritte)
3. [Verfügbare Befehle](#3-verfügbare-befehle)
4. [Fragen stellen](#4-fragen-stellen)
5. [Akronyme und Abkürzungen](#5-akronyme-und-abkürzungen)
6. [Screenshot-Funktion](#6-screenshot-funktion)
7. [Tipps & Best Practices](#7-tipps--best-practices)
8. [Beispiele](#8-beispiele)
9. [Fehlerbehebung](#9-fehlerbehebung)
10. [Technische Details](#10-technische-details)

---

## 1. Was ist neu in der Oracle Version?

### 1.1 Hauptunterschiede zur lokalen PC-Version

| Feature | Lokale Version (main) | Oracle Version (oracle-version) |
|---------|----------------------|--------------------------------|
| **LLM Backend** | Ollama (TinyLlama-1.1B) lokal | Groq API (llama-3.3-70b-versatile) cloud |
| **Antwortzeit** | 60-120 Sekunden | 2-5 Sekunden |
| **Hosting** | Windows PC | Oracle Cloud Free Tier (Ubuntu 22.04) |
| **Ressourcen** | CPU-intensiv | CPU-effizient |
| **Verfügbarkeit** | PC muss laufen | 24/7 ohne lokalen PC |
| **LLM-Qualität** | Basis (1.1B Parameter) | Hochwertig (70B Parameter) |

### 1.2 Neue Features

✅ **Explizite Akronym-Definitionen**: WP, RQ, RC, CAL, TARA werden korrekt interpretiert  
✅ **Verbesserte Tabellen-Formatierung**: Perfekt ausgerichtete Ausgaben  
✅ **Bot-Menü**: Alle Befehle direkt sichtbar in Telegram  
✅ **Flexible Antworten**: Längere und detailliertere Erklärungen möglich  
✅ **Cloud-basiert**: Kein lokaler PC erforderlich  

---

## 2. Erste Schritte

### 2.1 Bot finden und starten

1. **Telegram öffnen** (Smartphone, Desktop, oder Web)
2. **Bot suchen** - Kontaktieren Sie Ihren Administrator für den Bot-Namen
3. **Bot starten** - Senden Sie `/start`

**Willkommensnachricht:**
```
Willkommen beim Automotive-Cybersecurity-Bot.

So funktioniert es:
1️⃣ Drücke /start.
2️⃣ Stelle deine Frage oder nutze /screenshot für Seiten/Bilder/Tabellen.
3️⃣ /status zeigt den Index-Status.
4️⃣ /help zeigt die Hilfe.

⚠️ Hinweis: Die Dokumenteninhalte sind vertraulich. Bitte keine Screenshots speichern oder weitergeben.
```

### 2.2 Bot-Menü

Das Bot-Menü (unten links in Telegram) zeigt alle verfügbaren Befehle:

- 🚀 `/start` - Startmenü öffnen
- ❓ `/help` - Hilfe anzeigen
- 📊 `/status` - Indexstatus prüfen
- 📸 `/screenshot` - Screenshot-Funktion

---

## 3. Verfügbare Befehle

### 3.1 Übersicht

| Befehl | Beschreibung | Beispiel |
|--------|--------------|----------|
| `/start` | Begrüßung und Tastatur anzeigen | `/start` |
| `/help` | Ausführliche Hilfe mit Tipps | `/help` |
| `/status` | Indexstatus und Dokumentenliste | `/status` |
| `/screenshot` | Screenshot-Modus aktivieren | `/screenshot` |

### 3.2 `/start` - Startbefehl

Zeigt Willkommensnachricht und interaktive Tastatur mit Buttons:
- **[/help]** - Hilfe-Button
- **[/status]** - Status-Button  
- **[/screenshot]** - Screenshot-Button

**Wann verwenden?** 
- Beim ersten Start des Bots
- Wenn Sie zur Hauptansicht zurückkehren möchten

### 3.3 `/help` - Hilfe

Zeigt detaillierte Anleitung:
- Wie man Fragen stellt
- Unterstützte Fragetypen
- Beispiele
- Screenshot-Funktion
- Tipps für bessere Ergebnisse

**Wann verwenden?**
- Sie sind unsicher, wie man eine Frage formuliert
- Sie möchten die Screenshot-Funktion verstehen
- Sie suchen nach Beispielen

### 3.4 `/status` - Indexstatus

Zeigt:
- ✅ Anzahl indizierter Dokumente
- 📄 Liste aller Dokumentnamen
- 🔄 Ob Indexierung gerade läuft
- 📊 Statistiken zur Dokumentensammlung

**Beispielausgabe:**
```
📊 Status

✅ 3 Dokumente indiziert:
• ISO_SAE_21434_2021.pdf
• UNR_155_Regulation.pdf
• TARA_Guideline.pdf

Bereit für Fragen!
```

**Wann verwenden?**
- Sie möchten prüfen, welche Dokumente verfügbar sind
- Nach Upload neuer PDFs durch Admin
- Bei unerwarteten Suchergebnissen

### 3.5 `/screenshot` - Screenshot-Modus

Aktiviert den Screenshot-Modus für Tabellen, Grafiken oder spezifische Seiten.

**Ablauf:**
1. Senden Sie `/screenshot`
2. Bot fragt: "Welche Seite / welches Thema suchst du?"
3. Geben Sie Ihre Suchanfrage ein (z.B. "Tabelle mit Risiken für CAN-Bus")
4. Bot zeigt relevante Seitenbereiche als Text im Kopier-Format

**Wichtig:** Die Funktion gibt **Text** zurück, keine Bilder. Ideal zum Kopieren von Tabellen!

---

## 4. Fragen stellen

### 4.1 So funktioniert die Suche

Der Bot verwendet **Retrieval-Augmented Generation (RAG)**:

1. **Semantische Suche** - Findet relevante Textstellen basierend auf Bedeutung
2. **Kontext-Extraktion** - Wählt die besten Textabschnitte aus
3. **LLM-Generierung** - Groq's llama-3.3-70b formuliert die Antwort auf Deutsch
4. **HTML-Formatierung** - Übersichtliche Darstellung mit **Fettdruck** und Tabellen

### 4.2 Fragetypen

#### 📖 Definitionsfragen
**Format:** "Was ist [Begriff]?" / "Was bedeutet [Abkürzung]?"

**Beispiele:**
```
Was ist das WP?
Was bedeutet TARA?
Was ist der Unterschied zwischen CAL 1 und CAL 2?
```

**Antwort-Stil:** Präzise Definition + Kontext aus ISO/SAE 21434

---

#### 🔍 Detailfragen
**Format:** "Wie funktioniert [Prozess]?" / "Welche [Anforderungen] gibt es für [Kontext]?"

**Beispiele:**
```
Wie funktioniert der Threat Analysis Prozess?
Welche Anforderungen gibt es für Secure Boot?
Welche Maßnahmen gibt es gegen Spoofing-Angriffe?
```

**Antwort-Stil:** Ausführliche Erklärung mit Schritten

---

#### 📊 Listenfragen
**Format:** "Liste alle [Items]" / "Zeige mir eine Übersicht über [Thema]"

**Beispiele:**
```
Liste alle Work Products für Konzept-Phase
Zeige mir alle Risiken für CAN-Bus
Liste alle CAL Levels mit Beschreibung
```

**Antwort-Stil:** Strukturierte Liste oder Tabelle

---

#### 🔗 Vergleichsfragen
**Format:** "Was ist der Unterschied zwischen [A] und [B]?"

**Beispiele:**
```
Was ist der Unterschied zwischen RQ und RC?
Unterschied zwischen Item-Definition und TARA
Vergleich ISO 21434 und UNR 155
```

**Antwort-Stil:** Gegenüberstellung mit Tabelle

---

#### 📄 Quellenangaben
**Format:** "Wo steht [Information] in [Dokument]?"

**Beispiele:**
```
Wo steht die Definition von Cybersecurity Goals?
In welchem Kapitel wird TARA beschrieben?
Welche Seite behandelt Risk Treatment?
```

**Antwort-Stil:** Kapitel-/Seitenangabe + EXCERPT-Referenzen

---

### 4.3 Tipps für bessere Antworten

✅ **Verwenden Sie Fachbegriffe** - Der Bot kennt die ISO/SAE 21434 Terminologie  
✅ **Seien Sie spezifisch** - "CAN-Bus Sicherheit" statt nur "Sicherheit"  
✅ **Nutzen Sie Akronyme** - WP, RQ, CAL, TARA werden erkannt  
✅ **Fragen Sie nach Quellen** - "Wo steht das in ISO 21434?"  
✅ **Mehrere Fragen nacheinander** - Der Bot hat keinen Kontext vorheriger Fragen (stateless)

❌ **Vermeiden Sie:**
- Zu allgemeine Fragen ("Was ist Cybersecurity?")
- Fragen zu Themen außerhalb der PDFs
- Mehrere Fragen in einer Nachricht (stellen Sie sie einzeln)

---

## 5. Akronyme und Abkürzungen

Der Bot ist spezialisiert auf **ISO/SAE 21434** und interpretiert Akronyme korrekt im Standard-Kontext.

### 5.1 Häufige Akronyme

| Akronym | Bedeutung (Deutsch) | Bedeutung (Englisch) |
|---------|---------------------|----------------------|
| **WP** | Arbeitsprodukt | Work Product |
| **RQ** | Anforderung | Requirement |
| **RC** | Empfehlung | Recommendation |
| **CAL** | Cybersecurity Assurance Level | Cybersecurity Assurance Level |
| **TARA** | Bedrohungsanalyse und Risikobewertung | Threat Analysis and Risk Assessment |
| **OEM** | Fahrzeughersteller | Original Equipment Manufacturer |
| **ECU** | Steuergerät | Electronic Control Unit |
| **CAN** | Controller Area Network | Controller Area Network |
| **V&V** | Verifikation und Validierung | Verification and Validation |

### 5.2 Beispiele Akronym-Fragen

```
Was ist das WP?
→ Antwort: WP steht für Work Product (Arbeitsprodukt). In ISO/SAE 21434 sind WPs dokumentierte Ergebnisse aus den verschiedenen Phasen...

Was bedeutet CAL?
→ Antwort: CAL steht für Cybersecurity Assurance Level. Es gibt vier CAL-Stufen (CAL 1-4), die das erforderliche Vertrauensniveau...

Welche WPs gibt es für Konzept-Phase?
→ Antwort: [Tabelle mit allen Work Products]
```

**Wichtig:** Der Bot **blockiert keine kurzen Akronyme** mehr (seit Version 2.0). Wenn das Akronym nicht in den Dokumenten vorkommt, gibt er eine entsprechende Meldung.

---

## 6. Screenshot-Funktion

### 6.1 Wann verwenden?

Die Screenshot-Funktion ist ideal für:
- 📊 **Tabellen** - Risikotabellen, Maßnahmen-Listen, Vergleiche
- 🔢 **Komplexe Strukturen** - Prozessdiagramme als Text, Hierarchien
- 📖 **Spezifische Seiten** - Wenn Sie wissen, dass Informationen in einem bestimmten Abschnitt stehen

### 6.2 Schritt-für-Schritt

**Schritt 1:** Senden Sie `/screenshot`

**Schritt 2:** Bot antwortet:
```
🖼️ Screenshot-Modus

Welche Seite / welches Thema suchst du?
Beispiele:
• "Tabelle mit Risiken für CAN-Bus"
• "Seite über Threat Scenarios"
• "UNR 155 Anforderungen"

Oder "abbrechen" zum Beenden.
```

**Schritt 3:** Geben Sie Ihre Suchanfrage ein:
```
Tabelle mit Risiken für CAN-Bus
```

**Schritt 4:** Bot zeigt Textabschnitte im `<pre>`-Format (monospacer Font, kopierfähig)

### 6.3 Beispiel-Ausgabe

```
📄 Relevante Abschnitte zu "Tabelle mit Risiken für CAN-Bus"

EXCERPT 1: ISO_SAE_21434_2021.pdf (Seite 89-91)

Risiko | Beschreibung                                    | Quelle        
-------|------------------------------------------------|---------------
R1     | Spoofing von CAN-Nachrichten                   | EXCERPT 1, 2  
R2     | Unzureichende Sicherheitsprozesse innerhalb... | EXCERPT 1, 2  
R3     | Unzureichende Risikobewertung                  | EXCERPT 3, 4  
...

(Kopierbar für Excel/Word)
```

### 6.4 Screenshot-Modus beenden

Senden Sie:
- `abbrechen` / `cancel` / `stop`
- `/start` - Zurück zum Hauptmenü

---

## 7. Tipps & Best Practices

### 7.1 Wie bekomme ich die besten Antworten?

#### ✅ **Verwenden Sie die richtige Fachsprache**

**Schlecht:**
```
Wie schütze ich das Auto?
```

**Gut:**
```
Welche Sicherheitsmaßnahmen gibt es für ECU-Kommunikation gemäß ISO 21434?
```

---

#### ✅ **Seien Sie spezifisch bei Dokumenten**

**Schlecht:**
```
Was steht im Standard?
```

**Gut:**
```
Was sagt ISO/SAE 21434 über Risk Treatment Decision?
```

---

#### ✅ **Fragen Sie nach konkreten Outputs**

**Beispiele:**
```
Gib mir eine Tabelle mit allen CAL Levels
Liste alle Work Products für die Konzept-Phase
Zeige mir die Struktur des TARA-Prozesses als Schritte
```

---

#### ✅ **Nutzen Sie Folge-Fragen**

**Beispiel-Dialog:**
```
Sie: Was ist TARA?
Bot: [Definition]

Sie: Welche Schritte umfasst TARA?
Bot: [Detaillierte Schritte]

Sie: Wo steht das in ISO 21434?
Bot: [Kapitel-Angabe]
```

---

### 7.2 Einschränkungen

❌ **Der Bot kann NICHT:**
- Kontext aus vorherigen Fragen merken (stateless)
- Informationen außerhalb der indizierten PDFs abrufen
- Grafiken oder Diagramme als Bilder zeigen
- Echte Screenshots erzeugen (nur Text)
- Mit externen APIs oder Datenbanken kommunizieren

✅ **Der Bot kann:**
- Alle Textinhalte aus den indizierten PDFs durchsuchen
- Tabellen als Text formatieren
- Akronyme und Abkürzungen erkennen
- Mehrsprachig antworten (Deutsch/Englisch)
- Fundstellen mit EXCERPT-Nummern angeben

---

## 8. Beispiele

### 8.1 Typische Frage-Antwort-Paare

#### Beispiel 1: Definition eines Work Products

**Frage:**
```
Was ist das WP-03-01?
```

**Antwort:**
```
WP-03-01: Cybersecurity Goals

Beschreibung:
Das Work Product WP-03-01 dokumentiert die Cybersecurity Goals, die während der Konzept-Phase definiert werden. Diese Goals beschreiben die zu erreichenden Sicherheitsziele auf Item-Ebene.

Quelle: ISO/SAE 21434:2021, Clause 9.3
```

---

#### Beispiel 2: Liste von Anforderungen

**Frage:**
```
Liste alle Anforderungen für TARA
```

**Antwort:**
```
Anforderungen für TARA (Threat Analysis and Risk Assessment):

RQ-05-01: Damage Scenarios identifizieren
RQ-05-02: Threat Scenarios entwickeln
RQ-05-03: Impact Rating durchführen
RQ-05-04: Attack Feasibility Rating durchführen
RQ-05-05: Risk Determination durchführen
RQ-05-06: Risk Treatment Decisions treffen

Quelle: ISO/SAE 21434:2021, Clause 10
```

---

#### Beispiel 3: Vergleich

**Frage:**
```
Was ist der Unterschied zwischen CAL 1 und CAL 4?
```

**Antwort:**
```
Unterschied zwischen CAL 1 und CAL 4:

CAL 1 (niedrigstes Assurance Level):
• Minimale Verifikation/Validierung
• Einfache Sicherheitsmaßnahmen
• Geringes Risiko

CAL 4 (höchstes Assurance Level):
• Umfassende V&V-Aktivitäten
• Formale Verifikation erforderlich
• Kritische Systeme (z.B. Brems-ECU)
• Höchstes Risiko

Quelle: ISO/SAE 21434:2021, Table 5
```

---

#### Beispiel 4: Tabelle im Screenshot-Modus

**Frage (nach `/screenshot`):**
```
Tabelle mit allen Work Products für Konzept-Phase
```

**Antwort:**
```
WP-ID    | Name                                | Phase      
---------|-------------------------------------|------------
WP-03-01 | Cybersecurity Goals                 | Konzept    
WP-03-02 | Cybersecurity Concept               | Konzept    
WP-03-03 | Cybersecurity Requirements          | Konzept    

[Kopierfähig für Excel/Word]
```

---

### 8.2 Komplexe Multi-Dokument-Suche

**Frage:**
```
Vergleiche die Anforderungen in ISO 21434 und UNR 155 für Secure Software Updates
```

**Antwort:**
```
Vergleich: Secure Software Updates

ISO/SAE 21434:
• RQ-14-02: Software Update Authentifizierung
• RQ-14-03: Software Update Integrität
• Clause 14 beschreibt detaillierte V&V-Anforderungen

UNR 155:
• Paragraph 7.2.4.3: Software Update Management
• Paragraph 7.3.2: Secure Communication
• Fokus auf Compliance und Typgenehmigung

Gemeinsamkeiten:
• Authentifizierung erforderlich
• Integrität muss gewährleistet sein
• Sichere Übertragungskanäle

Quellen:
• EXCERPT 1, 2: ISO_SAE_21434_2021.pdf
• EXCERPT 4: UNR_155_Regulation.pdf
```

---

## 9. Fehlerbehebung

### 9.1 Häufige Probleme

#### Problem: "Keine relevanten Informationen im Kontext"

**Ursachen:**
- Das Thema ist nicht in den indizierten PDFs vorhanden
- Die Frage ist zu allgemein formuliert
- Schreibfehler in Fachbegriffen

**Lösungen:**
1. Prüfen Sie mit `/status`, welche Dokumente indiziert sind
2. Formulieren Sie die Frage spezifischer
3. Verwenden Sie alternative Begriffe (z.B. "Arbeitsprodukt" statt "WP")

---

#### Problem: Bot antwortet sehr langsam oder gar nicht

**Ursachen:**
- Groq API überlastet (sehr selten)
- Oracle Cloud Instanz überlastet
- Netzwerkprobleme

**Lösungen:**
1. Warten Sie 30 Sekunden und versuchen Sie erneut
2. Senden Sie `/status` - wenn das funktioniert, ist der Bot aktiv
3. Kontaktieren Sie Ihren Administrator

---

#### Problem: Antwort ist unvollständig abgeschnitten

**Hinweis:**
Sie sehen dann am Ende:
```
Hinweis: Antwort möglicherweise unvollständig.
```

**Lösung:**
- Stellen Sie eine spezifischere Frage
- Fragen Sie in mehreren Teilfragen (z.B. erst "Was ist TARA?", dann "Welche Schritte umfasst TARA?")

---

#### Problem: Tabellen sehen ungleichmäßig aus

**Lösung:**
- Nutzen Sie die `/screenshot`-Funktion für Tabellen
- Telegram's `<pre>`-Tag verwendet monospacen Font für perfekte Ausrichtung
- Kopieren Sie die Tabelle in Excel/Word für weitere Bearbeitung

---

### 9.2 Kontakt zum Administrator

**Wann kontaktieren?**
- Bot antwortet mehr als 1 Minute nicht
- Fehlermeldung "LLM nicht erreichbar"
- Dokumente fehlen nach Upload
- Systematische falsche Antworten

**Was bereitstellen?**
- Screenshot der Fehlermeldung
- Ihre Frage (kopiert als Text)
- Ungefähre Uhrzeit des Fehlers
- Telegram Username (falls relevant)

---

## 10. Technische Details

### 10.1 Architektur

```
[Telegram User]
       ↓
[Telegram Bot API]
       ↓
[Python Bot (Ubuntu 22.04 auf Oracle Cloud)]
       ↓
[ChromaDB] → [Sentence Embeddings (all-MiniLM-L6-v2)]
       ↓
[RAG Pipeline] → Retrieval + Context
       ↓
[Groq API] → llama-3.3-70b-versatile (Cloud LLM)
       ↓
[Formatierte Antwort] → Zurück an Telegram
```

### 10.2 Systemspezifikationen

**Oracle Cloud Free Tier:**
- **CPU**: 1 Core (x86_64, 2.0-2.25 GHz)
- **RAM**: 1 GB + 8 GB Swap
- **Storage**: 50 GB Block Volume
- **OS**: Ubuntu 22.04 LTS
- **Uptime**: 24/7

**Software-Stack:**
- **Python**: 3.11+
- **ChromaDB**: 0.4.x (persistente Vektordatenbank)
- **Sentence-Transformers**: all-MiniLM-L6-v2 (Embedding-Modell)
- **Groq API**: llama-3.3-70b-versatile (LLM)
- **python-telegram-bot**: 20.x (Bot-Framework)

### 10.3 Datenschutz & Sicherheit

#### Was wird lokal verarbeitet?
- ✅ PDF-Dokumente (niemals hochgeladen)
- ✅ Vektorembeddings (ChromaDB lokal)
- ✅ Indexierung und Suche

#### Was geht an Groq API?
- ❌ **KEINE** kompletten Dokumente
- ❌ **KEINE** Telegram-Userdaten
- ✅ **NUR**: Ihre Frage + relevante Text-Excerpts (max. 2-3 kurze Absätze)

**Beispiel Groq-Request:**
```
FRAGE: Was ist das WP?
EXCERPTS:
[~200 Wörter aus ISO 21434 mit Definition von Work Product]

→ Groq verarbeitet nur diese 200 Wörter, nicht das gesamte 200-Seiten-Dokument
```

#### Telegram Content Protection

**PROTECT_CONTENT=1** aktiviert:
- ✅ Nachrichten können nicht weitergeleitet werden
- ✅ Screenshots sind erschwert (Telegram-Warnung)
- ✅ Kopieren funktioniert weiterhin (für legitime Nutzung)

---

### 10.4 Performance-Metriken

| Metrik | Oracle Cloud Version | Lokale PC Version |
|--------|---------------------|-------------------|
| **Antwortzeit (einfache Frage)** | 2-5 Sekunden | 60-120 Sekunden |
| **Antwortzeit (komplexe Frage)** | 5-8 Sekunden | 120-180 Sekunden |
| **Indexierung (1 PDF, 200 Seiten)** | 30-60 Sekunden | 20-40 Sekunden |
| **Gleichzeitige Nutzer** | 2-3 empfohlen | 1 |
| **Verfügbarkeit** | 99.5% (24/7) | Nur wenn PC läuft |

---

### 10.5 Kostenübersicht (monatlich)

**Oracle Cloud Free Tier:**
- Compute: **0 EUR** (Always Free)
- Storage: **0 EUR** (50 GB Always Free)
- Netzwerk: **0 EUR** (10 TB Egress/Monat)

**Groq API:**
- **Free Tier**: 14,400 Requests/Tag
- **Kosten**: 0 EUR bei normaler Nutzung
- **Überschreitung**: Sehr unwahrscheinlich (1 Nutzer = ~100 Requests/Tag)

**Telegram Bot API:**
- **Kosten**: 0 EUR (immer kostenlos)

**Gesamt: 0 EUR/Monat** bei normaler Nutzung im Free Tier

---

## 11. Kontakt & Support

### 11.1 Bei Problemen

**Technischer Support:**
- Kontaktieren Sie Ihren Bot-Administrator
- Geben Sie Screenshots und Fehlermeldungen weiter
- Nennen Sie Datum/Uhrzeit des Problems

**Fragen zur Nutzung:**
- Lesen Sie dieses Handbuch
- Probieren Sie `/help` im Bot
- Testen Sie verschiedene Formulierungen

### 11.2 Feedback

**Ihre Meinung hilft!**
- Welche Fragen funktionieren gut?
- Wo sind Antworten ungenau?
- Welche Features fehlen?

Teilen Sie Feedback mit Ihrem Administrator.

---

## 12. Changelog

### Version 2.0 (12.02.2026) - Oracle Cloud Edition

**Neue Features:**
- ✅ Groq API Integration (llama-3.3-70b-versatile)
- ✅ Explizite ISO/SAE 21434 Akronym-Definitionen in Prompts
- ✅ Verbesserte Tabellen-Formatierung (kein Doppel-Escaping)
- ✅ Bot-Menü mit allen Befehlen
- ✅ ACRONYM_STRICT=0 für flexible Interpretation
- ✅ Erhöhte Token-Limits (512/256 statt 256/128)

**Bugfixes:**
- 🐛 UnboundLocalError in global retrieval behoben
- 🐛 Webhook-Guard für leere URLs
- 🐛 HTML-Sanitization ohne Tag-Zerstörung
- 🐛 Lazy Import für pytesseract (OCR optional)

**Performance:**
- ⚡ 95% schnellere Antwortzeiten (2-5s statt 60-120s)
- ⚡ 99%+ Verfügbarkeit (Oracle Cloud 24/7)
- ⚡ Niedrigere CPU-Last (kein lokales LLM)

### Version 1.0 (27.01.2024) - Lokale PC-Version

- Initiales Release mit Ollama + TinyLlama
- Basis-RAG-Pipeline
- Screenshot-Funktion
- Multi-PDF-Indexierung

---

**Ende des Benutzerhandbuchs**

Viel Erfolg mit dem Automotive-Cybersecurity-Bot! 🚗🔒
