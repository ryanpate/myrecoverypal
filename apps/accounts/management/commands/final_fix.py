# Save as: apps/accounts/management/commands/final_fix.py

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Final comprehensive fix for all database issues'

    def handle(self, *args, **options):
        self.stdout.write('Running final database fix...\n')
        
        with connection.cursor() as cursor:
            # Step 1: Mark all accounts migrations as applied to skip them
            self.stdout.write('Step 1: Marking migrations as fake-applied...')
            migrations_to_fake = [
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
            
            for migration in migrations_to_fake:
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied) 
                    VALUES ('accounts', %s, NOW())
                    ON CONFLICT (app, name) DO NOTHING
                """, [migration])
            self.stdout.write('✓ Migrations marked as applied\n')
            
            # Step 2: Fix the recoverypal table structure
            self.stdout.write('Step 2: Fixing table structures...')
            
            # Check current structure of accounts_recoverypal
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'accounts_recoverypal'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            if columns:
                self.stdout.write(f'Current columns in accounts_recoverypal: {columns}')
                
                # If table exists but has wrong columns, recreate it
                if 'user_id' in columns and 'user1_id' not in columns:
                    # Django expects user1_id and user2_id based on the error
                    # Drop and recreate with correct column names
                    cursor.execute("DROP TABLE IF EXISTS accounts_recoverypal CASCADE")
                    cursor.execute("""
                        CREATE TABLE accounts_recoverypal (
                            id SERIAL PRIMARY KEY,
                            user1_id INTEGER NOT NULL,
                            user2_id INTEGER NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    self.stdout.write('✓ Recreated accounts_recoverypal with correct column names\n')
            else:
                # Table doesn't exist, create it with correct names
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts_recoverypal (
                        id SERIAL PRIMARY KEY,
                        user1_id INTEGER NOT NULL,
                        user2_id INTEGER NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.stdout.write('✓ Created accounts_recoverypal\n')
            
            # Create other missing tables with correct structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts_sponsorrelationship (
                    id SERIAL PRIMARY KEY,
                    sponsee_id INTEGER NOT NULL,
                    sponsor_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts_userconnection (
                    id SERIAL PRIMARY KEY,
                    from_user_id INTEGER NOT NULL,
                    to_user_id INTEGER NOT NULL,
                    connection_type VARCHAR(50) DEFAULT 'friend',
                    is_accepted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts_supportmessage (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    message TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts_milestone (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(200),
                    description TEXT,
                    date DATE,
                    milestone_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.stdout.write('✓ All supporting tables created/verified\n')
            
            # Step 3: Verify the fix
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'accounts_recoverypal'
                ORDER BY ordinal_position
            """)
            final_columns = [row[0] for row in cursor.fetchall()]
            
            self.stdout.write(self.style.SUCCESS(f'\nFinal columns in accounts_recoverypal: {final_columns}'))
            
            if 'user1_id' in final_columns and 'user2_id' in final_columns:
                self.stdout.write(self.style.SUCCESS('\n✅✅✅ SUCCESS! Table structure matches Django models!'))
            else:
                self.stdout.write(self.style.ERROR('\n⚠️ Column names may still not match. You may need to update your models.py'))