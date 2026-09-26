"""Free by default; a 7-day card-required Premium trial started at Stripe checkout.

Replaces the automatic no-card 14-day signup trial (1 paid user from 411
signups): users never felt a loss when it ended, and it gave every new
signup paid add-ons (e.g. the HD Medallion Pack) for free.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.payment_models import Subscription, SubscriptionPlan

User = get_user_model()


def _plan(tier='premium', period='monthly'):
    # Plan rows are seeded by data migrations (unique per tier + period).
    plan, _ = SubscriptionPlan.objects.get_or_create(
        tier=tier, billing_period=period,
        defaults={'name': f'{tier} {period}', 'price': 9.99,
                  'stripe_price_id': f'price_{tier}_{period}', 'is_active': True})
    return plan


class SignupTierTest(TestCase):

    def test_new_accounts_start_free_with_no_trial(self):
        user = User.objects.create_user(username='new', email='new@example.com', password='pw')
        sub = user.subscription
        self.assertEqual((sub.tier, sub.status, sub.trial_end), ('free', 'active', None))
        self.assertFalse(sub.is_premium())
        self.assertTrue(sub.card_trial_eligible())

    def test_users_who_already_had_a_trial_are_not_eligible_again(self):
        user = User.objects.create_user(username='legacy', email='legacy@example.com', password='pw')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(days=30)
        sub.save()
        self.assertFalse(sub.card_trial_eligible())

    def test_past_stripe_customers_are_not_eligible(self):
        user = User.objects.create_user(username='paid', email='paid@example.com', password='pw')
        sub = user.subscription
        sub.stripe_subscription_id = 'sub_old'
        sub.save()
        self.assertFalse(sub.card_trial_eligible())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CheckoutTrialTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='buyer', email='b@example.com', password='pw')
        self.sub = self.user.subscription
        self.sub.stripe_customer_id = 'cus_1'
        self.sub.save()

    def _checkout(self, plan):
        from apps.accounts.payment_views import _build_checkout_session
        request = SimpleNamespace(user=self.user, build_absolute_uri=lambda p: 'https://x' + p)
        with patch('apps.accounts.payment_views.stripe.checkout.Session.create') as create:
            _build_checkout_session(request, plan)
        return create.call_args.kwargs

    def test_eligible_premium_checkout_gets_a_7_day_card_trial(self):
        kw = self._checkout(_plan())
        self.assertEqual(kw['subscription_data']['trial_period_days'], 7)
        self.assertNotIn('trial_end', kw['subscription_data'])
        self.assertEqual(kw.get('payment_method_collection', 'always'), 'always')

    def test_court_and_supporter_plans_have_no_trial(self):
        for tier in ('court', 'supporter'):
            kw = self._checkout(_plan(tier=tier))
            self.assertNotIn('trial_period_days', kw['subscription_data'], tier)

    def test_ineligible_user_is_billed_now(self):
        self.sub.trial_end = timezone.now() - timedelta(days=30)
        self.sub.save()
        kw = self._checkout(_plan())
        self.assertNotIn('trial_period_days', kw['subscription_data'])
        self.assertNotIn('trial_end', kw['subscription_data'])

    def test_legacy_signup_trial_still_aligns_to_its_remaining_days(self):
        self.sub.tier, self.sub.status = 'premium', 'trialing'
        self.sub.trial_end = timezone.now() + timedelta(days=5)
        self.sub.save()
        kw = self._checkout(_plan())
        self.assertEqual(kw['subscription_data']['trial_end'], int(self.sub.trial_end.timestamp()))
        self.assertNotIn('trial_period_days', kw['subscription_data'])


class TrialEndingEmailTest(TestCase):

    @patch('apps.accounts.tasks.send_email')
    def test_card_trials_do_not_get_the_you_will_lose_access_email(self, send):
        from apps.accounts.tasks import send_trial_ending_notifications
        user = User.objects.create_user(username='carder', email='c@example.com', password='pw')
        sub = user.subscription
        sub.tier, sub.status = 'premium', 'trialing'
        sub.trial_end = timezone.now() + timedelta(hours=36)
        sub.stripe_subscription_id = 'sub_trial'
        sub.save()
        send_trial_ending_notifications()
        send.assert_not_called()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class TrialCopyTest(TestCase):

    def setUp(self):
        _plan()
        _plan(period='yearly')
        from apps.accounts.invite_models import SystemSettings
        s = SystemSettings.get_settings()
        s.invite_only_mode = False
        s.save()

    def test_pricing_offers_the_7_day_trial_to_eligible_users(self):
        User.objects.create_user(username='elig', email='e@example.com', password='pw')
        self.client.login(username='elig', password='pw')
        resp = self.client.get(reverse('accounts:pricing'))
        self.assertContains(resp, '7-day free trial')
        self.assertNotContains(resp, '14-day')
        self.assertNotContains(resp, '14-Day')

    def test_pricing_says_start_premium_when_not_eligible(self):
        user = User.objects.create_user(username='used', email='u@example.com', password='pw')
        user.subscription.trial_end = timezone.now() - timedelta(days=30)
        user.subscription.save()
        self.client.login(username='used', password='pw')
        resp = self.client.get(reverse('accounts:pricing'))
        self.assertNotContains(resp, 'Start 7-day free trial')

    def test_register_page_no_longer_promises_a_14_day_trial(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertNotContains(resp, '14-day')



@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class TrialBannerTest(TestCase):
    """Someone who has already subscribed must not be told to 'Keep Premium'."""

    def _user(self, stripe_id):
        user = User.objects.create_user(username=f'b{stripe_id}', email=f'b{stripe_id}@e.com', password='pw')
        Subscription.objects.filter(user=user).update(
            tier='premium', status='trialing', trial_end=timezone.now() + timedelta(days=1),
            stripe_subscription_id=stripe_id)
        self.client.force_login(user)
        return self.client.get(reverse('accounts:progress')).content.decode()

    def test_legacy_no_card_trial_sees_the_banner(self):
        self.assertIn('id="trialBanner"', self._user(''))

    def test_subscribed_user_does_not(self):
        html = self._user('sub_123')
        self.assertNotIn('id="trialBanner"', html)
        self.assertNotIn('trial-countdown-banner', html)
