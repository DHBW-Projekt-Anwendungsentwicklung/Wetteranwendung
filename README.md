# How to Install Wetteranwendung (Windows)

## 1. Voraussetzungen
Bevor Sie starten, stellen Sie sicher, dass folgende Programme installiert sind:

### Git installieren
- Git für Windows herunterladen: [Git-SCM Download](https://git-scm.com/downloads)
- Nach der Installation: Prüfe die Installation mit:
  ```sh
  git --version
  ```

### Docker & Docker Compose installieren
- Docker Desktop für Windows herunterladen: [Docker Download](https://www.docker.com/get-started)
- Nach der Installation: Stellen Sie sicher, dass Docker läuft und überprüfen Sie die Version:
  ```sh
  docker --version
  ```
- Starten Sie Docker Desktop, bevor Sie mit den nächsten Schritten fortfahren.

---

### 2. Docker-Container starten
Um den Container zu starten, führen Sie folgenden Befehle aus:

```sh
docker run -d --cpus=2 --memory=1g -p 127.0.0.1:8000:8000 ghcr.io/dhbw-projekt-anwendungsentwicklung/wetteranwendung:latest
```

### 3. Anwendung im Browser öffnen
Sobald Docker läuft, können Sie die Anwendung unter folgender URL aufrufen:

```sh
http://127.0.0.1:8000/
```

### 4. Container stoppen und neustarten
Falls Sie den Container stoppen möchten:

```sh
docker down CONTAINER-ID
```
Container erneut starten:

```sh
Docker start CONTAINER_ID
```
