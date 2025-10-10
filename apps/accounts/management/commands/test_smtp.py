from django.core.management.base import BaseCommand
from django.conf import settings
import smtplib
import ssl

class Command(BaseCommand):
    help = 'Test SMTP connection only (no email sending)'

    def handle(self, *args, **options):
        self.stdout.write('='*70)
        self.stdout.write('🔌 TESTING SMTP CONNECTION')
        self.stdout.write('='*70)
        
        self.stdout.write(f'\nHost: {settings.EMAIL_HOST}')
        self.stdout.write(f'Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'Password: {"Set" if settings.EMAIL_HOST_PASSWORD else "NOT SET"}')
        
        try:
            self.stdout.write('\n1️⃣ Connecting to SMTP server...')
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10)
            self.stdout.write(self.style.SUCCESS('   ✓ Connected'))
            
            self.stdout.write('\n2️⃣ Starting TLS...')
            context = ssl.create_default_context()
            server.starttls(context=context)
            self.stdout.write(self.style.SUCCESS('   ✓ TLS started'))
            
            self.stdout.write('\n3️⃣ Logging in...')
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS('   ✓ Login successful'))
            
            self.stdout.write('\n4️⃣ Closing connection...')
            server.quit()
            self.stdout.write(self.style.SUCCESS('   ✓ Connection closed'))
            
            self.stdout.write(self.style.SUCCESS('\n✅ SMTP CONNECTION TEST PASSED!'))
            self.stdout.write('Email credentials are working correctly.\n')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ SMTP TEST FAILED: {str(e)}'))
            
            if '535' in str(e) or 'authentication' in str(e).lower():
                self.stdout.write(self.style.WARNING('\n🔐 Authentication Failed:'))
                self.stdout.write('   - Check EMAIL_PASSWORD in Railway variables')
                self.stdout.write('   - Verify password for ryan@myrecoverypal.com')
                self.stdout.write('   - Check SMTP is enabled in Microsoft 365')
            
            import traceback
            self.stdout.write(f'\nFull error:\n{traceback.format_exc()}')