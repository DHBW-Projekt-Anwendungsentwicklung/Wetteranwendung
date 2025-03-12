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

### 2. Container-Image abrufen
Da das Image bereits im GitHub Container Registry veröffentlicht ist, müssen Sie das Repository nicht lokal klonen. Laden Sie das aktuelle Image mit:

```sh
docker pull ghcr.io/dhbw-projekt-anwendungsentwicklung/wetteranwendung:latest
```

### 3. Docker-Container starten
Navigieren Sie in das Verzeichnis, in dem sich die docker-compose.yml befindet (dies ist im geklonten Repository oder in einem heruntergeladenen Ordner mit dem Projektinhalt). Führen Sie anschließend folgende Befehle aus:

```sh
docker run -d -p 127.0.0.1:8000:8000 ghcr.io/dhbw-projekt-anwendungsentwicklung/wetteranwendung:latest
```

Der erste Befehl baut den Container (dadurch werden alle Änderungen, z. B. an der Konfiguration, übernommen), und der zweite Befehl startet den Container im Hintergrund.

### 4. Anwendung im Browser öffnen
Sobald Docker läuft, können Sie die Anwendung unter folgender URL aufrufen:

```sh
http://127.0.0.1:8000/
```

### 5. Container stoppen und neustarten
Falls Sie den Container stoppen möchten:

```sh
docker-compose down
```
Falls Sie Änderungen am Code oder an der Konfiguration vornehmen, starten Sie den Container neu:

```sh
docker-compose up --build
```
