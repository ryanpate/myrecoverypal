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
        self._set_sub(self.user, tier='free', status='canceled', stripe_subscription_id='sub_old')
        self.client.force_login(self.user)
        SubscriptionPlan.objects.filter(tier='premium').delete()
        self.yearly = SubscriptionPlan.objects.create(
            tier='premium', billing_period='yearly', name='Premium (Yearly)',
            price='59.99', is_active=True, stripe_price_id='price_year',
        )

    def _set_sub(self, user, **fields):
        sub = Subscription.objects.get(user=user)
        for k, v in fields.items():
            setattr(sub, k, v)
        sub.save()

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


    @patch('apps.accounts.payment_views._get_winback_coupon', return_value='winback50_3mo')
    @patch('apps.accounts.payment_views._build_checkout_session')
    def test_lapsed_trial_from_the_email_reaches_checkout(self, mock_build, mock_coupon):
        # The audience of send_winback_offers: a legacy no-card trial that expired.
        self._set_sub(self.user, status='expired', stripe_subscription_id=None,
                      trial_end=timezone.now() - timedelta(days=2))
        mock_build.return_value = MagicMock(url='https://checkout/winback')
        resp = self.client.get(reverse('accounts:winback'))
        self.assertEqual(resp['Location'], 'https://checkout/winback')
        self.assertEqual(mock_build.call_args.kwargs['coupon'], 'winback50_3mo')

    def _assert_sent_to_pricing(self, mock_build):
        resp = self.client.get(reverse('accounts:winback'), follow=True)
        self.assertRedirects(resp, reverse('accounts:pricing'))
        self.assertTrue(list(resp.context['messages']))
        mock_build.assert_not_called()

    @patch('apps.accounts.payment_views._build_checkout_session')
    def test_never_paid_free_member_goes_to_pricing(self, mock_build):
        self._set_sub(self.user, tier='free', status='active', stripe_subscription_id=None, trial_end=None)
        self._assert_sent_to_pricing(mock_build)

    @patch('apps.accounts.payment_views._build_checkout_session')
    def test_paying_member_goes_to_pricing(self, mock_build):
        self._set_sub(self.user, tier='premium', status='active', stripe_subscription_id='sub_live')
        self._assert_sent_to_pricing(mock_build)

    def test_eligibility_rules(self):
        cases = [
            # (fields, eligible)
            (dict(tier='free', status='canceled', stripe_subscription_id='sub_1'), True),
            (dict(tier='premium', status='unpaid', stripe_subscription_id='sub_1'), True),
            (dict(tier='free', status='expired', stripe_subscription_id=None,
                  trial_end=timezone.now() - timedelta(days=3)), True),
            (dict(tier='free', status='active', stripe_subscription_id=None, trial_end=None), False),
            (dict(tier='premium', status='active', stripe_subscription_id='sub_1'), False),
            (dict(tier='premium', status='active', stripe_subscription_id=None), False),  # Apple
            (dict(tier='premium', status='past_due', stripe_subscription_id='sub_1'), False),
            (dict(tier='supporter', status='active', stripe_subscription_id='sub_1'), False),
        ]
        for fields, eligible in cases:
            with self.subTest(**{k: str(v) for k, v in fields.items()}):
                self._set_sub(self.user, **{'trial_end': None, **fields})
                self.user.refresh_from_db()
                self.assertEqual(payment_views.winback_eligible(self.user), eligible)


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
