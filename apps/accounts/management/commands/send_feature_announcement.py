"""
Send the one-off "recovery toolkit" announcement email (the new library:
audio, programs, reflections, worksheets, family course).

Targets opted-in (marketing_emails_enabled) active members with an email who
haven't received this announcement (AnnouncementDelivery with KEY). Default
segment is 'engaged' (a check-in in the last 30 days); 'all' is everyone opted
in. Premium members get a thank-you version with no upsell. Reuses the
`unsubscribe_marketing` route for one-click opt-out. Safe to re-run: anyone
already sent is skipped.

Dry-run by default. Run in-container via railway ssh:
    python manage.py send_feature_announcement                          # dry-run, engaged
    python manage.py send_feature_announcement --test you@example.com   # one test email
    python manage.py send_feature_announcement --segment all            # dry-run, everyone
    python manage.py send_feature_announcement --segment all --commit   # send
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
from apps.accounts.models import AnnouncementDelivery, DailyCheckIn, User

KEY = 'library-2026-10'
SUBJECT = 'We built you a recovery toolkit'
TEMPLATE = 'emails/library_announcement.html'
ENGAGED_DAYS = 30
UTM = f'?utm_source=email&utm_medium=announcement&utm_campaign={KEY}'


def link_urls(site_url):
    def u(name, *args):
        return f'{site_url}{reverse(name, args=args)}{UTM}'
    return {
        'library': u('resources:list'),
        'audio': u('resources:audio'),
        'programs': u('resources:programs'),
        'reflections': u('resources:reflections'),
        'worksheets': u('resources:worksheets'),
        'family': u('resources:program_detail', 'family-and-friends'),
        'pricing': u('accounts:pricing'),
    }


class Command(BaseCommand):
    help = 'Send the recovery-toolkit announcement email to opted-in members.'

    def add_arguments(self, parser):
        parser.add_argument('--segment', choices=['engaged', 'all'], default='engaged')
        parser.add_argument('--test', metavar='EMAIL', help='Send one test email to this address and exit.')
        parser.add_argument('--commit', action='store_true', help='Actually send (default is dry-run).')
        parser.add_argument('--sleep', type=float, default=0.6, help='Seconds between sends (Resend allows ~2/s).')

    def handle(self, *args, **opts):
        site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
        if opts['test']:
            self._send_one_test(opts['test'], site_url)
            return

        commit, segment = opts['commit'], opts['segment']
        already = AnnouncementDelivery.objects.filter(key=KEY).values_list('user_id', flat=True)
        qs = (User.objects.filter(is_active=True, marketing_emails_enabled=True)
              .exclude(email='').exclude(id__in=already)
              .select_related('subscription').order_by('id'))
        if segment == 'engaged':
            cutoff = timezone.now().date() - timedelta(days=ENGAGED_DAYS)
            engaged = DailyCheckIn.objects.filter(date__gte=cutoff).values_list('user_id', flat=True)
            qs = qs.filter(id__in=engaged)

        recipients = list(qs)
        premium = sum(1 for u in recipients if self._is_premium(u))
        self.stdout.write(f"Segment: {segment}  |  Recipients: {len(recipients)} "
                          f"({premium} Premium, {len(recipients) - premium} free)  |  "
                          f"Mode: {'COMMIT' if commit else 'DRY-RUN'}")
        if not commit:
            for u in recipients[:25]:
                self.stdout.write(f"  would send -> {u.email} ({u.username})")
            if len(recipients) > 25:
                self.stdout.write(f"  ... and {len(recipients) - 25} more")
            self.stdout.write('Dry-run complete. Re-run with --commit to send.')
            return

        sent = failed = 0
        for u in recipients:
            try:
                self._send_to_user(u, site_url)
                AnnouncementDelivery.objects.get_or_create(user=u, key=KEY)
                sent += 1
            except Exception as exc:  # never let one bad address halt the run
                failed += 1
                self.stderr.write(f'  FAILED {u.email}: {exc}')
            time.sleep(opts['sleep'])
        self.stdout.write(self.style.SUCCESS(f'Done. Sent {sent}, failed {failed}.'))

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _is_premium(user):
        sub = getattr(user, 'subscription', None)
        return bool(sub and sub.is_premium())

    def _context(self, user, site_url):
        sub = getattr(user, 'subscription', None)
        token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
        return {
            'first_name': user.first_name or user.username or 'there',
            'is_premium': self._is_premium(user),
            'trial_eligible': bool(sub and sub.card_trial_eligible()),
            'urls': link_urls(site_url),
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
            ctx = {'first_name': 'there', 'is_premium': False, 'trial_eligible': True,
                   'urls': link_urls(site_url),
                   'unsubscribe_url': f"{site_url}{reverse('accounts:edit_profile')}"}
        html = render_to_string(TEMPLATE, ctx)
        send_email(subject=f'[TEST] {SUBJECT}', plain_message=strip_tags(html),
                   html_message=html, recipient_email=email)
        self.stdout.write(self.style.SUCCESS(f'Test email sent to {email}. (Not recorded as delivered.)'))
