# apps/accounts/tests_stripe_webhook.py
"""Tests for Stripe webhook subscription handling across API versions."""
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.payment_views import handle_subscription_updated

User = get_user_model()


class SubscriptionUpdatedPeriodTest(TestCase):
    """Stripe's Basil release (2025-03-31) moved current_period_start/end off
    the subscription and onto its items. The webhook must handle both shapes."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='sub_user', email='s@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_subscription_id = 'sub_test_periods'
        sub.tier = 'premium'
        sub.status = 'active'
        sub.save()

        self.start_ts = 1757000000
        self.end_ts = self.start_ts + 30 * 86400

    def _expected(self, ts):
        return datetime.fromtimestamp(ts, tz=dt_timezone.utc)

    def test_legacy_payload_with_top_level_periods(self):
        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'active',
            'current_period_start': self.start_ts,
            'current_period_end': self.end_ts,
        })

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_basil_payload_with_item_level_periods(self):
        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'active',
            'items': {'data': [{
                'current_period_start': self.start_ts,
                'current_period_end': self.end_ts,
            }]},
        })

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_payload_without_any_periods_keeps_existing_values(self):
        existing_start = self._expected(self.start_ts)
        existing_end = self._expected(self.end_ts)
        sub = self.user.subscription
        sub.current_period_start = existing_start
        sub.current_period_end = existing_end
        sub.save()

        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'past_due',
        })

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'past_due')
        self.assertEqual(sub.current_period_start, existing_start)
        self.assertEqual(sub.current_period_end, existing_end)
