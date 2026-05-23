# apps/accounts/tests_court.py
"""Tests for Court Compliance feature."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.payment_models import Subscription

User = get_user_model()


class TierRenameTest(TestCase):
    """The unused `pro` tier should be renamed to `court` for semantic clarity."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='court_user', email='c@example.com', password='pw'
        )

    def test_court_is_a_valid_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertIn('court', valid_tiers)

    def test_pro_is_no_longer_a_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertNotIn('pro', valid_tiers)

    def test_is_court_returns_true_for_active_court_subscription(self):
        # A Subscription is auto-created by signal on user creation; update it.
        sub = self.user.subscription
        sub.tier = 'court'
        sub.status = 'active'
        sub.save()
        self.assertTrue(sub.is_court())
        self.assertTrue(sub.is_premium())  # court is a superset of premium

    def test_is_court_returns_false_for_premium_user(self):
        sub = self.user.subscription
        sub.tier = 'premium'
        sub.status = 'active'
        sub.save()
        self.assertFalse(sub.is_court())

    def test_is_court_returns_false_for_canceled_court(self):
        sub = self.user.subscription
        sub.tier = 'court'
        sub.status = 'canceled'
        sub.save()
        self.assertFalse(sub.is_court())
