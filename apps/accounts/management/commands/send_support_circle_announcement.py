"""
Send the one-off "Support Circle" announcement email.

Targets opted-in (marketing_emails_enabled) active users with an email who
haven't already received it (support_circle_email_sent_at is null). Default
segment is 'engaged' (a check-in within the last 30 days); 'all' targets
everyone opted in. Reuses the existing `unsubscribe_marketing` route for a
one-click opt-out.

Dry-run by default. Run in-container via railway ssh:
    railway ssh "python manage.py send_support_circle_announcement"                  # dry-run, engaged
    railway ssh "python manage.py send_support_circle_announcement --test you@x.com" # one test email
    railway ssh "python manage.py send_support_circle_announcement --commit"         # send to engaged
    railway ssh "python manage.py send_support_circle_announcement --segment all --commit"
"""
import time
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.accounts.email_service import send_email
from apps.accounts.models import User, DailyCheckIn

SUBJECT = "Invite someone who's in your corner"
TEMPLATE = 'emails/support_circle_announcement.html'
ENGAGED_DAYS = 30


class Command(BaseCommand):
    help = "Send the Support Circle announcement email to opted-in users."

    def add_arguments(self, parser):
        parser.add_argument('--segment', choices=['engaged', 'all'], default='engaged')
        parser.add_argument('--test', metavar='EMAIL', help='Send one test email to this address and exit.')
        parser.add_argument('--commit', action='store_true', help='Actually send (default is dry-run).')
        parser.add_argument('--sleep', type=float, default=0.4, help='Seconds between sends (rate-limit politeness).')

    def handle(self, *args, **opts):
        site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')

        if opts['test']:
            self._send_one_test(opts['test'], site_url)
            return

        commit = opts['commit']
        segment = opts['segment']

        qs = (User.objects
              .filter(is_active=True, marketing_emails_enabled=True,
                      support_circle_email_sent_at__isnull=True)
              .exclude(email=''))
        if segment == 'engaged':
            cutoff = timezone.now().date() - timedelta(days=ENGAGED_DAYS)
            engaged_ids = (DailyCheckIn.objects.filter(date__gte=cutoff)
                           .values_list('user_id', flat=True).distinct())
            qs = qs.filter(id__in=list(engaged_ids))

        recipients = list(qs)
        self.stdout.write(f"Segment: {segment}  |  Recipients: {len(recipients)}  |  "
                          f"Mode: {'COMMIT' if commit else 'DRY-RUN'}")

        if not commit:
            for u in recipients[:25]:
                self.stdout.write(f"  would send -> {u.email} ({u.username})")
            if len(recipients) > 25:
                self.stdout.write(f"  ... and {len(recipients) - 25} more")
            self.stdout.write("Dry-run complete. Re-run with --commit to send.")
            return

        sent = failed = 0
        for u in recipients:
            try:
                self._send_to_user(u, site_url)
                u.support_circle_email_sent_at = timezone.now()
                u.save(update_fields=['support_circle_email_sent_at'])
                sent += 1
            except Exception as exc:  # never let one bad address halt the run
                failed += 1
                self.stderr.write(f"  FAILED {u.email}: {exc}")
            time.sleep(opts['sleep'])
        self.stdout.write(self.style.SUCCESS(f"Done. Sent {sent}, failed {failed}."))

    # ---- helpers ---------------------------------------------------------

    def _context(self, user, site_url):
        token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
        return {
            'first_name': user.first_name or user.username or 'there',
            'cta_url': f"{site_url}{reverse('accounts:supporter_manage')}",
            'unsubscribe_url': f"{site_url}{reverse('unsubscribe_marketing', args=[token])}",
        }

    def _send_to_user(self, user, site_url):
        html = render_to_string(TEMPLATE, self._context(user, site_url))
        send_email(subject=SUBJECT, plain_message=strip_tags(html),
                   html_message=html, recipient_email=user.email)

    def _send_one_test(self, email, site_url):
        user = User.objects.filter(email__iexact=email).first()
        if user:
            ctx = self._context(user, site_url)
        else:
            ctx = {
                'first_name': 'there',
                'cta_url': f"{site_url}{reverse('accounts:supporter_manage')}",
                'unsubscribe_url': f"{site_url}{reverse('accounts:edit_profile')}",
            }
        html = render_to_string(TEMPLATE, ctx)
        send_email(subject=f"[TEST] {SUBJECT}", plain_message=strip_tags(html),
                   html_message=html, recipient_email=email)
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {email}."))
