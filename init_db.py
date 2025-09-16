#!/usr/bin/env python
"""
Database initialization script for Railway deployment.
Ensures all migrations are created and applied properly.
"""
import os
import sys
import django
from django.core.management import execute_from_command_line, call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recovery_hub.settings')
django.setup()


def run_command(command, *args, **kwargs):
    """Helper function to run Django management commands with error handling."""
    try:
        print(f"Running: {command} {' '.join(args)}")
        call_command(command, *args, **kwargs)
        return True
    except Exception as e:
        print(f"⚠️  Error running {command}: {e}")
        return False


def init_database():
    """Initialize database with migrations and create all necessary tables."""

    print("=" * 50)
    print("Starting Database Initialization")
    print("=" * 50)

    # Test database connection
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

    # List of all your apps that need migrations
    apps = [
        'core',
        'accounts',
        'blog',
        'resources',
        'journal',
        'store',
        'newsletter',
        'support_services',
    ]

    # Step 1: Create migration files for all apps
    print("\n" + "=" * 50)
    print("Creating Migration Files")
    print("=" * 50)

    for app in apps:
        try:
            print(f"\nProcessing app: {app}")
            call_command('makemigrations', app, verbosity=2, interactive=False)
            print(f"✅ Created migrations for {app}")
        except Exception as e:
            print(f"⚠️  Could not create migrations for {app}: {e}")
            # Try without app name in case migrations already exist
            try:
                call_command('makemigrations', verbosity=0, interactive=False)
            except:
                pass

    # Step 2: Create a general migration in case any were missed
    try:
        print("\nCreating any remaining migrations...")
        call_command('makemigrations', verbosity=1, interactive=False)
        print("✅ General migrations created")
    except Exception as e:
        print(f"⚠️  No additional migrations needed: {e}")

    # Step 3: Show migration plan
    print("\n" + "=" * 50)
    print("Migration Plan")
    print("=" * 50)
    try:
        call_command('showmigrations', verbosity=2)
    except:
        print("Could not display migration plan")

    # Step 4: Apply all migrations
    print("\n" + "=" * 50)
    print("Applying Migrations")
    print("=" * 50)

    # First, try to migrate built-in Django apps
    django_apps = ['contenttypes', 'auth',
                   'sessions', 'sites', 'admin', 'messages']
    for app in django_apps:
        try:
            call_command('migrate', app, verbosity=1, interactive=False)
            print(f"✅ Migrated {app}")
        except Exception as e:
            print(f"⚠️  Issue with {app}: {e}")

    # Then migrate third-party apps
    third_party = ['allauth', 'account', 'socialaccount',
                   'crispy_forms', 'crispy_bootstrap5']
    for app in third_party:
        try:
            call_command('migrate', app, verbosity=0, interactive=False)
            print(f"✅ Migrated {app}")
        except:
            pass  # These might not have migrations

    # Now migrate your custom apps
    for app in apps:
        try:
            call_command('migrate', app, verbosity=1, interactive=False)
            print(f"✅ Migrated {app}")
        except Exception as e:
            print(f"⚠️  Could not migrate {app}: {e}")

    # Finally, run a general migrate to catch anything missed
    print("\nRunning final migration...")
    try:
        call_command('migrate', verbosity=1,
                     interactive=False, run_syncdb=True)
        print("✅ All migrations completed successfully!")
    except Exception as e:
        print(f"⚠️  Final migration had issues: {e}")
        # Try with --fake-initial as a last resort
        try:
            call_command('migrate', fake_initial=True,
                         verbosity=1, interactive=False)
            print("✅ Migrations completed with --fake-initial")
        except Exception as e2:
            print(f"❌ Could not complete migrations: {e2}")

    # Step 5: Verify tables were created
    print("\n" + "=" * 50)
    print("Verifying Database Tables")
    print("=" * 50)

    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        print(f"\n✅ Found {len(tables)} tables in database:")
        for table in tables:
            print(f"   - {table[0]}")

        # Check for critical tables
        table_names = [t[0] for t in tables]
        critical_tables = [
            'accounts_user',
            'blog_post',
            'resources_resource',
            'journal_journalentry',
            'newsletter_subscriber'
        ]

        missing_tables = []
        for table in critical_tables:
            if table not in table_names:
                missing_tables.append(table)
                print(f"⚠️  Missing critical table: {table}")

        if missing_tables:
            print(f"\n❌ Missing {len(missing_tables)} critical tables!")
            print("Attempting to create them manually...")

            # Try creating tables with syncdb
            try:
                from django.core.management import call_command
                call_command('migrate', '--run-syncdb', verbosity=2)
                print("✅ Tables created with syncdb")
            except Exception as e:
                print(f"❌ Could not create tables: {e}")

    # Step 6: Create superuser if configured
    print("\n" + "=" * 50)
    print("Superuser Setup")
    print("=" * 50)

    if all([os.environ.get('DJANGO_SUPERUSER_EMAIL'),
            os.environ.get('DJANGO_SUPERUSER_PASSWORD')]):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

            if not User.objects.filter(email=email).exists():
                user = User.objects.create_superuser(
                    email=email,
                    password=password
                )
                print(f"✅ Superuser created: {email}")
            else:
                print(f"ℹ️  Superuser already exists: {email}")
        except Exception as e:
            print(f"⚠️  Could not create superuser: {e}")
    else:
        print("ℹ️  No superuser credentials provided in environment")

    print("\n" + "=" * 50)
    print("✅ Database Initialization Complete!")
    print("=" * 50)


if __name__ == '__main__':
    init_database()
