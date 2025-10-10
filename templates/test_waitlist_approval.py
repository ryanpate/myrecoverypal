# apps/accounts/management/commands/test_waitlist_approval.py
from django.core.management.base import BaseCommand
from apps.accounts.invite_models import WaitlistRequest, InviteCode
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Test the complete waitlist approval and email sending process'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email to test with')

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('WAITLIST APPROVAL TEST'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))
        
        # Clean up any existing test data
        WaitlistRequest.objects.filter(email=email).delete()
        InviteCode.objects.filter(email=email).delete()
        
        # Create a test waitlist request
        self.stdout.write('1️⃣ Creating test waitlist request...')
        waitlist_request = WaitlistRequest.objects.create(
            email=email,
            first_name='Test',
            last_name='User',
            reason='Testing the waitlist approval system',
            referral_source='Management Command',
            status='pending'
        )
        self.stdout.write(self.style.SUCCESS(f'   ✓ Created: {waitlist_request}\n'))
        
        # Approve it
        self.stdout.write('2️⃣ Approving waitlist request...')
        try:
            admin_user = User.objects.filter(is_staff=True).first()
            invite_code = waitlist_request.approve(admin_user=admin_user)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Approved!'))
            self.stdout.write(self.style.SUCCESS(f'   ✓ Invite Code: {invite_code.code}\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Approval failed: {e}\n'))
            return
        
        # Send email
        self.stdout.write('3️⃣ Sending invite email...')
        self.stdout.write('   (Check logs above for detailed email sending process)\n')
        
        success = invite_code.send_invite_email()
        
        if success:
            self.stdout.write(self.style.SUCCESS('\n✅ COMPLETE! Email sent successfully!'))
            self.stdout.write(self.style.SUCCESS(f'   Check {email} for the invite email.\n'))
        else:
            self.stdout.write(self.style.ERROR('\n❌ Email sending failed!'))
            self.stdout.write(self.style.ERROR('   Check the error logs above for details.\n'))
        
        # Show the created records
        self.stdout.write('\n📊 Created Records:')
        self.stdout.write(f'   Waitlist Request: {waitlist_request.status}')
        self.stdout.write(f'   Invite Code: {invite_code.code} ({invite_code.status})')