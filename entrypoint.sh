#!/bin/sh
set -e

cd /app/summarizeit

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn on port ${PORT:-8080}..."
exec gunicorn summarizeit.wsgi:application \
    --bind "0.0.0.0:${PORT:-8080}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --log-level info
