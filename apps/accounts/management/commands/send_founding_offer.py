"""
Email the founding-member offer (apps/accounts/founding_offer.py) to members
who can claim it: opted in to product email (marketing_emails_enabled),
active, and eligible (not already paying for Premium). Never twice per
email type (AnnouncementDelivery). --reminder sends the "last few days"
version, under its own key, to eligible members who haven't claimed it.

Dry-run by default. Run in-container via railway ssh:
    python manage.py send_founding_offer --test you@example.com
    python manage.py send_founding_offer                 # dry-run
    python manage.py send_founding_offer --commit        # send the offer
    python manage.py send_founding_offer --reminder --commit   # ~3 days before it ends
"""
import time

from django.conf import settings
from django.core import signing
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from apps.accounts import founding_offer as offer
from apps.accounts.email_service import send_email
from apps.accounts.models import AnnouncementDelivery, User
from apps.accounts.payment_models import SubscriptionPlan

TEMPLATE = 'emails/founding_offer.html'


def keys(reminder):
    base = f'founding-offer-{offer.ends_on().isoformat()}'
    return base + ('-reminder' if reminder else '')


def subject(reminder):
    if reminder:
        return f"Last few days: your founding-member price ends {offer.ends_on():%B} {offer.ends_on().day}"
    return f'A thank-you for being here early: {offer.percent_off()}% off Premium'


class Command(BaseCommand):
    help = 'Email the founding-member offer to eligible, opted-in members.'

    def add_arguments(self, parser):
        parser.add_argument('--reminder', action='store_true', help='Send the "last few days" reminder instead.')
        parser.add_argument('--test', metavar='EMAIL', help='Send one test email to this address and exit.')
        parser.add_argument('--commit', action='store_true', help='Actually send (default is dry-run).')
        parser.add_argument('--sleep', type=float, default=0.6)

    def handle(self, *args, **opts):
        plan = SubscriptionPlan.objects.filter(tier='premium', billing_period='yearly', is_active=True).first()
        if plan is None:
            raise CommandError('No active annual Premium plan.')
        if not offer.is_active():
            raise CommandError(f'The offer ended on {offer.ends_on()}. Set FOUNDING_OFFER_ENDS to run it again.')
        site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
        reminder = opts['reminder']
        key = keys(reminder)

        if opts['test']:
            user = User.objects.filter(email__iexact=opts['test']).first()
            html = render_to_string(TEMPLATE, self._context(user, plan, site_url, reminder))
            send_email(subject=f'[TEST] {subject(reminder)}', plain_message=strip_tags(html),
                       html_message=html, recipient_email=opts['test'])
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {opts['test']}. (Not recorded.)"))
            return

        already = AnnouncementDelivery.objects.filter(key=key).values_list('user_id', flat=True)
        qs = (User.objects.filter(is_active=True, marketing_emails_enabled=True)
              .exclude(email='').exclude(id__in=already)
              .select_related('subscription').order_by('id'))
        recipients = [u for u in qs if offer.is_eligible(u)]
        self.stdout.write(f"{'Reminder' if reminder else 'Offer'}: {offer.percent_off()}% off the first year "
                          f"(${offer.discounted_price(plan)} instead of ${plan.price}), ends {offer.ends_on()}  |  "
                          f"Recipients: {len(recipients)}  |  Mode: {'COMMIT' if opts['commit'] else 'DRY-RUN'}")
        if not opts['commit']:
            for u in recipients[:25]:
                self.stdout.write(f'  would send -> {u.email} ({u.username})')
            if len(recipients) > 25:
                self.stdout.write(f'  ... and {len(recipients) - 25} more')
            self.stdout.write('Dry-run complete. Re-run with --commit to send.')
            return

        sent = failed = 0
        for u in recipients:
            try:
                html = render_to_string(TEMPLATE, self._context(u, plan, site_url, reminder))
                send_email(subject=subject(reminder), plain_message=strip_tags(html),
                           html_message=html, recipient_email=u.email)
                AnnouncementDelivery.objects.get_or_create(user=u, key=key)
                sent += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f'  FAILED {u.email}: {exc}')
            time.sleep(opts['sleep'])
        self.stdout.write(self.style.SUCCESS(f'Done. Sent {sent}, failed {failed}.'))

    @staticmethod
    def _context(user, plan, site_url, reminder):
        sub = getattr(user, 'subscription', None) if user else None
        utm = f'?utm_source=email&utm_medium=offer&utm_campaign={keys(reminder)}'
        if user:
            token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
            unsubscribe = f"{site_url}{reverse('unsubscribe_marketing', args=[token])}"
        else:
            unsubscribe = f"{site_url}{reverse('accounts:edit_profile')}"
        return {
            'first_name': (user.first_name or user.username) if user else 'there',
            'reminder': reminder,
            'percent': offer.percent_off(),
            'price': offer.discounted_price(plan),
            'full_price': plan.price,
            'ends': offer.ends_on(),
            'trial': bool(sub and sub.card_trial_eligible()) if user else True,
            'claim_url': f"{site_url}{reverse('accounts:founding_offer')}{utm}",
            'library_url': f"{site_url}{reverse('resources:list')}{utm}",
            'unsubscribe_url': unsubscribe,
        }
