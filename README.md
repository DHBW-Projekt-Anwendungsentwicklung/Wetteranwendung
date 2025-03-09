# How to Install Wetteranwendung (Windows)

## 1. Voraussetzungen
Bevor du startest, stelle sicher, dass folgende Programme installiert sind:

### Git installieren
- Git für Windows herunterladen: [Git-SCM Download](https://git-scm.com/downloads)
- Nach der Installation: Prüfe die Installation mit:
  ```sh
  git --version
  ```

### Docker & Docker Compose installieren
- Docker Desktop für Windows herunterladen: [Docker Download](https://www.docker.com/get-started)
- Nach der Installation: Stelle sicher, dass Docker läuft und überprüfe die Version:
  ```sh
  docker --version
  docker-compose --version
  ```
- Starte Docker Desktop, bevor du mit den nächsten Schritten fortfährst.

---

## 2. Projekt klonen
Öffne PowerShell oder die Eingabeaufforderung (CMD) und klone das GitHub-Repository:

```sh
git clone https://github.com/DHBW-Projekt-Anwendungsentwicklung/Wetteranwendung.git
cd wetteranwendung
```

Falls du einen bestimmten Branch benötigst:
```sh
git checkout branch-name
```

---

## 3. `.env` Datei einrichten
Erstelle eine `.env` Datei basierend auf `.env.example`:
```sh
copy .env.example .env
```

Bearbeite die `.env` Datei mit einem Texteditor (z. B. Notepad oder VS Code) und passe die Werte an.

---

## 4. Docker-Container starten
Führe folgenden Befehl aus, um das Projekt mit Docker Compose zu starten:
```sh
docker-compose up --build
```
Falls du den Container im Hintergrund laufen lassen möchtest:
```sh
docker-compose up -d
```

---

## 5. Anwendung im Browser öffnen
Sobald Docker läuft, kannst du die Anwendung unter folgender URL aufrufen:

http://127.0.0.1:8000/

## 6. Container stoppen und neustarten
Falls du den Container stoppen möchtest:
```sh
docker-compose down
```

Falls du Änderungen am Code machst, starte den Container neu:
```sh
docker-compose up --build
```

---
