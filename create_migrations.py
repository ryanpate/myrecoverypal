#!/usr/bin/env python
"""
Script to ensure all apps have proper migration folders.
Run this locally before deploying.
"""
import os
from pathlib import Path

# Define base directory
BASE_DIR = Path(__file__).resolve().parent

# List of app directories
app_dirs = [
    'apps/core',
    'apps/accounts',
    'apps/blog',
    'resources',  # Note: This one is at root level based on your settings
    'apps/journal',
    'apps/store',
    'apps/newsletter',
    'apps/support_services',
]

def create_migration_folders():
    """Ensure each app has a migrations folder with __init__.py."""
    
    for app_dir in app_dirs:
        app_path = BASE_DIR / app_dir
        migrations_path = app_path / 'migrations'
        
        # Create app directory if it doesn't exist
        if not app_path.exists():
            print(f"⚠️  App directory doesn't exist: {app_path}")
            continue
        
        # Create migrations folder if it doesn't exist
        if not migrations_path.exists():
            migrations_path.mkdir(parents=True)
            print(f"✅ Created migrations folder: {migrations_path}")
        else:
            print(f"ℹ️  Migrations folder exists: {migrations_path}")
        
        # Create __init__.py in migrations folder
        init_file = migrations_path / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"✅ Created __init__.py in {migrations_path}")
        else:
            print(f"ℹ️  __init__.py exists in {migrations_path}")

if __name__ == '__main__':
    print("Checking migration folders...")
    print("=" * 50)
    create_migration_folders()
    print("=" * 50)
    print("✅ Migration folder check complete!")
    print("\nNow run the following commands:")
    print("1. python manage.py makemigrations")
    print("2. git add -A")
    print("3. git commit -m 'Add migration files'")
    print("4. git push")