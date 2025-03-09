FROM python:3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "--workers=3", "--bind", "0.0.0.0:8000", "weather_application.wsgi:application"]