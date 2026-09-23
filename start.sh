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
# Access log format: the default logs %(h)s, which behind Railway's proxy is
# always 100.64.0.x and tells us nothing about who is calling. Log the real
# client (cf-connecting-ip via Cloudflare, x-forwarded-for otherwise) and the
# request duration %(L)s, so a traffic spike can be attributed and timed.
exec gunicorn recovery_hub.wsgi:application -c /app/gunicorn.conf.py --bind 0.0.0.0:$PORT --timeout 120 --workers 2 --preload --max-requests 1000 --max-requests-jitter 100 --access-logfile - --error-logfile - --access-logformat '%({cf-connecting-ip}i)s %({x-forwarded-for}i)s %(t)s "%(r)s" %(s)s %(b)s %(L)s "%(f)s" "%(a)s"'
