Lastenheft
Funktionale Anforderungen.
1.	Beim Start des Systems werden alle PDF-Dateien im Projektordner automatisch eingelesen.
Da sämtliche verwendeten Dokumente bereits echten, durchsuchbaren Text enthalten, erfolgt die Verarbeitung rein textbasiert. Es muss eine OCR-Funktion für gescannte PDFs implementiert werden. Die Inhalte der Dokumente werden in kleinere, thematisch sinnvolle Textabschnitte („Text-Chunks“) aufgeteilt. Diese Abschnitte werden anschließend mithilfe eines Embedding-Modells in Zahlenvektoren umgewandelt und zusammen mit Metadaten (z. B. Dateiname und Position im Dokument) in der lokalen Vektordatenbank ChromaDB gespeichert. Dies ermöglicht dem Bot später eine schnelle und präzise semantische Suche.
2.	Bei einer Benutzeranfrage wird die Frage ebenfalls in einen Vektor umgerechnet und per semantischer Ähnlichkeitssuche mit den gespeicherten Vektoren abgeglichen. Die relevantesten Segmente werden als Kontext an das Sprachmodell übergeben, das daraus eine präzise Antwort generiert. Auf diese Weise entsteht eine schnelle und intelligente Dokumentensuche, die über reine Schlagwortsuche hinausgeht und inhaltliche Zusammenhänge erkennt.
3.	Prompt-Engineering: kombiniertes Kontext-Prompt an LLM.
4.	Telegram: Webhook-Betrieb, Inline-Buttons, Pagination bei langen Antworten.
5.	Neue Dokumente werden durch das Ablegen einer PDF-Datei im vorgesehenen Projektordner hinzugefügt. Eine Benutzer- oder Rollenverwaltung ist in dieser Version nicht vorgesehen.
6.	Es wird eine einfache, übersichtliche und moderne Benutzeroberfläche konfiguriert, die sowohl auf PC als auch mobil zugängig ist, nicht viele Ressourcen verbraucht und schnell Information liefert, die das jeweilige Thema so detailliert wie möglich abgedeckten, eine eingehende Analyse bietet oder die Ergebnisse zusammenfassen. Das System sowohl die Bilder als auch die Tabellen aus Unterlagen liefern müssen oder Screenshots von den Seiten der Dokumente schicken, ohne manuelle Sucher der Seiten zu erledigen.
Nichtfunktionelle Anforderungen
1.	Antwortvollständigkeit (ausreichend Token-Budget).
2.	Robustheit gegenüber OCR-Fehlern.
Einschränkungen
1.	LLM läuft lokal → abhängig von Hardware-Leistung.
2.	Kontextlimit des Modells → lange Dokumente müssen sinnvoll gesplittet oder gefiltert werden.
3.	Keine Live-Schutzmechanismen gegen falsche Inhalte → stattdessen Disclaimer.
4.	Für externe Verfügbarkeit kann später ein öffentlich erreichbarer Server benötigt (z. B. Cloud-VM oder Hosting).

