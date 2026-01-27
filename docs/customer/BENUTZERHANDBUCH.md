# BENUTZERHANDBUCH
## Telegram PDF Chatbot für Automotive Cybersecurity

**Version**: 1.0  
**Datum**: 27.01.2024  
**Zielgruppe**: Endnutzer (Cybersecurity Engineers, Compliance Officers, Software Engineers)

---

## Inhaltsverzeichnis

1. [Erste Schritte](#1-erste-schritte)
2. [Befehle](#2-befehle)
3. [Fragen stellen](#3-fragen-stellen)
4. [Screenshot-Funktion](#4-screenshot-funktion)
5. [Tipps & Tricks](#5-tipps--tricks)
6. [Häufig gestellte Fragen (FAQ)](#6-häufig-gestellte-fragen-faq)
7. [Fehlerbehebung](#7-fehlerbehebung)
8. [Beispiele](#8-beispiele)
9. [Datenschutz & Sicherheit](#9-datenschutz--sicherheit)

---

## 1. Erste Schritte

### 1.1 Bot finden

1. Öffnen Sie Telegram auf Ihrem Gerät (Smartphone, Desktop, Web)
2. Suchen Sie nach dem Bot-Namen (von Ihrem Administrator bereitgestellt)
3. Tippen/Klicken Sie auf den Bot, um die Konversation zu öffnen

### 1.2 Bot starten

**Schritt 1**: Senden Sie `/start`

Der Bot antwortet mit einer Willkommensnachricht:

```
Willkommen beim Automotive-Cybersecurity-Bot.

So funktioniert es:
1️⃣ Drücke /Start.
2️⃣ Stelle deine Frage oder nutze /screenshot für Seiten/Bilder/Tabellen.
⚠️ Hinweis: Die Dokumenteninhalte sind vertraulich. Bitte keine Screenshots speichern oder weitergeben.
```

**Schritt 2**: Sie sehen eine Tastatur mit zwei Buttons:
- **[/start]** - Zurück zum Startmenü
- **[/screenshot]** - Screenshot-Funktion

### 1.3 Erste Frage stellen

Tippen Sie einfach eine Frage in natürlicher Sprache, z.B.:

```
Was ist TARA in ISO 21434?
```

Der Bot antwortet mit einer strukturierten Antwort basierend auf den indexierten PDF-Dokumenten.

---

## 2. Befehle

### 2.1 `/start` - Bot starten/neu starten

**Wann verwenden**: 
- Beim ersten Öffnen des Bots
- Um zum Hauptmenü zurückzukehren
- Um die Willkommensnachricht erneut anzuzeigen

**Beispiel**:
```
/start
```

**Antwort**: Willkommensnachricht + Tastatur mit Haupt-Buttons

---

### 2.2 `/help` - Hilfe anzeigen

**Wann verwenden**: Wenn Sie eine schnelle Übersicht der verfügbaren Befehle benötigen

**Beispiel**:
```
/help
```

**Antwort**:
```
Hilfe: /start (Startmenü) • /status (Index) • /screenshot (Seite/Bild/Tabelle).
```

---

### 2.3 `/status` - Systemstatus abfragen

**Wann verwenden**: 
- Um zu prüfen, ob Dokumente indexiert sind
- Um den Indexierungs-Fortschritt zu sehen
- Bei Problemen mit der Suche

**Beispiel**:
```
/status
```

**Antwort**:
```
VectorStore chunks: 1234
Persist dir: /app/chroma_db
Preindex: running=False, done=5/5
```

**Erklärung**:
- **VectorStore chunks**: Anzahl indexierter Textabschnitte
- **Persist dir**: Speicherort der Vektordatenbank
- **Preindex**: `running=True` bedeutet Indexierung läuft, `done=X/Y` zeigt Fortschritt

---

### 2.4 `/screenshot` - Screenshot-Funktion

**Wann verwenden**: 
- Wenn Sie eine bestimmte PDF-Seite als Bild sehen möchten
- Um Tabellen oder Abbildungen zu visualisieren
- Um den Kontext einer Textstelle zu verstehen

**Workflow**: Siehe [Kapitel 4](#4-screenshot-funktion)

---

## 3. Fragen stellen

### 3.1 Freitextfragen

Sie können Fragen in **natürlicher Sprache** stellen. Der Bot versteht Deutsch und Englisch.

**Deutsch**:
```
Was ist TARA?
Erkläre den Unterschied zwischen CAL 1 und CAL 4
Wie führe ich eine Risikoanalyse nach ISO 21434 durch?
```

**Englisch**:
```
What is TARA?
Explain the difference between CAL 1 and CAL 4
How do I conduct a risk analysis according to ISO 21434?
```

**Hinweis**: Der Bot erkennt automatisch die Sprache Ihrer Frage und antwortet in derselben Sprache.

---

### 3.2 Fragentypen

#### 3.2.1 Definitions-Fragen

**Format**: "Was ist X?" / "What is X?"

**Beispiele**:
```
Was ist TARA?
What is ECU?
Definiere Cybersecurity Assurance Level
```

**Antwort**: Der Bot findet die Definition in den Dokumenten und erklärt sie.

---

#### 3.2.2 Erklärungen

**Format**: "Erkläre X" / "Explain X"

**Beispiele**:
```
Erkläre die CAL-Stufen
Explain the TARA process
Beschreibe die Phasen von ISO 21434
```

**Antwort**: Ausführliche Erklärung mit mehreren Absätzen.

---

#### 3.2.3 Vergleiche

**Format**: "Was ist der Unterschied zwischen X und Y?"

**Beispiele**:
```
Was ist der Unterschied zwischen CAL 1 und CAL 4?
What's the difference between UNR 155 and ISO 21434?
Vergleiche Threat und Vulnerability
```

**Antwort**: Gegenüberstellung der beiden Begriffe.

---

#### 3.2.4 Anleitungen

**Format**: "Wie macht man X?" / "How to X?"

**Beispiele**:
```
Wie führe ich eine TARA durch?
How do I implement CAL 3 requirements?
Welche Schritte sind für eine Risikoanalyse nötig?
```

**Antwort**: Schritt-für-Schritt-Anleitung.

---

#### 3.2.5 Listen/Aufzählungen

**Format**: "Liste X auf" / "List X"

**Beispiele**:
```
Liste alle CAL-Stufen auf
List the phases of ISO 21434
Welche Rollen gibt es im RASIC-Modell?
```

**Antwort**: Nummerierte oder Bullet-Point-Liste.

---

### 3.3 Akronyme und Abkürzungen

Der Bot ist spezialisiert auf **technische Akronyme** im Automotive-Bereich.

**Erkannte Akronyme**:
- TARA, CAN, ECU, OEM, OBD, CVSS
- CAL, RASIC, FMEA, FTA
- ISO 21434, SAE J3061, UNR 155, UNR 156

**Beispiel**:
```
User: Was ist TARA?
Bot:  <b>TARA - Threat Analysis and Risk Assessment</b>
     
      TARA ist ein Prozess zur systematischen Identifizierung und Bewertung 
      von Cybersecurity-Bedrohungen in Fahrzeugsystemen...
```

**Tipp**: Bei Akronymfragen antwortet der Bot bevorzugt mit der **Definition**, nicht mit allgemeinen Erklärungen.

---

### 3.4 Lange Antworten

Wenn die Antwort länger als ~3600 Zeichen ist, wird sie automatisch **paginiert** (auf mehrere Nachrichten aufgeteilt).

**Navigation**:
- **[◀️ Prev]** - Vorherige Seite
- **[▶️ Next]** - Nächste Seite

**Beispiel**:
```
Bot:  <b>ISO 21434 - Übersicht</b>
     
      ISO/SAE 21434 ist ein internationaler Standard für Cybersecurity 
      Engineering im Automotive-Bereich...
     
      📄 1/3
      
      [◀️ Prev] [▶️ Next]
```

Klicken Sie auf **[▶️ Next]**, um die nächste Seite zu sehen.

---

## 4. Screenshot-Funktion

### 4.1 Übersicht

Die **Screenshot-Funktion** ermöglicht es, einzelne PDF-Seiten, Tabellen oder Abbildungen als Bild anzuzeigen.

**Anwendungsfälle**:
- Visualisierung von Diagrammen
- Anzeige komplexer Tabellen
- Kontext einer Textstelle verstehen

---

### 4.2 Workflow

**Schritt 1**: Senden Sie `/screenshot`

**Schritt 2**: Wählen Sie ein Dokument aus der Liste

Der Bot zeigt eine Tastatur mit allen verfügbaren PDF-Dokumenten:

```
📄 Bitte wählen Sie ein Dokument für den Screenshot:

[ISO_21434.pdf] [UNR_155.pdf]
[SAE_J3061.pdf] [CAN_Spec.pdf]
```

**Schritt 3**: Klicken Sie auf das gewünschte Dokument

**Schritt 4**: Geben Sie an, was Sie sehen möchten

Der Bot fragt:

```
Ausgewählt: ISO_21434.pdf

Geben Sie ein, was gerendert werden soll, z.B.:
• „Seite 10" oder „Page 10"
• „Tabelle 3" / „Table 3" oder „Abbildung 2" / „Figure 2"
• oder einen Titel-/Kapiteltext
```

**Schritt 5**: Senden Sie Ihr Ziel

---

### 4.3 Ziel-Formate

#### 4.3.1 Seitennummer

**Deutsch**: `Seite X`  
**Englisch**: `Page X`

**Beispiele**:
```
Seite 42
Page 10
Seite 123
```

**Ergebnis**: Die angegebene Seite wird als PNG-Bild gesendet.

---

#### 4.3.2 Tabelle

**Deutsch**: `Tabelle X` / `Tab. X`  
**Englisch**: `Table X` / `Tbl. X`

**Beispiele**:
```
Tabelle 3
Table A.2
Tab. H-5
Tabelle H.3
```

**Ergebnis**: Der Bot sucht nach der Tabelle im Dokument und zeigt die entsprechende Seite.

**Hinweis**: Wenn mehrere Tabellen zum Begriff passen, zeigt der Bot eine Auswahl:

```
Mehrere Treffer – bitte wählen:

[S.42: Tabelle 3 - CAL Requirements]
[S.87: Tabelle 3.1 - Risk Matrix]
[S.120: Tabelle H.3 - Test Cases]
```

---

#### 4.3.3 Abbildung

**Deutsch**: `Abbildung X` / `Abb. X` / `Fig. X`  
**Englisch**: `Figure X` / `Fig. X`

**Beispiele**:
```
Abbildung 2
Figure H.2
Fig. 4.3
Abbildung A-5
```

**Ergebnis**: Die Seite mit der Abbildung wird als Bild gesendet.

---

#### 4.3.4 Stichwortsuche

Sie können auch **Keywords** aus Titeln eingeben:

**Beispiele**:
```
System Overview
Threat Model
Risk Assessment Process
```

**Ergebnis**: Der Bot sucht nach Überschriften/Titeln, die das Keyword enthalten, und zeigt passende Treffer.

---

### 4.4 Beispiel-Session

```
User:  /screenshot

Bot:   📄 Bitte wählen Sie ein Dokument für den Screenshot:
       [ISO_21434.pdf] [UNR_155.pdf]

User:  [Klick auf ISO_21434.pdf]

Bot:   Ausgewählt: ISO_21434.pdf
       Geben Sie ein, was gerendert werden soll...

User:  Tabelle 3

Bot:   Mehrere Treffer – bitte wählen:
       [S.42: Tabelle 3 - CAL Requirements]
       [S.87: Tabelle 3.1 - Risk Matrix]

User:  [Klick auf S.42]

Bot:   📄 ISO_21434.pdf – Seite 42: Tabelle 3 - CAL Requirements
       [Bild der Seite wird gesendet]
```

---

## 5. Tipps & Tricks

### 5.1 Präzise Fragen stellen

**Tipp**: Je spezifischer Ihre Frage, desto präziser die Antwort.

**Weniger gut**:
```
Wie funktioniert Cybersecurity?
```

**Besser**:
```
Wie funktioniert TARA in ISO 21434?
```

**Noch besser**:
```
Welche Schritte umfasst der TARA-Prozess nach ISO 21434?
```

---

### 5.2 Kontext hinzufügen

**Tipp**: Nennen Sie den Standard oder das Dokument, wenn möglich.

**Beispiele**:
```
Was ist CAL in ISO 21434?
Erkläre die Risk Matrix nach UNR 155
Was sagt SAE J3061 über Bedrohungsmodellierung?
```

---

### 5.3 Schreibvarianten

Der Bot ist **tolerant** gegenüber Schreibvarianten:

**Akzeptiert**:
- `ISO 21434`, `ISO/SAE 21434`, `ISO21434`
- `TARA`, `T.A.R.A.`, `Tara`
- `CAL 1`, `CAL1`, `CAL-1`

**Beispiel**:
```
User: Was ist ISO/SAE 21434?
Bot:  [Gleiche Antwort wie bei "Was ist ISO 21434?"]
```

---

### 5.4 Mehrere Fragen nacheinander

Sie können mehrere Fragen hintereinander stellen. Der Bot behandelt jede Frage unabhängig.

**Beispiel**:
```
User: Was ist TARA?
Bot:  [Antwort zu TARA]

User: Und was ist CAL?
Bot:  [Antwort zu CAL]
```

**Hinweis**: Der Bot hat **kein Kontext-Gedächtnis** zwischen Fragen. "Und was ist X?" wird behandelt wie "Was ist X?".

---

### 5.5 Screenshot für Tabellen

**Tipp**: Bei komplexen Tabellen ist die Screenshot-Funktion oft hilfreicher als die Textantwort.

**Beispiel**:
```
User: /screenshot → ISO_21434.pdf → Tabelle A.1
Bot:  [Zeigt Tabelle als Bild mit allen Spalten/Zeilen]
```

---

### 5.6 Status prüfen bei langsamer Antwort

Wenn der Bot länger als 30 Sekunden nicht antwortet:

1. Senden Sie `/status`, um zu prüfen, ob Dokumente noch indexiert werden
2. Wenn `Preindex: running=True, done=2/5`, warten Sie, bis Indexierung abgeschlossen ist
3. Nach Abschluss (`done=5/5`) stellen Sie Ihre Frage erneut

---

## 6. Häufig gestellte Fragen (FAQ)

### 6.1 Allgemein

**F: Welche Dokumente kann der Bot durchsuchen?**  
A: Der Bot durchsucht alle PDF-Dokumente, die vom Administrator im konfigurierten Verzeichnis abgelegt wurden. Typischerweise sind das Standards wie ISO 21434, UNR 155, SAE J3061, etc.

**F: Kann ich eigene PDFs hochladen?**  
A: Nein, das Hochladen von PDFs über Telegram ist aus Sicherheitsgründen nicht möglich. Kontaktieren Sie Ihren Administrator, um Dokumente hinzufügen zu lassen.

**F: Werden meine Fragen gespeichert?**  
A: Nein, der Bot speichert keine Fragen oder Konversationsverläufe. Alle Verarbeitungen erfolgen in Echtzeit und temporär im Speicher.

**F: Kann der Bot auch Web-Seiten oder externe Quellen durchsuchen?**  
A: Nein, der Bot arbeitet ausschließlich mit den lokal indexierten PDF-Dokumenten. Es werden keine externen APIs oder Web-Suchen durchgeführt.

**F: Wie lange dauert eine Antwort?**  
A: Typischerweise 5-15 Sekunden, abhängig von der Komplexität der Frage und der Systemauslastung.

---

### 6.2 Fragen stellen

**F: Muss ich Fragen in ganzen Sätzen stellen?**  
A: Nein, Stichworte reichen oft aus, z.B. "TARA Definition" oder "CAL Levels". Vollständige Sätze können jedoch präzisere Antworten liefern.

**F: Versteht der Bot Umgangssprache?**  
A: Der Bot versteht natürliche Sprache, ist aber auf technische Fachbegriffe spezialisiert. Umgangssprachliche Formulierungen funktionieren, solange die Kernbegriffe enthalten sind.

**F: Kann ich mehrere Fragen in einer Nachricht stellen?**  
A: Ja, aber die Antwort kann weniger fokussiert sein. Für beste Ergebnisse stellen Sie eine Frage pro Nachricht.

**F: Was passiert, wenn der Bot die Antwort nicht kennt?**  
A: Der Bot antwortet mit "Keine relevanten Informationen gefunden." Das bedeutet, die Frage konnte nicht mit den verfügbaren Dokumenten beantwortet werden.

**F: Wie kann ich bessere Antworten bekommen?**  
A: 
- Verwenden Sie spezifische Fachbegriffe
- Nennen Sie den Standard (z.B. "ISO 21434")
- Formulieren Sie präzise Fragen
- Nutzen Sie Akronyme (TARA, CAL, etc.)

---

### 6.3 Screenshot-Funktion

**F: Kann ich mehrere Seiten gleichzeitig als Screenshot bekommen?**  
A: Nein, Screenshots werden einzeln gesendet. Sie können aber mehrere `/screenshot`-Anfragen nacheinander stellen.

**F: Warum finde ich eine Tabelle nicht?**  
A: 
- Stellen Sie sicher, dass die Tabelle eine Überschrift hat (z.B. "Tabelle 3")
- Versuchen Sie alternative Schreibweisen: "Table 3", "Tab. 3", "Tabelle H.3"
- Bei Problemen geben Sie direkt die Seitenzahl ein

**F: Kann ich Screenshots speichern oder weiterleiten?**  
A: Aus Sicherheitsgründen ist das **nicht empfohlen**. Screenshots sind mit `protect_content=True` markiert, was Screenshots und Weiterleitung in Telegram blockiert (auf unterstützten Plattformen).

**F: Ist die Screenshot-Qualität gut genug für detaillierte Diagramme?**  
A: Ja, Screenshots werden mit 180 DPI gerendert, was für die meisten technischen Diagramme und Tabellen ausreichend ist.

---

### 6.4 Technisches

**F: Warum antwortet der Bot manchmal langsam?**  
A: Mögliche Gründe:
- Hohe Systemauslastung (viele gleichzeitige Nutzer)
- Hintergrund-Indexierung läuft
- Komplexe Frage erfordert intensive Suche
- LLM-Modell generiert lange Antwort

**F: Was bedeutet "Indexierung gestartet im Hintergrund"?**  
A: Dokumente werden initial verarbeitet, um schnelle Suchen zu ermöglichen. Warten Sie 1-5 Minuten und prüfen Sie den Status mit `/status`.

**F: Warum zeigt `/status` "done=0/0"?**  
A: Entweder sind keine PDFs verfügbar, oder die Indexierung wurde nicht gestartet. Kontaktieren Sie Ihren Administrator.

**F: Kann ich den Bot auch offline nutzen?**  
A: Nein, der Bot benötigt eine Internetverbindung zu den Telegram-Servern. Die Dokumentenverarbeitung erfolgt jedoch lokal (keine Cloud-APIs).

---

### 6.5 Datenschutz & Sicherheit

**F: Sind meine Fragen vertraulich?**  
A: Ja. Alle Verarbeitungen (LLM, Suche) erfolgen **lokal** auf dem Server. Es werden keine Daten an externe Cloud-Services (OpenAI, Google, etc.) gesendet. Nur die Telegram-Kommunikation läuft über Telegram-Server.

**F: Kann der Bot auf andere Telegram-Chats zugreifen?**  
A: Nein, der Bot kann nur auf Nachrichten in Ihrem direkten Chat mit ihm zugreifen. Gruppen-Chats sind nicht unterstützt.

**F: Werden Dokumente mit anderen Nutzern geteilt?**  
A: Alle Nutzer greifen auf dieselbe Dokumentensammlung zu. Die Fragen und Antworten sind jedoch privat pro Nutzer.

**F: Wie sicher ist der Bot?**  
A: 
- Lokale LLM-Verarbeitung (keine Cloud-APIs)
- Verschlüsselte Telegram-Kommunikation (HTTPS)
- Keine Speicherung von Konversationen
- Content-Protection auf Screenshots
- Log-Sanitization (Tokens werden nicht protokolliert)

---

## 7. Fehlerbehebung

### 7.1 Bot antwortet nicht

**Problem**: Sie senden `/start` oder eine Frage, aber der Bot antwortet nicht.

**Lösungen**:
1. **Prüfen Sie Ihre Internet-Verbindung**: Der Bot benötigt Zugriff auf Telegram-Server.
2. **Warten Sie 30 Sekunden**: Der Bot könnte gerade ausgelastet sein.
3. **Senden Sie `/start` erneut**: Manchmal hilft ein Neustart der Konversation.
4. **Prüfen Sie den Bot-Status**: Fragen Sie Ihren Administrator, ob der Bot läuft.

---

### 7.2 "Keine relevanten Informationen gefunden"

**Problem**: Der Bot findet keine Antwort auf Ihre Frage.

**Lösungen**:
1. **Reformulieren Sie die Frage**: Verwenden Sie andere Begriffe oder Akronyme.
   - Statt: "Wie sichert man ein Auto ab?"
   - Versuchen: "Welche Cybersecurity-Maßnahmen erfordert ISO 21434?"

2. **Prüfen Sie die Schreibweise**: Akronyme sind case-sensitive.
   - `TARA` funktioniert, `tara` evtl. nicht

3. **Nutzen Sie Fachbegriffe**: Der Bot ist auf technische Sprache spezialisiert.
   - Statt: "Gefahr"
   - Verwenden Sie: "Bedrohung" oder "Threat"

4. **Prüfen Sie Dokumentenverfügbarkeit**: 
   - Senden Sie `/status`
   - Wenn `chunks: 0`, sind keine Dokumente indexiert. Kontaktieren Sie Ihren Administrator.

5. **Frage ist zu allgemein**: Spezifizieren Sie den Kontext.
   - Statt: "Was ist Risiko?"
   - Besser: "Was ist Risiko im Kontext von ISO 21434?"

---

### 7.3 Screenshot nicht verfügbar

**Problem**: "Seite konnte nicht gerendert werden."

**Lösungen**:
1. **Prüfen Sie die Seitenzahl**: 
   - Senden Sie `/status` oder fragen Sie, wie viele Seiten das Dokument hat
   - Beispiel: Wenn das PDF 150 Seiten hat, existiert "Seite 200" nicht

2. **Versuchen Sie eine andere Seite**: Das Problem könnte seitenspezifisch sein.

3. **Verwenden Sie Seitenzahl statt Tabelle**: 
   - Statt: "Tabelle XY" (wenn nicht gefunden)
   - Versuchen: "Seite Z" (wenn Sie die Seite kennen)

4. **Dokument ist nicht lesbar**: Kontaktieren Sie Ihren Administrator. Das PDF könnte beschädigt oder verschlüsselt sein.

---

### 7.4 Antwort abgeschnitten

**Problem**: Die Antwort endet mitten im Satz oder mit "..."

**Lösungen**:
1. **Warten Sie auf Paginierung**: Bei langen Antworten folgen mehrere Seiten. Klicken Sie auf **[▶️ Next]**.

2. **Frage spezifischer stellen**: Sehr breite Fragen führen zu langen Antworten, die gekürzt werden müssen.
   - Statt: "Erkläre ISO 21434 komplett"
   - Besser: "Erkläre die TARA-Phase von ISO 21434"

3. **Mehrere Fragen stellen**: Teilen Sie komplexe Fragen auf.
   - Frage 1: "Was sind die Phasen von ISO 21434?"
   - Frage 2: "Erkläre die TARA-Phase im Detail"

---

### 7.5 Lange Wartezeiten (>30s)

**Problem**: Der Bot braucht sehr lange für eine Antwort.

**Lösungen**:
1. **Prüfen Sie den Status**: 
   ```
   /status
   ```
   - Wenn `Preindex: running=True`, läuft Hintergrund-Indexierung. Warten Sie ab.

2. **Vereinfachen Sie die Frage**: Komplexe Fragen benötigen mehr Zeit.
   - Statt: "Erkläre ausführlich alle CAL-Levels mit Beispielen und Anforderungen"
   - Besser: "Was ist CAL 1?"

3. **Warten Sie 1-2 Minuten**: Bei hoher Auslastung kann es länger dauern.

4. **Kontaktieren Sie Ihren Administrator**: Evtl. ist das System überlastet.

---

## 8. Beispiele

### 8.1 Definition abfragen

**Beispiel 1: TARA**
```
User:  Was ist TARA?

Bot:   <b>TARA - Threat Analysis and Risk Assessment</b>
      
       TARA ist ein Prozess zur systematischen Identifizierung, Analyse 
       und Bewertung von Cybersecurity-Bedrohungen in Fahrzeugsystemen. 
       Der Prozess umfasst folgende Schritte:
       
       1. <b>Threat Identification</b>: Identifikation potenzieller Bedrohungen
       2. <b>Impact Assessment</b>: Bewertung der Auswirkungen
       3. <b>Risk Determination</b>: Bestimmung des Risikos
       4. <b>Risk Treatment</b>: Definition von Maßnahmen
       
       TARA ist Teil der Konzeptphase (Concept Phase) von ISO 21434.
       
       <i>Quellen: ISO 21434, Kapitel 8</i>
```

---

**Beispiel 2: CAL**
```
User:  What is CAL?

Bot:   <b>CAL - Cybersecurity Assurance Level</b>
      
       CAL defines four levels of cybersecurity requirements (CAL 1-4) 
       in ISO 21434, where higher levels indicate more stringent 
       cybersecurity measures.
       
       <pre>
       Level | Description                | Use Case
       ------|----------------------------|--------------------------
       CAL 1 | Basic security             | Low risk components
       CAL 2 | Enhanced security          | Medium risk systems
       CAL 3 | High security              | High risk systems
       CAL 4 | Highest security           | Critical systems (e.g. braking)
       </pre>
       
       CAL is determined based on the TARA results (risk level).
       
       <i>Source: ISO 21434, Clause 10</i>
```

---

### 8.2 Vergleiche

**Beispiel: CAL 1 vs. CAL 4**
```
User:  Was ist der Unterschied zwischen CAL 1 und CAL 4?

Bot:   <b>Vergleich: CAL 1 vs. CAL 4</b>
      
       <b>CAL 1 (niedrigste Stufe)</b>:
       • Basismaßnahmen zur Cybersecurity
       • Geeignet für Komponenten mit niedrigem Risiko
       • Beispiel: Infotainment-System
       • Anforderungen: Code-Reviews, grundlegende Tests
       
       <b>CAL 4 (höchste Stufe)</b>:
       • Maximale Sicherheitsanforderungen
       • Für kritische Systeme mit hohem Risiko
       • Beispiel: Bremssystem, Lenksystem
       • Anforderungen: Formale Verifikation, Penetration-Tests, 
         umfassende Sicherheitsaudits
       
       <b>Hauptunterschiede</b>:
       1. Testtiefe: CAL 4 erfordert deutlich mehr Tests
       2. Dokumentation: CAL 4 benötigt vollständige Nachweise
       3. Entwicklungsprozess: CAL 4 hat strengere Prozessanforderungen
       4. Toolqualifizierung: CAL 4 erfordert qualifizierte Tools
```

---

### 8.3 Anleitungen

**Beispiel: TARA durchführen**
```
User:  Wie führe ich eine TARA durch?

Bot:   <b>TARA-Prozess: Schritt-für-Schritt-Anleitung</b>
      
       <b>Schritt 1: Asset Identification</b>
       • Identifiziere alle relevanten Assets (Daten, Funktionen, Komponenten)
       • Erstelle eine Asset-Liste
       • Bewerte die Kritikalität jedes Assets
       
       <b>Schritt 2: Threat Scenario Identification</b>
       • Nutze Threat-Kataloge (z.B. HEAVENS, EVITA)
       • Identifiziere Angriffsvektoren (Remote, Physical, etc.)
       • Dokumentiere Bedrohungsszenarien
       
       <b>Schritt 3: Impact Rating</b>
       • Bewerte Auswirkungen auf:
         - Sicherheit (Safety)
         - Finanzen
         - Operationen
         - Datenschutz
       • Vergebe Impact-Level (Negligible, Moderate, Major, Severe)
       
       <b>Schritt 4: Attack Path Analysis</b>
       • Analysiere Angriffspfade (Attack Trees)
       • Bestimme Attack Feasibility (Very Low, Low, Medium, High, Very High)
       
       <b>Schritt 5: Risk Determination</b>
       • Kombiniere Impact + Attack Feasibility → Risk Level
       • Nutze Risk Matrix aus ISO 21434
       
       <b>Schritt 6: Risk Treatment</b>
       • Entscheide für jedes Risiko:
         - Mitigate (Maßnahmen definieren)
         - Accept (Risiko akzeptieren)
         - Share (Risiko teilen)
         - Avoid (Änderung des Designs)
       
       <b>Schritt 7: Documentation</b>
       • TARA Report erstellen
       • Cybersecurity Requirements ableiten
       • CAL-Levels zuweisen
       
       <i>Referenz: ISO 21434, Clause 8 & 15</i>
```

---

### 8.4 Listen

**Beispiel: ISO 21434 Phasen**
```
User:  Liste die Phasen von ISO 21434 auf

Bot:   <b>ISO 21434 Lifecycle-Phasen</b>
      
       1. <b>Concept Phase</b>
          • Cybersecurity Goals definieren
          • TARA durchführen
          • Cybersecurity Requirements ableiten
       
       2. <b>Product Development Phase</b>
          • Design & Implementation
          • Integration & Verification
          • Cybersecurity Validation
       
       3. <b>Production Phase</b>
          • Manufacturing Controls
          • Cybersecurity Monitoring
       
       4. <b>Operations & Maintenance Phase</b>
          • Incident Response
          • Vulnerability Management
          • Software Updates
       
       5. <b>End of Cybersecurity Support / Decommissioning</b>
          • End-of-Life Planung
          • Datenvernichtung
       
       <i>Jede Phase hat spezifische Anforderungen und Outputs.</i>
```

---

### 8.5 Screenshot-Beispiel

**Beispiel: Tabelle anzeigen**
```
User:  /screenshot

Bot:   📄 Bitte wählen Sie ein Dokument für den Screenshot:
       [ISO_21434.pdf] [UNR_155.pdf]

User:  [Klick auf ISO_21434.pdf]

Bot:   Ausgewählt: ISO_21434.pdf
       Geben Sie ein, was gerendert werden soll, z.B.:
       • „Seite 10" oder „Page 10"
       • „Tabelle 3" / „Table 3"

User:  Table A.1

Bot:   📄 ISO_21434.pdf – Seite 87: Table A.1 - Risk Matrix
       [PNG-Bild der Seite wird gesendet, zeigt vollständige Risk Matrix]
```

---

## 9. Datenschutz & Sicherheit

### 9.1 Datenverarbeitung

**Wo werden Daten verarbeitet?**
- **100% lokal**: LLM (Ollama), Embeddings, Suche, PDF-Verarbeitung
- **Nur Telegram-API**: Nachrichten-Übertragung (verschlüsselt via HTTPS)
- **Keine Cloud-APIs**: OpenAI, Google, Azure, AWS, etc. werden **NICHT** verwendet

**Datenspeicherung**:
- **Temporär** (während Verarbeitung): Fragen, Antworten, Zwischenergebnisse
- **Permanent**: Indexierte Dokumente (Vektoren, Metadaten) in lokaler Datenbank
- **Nicht gespeichert**: Konversationsverläufe, User-Fragen nach Antwort

---

### 9.2 Vertraulichkeit

**Sind meine Fragen vertraulich?**  
Ja, mit folgenden Einschränkungen:
- Telegram-Server sehen die Nachrichtenübertragung (Ende-zu-Ende-Verschlüsselung für Bots nicht möglich)
- Server-Administratoren können Logs einsehen (empfohlene Praxis: Logs nicht persistent speichern)
- Telegram-Bot-API ist TLS-verschlüsselt

**Best Practice**:
- Stellen Sie keine Fragen mit personenbezogenen Daten (Namen, IDs, etc.)
- Nutzen Sie nur technische Fachbegriffe

---

### 9.3 Content-Protection

**Screenshot-Schutz**:
- Alle Nachrichten haben `protect_content=True` gesetzt
- Verhindert:
  - Screenshots in Telegram (auf unterstützten Plattformen)
  - Weiterleitung von Nachrichten
  - Speicherung von Medien

**Wichtig**: Dies ist eine Telegram-Funktion und kann auf manchen Plattformen umgangen werden. **Behandeln Sie alle Inhalte als vertraulich.**

---

### 9.4 DSGVO-Konformität

**Rechtsgrundlage**: Einwilligung (Art. 6 Abs. 1 lit. a DSGVO) durch Nutzung des Bots

**Betroffenenrechte**:
- **Auskunft**: Keine personenbezogenen Daten werden gespeichert
- **Löschung**: Nicht anwendbar (keine persistente Speicherung)
- **Widerspruch**: Nutzung des Bots einstellen

**Datenminimierung**: 
- Nur Telegram-User-ID wird temporär verarbeitet (für Session-State)
- Keine Namen, E-Mails, IP-Adressen gespeichert

---

### 9.5 Sicherheitshinweise

**Do's**:
- ✅ Stellen Sie Fragen zu technischen Standards
- ✅ Nutzen Sie Fachbegriffe
- ✅ Verwenden Sie den Bot nur für berufliche Zwecke
- ✅ Melden Sie verdächtige Aktivitäten Ihrem Administrator

**Don'ts**:
- ❌ Teilen Sie keine personenbezogenen Daten
- ❌ Laden Sie keine Screenshots weiter (wenn blockiert, Grund!)
- ❌ Nutzen Sie den Bot nicht für nicht-technische Fragen
- ❌ Geben Sie den Bot-Zugang nicht an unbefugte Personen weiter

---

## Anhang

### A. Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **TARA** | Threat Analysis and Risk Assessment |
| **CAL** | Cybersecurity Assurance Level (1-4) |
| **ISO 21434** | Internationaler Standard für Automotive Cybersecurity |
| **UNR 155** | UN-Regelung für Cybersecurity Management |
| **ECU** | Electronic Control Unit (Steuergerät) |
| **CAN** | Controller Area Network (Fahrzeug-Bus) |
| **OEM** | Original Equipment Manufacturer (Fahrzeughersteller) |
| **RASIC** | Responsible, Accountable, Supportive, Informed, Consulted |

---

### B. Kontakt & Support

**Bei technischen Problemen**:
- Prüfen Sie zunächst diese FAQ und Fehlerbehebung
- Senden Sie `/status` zur Diagnose
- Kontaktieren Sie Ihren Administrator mit:
  - Beschreibung des Problems
  - Zeitpunkt des Auftretens
  - Ihre Frage/Befehl (falls relevant)
  - Screenshot (wenn möglich)

**Administrator-Kontakt**: [Von Ihrer Organisation bereitgestellt]

---

### C. Versionshinweise

**Version 1.0** (27.01.2024):
- Initial Release
- Unterstützte Sprachen: Deutsch, Englisch
- Kern-Features: Q&A, Screenshot, Paginierung
- Dokumentenunterstützung: PDF (mit OCR-Option)

**Geplante Features** (Roadmap):
- Multi-User-Dokument-Isolation
- Export-Funktion (Konversationen)
- Erweiterte Filter-Optionen
- Weitere Sprachen (FR, ES, IT)

---

**Ende des Benutzerhandbuchs**

Bei Fragen oder Anregungen kontaktieren Sie bitte Ihren Administrator.
