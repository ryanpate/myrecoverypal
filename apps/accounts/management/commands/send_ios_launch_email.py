from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings

from apps.accounts.email_service import send_email


class Command(BaseCommand):
    help = 'Send iOS app launch announcement email to all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without sending emails',
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Send a test email to this address only',
        )

    def handle(self, *args, **options):
        from apps.accounts.models import User
        import time

        site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

        if options['test_email']:
            self.stdout.write(f"Sending test email to {options['test_email']}...")
            user = User.objects.filter(is_active=True).first()
            html_message = render_to_string('emails/ios_app_launch.html', {
                'user': user,
                'site_url': site_url,
                'current_year': timezone.now().year,
            })
            plain_message = strip_tags(html_message)
            success, error = send_email(
                subject="MyRecoveryPal is Now on the App Store! 🎉",
                plain_message=plain_message,
                html_message=html_message,
                recipient_email=options['test_email'],
            )
            if success:
                self.stdout.write(self.style.SUCCESS(f"Test email sent to {options['test_email']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed: {error}"))
            return

        users = User.objects.filter(
            is_active=True,
            email_notifications=True,
        ).exclude(email='').exclude(email__isnull=True)

        total = users.count()
        self.stdout.write(f"Found {total} users to email")

        if options['dry_run']:
            for user in users:
                self.stdout.write(f"  Would send to: {user.email} ({user.username})")
            self.stdout.write(self.style.SUCCESS(f"Dry run complete. {total} emails would be sent."))
            return

        sent = 0
        failed = 0

        for user in users:
            try:
                html_message = render_to_string('emails/ios_app_launch.html', {
                    'user': user,
                    'site_url': site_url,
                    'current_year': timezone.now().year,
                })
                plain_message = strip_tags(html_message)

                success, error = send_email(
                    subject="MyRecoveryPal is Now on the App Store! 🎉",
                    plain_message=plain_message,
                    html_message=html_message,
                    recipient_email=user.email,
                )

                if success:
                    sent += 1
                    self.stdout.write(f"  Sent to {user.email}")
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f"  Failed for {user.email}: {error}"))

                # Rate limit: 0.5s between emails
                time.sleep(0.5)

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  Error for {user.email}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Done! Sent: {sent}, Failed: {failed}, Total: {total}"
        ))
