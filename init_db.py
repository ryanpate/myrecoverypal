#!/usr/bin/env python
"""
Robust database initialization for Railway deployment.
Forces migration application even if Django thinks they're already applied.
"""
from django.db import connection, transaction
from django.core.management import call_command
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recovery_hub.settings')
django.setup()


def init_database():
    print("=" * 50)
    print("Database Initialization Starting")
    print("=" * 50)

    # Step 1: Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    # Step 2: Check current table status
    print("\n📊 Current database status:")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Found {len(existing_tables)} tables")

        # Check for our app tables
        app_tables = {
            'blog_post': False,
            'resources_resource': False,
            'journal_journalentry': False,
            'newsletter_subscriber': False,
            'store_product': False,
            'support_services_meeting': False
        }

        for table in app_tables:
            if table in existing_tables:
                app_tables[table] = True
                print(f"  ✅ {table} exists")
            else:
                print(f"  ❌ {table} missing")

    # Step 3: Force migration if tables are missing
    if not all(app_tables.values()):
        print("\n🔧 Missing tables detected. Forcing migration...")

        # Try to clear migration history for apps with missing tables
        try:
            with connection.cursor() as cursor:
                # Get list of applied migrations
                cursor.execute("""
                    SELECT app, name 
                    FROM django_migrations 
                    WHERE app IN ('blog', 'resources', 'journal', 'newsletter', 'store', 'support_services')
                """)
                applied_migrations = cursor.fetchall()

                if applied_migrations:
                    print(
                        f"Found {len(applied_migrations)} recorded migrations")
                    print("Clearing migration records for apps with missing tables...")

                    # Clear migration records for apps with missing tables
                    for app_name, table_name in [
                        ('blog', 'blog_post'),
                        ('resources', 'resources_resource'),
                        ('journal', 'journal_journalentry'),
                        ('newsletter', 'newsletter_subscriber'),
                        ('store', 'store_product'),
                        ('support_services', 'support_services_meeting')
                    ]:
                        if not app_tables.get(table_name, False):
                            cursor.execute(
                                "DELETE FROM django_migrations WHERE app = %s",
                                [app_name]
                            )
                            print(
                                f"  Cleared migration records for {app_name}")
        except Exception as e:
            print(f"⚠️ Could not clear migration history: {e}")

    # Step 4: Run migrations
    print("\n🚀 Applying migrations...")

    # Migrate each app explicitly
    apps_to_migrate = [
        ('contenttypes', 'Django'),
        ('auth', 'Django'),
        ('accounts', 'Custom'),
        ('sessions', 'Django'),
        ('admin', 'Django'),
        ('sites', 'Django'),
        ('blog', 'Custom'),
        ('resources', 'Custom'),
        ('journal', 'Custom'),
        ('newsletter', 'Custom'),
        ('store', 'Custom'),
        ('support_services', 'Custom'),
    ]

    for app, app_type in apps_to_migrate:
        try:
            print(f"\nMigrating {app} ({app_type} app)...")
            call_command('migrate', app, verbosity=2, interactive=False)
            print(f"✅ {app} migrated successfully")
        except Exception as e:
            print(f"⚠️ Issue with {app}: {e}")

            # If migration failed, try with --fake-initial
            if app_type == 'Custom':
                try:
                    print(f"  Trying {app} with --fake-initial...")
                    call_command('migrate', app, '--fake-initial',
                                 interactive=False)
                    print(f"  ✅ {app} migrated with --fake-initial")
                except Exception as e2:
                    print(f"  ❌ Still couldn't migrate {app}: {e2}")

    # Step 5: Final catch-all migration
    print("\n🔄 Running final migration pass...")
    try:
        call_command('migrate', '--run-syncdb', verbosity=1, interactive=False)
        print("✅ Final migration complete")
    except Exception as e:
        print(f"⚠️ Final migration warning: {e}")

    # Step 6: Verify tables were created
    print("\n✅ Verifying database tables...")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('blog_post', 'resources_resource', 'journal_journalentry', 
                               'newsletter_subscriber', 'store_product', 'support_services_meeting')
            ORDER BY table_name;
        """)
        created_tables = [row[0] for row in cursor.fetchall()]

        if created_tables:
            print(f"Successfully verified {len(created_tables)} app tables:")
            for table in created_tables:
                print(f"  ✅ {table}")
        else:
            print("❌ WARNING: App tables still missing!")
            print("Attempting emergency table creation...")

            # Last resort: try to create tables manually
            try:
                from django.db import models
                from django.apps import apps

                for app_label in ['blog', 'resources', 'journal', 'newsletter', 'store', 'support_services']:
                    try:
                        app = apps.get_app_config(app_label)
                        with connection.schema_editor() as schema_editor:
                            for model in app.get_models():
                                if not model._meta.db_table in existing_tables:
                                    schema_editor.create_model(model)
                                    print(
                                        f"  Created table for {model._meta.label}")
                    except Exception as e:
                        print(
                            f"  Could not create tables for {app_label}: {e}")
            except Exception as e:
                print(f"Emergency table creation failed: {e}")

    # Step 7: Create superuser if configured
    if os.environ.get('DJANGO_SUPERUSER_EMAIL'):
        print("\n👤 Setting up superuser...")
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
            password = os.environ.get(
                'DJANGO_SUPERUSER_PASSWORD', 'changeme123')

            if not User.objects.filter(email=email).exists():
                User.objects.create_superuser(email=email, password=password)
                print(f"✅ Superuser created: {email}")
            else:
                print(f"ℹ️ Superuser already exists: {email}")
        except Exception as e:
            print(f"⚠️ Could not create superuser: {e}")

    print("\n" + "=" * 50)
    print("Database initialization complete!")
    print("=" * 50)


if __name__ == '__main__':
    init_database()
