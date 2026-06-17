from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts import payment_views
from apps.accounts.payment_models import Subscription, SubscriptionPlan

User = get_user_model()


class _FakeSession:
    url = 'https://checkout.stripe.com/c/pay/fake'
    id = 'cs_test_fake'


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class KeepPremiumTests(TestCase):
    """The one-click 'Keep Premium' trial-conversion link.

    Plan selection + fallback are tested directly; the Stripe call is mocked so
    no network/keys are needed.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='trialuser', email='t@example.com', password='pw'
        )
        self.client.force_login(self.user)
        # Ensure clean, controllable premium plans (migration may seed others).
        SubscriptionPlan.objects.filter(tier='premium').delete()
        self.yearly = SubscriptionPlan.objects.create(
            tier='premium', billing_period='yearly', name='Premium (Yearly)',
            price='59.99', is_active=True, stripe_price_id='price_year',
        )
        self.monthly = SubscriptionPlan.objects.create(
            tier='premium', billing_period='monthly', name='Premium',
            price='9.99', is_active=True, stripe_price_id='price_month',
        )

    @patch('apps.accounts.payment_views._build_checkout_session', return_value=_FakeSession())
    def test_default_uses_yearly_and_redirects_to_stripe(self, mock_build):
        resp = self.client.get(reverse('accounts:keep_premium'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], _FakeSession.url)
        # Yearly is the plan we push by default.
        self.assertEqual(mock_build.call_args.args[1].id, self.yearly.id)

    @patch('apps.accounts.payment_views._build_checkout_session', return_value=_FakeSession())
    def test_period_monthly_override(self, mock_build):
        resp = self.client.get(reverse('accounts:keep_premium') + '?period=monthly')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(mock_build.call_args.args[1].id, self.monthly.id)

    def test_no_active_plan_falls_back_to_pricing(self):
        SubscriptionPlan.objects.filter(tier='premium').update(is_active=False)
        resp = self.client.get(reverse('accounts:keep_premium'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('accounts:pricing'))

    @patch('apps.accounts.payment_views._build_checkout_session', side_effect=Exception('Stripe down'))
    def test_stripe_failure_falls_back_to_pricing(self, mock_build):
        resp = self.client.get(reverse('accounts:keep_premium'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('accounts:pricing'))

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('accounts:keep_premium'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp['Location'].lower())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class BuildCheckoutSessionTrialTests(TestCase):
    """No second free trial: align Stripe trial_end to the user's existing
    app-trial, or subscribe-now if it's gone / too soon."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='u', email='u@example.com', password='pw'
        )
        self.plan = SubscriptionPlan(
            id=999, tier='premium', billing_period='yearly',
            name='Premium (Yearly)', price='59.99', stripe_price_id='price_year',
        )

    def _capture_subscription_data(self):
        """Call _build_checkout_session with stripe mocked; return the
        subscription_data kwarg passed to Session.create."""
        req = self.factory.get('/accounts/keep-premium/')
        # Fresh instance so the reverse one-to-one isn't cached from setUp.
        req.user = User.objects.get(pk=self.user.pk)
        with patch.object(payment_views, 'stripe') as mock_stripe:
            mock_stripe.Customer.create.return_value = MagicMock(id='cus_x')
            mock_stripe.checkout.Session.create.return_value = MagicMock(id='cs', url='https://x')
            payment_views._build_checkout_session(req, self.plan)
            _, kwargs = mock_stripe.checkout.Session.create.call_args
            return kwargs['subscription_data']

    def test_active_trial_aligns_trial_end(self):
        sub = Subscription.objects.get(user=self.user)
        sub.trial_end = timezone.now() + timedelta(days=7)
        sub.stripe_subscription_id = ''
        sub.save()
        data = self._capture_subscription_data()
        self.assertIn('trial_end', data)
        self.assertAlmostEqual(data['trial_end'], int(sub.trial_end.timestamp()), delta=5)

    def test_trial_ending_soon_subscribes_now(self):
        sub = Subscription.objects.get(user=self.user)
        sub.trial_end = timezone.now() + timedelta(hours=24)  # < 48h
        sub.stripe_subscription_id = ''
        sub.save()
        data = self._capture_subscription_data()
        self.assertNotIn('trial_end', data)  # billed now — no second trial

    def test_expired_trial_subscribes_now(self):
        sub = Subscription.objects.get(user=self.user)
        sub.trial_end = timezone.now() - timedelta(days=1)
        sub.stripe_subscription_id = ''
        sub.save()
        data = self._capture_subscription_data()
        self.assertNotIn('trial_end', data)
