# Anleitung für Kollaboratoren
## Arbeiten mit dem telegram-chat-bot Repository

**Datum**: 16.02.2026  
**Für**: Projektleiter und Kollaboratoren

---

## Inhaltsverzeichnis

1. [Ersteinrichtung](#1-ersteinrichtung)
2. [Repository-Struktur](#2-repository-struktur)
3. [Code ansehen](#3-code-ansehen)
4. [Repository klonen](#4-repository-klonen)
5. [Mit Branches arbeiten](#5-mit-branches-arbeiten)
6. [Änderungen vornehmen](#6-änderungen-vornehmen)
7. [Änderungshistorie ansehen](#7-änderungshistorie-ansehen)
8. [Nützliche Befehle](#8-nützliche-befehle)

---

## 1. Ersteinrichtung

### 1.1 Git installieren

**Windows:**
1. Git von https://git-scm.com/download/win herunterladen
2. Mit Standardeinstellungen installieren
3. Git Bash (oder Eingabeaufforderung) öffnen

**Mac:**
```bash
# Installation über Homebrew
brew install git
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install git
```

### 1.2 Git konfigurieren

```bash
# Name und E-Mail angeben (wie bei GitHub)
git config --global user.name "Ihr Name"
git config --global user.email "ihre-email@example.com"

# Einstellungen überprüfen
git config --list
```

---

## 2. Repository-Struktur

Das Repository enthält **zwei Hauptbranches**:

| Branch | Beschreibung | Technologien |
|--------|--------------|--------------|
| **main** | Lokale PC-Version des Bots | Ollama (TinyLlama-1.1B), Windows |
| **oracle-version** | Oracle Cloud Version | Groq API (llama-3.3-70b), Ubuntu 22.04 |

### Hauptordner:

```
telegram-chat-bot/
├── docs/                    # Dokumentation
│   ├── customer/           # Benutzerhandbücher
│   ├── technical/          # Technische Dokumentation
│   ├── lastenheft/         # Anforderungen
│   └── pflichtenheft/      # Spezifikationen
├── tests/                   # Tests
├── pdfs/                    # PDF-Dokumente zur Verarbeitung
├── chroma_db/              # Vektordatenbank
├── bot.py                  # Haupt-Bot-Datei
├── llm_client.py           # LLM-Client
├── retrieval.py            # Informationssuche
├── requirements.txt        # Python-Abhängigkeiten
└── README.md               # Hauptbeschreibung
```

---

## 3. Code ansehen

### 3.1 Über GitHub-Weboberfläche

1. Öffnen Sie https://github.com/Natashick/telegram-chat-bot
2. Wählen Sie den gewünschten Branch im Dropdown-Menü (main oder oracle-version)
3. Durchsuchen Sie die Dateien durch Anklicken

### 3.2 Änderungshistorie ansehen

1. Wechseln Sie zum Tab **Commits**
2. Klicken Sie auf einen Commit, um die Änderungen zu sehen
3. Grün zeigt Hinzufügungen, Rot zeigt Löschungen

### 3.3 Branches ansehen

https://github.com/Natashick/telegram-chat-bot/branches

---

## 4. Repository klonen

### 4.1 Main-Branch klonen (PC-Version)

```bash
# In gewünschten Ordner wechseln
cd ~/Documents/Projects

# Repository klonen
git clone https://github.com/Natashick/telegram-chat-bot.git

# In Ordner wechseln
cd telegram-chat-bot
```

### 4.2 Oracle-version Branch klonen

```bash
# Direkt oracle-version klonen
git clone -b oracle-version https://github.com/Natashick/telegram-chat-bot.git telegram-chat-bot-oracle

# Oder nach dem Klonen wechseln:
cd telegram-chat-bot
git checkout oracle-version
```

---

## 5. Mit Branches arbeiten

### 5.1 Verfügbare Branches ansehen

```bash
# Lokale Branches
git branch

# Alle Branches (inkl. remote)
git branch -a
```

### 5.2 Zwischen Branches wechseln

```bash
# Zu main wechseln (PC-Version)
git checkout main

# Zu oracle-version wechseln (Cloud-Version)
git checkout oracle-version

# Aktuellen Branch prüfen
git branch
```

### 5.3 Branch-Informationen aktualisieren

```bash
# Neueste Änderungen von GitHub holen
git fetch origin

# Aktuellen Branch aktualisieren
git pull
```

---

## 6. Änderungen vornehmen

### 6.1 Status ansehen

```bash
# Geänderte Dateien ansehen
git status

# Spezifische Änderungen ansehen
git diff
```

### 6.2 Änderungen erstellen

```bash
# 1. Nehmen Sie Änderungen in Dateien vor (z.B. bot.py bearbeiten)

# 2. Dateien zum Staging hinzufügen
git add bot.py                    # Eine Datei hinzufügen
git add .                         # Alle geänderten Dateien hinzufügen

# 3. Commit mit Beschreibung erstellen
git commit -m "Kurze Beschreibung der Änderungen"

# 4. Zu GitHub hochladen
git push origin main              # Für main Branch
git push origin oracle-version    # Für oracle-version Branch
```

### 6.3 Beispiel-Workflow

```bash
# Sicherstellen, dass Sie im richtigen Branch sind
git checkout oracle-version

# Lokale Version aktualisieren
git pull

# Änderungen in Dateien vornehmen
# (in Ihrem Editor bearbeiten)

# Änderungen überprüfen
git status
git diff

# Hinzufügen und committen
git add docs/customer/BENUTZERHANDBUCH_ORACLE.md
git commit -m "docs: Benutzerhandbuch für Oracle-Version aktualisiert"

# Zu GitHub hochladen
git push origin oracle-version
```

---

## 7. Änderungshistorie ansehen

### 7.1 Commits ansehen

```bash
# Letzte 10 Commits
git log --oneline -10

# Detaillierte Historie
git log

# Historie einer bestimmten Datei
git log -- bot.py
```

### 7.2 Änderungen in einem Commit ansehen

```bash
# Änderungen in einem bestimmten Commit anzeigen
git show <commit-hash>

# Beispiel:
git show 0c40524
```

### 7.3 Branches vergleichen

```bash
# Unterschiede zwischen main und oracle-version anzeigen
git diff main..oracle-version

# Liste der Dateien, die sich unterscheiden
git diff --name-only main..oracle-version
```

---

## 8. Nützliche Befehle

### 8.1 Repository-Informationen

```bash
# Remote-Repositories anzeigen
git remote -v

# Branch-Informationen anzeigen
git branch -vv

# Letzte Änderungen anzeigen
git log --oneline --graph --all --decorate -10
```

### 8.2 Änderungen rückgängig machen

```bash
# Änderungen in einer Datei rückgängig machen (vor add)
git checkout -- dateiname

# Datei aus Staging entfernen (nach add, vor commit)
git reset HEAD dateiname

# Letzten Commit rückgängig machen (Änderungen bleiben)
git reset --soft HEAD~1

# Letzten Commit vollständig rückgängig machen (VORSICHT!)
git reset --hard HEAD~1
```

### 8.3 Mit GitHub über Weboberfläche arbeiten

**Änderungen ohne Klonen erstellen:**

1. Öffnen Sie die gewünschte Datei auf GitHub
2. Klicken Sie auf **Edit** (Stift-Symbol)
3. Nehmen Sie Änderungen vor
4. Füllen Sie die Commit-Beschreibung unten aus
5. Klicken Sie auf **Commit changes**

**Pull Request erstellen:**

1. Wechseln Sie zum Tab **Pull requests**
2. Klicken Sie auf **New pull request**
3. Wählen Sie die Branches zum Vergleichen
4. Fügen Sie eine Beschreibung hinzu
5. Klicken Sie auf **Create pull request**

---

## 9. Schnellstart für Projektleiter

### Nur Ansehen (ohne Installation):

✅ Nutzen Sie die GitHub-Weboberfläche: https://github.com/Natashick/telegram-chat-bot

### Für lokale Arbeit mit Code:

```bash
# Schritt 1: Git installieren (siehe Abschnitt 1.1)

# Schritt 2: Repository klonen
git clone https://github.com/Natashick/telegram-chat-bot.git
cd telegram-chat-bot

# Schritt 3: Branches ansehen
git branch -a

# Schritt 4: Zum gewünschten Branch wechseln
git checkout oracle-version    # Für Oracle-Version
# oder
git checkout main              # Für PC-Version

# Schritt 5: Bei Bedarf aktualisieren
git pull
```

---

## 10. Support und Fragen

**GitHub Issues**: https://github.com/Natashick/telegram-chat-bot/issues

**Entwickler-Kontakt**: @Natashick

**Projektdokumentation**: `/docs` Ordner im Repository

---

## Anhang A: Glossar

| Begriff | Beschreibung |
|---------|--------------|
| **Repository** | Code-Speicher des Projekts |
| **Branch** | Separate Version des Codes |
| **Commit** | Speichern von Änderungen mit Beschreibung |
| **Clone** | Repository auf lokalen Computer kopieren |
| **Pull** | Updates von GitHub holen |
| **Push** | Änderungen zu GitHub hochladen |
| **Merge** | Änderungen aus verschiedenen Branches zusammenführen |
| **Pull Request** | Anfrage zur Überprüfung und Zusammenführung von Änderungen |
| **Collaborator** | Benutzer mit Änderungsrechten für das Repository |

---

## Anhang B: Empfehlungen

### Zum Code-Ansehen:
- Nutzen Sie die GitHub-Weboberfläche - keine Installation erforderlich
- Nutzen Sie VS Code mit GitHub-Erweiterung für komfortable Navigation

### Für Änderungen:
- Führen Sie immer `git pull` vor Arbeitsbeginn aus
- Schreiben Sie verständliche Commit-Beschreibungen
- Verwenden Sie Präfixe: `feat:`, `fix:`, `docs:`, `refactor:`
- Testen Sie Änderungen lokal vor dem Push

### Für Sicherheit:
- Committen Sie keine API-Schlüssel und Passwörter
- Verwenden Sie `.env`-Dateien (diese sind in `.gitignore`)
- Erstellen Sie regelmäßig Backups wichtiger Branches

---

**Dokumentversion**: 1.0  
**Letzte Aktualisierung**: 16.02.2026
