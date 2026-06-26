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


from unittest.mock import patch
from decimal import Decimal


class FeaturedProductSelectionTest(TestCase):
    """select_featured_products() picks featured first, falls back to newest."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='Test', slug='test')

    def _product(self, name, **kwargs):
        from apps.store.models import Product
        defaults = dict(
            name=name,
            category=self.cat,
            description='x',
            price=Decimal('10.00'),
            external_url='https://example.com/p',
            is_active=True,
            is_featured=False,
        )
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def test_returns_featured_first(self):
        from apps.store.email_service import select_featured_products
        self._product('Plain A')
        f1 = self._product('Featured A', is_featured=True)
        f2 = self._product('Featured B', is_featured=True)
        result = list(select_featured_products(limit=3))
        self.assertEqual(result[0], f2)  # newest featured first
        self.assertEqual(result[1], f1)
        # Third slot filled by the plain product as fallback
        self.assertEqual(len(result), 3)

    def test_falls_back_to_newest_when_no_featured(self):
        from apps.store.email_service import select_featured_products
        p1 = self._product('Plain A')
        p2 = self._product('Plain B')
        result = list(select_featured_products(limit=3))
        self.assertIn(p1, result)
        self.assertIn(p2, result)

    def test_excludes_inactive_products(self):
        from apps.store.email_service import select_featured_products
        active = self._product('Active', is_featured=True)
        self._product('Inactive', is_featured=True, is_active=False)
        result = list(select_featured_products(limit=3))
        self.assertIn(active, result)
        self.assertEqual(len(result), 1)

    def test_respects_limit(self):
        from apps.store.email_service import select_featured_products
        for i in range(5):
            self._product(f'P{i}', is_featured=True)
        result = list(select_featured_products(limit=3))
        self.assertEqual(len(result), 3)

    def test_offset_rotates_window_for_weekly_variety(self):
        from apps.store.email_service import select_featured_products
        for i in range(9):
            self._product(f'P{i}')
        week_a = set(p.pk for p in select_featured_products(limit=3, offset=1))
        week_b = set(p.pk for p in select_featured_products(limit=3, offset=2))
        week_c = set(p.pk for p in select_featured_products(limit=3, offset=3))
        # Consecutive weeks show different products...
        self.assertNotEqual(week_a, week_b)
        self.assertNotEqual(week_b, week_c)
        # ...and over a full cycle the whole catalog is covered.
        self.assertEqual(week_a | week_b | week_c, set(p.pk for p in __import__(
            'apps.store.models', fromlist=['Product']).Product.objects.all()))

    def test_offset_is_deterministic_within_a_week(self):
        from apps.store.email_service import select_featured_products
        for i in range(9):
            self._product(f'P{i}')
        first = [p.pk for p in select_featured_products(limit=3, offset=5)]
        second = [p.pk for p in select_featured_products(limit=3, offset=5)]
        self.assertEqual(first, second)


class MilestoneEligibilityTest(TestCase):
    """find_users_hitting_milestone_today() returns the right user set."""

    def _user_sober_for(self, days, **overrides):
        kwargs = dict(
            username=f'u{days}',
            email=f'u{days}@example.com',
            password='pw',
        )
        kwargs.update(overrides)
        user = User.objects.create_user(**kwargs)
        user.sobriety_date = date.today() - timedelta(days=days)
        user.marketing_emails_enabled = True
        user.save()
        return user

    def test_finds_user_at_exact_milestone(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(30)
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 1)
        user, milestone = results[0]
        self.assertEqual(milestone, 30)

    def test_skips_user_not_at_milestone(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(45)  # not a milestone
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_skips_user_with_marketing_disabled(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        user = self._user_sober_for(30)
        user.marketing_emails_enabled = False
        user.save()
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_skips_user_already_emailed(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        from apps.store.models import MilestoneEmailSent
        user = self._user_sober_for(30)
        MilestoneEmailSent.objects.create(user=user, milestone_days=30)
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_finds_year_anniversaries(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(730)  # 2 years
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 1)
        _, milestone = results[0]
        self.assertEqual(milestone, 730)

    def test_skips_user_without_sobriety_date(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        u = User.objects.create_user(username='nodate', email='nd@x.com', password='pw')
        u.sobriety_date = None
        u.save()
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WeeklyDigestSendTest(TestCase):
    """send_weekly_shop_digest() sends to opted-in users only."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='X', slug='x')
        Product.objects.create(
            name='Featured', category=self.cat, description='x',
            price=Decimal('10.00'), external_url='https://example.com/f',
            is_active=True, is_featured=True,
        )
        # Three users: two opted-in, one opted-out
        self.opted_in_1 = User.objects.create_user(
            username='oi1', email='oi1@example.com', password='pw'
        )
        self.opted_in_2 = User.objects.create_user(
            username='oi2', email='oi2@example.com', password='pw'
        )
        self.opted_out = User.objects.create_user(
            username='oo', email='oo@example.com', password='pw'
        )
        self.opted_out.marketing_emails_enabled = False
        self.opted_out.save()

    @patch('apps.store.email_service.send_email')
    def test_sends_to_opted_in_users_only(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_weekly_shop_digest
        sent_count = send_weekly_shop_digest()
        self.assertEqual(sent_count, 2)  # opted_in_1 + opted_in_2
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertIn('oi1@example.com', recipients)
        self.assertIn('oi2@example.com', recipients)
        self.assertNotIn('oo@example.com', recipients)

    @patch('apps.store.email_service.send_email')
    def test_email_contains_unsubscribe_url(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_weekly_shop_digest
        send_weekly_shop_digest()
        first_call = mock_send.call_args_list[0]
        html = first_call.kwargs['html_message']
        self.assertIn('/email/unsubscribe/', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MilestoneCelebrationSendTest(TestCase):
    """send_milestone_celebration_email() sends one email + creates dedup row."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='Stickers', slug='stickers')
        Product.objects.create(
            name='30d Sticker', category=self.cat, description='x',
            price=Decimal('5.00'), external_url='https://example.com/s',
            is_active=True, is_featured=True,
        )
        self.user = User.objects.create_user(
            username='mile', email='mile@example.com', password='pw'
        )
        self.user.sobriety_date = date.today() - timedelta(days=30)
        self.user.save()

    @patch('apps.store.email_service.send_email')
    def test_creates_milestone_sent_row(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_milestone_celebration_email
        from apps.store.models import MilestoneEmailSent
        send_milestone_celebration_email(self.user, 30)
        self.assertTrue(
            MilestoneEmailSent.objects.filter(user=self.user, milestone_days=30).exists()
        )
        mock_send.assert_called_once()

    @patch('apps.store.email_service.send_email')
    def test_does_not_send_when_send_email_fails(self, mock_send):
        mock_send.return_value = (False, 'SMTP fail')
        from apps.store.email_service import send_milestone_celebration_email
        from apps.store.models import MilestoneEmailSent
        send_milestone_celebration_email(self.user, 30)
        # No dedup row created on failure — so a retry can succeed
        self.assertFalse(
            MilestoneEmailSent.objects.filter(user=self.user, milestone_days=30).exists()
        )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WeeklyDigestTaskTest(TestCase):
    """The weekly_shop_digest_task wraps the service and is idempotent on retry."""

    def setUp(self):
        from apps.store.models import Category, Product
        cat = Category.objects.create(name='X', slug='x')
        Product.objects.create(
            name='F', category=cat, description='x',
            price=Decimal('10.00'), external_url='https://example.com/f',
            is_active=True, is_featured=True,
        )
        User.objects.create_user(username='wt1', email='wt1@example.com', password='pw')

    @patch('apps.store.tasks.send_weekly_shop_digest')
    def test_task_calls_service(self, mock_send):
        mock_send.return_value = 1
        from apps.store.tasks import weekly_shop_digest_task
        weekly_shop_digest_task()
        mock_send.assert_called_once()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MilestoneCelebrationTaskTest(TestCase):
    """The daily milestone task finds eligible users and sends to each."""

    def setUp(self):
        from apps.store.models import Category, Product
        cat = Category.objects.create(name='Stickers', slug='stickers')
        Product.objects.create(
            name='S', category=cat, description='x',
            price=Decimal('5.00'), external_url='https://example.com/s',
            is_active=True, is_featured=True,
        )

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_sends_to_users_at_milestones(self, mock_send):
        mock_send.return_value = True
        # User at 30 days
        u = User.objects.create_user(username='mu', email='mu@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=30)
        u.save()
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_called_once_with(u, 30)

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_no_op_when_no_users_at_milestone(self, mock_send):
        mock_send.return_value = True
        # User at 45 days — not a milestone
        u = User.objects.create_user(username='mu2', email='mu2@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=45)
        u.save()
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_not_called()

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_idempotent_when_already_sent(self, mock_send):
        from apps.store.models import MilestoneEmailSent
        mock_send.return_value = True
        u = User.objects.create_user(username='mu3', email='mu3@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=30)
        u.save()
        MilestoneEmailSent.objects.create(user=u, milestone_days=30)
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_not_called()
