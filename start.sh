#!/bin/bash
set -e

# Extract APNs auth key from environment variable if set
if [ -n "$APNS_KEY_CONTENT" ]; then
    echo "Writing APNs auth key..."
    echo "$APNS_KEY_CONTENT" > /app/apns-auth-key.p8
fi

echo "Running database migrations..."
python manage.py migrate --noinput

# Seed recovery quotes if table is empty (one-time init)
python manage.py seed_recovery_quotes 2>/dev/null || true

# Populate recovery resources (idempotent: update_or_create by slug, self-heals
# the resources section if the DB is ever reset)
python manage.py populate_resource_content 2>/dev/null || true
python manage.py populate_category_resources 2>/dev/null || true

echo "Starting gunicorn..."
exec gunicorn recovery_hub.wsgi:application -c /app/gunicorn.conf.py --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile -
