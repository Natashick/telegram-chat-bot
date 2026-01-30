Kundendokumentation

Diese Anleitung erklärt leicht verständlich, wie der Bot genutzt wird, welche Funktionen er bietet und wie Sie bei Fragen oder Problemen vorgehen können.

1. Zweck und Nutzen
- **"Worum geht es?** Der Bot beantwortet Fragen zu Automotive-Cybersecurity, z. B. zu ISO/SAE 21434 und UN R155.
- **Woher kommen die Antworten?** Aus lokal verarbeiteten, internen PDF-Dokumenten. Inhalte werden nicht an externe Cloud-Dienste gesendet.

 2. Wie benutze ich den Bot?
- **Starten**: Öffnen Sie den Bot in Telegram und drücken Sie die Taste Start oder senden Sie den Befehl `/start`.
- **Frage stellen**: Schreiben Sie Ihre Frage als Nachricht, z. B.: „Was ist TARA?“ oder „Welche Anforderungen stellt ISO/SAE 21434 an das CSMS?“
- **Antwort lesen**: Der Bot sendet eine oder mehrere Nachrichten. Längere Antworten werden automatisch in mehrere Seiten aufgeteilt (Navigation per Buttons).

 3. Wichtige Befehle
- **/start**: Begrüßung, kurze Anleitung und Hinweise zum Umgang mit vertraulichen Inhalten.
- **/help**: Kurzhilfe zur Nutzung und zu den wichtigsten Funktionen.
- **/status**: Zeigt den Index-/Datenstatus (nur informativ).
- **/screenshot**: Geführter Ablauf, um eine konkrete Seite eines Dokuments als Bild zu erhalten (Seite/Tabelle/Figur wählen).

Hinweis: Aus Sicherheitsgründen sind **Link-Vorschauen deaktiviert** und Antworten werden mit **Inhaltsschutz** gesendet (Weiterleiten/Kopieren/Speichern wird unterbunden; Screenshot-Schutz ist abhängig vom Telegram-Client).

 4. Gute Fragen – Beispiele
- „Erkläre TARA in zwei Sätzen.“
- „Nenne die Kernanforderungen der UN R155 zum Risikomanagement.“
- „Wie definiert ISO/SAE 21434 die Rollen im Cybersecurity-Managementsystem?“
- „Welche Unterschiede gibt es zwischen Bedrohung und Schwachstelle?“

Tipps:
- Stellen Sie Fragen präzise und fügen Sie bei Bedarf Fachbegriffe an.
- Wenn die Antwort nicht passt: Umformulieren, konkretisieren oder nachfragen („Bitte einfacher erklären.“).

 5. Screenshots von Seiten (optional)
- Senden Sie `/screenshot` und wählen Sie ein Dokument.
- Geben Sie danach Ihr Ziel an, z. B. „Seite 10“, „Tabelle 3“, „Figure H.3“ oder ein Stichwort.
- Der Bot erstellt eine Seitenansicht als PNG und sendet sie mit Inhaltsschutz.

Bitte beachten: Auch wenn der Bot Schutzmaßnahmen setzt, ist die Screenshot-Blockierung **geräte-/clientabhängig**. Behandeln Sie Inhalte stets vertraulich.

6. Sprachen
- Standardmäßig antwortet der Bot **auf Englisch**.
- Erkennt der Bot deutliche deutsche Formulierungen, antwortet er **auf Deutsch**.

7. Datenschutz und Vertraulichkeit
- Der Bot verarbeitet Dokumente **lokal**. Inhalte werden nicht in externe Cloud-APIs hochgeladen.
- Antworten und Screenshots werden mit **Schutzflag** gesendet (Weiterleiten/Kopieren/Speichern unterbunden; Screenshot-Schutz je nach Client).
- **Keine Link-Vorschau**: Externe Vorschauen sind deaktiviert.
- Bitte geben Sie **keine vertraulichen internen Informationen** in Anfragen ein, die nicht im Bot-Bestand enthalten sind.

8. Was tun bei Problemen?
- „Es kommt keine Antwort“: Senden Sie Ihre Frage erneut, präzisieren Sie den Begriff oder prüfen Sie `/status` (Index ggf. in Aufbau).
- „Unklare/zu lange Antwort“: Bitten Sie um eine kürzere Zusammenfassung („Kürzer, bitte.“) oder eine Liste („Stichpunkte, bitte.“).
- „Screenshot trifft nicht das Gesuchte“: Geben Sie Seite/Tabelle/Figur genauer an (z. B. „Figure 2“ statt „Abbildung“).

9. Grenzen des Systems
- **Kurze/zweideutige Fragen** können schwer zuordnen sein. Präzision hilft.
- **OCR-Qualität** variiert bei gescannten PDFs; Inhalte können unvollständig sein.
- **Lange Antworten** sind durch das Kontextfenster des Modells begrenzt; der Bot paginiert automatisch.

10. Kontakt
- Bei fachlichen Rückfragen oder Vorschlägen zur Verbesserung wenden Sie sich bitte an die betreuende Stelle/Ansprechperson in Ihrem Projekt.
