# apps/accounts/management/commands/test_email.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import sys

class Command(BaseCommand):
    help = 'Test email configuration with detailed output'

    def add_arguments(self, parser):
        parser.add_argument('recipient', type=str, help='Email address to send test email to')
        parser.add_argument('--invite-template', action='store_true', help='Test the invite email template')

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('EMAIL CONFIGURATION TEST'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
        
        # Display current email settings
        self.stdout.write(self.style.HTTP_INFO('📧 Current Email Settings:'))
        self.stdout.write(f'   Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'   Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'   Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'   Use TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'   Host User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'   From Email: {settings.DEFAULT_FROM_EMAIL}')
        
        # Check if password is set
        if settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.SUCCESS(f'   Password: Set (length: {len(settings.EMAIL_HOST_PASSWORD)})'))
        else:
            self.stdout.write(self.style.ERROR('   Password: NOT SET! ❌'))
            self.stdout.write(self.style.ERROR('   Set EMAIL_PASSWORD environment variable!'))
            return
        
        self.stdout.write(f'\n📨 Sending to: {recipient}\n')
        
        try:
            if options['invite_template']:
                # Test the actual invite template
                self.stdout.write('Testing invite email template...\n')
                
                context = {
                    'email': recipient,
                    'invite_code': 'TEST-1234-5678',
                    'registration_url': f"{settings.SITE_URL}/accounts/register/?invite=TEST-1234-5678",
                    'site_url': settings.SITE_URL,
                    'uses_remaining': 1,
                    'expires_at': None,
                }
                
                html_message = render_to_string('emails/invite_code.html', context)
                plain_message = strip_tags(html_message)
                
                email = EmailMultiAlternatives(
                    subject='🌟 [TEST] Welcome to MyRecoveryPal - Your Invite Code',
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient]
                )
                email.attach_alternative(html_message, "text/html")
                
                self.stdout.write('Connecting to SMTP server...')
                email.send(fail_silently=False)
                
            else:
                # Simple test email
                self.stdout.write('Sending simple test email...\n')
                send_mail(
                    subject='Test Email from MyRecoveryPal',
                    message='This is a test email. If you receive this, your email configuration is working! ✅',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )
            
            self.stdout.write(self.style.SUCCESS('\n✅ SUCCESS! Test email sent successfully!'))
            self.stdout.write(self.style.SUCCESS(f'Check {recipient} for the email.\n'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR('\n❌ FAILED to send email!\n'))
            self.stdout.write(self.style.ERROR(f'Error Type: {type(e).__name__}'))
            self.stdout.write(self.style.ERROR(f'Error Message: {str(e)}\n'))
            
            # Provide specific troubleshooting based on error
            error_str = str(e).lower()
            
            if 'authentication failed' in error_str or '535' in error_str:
                self.stdout.write(self.style.WARNING('🔐 Authentication Issue:'))
                self.stdout.write('   - Check your EMAIL_PASSWORD is correct')
                self.stdout.write('   - Verify ryan@myrecoverypal.com password in Microsoft 365')
                self.stdout.write('   - Ensure SMTP authentication is enabled for this account')
                
            elif 'connection refused' in error_str or 'timed out' in error_str:
                self.stdout.write(self.style.WARNING('🌐 Connection Issue:'))
                self.stdout.write('   - Check if smtp.office365.com is accessible')
                self.stdout.write('   - Verify port 587 is not blocked')
                self.stdout.write('   - Check Railway network settings')
                
            elif 'recipient' in error_str or 'address' in error_str:
                self.stdout.write(self.style.WARNING('📧 Recipient Issue:'))
                self.stdout.write(f'   - Check if {recipient} is a valid email address')
                
            else:
                self.stdout.write(self.style.WARNING('📋 General troubleshooting:'))
                self.stdout.write('   1. Verify EMAIL_PASSWORD is set in Railway')
                self.stdout.write('   2. Check Microsoft 365 admin center')
                self.stdout.write('   3. Ensure account has SMTP enabled')
                self.stdout.write('   4. Try with a different recipient email')
            
            import traceback
            self.stdout.write(self.style.ERROR('\nFull traceback:'))
            self.stdout.write(traceback.format_exc())