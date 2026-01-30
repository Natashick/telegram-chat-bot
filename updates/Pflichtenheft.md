Pflichtenheft

 1. Projektziel und Geltungsbereich
Dieses Pflichtenheft beschreibt die Anforderungen, Rahmenbedingungen und Abnahmekriterien für ein lokal betriebenes Frage-Antwort-System zu Automotive-Cybersecurity. Zielgruppe sind Auftraggeber, Fachbeteiligte und Entwickler. Dieses Dokument dient als verbindliche Grundlage für Umsetzung, Abnahme und spätere Erweiterungen.

2. Systembeschreibung (unverändert übernommen)
Das System lädt beim Start alle technische Dokumente als PDF ein, zerlegt sie in Textsegmente und speichert diese als Vektoren in der lokalen ChromaDB. Nutzenfragen werden semantisch mit den gespeicherten Segmenten abgeglichen und relevante Inhalte als Kontext an das lokales Ollama-Model (llama.3.2:1b) übergeben. Die Antworten werden ausschließlich aus den verfügbaren Unterlagen generiert und über eine einfache Telegram-Oberfläche ausgegeben, inklusive Pagination und Screenshot-Funktion. Das System läuft vollständig lokal in Docker-Container, erfolgt keine Cloud-Dienste und schützt alle vertrauliche Inhalte. Einschränkungen ergeben sich aus der verfügbaren Hardwareleistungen und der begrenzten Kontextlänge des Modells. 

 3. Anforderungen

 3.1 Musskriterien (unverändert übernommen)
1.	PDF-Dokumente automatisch verarbeiten
– Texte extrahieren, Abschnitte bilden, Embeddings erzeugen und in einer persistenten Datenbank speichern.
2.	Lokal funktionieren (Offline-fähig)
– LLM läuft über Ollama lokal;
– keine Cloud-Uploads.
3.	Nutzeranfragen über Telegram entgegennehmen
– Telegram mit Webhook;
– Antworten im Chat anzeigen.
4.	Relevante Dokumentpassagen wiederfinden
– semantische Suche über ChromaDB;
– Extraktion passender Absätze.
5.	Antworten mittels LLM generieren
– LLM baut Antwort aus Dokumentkontext;
– keine Halluzinationen (strikte Prompt-Kontrolle);
– LLM läuft lokal.
6.	Acronyme erkennen
– Begriffe wie TARA, CAN Bus, CAL, RQ, PR, CSMS erkennen;
– passende Definition im Dokument finden.
7.	Screenshots einzelner PDF-Seiten liefern
– Tabellen;
– Grafiken;
– Text.
8.	Sensible Daten schützen
– Logging-Filter;
– Schutzfunktionen in Telegram – protect_content=True zur Schutzfunktion;
– keine Weitergabe von PDFs.
9.	Als Docker-Container betreibbar sein
– reproduzierbare Installation;
– automatische Initialindexierung beim Start.

3.2 Kann Kriterien (unverändert übernommen)
1.	eine einfache Spracherkennung (DE/EN) durchführen;
2.	mehrere PDF-Dokumente gleichzeitig durchsuchen;
3.	sehr große Dokumente effizient verarbeiten (Chunking);
4.	OCR für gescannte PDFs nutzen (optional)

4. Randbedingungen und Annahmen
- Betrieb vollständig lokal in Docker-Containern (Bot, Ollama, persistente ChromaDB).
- Keine Nutzung externer Cloud-Dienste; Daten verbleiben im lokalen Umfeld.
- Hardware-Leistung (CPU/RAM) bestimmt Antwortzeit, OCR-Tempo und Modellgröße.
- Telegram wird im Webhook-Modus betrieben; Internetzugang für Telegram-API ist erforderlich.

5. Abnahmekriterien
- Startet lokal via Docker Compose; Healthcheck und Webhook sind funktionsfähig.
- PDFs werden automatisch eingelesen, geparst und in ChromaDB persistiert (sichtbar im `/status`). 
- Nutzerfragen über Telegram werden beantwortet; Paginierung funktioniert bei langen Antworten.
- Semantische Suche liefert relevante Absätze aus den bereitgestellten Dokumenten.
- LLM-Antworten entstehen ausschließlich aus Dokumentkontext; kein externer Versand von Inhalten.
- Acronyme (z. B. TARA, CAN Bus, CAL, RQ, PR, CSMS) werden erkannt und korrekt definiert.
- Screenshot-Funktion liefert Seitenbilder (Tabellen/Grafiken/Text) eines ausgewählten Dokuments.
- Schutzmaßnahmen aktiv: Logging-Filter, `disable_web_page_preview`, `protect_content=True`.
- System ist als Container reproduzierbar startbar; Initialindexierung erfolgt automatisch.

### 6. Betrieb, Wartung und Erweiterbarkeit
- Konfiguration über Umgebungsvariablen (z. B. Parser-/Retrieval-Parameter, Modellwahl).
- Austausch/Erweiterung der Dokumente durch erneutes Indizieren möglich.
- Modellwechsel über Ollama-Konfiguration (lokal pullen, Variable anpassen).
- Updates ohne Datenverlust dank persistenter ChromaDB.

### 7. Risiken und Grenzen
- Begrenzte Kontextlänge des Modells kann sehr lange Antworten einschränken.
- Leistungsabhängigkeit von verfügbarer Hardware (Latenz, Durchsatz).

