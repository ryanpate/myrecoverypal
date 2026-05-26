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


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class UnsubscribeViewTest(TestCase):
    """One-click unsubscribe from marketing emails via signed-URL token."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='unsub', email='u@example.com', password='pw'
        )
        self.user.marketing_emails_enabled = True
        self.user.save()

    def _signed_token(self, user_id, kind='marketing'):
        from django.core import signing
        return signing.dumps({'user_id': user_id, 'kind': kind})

    def test_valid_token_sets_flag_false(self):
        token = self._signed_token(self.user.id)
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.marketing_emails_enabled)

    def test_invalid_token_returns_404(self):
        resp = self.client.get(reverse('unsubscribe_marketing', args=['garbage-token-not-signed']))
        self.assertEqual(resp.status_code, 404)

    def test_wrong_kind_returns_404(self):
        token = self._signed_token(self.user.id, kind='transactional')
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 404)
        self.user.refresh_from_db()
        self.assertTrue(self.user.marketing_emails_enabled)  # not changed

    def test_unknown_user_returns_404(self):
        token = self._signed_token(999999)
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 404)
