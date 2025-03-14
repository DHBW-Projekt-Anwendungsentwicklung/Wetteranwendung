#!/bin/bash
set -e

echo "=== Starte FRONTEND-Tests (npm test) ==="
npm run test

echo "=== Starte BACKEND-Tests (python manage.py test) ==="
python manage.py test

echo "=== Tests erfolgreich, Collectstatic ausführen ==="
python manage.py collectstatic --noinput || true

echo "=== Starte Gunicorn ==="
gunicorn -w 4 --timeout 180 -b 0.0.0.0:8000 --log-level=info weather_application.wsgi:application
