"""Founding-member offer: eligibility, pricing, claim link, banners, email."""
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts import founding_offer as offer
from apps.accounts.models import AnnouncementDelivery
from apps.accounts.payment_models import SubscriptionPlan
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()
FUTURE = (timezone.localdate() + timedelta(days=20)).isoformat()
PAST = (timezone.localdate() - timedelta(days=1)).isoformat()


def yearly_plan():
    plan, _ = SubscriptionPlan.objects.update_or_create(
        tier='premium', billing_period='yearly',
        defaults={'name': 'Premium Annual', 'price': Decimal('59.99'), 'is_active': True,
                  'stripe_price_id': 'price_test_yearly'})
    return plan


def member(name, **sub):
    u = User.objects.create_user(name, f'{name}@example.com', 'pw12345!')
    make_free(u)
    if sub:
        s = u.subscription
        for k, v in sub.items():
            setattr(s, k, v)
        s.save()
    return u


@override_settings(FOUNDING_OFFER_ENDS=FUTURE, FOUNDING_OFFER_PERCENT='40')
class EligibilityTests(TestCase):
    def test_price_and_coupon(self):
        self.assertEqual(offer.discounted_price(yearly_plan()), Decimal('35.99'))
        self.assertEqual(offer.coupon_id(), 'founding40_first_year')

    def test_who_is_eligible(self):
        self.assertTrue(offer.is_eligible(member('free')))
        paying = member('paying', tier='premium', status='active', stripe_subscription_id='sub_1')
        self.assertFalse(offer.is_eligible(paying))
        apple = member('apple', tier='premium', status='active', stripe_subscription_id='')
        self.assertFalse(offer.is_eligible(apple))
        legacy_trial = member('legacy', tier='premium', status='trialing', stripe_subscription_id='',
                              trial_end=timezone.now() + timedelta(days=3))
        self.assertTrue(offer.is_eligible(legacy_trial))
        lapsed = member('lapsed', tier='premium', status='canceled', stripe_subscription_id='sub_2')
        self.assertTrue(offer.is_eligible(lapsed))

    def test_ends(self):
        u = member('late')
        self.assertFalse(offer.is_eligible(u, today=offer.ends_on() + timedelta(days=1)))
        with override_settings(FOUNDING_OFFER_ENDS=PAST):
            self.assertFalse(offer.is_active())
        with override_settings(FOUNDING_OFFER_ENDS='not-a-date'):
            self.assertEqual(offer.ends_on(), date.fromisoformat(offer.DEFAULT_ENDS))

    def test_coupon_is_first_year_only_and_expires(self):
        import stripe
        with patch('stripe.Coupon.retrieve', side_effect=stripe.error.InvalidRequestError('missing', None)), \
                patch('stripe.Coupon.create', return_value=SimpleNamespace(id='founding40_first_year')) as create:
            self.assertEqual(offer.get_coupon(), 'founding40_first_year')
        kwargs = create.call_args.kwargs
        # Repeating for 11 months: covers the first annual invoice (even after a
        # trial) but not the renewal 12 months later.
        self.assertEqual((kwargs['percent_off'], kwargs['duration'], kwargs['duration_in_months']),
                         (40, 'repeating', 11))
        self.assertGreater(kwargs['redeem_by'], timezone.now().timestamp())


@override_settings(FOUNDING_OFFER_ENDS=FUTURE, PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ClaimViewTests(TestCase):
    def setUp(self):
        self.plan = yearly_plan()

    def test_eligible_member_goes_to_discounted_annual_checkout(self):
        self.client.force_login(member('claim'))
        with patch('apps.accounts.founding_offer.get_coupon', return_value='founding40_first_year'), \
                patch('apps.accounts.payment_views._build_checkout_session',
                      return_value=SimpleNamespace(url='https://checkout.stripe.test/x')) as build:
            resp = self.client.get(reverse('accounts:founding_offer'))
        self.assertEqual(resp['Location'], 'https://checkout.stripe.test/x')
        args, kwargs = build.call_args
        self.assertEqual(args[1], self.plan)
        self.assertEqual(kwargs['coupon'], 'founding40_first_year')

    def test_paying_member_sent_to_pricing(self):
        self.client.force_login(member('payer', tier='premium', status='active', stripe_subscription_id='sub_9'))
        resp = self.client.get(reverse('accounts:founding_offer'))
        self.assertEqual(resp['Location'], reverse('accounts:pricing'))

    def test_expired_offer_sent_to_pricing(self):
        self.client.force_login(member('expired'))
        with override_settings(FOUNDING_OFFER_ENDS=PAST):
            resp = self.client.get(reverse('accounts:founding_offer'), follow=True)
        self.assertContains(resp, 'founding-member offer has ended')

    def test_stripe_failure_never_dead_ends(self):
        self.client.force_login(member('oops'))
        with patch('apps.accounts.founding_offer.get_coupon', return_value=None), \
                patch('apps.accounts.payment_views._build_checkout_session', side_effect=RuntimeError('stripe down')):
            resp = self.client.get(reverse('accounts:founding_offer'))
        self.assertEqual(resp['Location'], reverse('accounts:pricing'))

    def test_login_required(self):
        resp = self.client.get(reverse('accounts:founding_offer'))
        self.assertIn(reverse('accounts:login'), resp['Location'])


@override_settings(FOUNDING_OFFER_ENDS=FUTURE, PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class BannerTests(TestCase):
    def setUp(self):
        yearly_plan()

    def assert_stripe_only(self, html, text):
        i = html.index(text)
        self.assertIn('stripe-only', html[html.rfind('<div class="founding-offer ', 0, i):i])

    def test_pricing_banner_for_eligible_member(self):
        self.client.force_login(member('pb'))
        html = self.client.get(reverse('accounts:pricing')).content.decode()
        self.assertIn('$35.99', html)
        self.assertIn(reverse('accounts:founding_offer'), html)
        self.assert_stripe_only(html, '40% off your first year')

    def test_no_banner_for_paying_member(self):
        self.client.force_login(member('pp', tier='premium', status='active', stripe_subscription_id='sub_3'))
        self.assertNotContains(self.client.get(reverse('accounts:pricing')), 'founding-offer-badge')

    def test_landing_banner_invites_visitors_to_join(self):
        resp = self.client.get(reverse('core:index'))
        self.assertContains(resp, 'Join free to claim it')
        self.assertContains(resp, f"{reverse('accounts:register')}?next={reverse('accounts:founding_offer')}")

    def test_no_banner_after_deadline(self):
        with override_settings(FOUNDING_OFFER_ENDS=PAST):
            self.assertNotContains(self.client.get(reverse('core:index')), 'founding-offer-badge')

    def test_progress_card_offers_founding_price_on_web_only(self):
        self.client.force_login(member('pc'))
        html = self.client.get(reverse('accounts:progress')).content.decode()
        i = html.index('Founding member offer: 40% off')
        self.assertIn('stripe-only', html[html.rfind('<div', 0, i):i])
        self.assertIn(f'href="{reverse("accounts:founding_offer")}" class="premium-upsell-btn stripe-only"', html)
        self.assertIn('<span class="iap-only">', html)  # iOS keeps the regular card


@override_settings(FOUNDING_OFFER_ENDS=FUTURE, SITE_URL='https://www.myrecoverypal.com')
class FoundingEmailTests(TestCase):
    SEND = 'apps.accounts.management.commands.send_founding_offer.send_email'

    def setUp(self):
        yearly_plan()
        self.free = member('fe1')
        member('fe2', tier='premium', status='active', stripe_subscription_id='sub_4')
        User.objects.filter(username='fe1').update()
        optout = member('fe3')
        User.objects.filter(pk=optout.pk).update(marketing_emails_enabled=False)

    def run_cmd(self, *args):
        out = StringIO()
        with patch(self.SEND) as send:
            call_command('send_founding_offer', *args, '--sleep', '0', stdout=out, stderr=StringIO())
        return out.getvalue(), send

    def test_only_eligible_opted_in_members_once(self):
        out, send = self.run_cmd()
        self.assertIn('Recipients: 1', out)
        send.assert_not_called()
        out, send = self.run_cmd('--commit')
        self.assertEqual(send.call_args.kwargs['recipient_email'], 'fe1@example.com')
        html = send.call_args.kwargs['html_message']
        self.assertIn('$35.99 for your first year', html)
        self.assertIn('/accounts/founding/', html)
        self.assertIn('/email/unsubscribe/', html)
        out, send = self.run_cmd('--commit')
        send.assert_not_called()

    def test_reminder_is_separate_and_skips_claimers(self):
        self.run_cmd('--commit')
        out, send = self.run_cmd('--reminder', '--commit')
        self.assertTrue(send.call_args.kwargs['subject'].startswith('Last few days'))
        self.assertEqual(AnnouncementDelivery.objects.count(), 2)
        s = self.free.subscription
        s.tier, s.status, s.stripe_subscription_id = 'premium', 'active', 'sub_new'
        s.save()
        AnnouncementDelivery.objects.filter(key__endswith='-reminder').delete()
        out, send = self.run_cmd('--reminder', '--commit')
        send.assert_not_called()  # claimed it: no reminder

    def test_refuses_after_deadline(self):
        from django.core.management.base import CommandError
        with override_settings(FOUNDING_OFFER_ENDS=PAST), self.assertRaises(CommandError):
            call_command('send_founding_offer', stdout=StringIO())
