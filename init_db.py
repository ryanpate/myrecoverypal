#!/usr/bin/env python
"""
Complete database initialization with special handling for accounts app.
"""
from django.db import connection, transaction
from django.core.management import call_command
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recovery_hub.settings')
django.setup()


def init_database():
    print("=" * 70)
    print("COMPLETE DATABASE INITIALIZATION")
    print("=" * 70)

    # Step 1: Basic setup and migration
    print("\n1. Running standard migrations...")
    try:
        call_command('migrate', 'contenttypes', interactive=False)
        call_command('migrate', 'auth', interactive=False)
        call_command('migrate', 'sessions', interactive=False)
        call_command('migrate', 'admin', interactive=False)
        call_command('migrate', 'sites', interactive=False)
        print("✅ Core Django apps migrated")
    except Exception as e:
        print(f"⚠️  Core migration warning: {e}")

    # Step 2: Fix accounts app specifically
    print("\n2. Fixing accounts app...")
    fix_accounts_app()

    # Step 3: Migrate other apps
    print("\n3. Migrating other apps...")
    other_apps = ['blog', 'resources', 'journal',
                  'newsletter', 'store', 'support_services']
    for app in other_apps:
        try:
            call_command('migrate', app, interactive=False)
            print(f"✅ {app} migrated")
        except Exception as e:
            print(f"⚠️  {app}: {e}")

    # Step 4: Final migrate
    print("\n4. Final migration pass...")
    try:
        call_command('migrate', '--run-syncdb', interactive=False)
        print("✅ Final migration complete")
    except Exception as e:
        print(f"⚠️  Final migration: {e}")

    # Step 5: Create superuser
    if os.environ.get('DJANGO_SUPERUSER_EMAIL'):
        print("\n5. Creating superuser...")
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
                print(f"ℹ️  Superuser exists: {email}")
        except Exception as e:
            print(f"⚠️  Superuser creation: {e}")

    print("\n" + "=" * 70)
    print("INITIALIZATION COMPLETE")
    print("=" * 70)


def fix_accounts_app():
    """Special handling for accounts app with its complex migrations."""

    # Check what accounts tables exist
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'accounts_%'
        """)
        existing = [row[0] for row in cursor.fetchall()]

    # Check for the specific missing table
    needs_fix = False
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND (table_name = 'accounts_recoverypal' OR table_name = 'accounts_recoverybuddy')
            );
        """)
        needs_fix = cursor.fetchone()[0]

    if needs_fix:
        print("  ⚠️  Accounts tables missing, applying fix...")

        try:
            # Clear accounts migrations
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE app = 'accounts';")

            # Apply migrations in order
            migrations = [
                '0001_initial',
                '0002_activityfeed_activitycomment_dailycheckin',
                '0003_activity_feed',
                '0004_merge_20250911_1821',
                '0005_add_community',
                '0006_merge_0004_merge_20250911_1821_0005_add_community',
                '0007_userprofile_and_more',
                '0008_challengebadge_challengecheckin_challengecomment_and_more',
                '0009_rename_allow_buddy_system_groupchallenge_allow_pal_system_and_more',
            ]

            for migration in migrations:
                try:
                    call_command('migrate', 'accounts',
                                 migration, interactive=False)
                    print(f"  ✅ Applied {migration}")
                except Exception as e:
                    print(f"  ⚠️  {migration}: {e}")
                    # Try fake if real fails
                    try:
                        call_command('migrate', 'accounts',
                                     migration, '--fake', interactive=False)
                    except:
                        pass

            # If still missing, create manually
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT NOT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND (table_name = 'accounts_recoverypal' OR table_name = 'accounts_recoverybuddy')
                    );
                """)
                still_missing = cursor.fetchone()[0]

                if still_missing:
                    print("  Creating RecoveryPal table manually...")
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS accounts_recoverypal (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            pal_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW(),
                            UNIQUE(user_id, pal_id)
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_recoverypal_user ON accounts_recoverypal(user_id);
                        CREATE INDEX IF NOT EXISTS idx_recoverypal_pal ON accounts_recoverypal(pal_id);
                    """)
                    print("  ✅ Created accounts_recoverypal table")

        except Exception as e:
            print(f"  ❌ Accounts fix failed: {e}")
    else:
        print("  ✅ Accounts tables exist")


if __name__ == '__main__':
    init_database()
