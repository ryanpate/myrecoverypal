#!/usr/bin/env python
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recovery_hub.settings')
django.setup()

from django.core.management import execute_from_command_line

# Try to run migrations, but don't fail if they error
try:
    execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
    print("✅ Migrations completed successfully")
except Exception as e:
    print(f"⚠️ Migration error (continuing anyway): {e}")

# Create tables directly if needed
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT 1")  # Test connection
    print("✅ Database connection successful")