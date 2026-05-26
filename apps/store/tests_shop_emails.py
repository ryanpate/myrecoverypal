# apps/store/tests_shop_emails.py
"""Tests for shop emails (weekly digest + milestone celebrations)."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class MarketingFieldTest(TestCase):
    """User has a marketing_emails_enabled flag, defaults True."""

    def test_field_defaults_to_true(self):
        user = User.objects.create_user(
            username='m1', email='m1@example.com', password='pw'
        )
        self.assertTrue(user.marketing_emails_enabled)

    def test_field_persists_after_save(self):
        user = User.objects.create_user(
            username='m2', email='m2@example.com', password='pw'
        )
        user.marketing_emails_enabled = False
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.marketing_emails_enabled)


class MilestoneEmailSentModelTest(TestCase):
    """MilestoneEmailSent tracks which milestones have been emailed per user."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='mes', email='mes@example.com', password='pw'
        )

    def test_create_milestone_sent_row(self):
        from apps.store.models import MilestoneEmailSent
        row = MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
        self.assertEqual(row.milestone_days, 30)
        self.assertIsNotNone(row.sent_at)

    def test_unique_per_user_and_milestone(self):
        from apps.store.models import MilestoneEmailSent
        MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
