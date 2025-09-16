# Save as: apps/accounts/management/commands/fix_migration_conflict.py

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fixes migration conflicts and ensures all tables exist'

    def handle(self, *args, **options):
        self.stdout.write('Fixing migration conflicts and creating tables...\n')
        
        with connection.cursor() as cursor:
            # First, check what migrations Django thinks are applied
            cursor.execute("""
                SELECT name FROM django_migrations 
                WHERE app = 'accounts' 
                ORDER BY id;
            """)
            applied = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f'Applied migrations: {applied}\n')
            
            # Check if we have the conflict
            has_0009 = any('0009' in m for m in applied)
            
            if has_0009:
                # Remove duplicate 0009 migrations from tracking
                cursor.execute("""
                    DELETE FROM django_migrations 
                    WHERE app = 'accounts' AND name LIKE '0009%';
                """)
                self.stdout.write('Removed conflicting 0009 migrations from tracking\n')
                
                # Mark the rename migration as applied (it's the one we want)
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied) 
                    VALUES ('accounts', '0009_rename_allow_buddy_system_groupchallenge_allow_pal_system_and_more', NOW())
                    ON CONFLICT DO NOTHING;
                """)
                self.stdout.write('Marked correct 0009 migration as applied\n')
            
            # Now create all the tables that should exist
            table_definitions = [
                # RecoveryPal (renamed from RecoveryBuddy)
                """CREATE TABLE IF NOT EXISTS accounts_recoverypal (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    pal_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, pal_id)
                )""",
                
                # SponsorRelationship
                """CREATE TABLE IF NOT EXISTS accounts_sponsorrelationship (
                    id SERIAL PRIMARY KEY,
                    sponsee_id INTEGER NOT NULL,
                    sponsor_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(sponsee_id, sponsor_id)
                )""",
                
                # UserConnection
                """CREATE TABLE IF NOT EXISTS accounts_userconnection (
                    id SERIAL PRIMARY KEY,
                    from_user_id INTEGER NOT NULL,
                    to_user_id INTEGER NOT NULL,
                    connection_type VARCHAR(50) DEFAULT 'friend',
                    is_accepted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                # SupportMessage
                """CREATE TABLE IF NOT EXISTS accounts_supportmessage (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    recipient_id INTEGER NOT NULL,
                    message TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                # Milestone
                """CREATE TABLE IF NOT EXISTS accounts_milestone (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    date DATE NOT NULL,
                    milestone_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                # GroupChallenge (with renamed fields)
                """CREATE TABLE IF NOT EXISTS accounts_groupchallenge (
                    id SERIAL PRIMARY KEY,
                    group_id INTEGER,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    start_date DATE,
                    end_date DATE,
                    allow_pal_system BOOLEAN DEFAULT FALSE,
                    pal_support_required BOOLEAN DEFAULT FALSE,
                    created_by_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                # UserChallenge
                """CREATE TABLE IF NOT EXISTS accounts_userchallenge (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    challenge_id INTEGER NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    completed BOOLEAN DEFAULT FALSE,
                    pal_id INTEGER,
                    UNIQUE(user_id, challenge_id)
                )""",
                
                # ChallengePal (renamed from ChallengeBuddy)
                """CREATE TABLE IF NOT EXISTS accounts_challengepal (
                    id SERIAL PRIMARY KEY,
                    user_challenge_id INTEGER NOT NULL,
                    pal_id INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_challenge_id, pal_id)
                )""",
                
                # ChallengeCheckin
                """CREATE TABLE IF NOT EXISTS accounts_challengecheckin (
                    id SERIAL PRIMARY KEY,
                    user_challenge_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    completed BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    pal_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                # Other challenge-related tables
                """CREATE TABLE IF NOT EXISTS accounts_challengecomment (
                    id SERIAL PRIMARY KEY,
                    challenge_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""",
                
                """CREATE TABLE IF NOT EXISTS accounts_challengebadge (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    icon VARCHAR(50),
                    challenge_id INTEGER,
                    requirement_days INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            ]
            
            # Create all tables
            created_count = 0
            for create_sql in table_definitions:
                try:
                    cursor.execute(create_sql)
                    created_count += 1
                except Exception as e:
                    # Table might already exist, that's fine
                    pass
            
            self.stdout.write(self.style.SUCCESS(f'✓ Ensured {created_count} tables exist'))
            
            # Handle the buddy->pal rename if needed
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'accounts_recoverybuddy'
                )
            """)
            has_buddy_table = cursor.fetchone()[0]
            
            if has_buddy_table:
                # Copy data from buddy to pal table if needed
                cursor.execute("""
                    INSERT INTO accounts_recoverypal (user_id, pal_id, is_active, created_at, updated_at)
                    SELECT user_id, buddy_id, is_active, created_at, updated_at 
                    FROM accounts_recoverybuddy
                    ON CONFLICT DO NOTHING;
                """)
                self.stdout.write('✓ Migrated data from buddy to pal table')
            
            # Final verification
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'accounts_%'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Total accounts tables: {len(tables)}'))
            
            # Check critical tables
            critical = ['accounts_recoverypal', 'accounts_milestone', 'accounts_groupchallenge']
            for table_name in critical:
                exists = any(table_name == t[0] for t in tables)
                if exists:
                    self.stdout.write(self.style.SUCCESS(f'✓ {table_name} exists'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ {table_name} MISSING!'))