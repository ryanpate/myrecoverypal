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


from apps.accounts.court_models import (
    CourtReportProfile, MeetingAttendance, CourtReport,
    PROGRAM_CHOICES, MEETING_TYPE_CHOICES, VERIFICATION_CHOICES,
)


class CourtReportProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='court_u', email='cu@example.com', password='pw'
        )

    def test_profile_has_sensible_defaults(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertEqual(profile.required_meetings_per_week, 3)
        self.assertFalse(profile.auto_email_monthly)
        self.assertEqual(profile.legal_name, '')

    def test_profile_is_one_to_one_with_user(self):
        CourtReportProfile.objects.create(user=self.user)
        with self.assertRaises(Exception):
            CourtReportProfile.objects.create(user=self.user)

    def test_profile_str_includes_username(self):
        profile = CourtReportProfile.objects.create(
            user=self.user, legal_name='Court User', case_number='2026-CR-0042'
        )
        self.assertIn('court_u', str(profile))

    def test_default_period_start_set_on_save_when_empty(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertIsNotNone(profile.report_period_start)
        self.assertLessEqual(profile.report_period_start, timezone.now().date())


class MeetingAttendanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='att_user', email='att@example.com', password='pw'
        )

    def _attendance(self, **overrides):
        kwargs = dict(
            user=self.user,
            meeting_name='Tuesday Big Book',
            meeting_date=timezone.now(),
            meeting_address='123 Main St, Austin, TX',
            program='aa',
            meeting_type='open',
            verification_method='self',
        )
        kwargs.update(overrides)
        return MeetingAttendance.objects.create(**kwargs)

    def test_attendance_str_shows_user_name_and_date(self):
        att = self._attendance()
        self.assertIn('att_user', str(att))
        self.assertIn('Big Book', str(att))

    def test_attendance_program_display(self):
        att = self._attendance(program='smart')
        self.assertEqual(att.get_program_display(), 'SMART Recovery')

    def test_attendance_ordering_descending_by_date(self):
        early = self._attendance(meeting_date=timezone.now() - timedelta(days=5))
        late = self._attendance(meeting_date=timezone.now())
        results = list(MeetingAttendance.objects.filter(user=self.user))
        self.assertEqual(results[0], late)
        self.assertEqual(results[1], early)

    def test_attendance_default_verification_is_self(self):
        att = MeetingAttendance.objects.create(
            user=self.user,
            meeting_name='Daily',
            meeting_date=timezone.now(),
            program='aa',
            meeting_type='open',
        )
        self.assertEqual(att.verification_method, 'self')


class CourtReportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rep_user', email='rep@example.com', password='pw'
        )

    def test_report_str(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='deadbeef' * 8,
            attendance_count=12,
        )
        self.assertIn('rep_user', str(report))
        self.assertIn('2026-05', str(report))

    def test_short_hash_property_returns_first_8_chars(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='abc123def456' + '0' * 52,
            attendance_count=0,
        )
        self.assertEqual(report.short_hash, 'abc123de')
