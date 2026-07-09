"""Tests for the public pricing page (July 2026 conversion fixes).

Locks in:
- /accounts/pricing/ is public (was @login_required, which walled off
  prospects and blocked search indexing despite being in the sitemap)
- exactly one Premium card renders (the old per-plan loop rendered a
  "MOST POPULAR" card per billing period)
- gate copy honesty: no second-trial promise to authenticated users
  (checkout does not grant one) and no fictional feature claims
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.payment_models import SubscriptionPlan

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PricingPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Plans may already be seeded by data migrations; make them deterministic.
        cls.monthly, _ = SubscriptionPlan.objects.update_or_create(
            tier='premium', billing_period='monthly',
            defaults=dict(name='Premium Monthly', price=Decimal('9.99'),
                          stripe_price_id='price_test_monthly', is_active=True),
        )
        cls.yearly, _ = SubscriptionPlan.objects.update_or_create(
            tier='premium', billing_period='yearly',
            defaults=dict(name='Premium Yearly', price=Decimal('59.99'),
                          stripe_price_id='price_test_yearly', is_active=True),
        )
        cls.user = User.objects.create_user(
            username='pricing_tester', email='pricing_tester@example.com',
            password='testpass123',
        )

    def test_pricing_is_public(self):
        response = self.client.get(reverse('accounts:pricing'))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_sees_trial_framing_and_register_cta(self):
        response = self.client.get(reverse('accounts:pricing'))
        content = response.content.decode()
        self.assertIn('14-day free trial', content.lower())
        self.assertIn('Start 14-Day Free Trial', content)

    def test_single_premium_card_with_annual_default(self):
        response = self.client.get(reverse('accounts:pricing'))
        content = response.content.decode()
        self.assertEqual(content.count('MOST POPULAR'), 1)
        self.assertIn('billing-toggle', content)
        self.assertIn('premium-price-yearly', content)

    def test_logged_in_user_gets_no_second_trial_promise(self):
        # Simulate a post-trial free user (signup signal grants a trialing
        # premium sub, which would render "Current Plan" instead of buttons).
        if hasattr(self.user, 'subscription'):
            self.user.subscription.tier = 'free'
            self.user.subscription.status = 'expired'
            self.user.subscription.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:pricing'))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        # Every account already received the signup trial; checkout will not
        # grant another, so the page must not promise one.
        self.assertNotIn('14-DAY FREE TRIAL', content)
        self.assertIn('data-monthly-id', content)
        self.assertIn('data-yearly-id', content)

    def test_no_fictional_feature_claims(self):
        response = self.client.get(reverse('accounts:pricing'))
        content = response.content.decode()
        self.assertNotIn('10 AI Coach messages', content)   # real limit is 3/day
        self.assertNotIn('30-day journal', content)          # never enforced
        self.assertNotIn('PDF export', content)              # export is CSV
        self.assertNotIn('Priority support', content)        # no such mechanism
        self.assertIn('3 AI Coach messages per day', content)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PaymentSuccessTierTests(TestCase):
    """The post-purchase page must speak to the tier that was bought —
    it used to show 'Welcome to Premium' + premium features to everyone."""

    def _user_with_tier(self, username, tier):
        user = User.objects.create_user(
            username=username, email=f'{username}@example.com', password='pw')
        user.subscription.tier = tier
        user.subscription.status = 'active'
        user.subscription.save()
        return user

    def _success_page(self, user):
        self.client.force_login(user)
        # No session_id: skips Stripe reconciliation, renders for current sub
        return self.client.get(reverse('accounts:payment_success')).content.decode()

    def test_court_buyer_sees_court_onboarding(self):
        content = self._success_page(self._user_with_tier('courtbuyer', 'court'))
        self.assertIn('Welcome to Court Compliance', content)
        self.assertIn('Set Up Your Court Profile', content)
        self.assertNotIn('Welcome to Premium', content)

    def test_supporter_buyer_sees_supporter_onboarding(self):
        content = self._success_page(self._user_with_tier('supbuyer', 'supporter'))
        self.assertIn('Welcome, Supporter', content)
        self.assertIn('Connect With Your Loved One', content)
        self.assertNotIn('Welcome to Premium', content)

    def test_premium_buyer_sees_premium_onboarding(self):
        content = self._success_page(self._user_with_tier('prembuyer', 'premium'))
        self.assertIn('Welcome to Premium', content)
        self.assertIn('Anchor', content)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class IosSyncTierGuardTests(TestCase):
    """iOS sync must not clobber ANY active paid Stripe tier (the old guard
    used is_premium(), which let supporter subscriptions be overwritten)."""

    def test_stripe_supporter_not_overwritten_by_ios_sync(self):
        import json
        user = User.objects.create_user(
            username='websupporter', email='ws@example.com', password='pw')
        sub = user.subscription
        sub.tier = 'supporter'
        sub.status = 'active'
        sub.subscription_source = 'stripe'
        sub.save()
        self.client.force_login(user)
        resp = self.client.post(
            reverse('accounts:ios_subscription_sync'),
            data=json.dumps({'is_premium': True,
                             'product_id': 'com.myrecoverypal.premium.monthly'}),
            content_type='application/json')
        self.assertEqual(resp.json().get('status'), 'skipped')
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'supporter')
