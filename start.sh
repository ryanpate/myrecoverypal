#!/bin/bash
set -e

# Extract APNs auth key from environment variable if set
if [ -n "$APNS_KEY_CONTENT" ]; then
    echo "Writing APNs auth key..."
    echo "$APNS_KEY_CONTENT" > /app/apns-auth-key.p8
fi

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting gunicorn..."
exec gunicorn recovery_hub.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --access-logfile - --error-logfile -
