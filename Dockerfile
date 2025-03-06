# --- Dockerfile für dein Django-Projekt ---
# Basis-Image mit Python 3.10
FROM python:3.10

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere Abhängigkeiten und installiere sie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den gesamten Code ins Container-Verzeichnis
COPY . .

# Setze Umgebungsvariablen für Django aus der .env-Datei
ENV PYTHONUNBUFFERED=1

# Statische Dateien sammeln (wird nur nötig sein, wenn du sie im Container nutzen möchtest)
RUN python manage.py collectstatic --noinput || true

# Exponiere den Standardport für Django
EXPOSE 8000

# Starte die Django-App mit daphne für ASGI (falls Websockets geplant sind) oder Gunicorn
CMD ["gunicorn", "--workers=3", "--bind", "0.0.0.0:8000", "weather_application.wsgi:application"]