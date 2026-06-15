from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts import payment_views
from apps.accounts.payment_models import Subscription, SubscriptionPlan
from apps.accounts.tasks import send_winback_offers

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WinbackViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('w', 'w@example.com', 'pw')
        self.client.force_login(self.user)
        SubscriptionPlan.objects.filter(tier='premium').delete()
        self.yearly = SubscriptionPlan.objects.create(
            tier='premium', billing_period='yearly', name='Premium (Yearly)',
            price='59.99', is_active=True, stripe_price_id='price_year',
        )

    @patch('apps.accounts.payment_views._get_winback_coupon', return_value='winback50_3mo')
    @patch('apps.accounts.payment_views._build_checkout_session')
    def test_winback_applies_coupon_and_redirects(self, mock_build, mock_coupon):
        mock_build.return_value = MagicMock(url='https://checkout/winback')
        resp = self.client.get(reverse('accounts:winback'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], 'https://checkout/winback')
        # Coupon is passed through to the session builder.
        self.assertEqual(mock_build.call_args.kwargs['coupon'], 'winback50_3mo')

    @patch('apps.accounts.payment_views._get_winback_coupon', return_value=None)
    @patch('apps.accounts.payment_views._build_checkout_session', side_effect=Exception('boom'))
    def test_winback_falls_back_to_pricing(self, mock_build, mock_coupon):
        resp = self.client.get(reverse('accounts:winback'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('accounts:pricing'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WinbackTaskTests(TestCase):
    def _make_user(self, username, trial_end, status='expired', winback_sent_at=None):
        u = User.objects.create_user(username, f'{username}@example.com', 'pw')
        sub = Subscription.objects.get(user=u)
        sub.status = status
        sub.trial_end = trial_end
        sub.winback_sent_at = winback_sent_at
        sub.save()
        return u, sub

    @patch('apps.accounts.tasks.send_email', return_value=True)
    def test_targets_recently_lapsed_and_sets_flag(self, mock_send):
        now = timezone.now()
        u, sub = self._make_user('lapsed', now - timedelta(days=2))
        result = send_winback_offers()
        self.assertEqual(result['sent'], 1)
        sub.refresh_from_db()
        self.assertIsNotNone(sub.winback_sent_at)
        mock_send.assert_called_once()

    @patch('apps.accounts.tasks.send_email', return_value=True)
    def test_skips_already_offered(self, mock_send):
        now = timezone.now()
        self._make_user('already', now - timedelta(days=2), winback_sent_at=now - timedelta(days=1))
        self.assertEqual(send_winback_offers()['sent'], 0)
        mock_send.assert_not_called()

    @patch('apps.accounts.tasks.send_email', return_value=True)
    def test_skips_too_recent_and_too_old(self, mock_send):
        now = timezone.now()
        self._make_user('toosoon', now - timedelta(hours=12))   # < 24h floor
        self._make_user('tooold', now - timedelta(days=45))     # > 30d ceiling
        self.assertEqual(send_winback_offers()['sent'], 0)

    @patch('apps.accounts.tasks.send_email', return_value=True)
    def test_skips_active_subscriptions(self, mock_send):
        now = timezone.now()
        self._make_user('active', now - timedelta(days=2), status='active')
        self.assertEqual(send_winback_offers()['sent'], 0)
