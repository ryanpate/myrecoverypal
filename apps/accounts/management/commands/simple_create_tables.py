# Save as: apps/accounts/management/commands/simple_create_tables.py

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Simply creates all missing tables without worrying about migrations'

    def handle(self, *args, **options):
        self.stdout.write('Creating missing tables...\n')
        
        with connection.cursor() as cursor:
            # Just create the tables we need - no fancy logic
            tables_to_create = {
                'accounts_recoverypal': """
                    CREATE TABLE IF NOT EXISTS accounts_recoverypal (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        pal_id INTEGER,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                
                'accounts_sponsorrelationship': """
                    CREATE TABLE IF NOT EXISTS accounts_sponsorrelationship (
                        id SERIAL PRIMARY KEY,
                        sponsee_id INTEGER,
                        sponsor_id INTEGER,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                
                'accounts_userconnection': """
                    CREATE TABLE IF NOT EXISTS accounts_userconnection (
                        id SERIAL PRIMARY KEY,
                        from_user_id INTEGER,
                        to_user_id INTEGER,
                        connection_type VARCHAR(50) DEFAULT 'friend',
                        is_accepted BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                
                'accounts_supportmessage': """
                    CREATE TABLE IF NOT EXISTS accounts_supportmessage (
                        id SERIAL PRIMARY KEY,
                        sender_id INTEGER,
                        recipient_id INTEGER,
                        message TEXT,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """,
                
                'accounts_milestone': """
                    CREATE TABLE IF NOT EXISTS accounts_milestone (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        title VARCHAR(200),
                        description TEXT,
                        date DATE,
                        milestone_type VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
            }
            
            for table_name, create_sql in tables_to_create.items():
                try:
                    cursor.execute(create_sql)
                    self.stdout.write(self.style.SUCCESS(f'✓ Created/verified {table_name}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠ Issue with {table_name}: {e}'))
            
            # Verify what we have
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'accounts_recoverypal'
            """)
            result = cursor.fetchone()
            
            if result:
                self.stdout.write(self.style.SUCCESS('\n✓✓✓ accounts_recoverypal table EXISTS - site should work now!'))
            else:
                self.stdout.write(self.style.ERROR('\n✗✗✗ accounts_recoverypal table STILL MISSING'))
            
            self.stdout.write('\nDone!')