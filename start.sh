#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn recovery_hub.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --access-logfile - --error-logfile -
