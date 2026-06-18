"""Tests for the treatment-center aftercare (Facility) feature."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.facility_models import (
    Facility, FacilityStaff, FacilityMembership, FacilityInvite,
)
from apps.accounts.models import DailyCheckIn
from apps.accounts import facility_service as fs

User = get_user_model()


class FacilityModelTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope Center', slug='hope-center')
        self.client_user = User.objects.create_user(
            username='alum1', email='alum1@example.com', password='pw')

    def test_membership_not_visible_without_consent(self):
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.client_user, status='invited')
        self.assertFalse(m.is_visible_to_staff)

    def test_membership_visible_when_active_and_consented(self):
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.client_user,
            status='active', consent_granted_at=timezone.now())
        self.assertTrue(m.is_visible_to_staff)

    def test_invite_validity(self):
        valid = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code())
        self.assertTrue(valid.is_valid())

        expired = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code(),
            expires_at=timezone.now() - timedelta(days=1))
        self.assertFalse(expired.is_valid())

        maxed = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code(),
            uses=3, max_uses=3)
        self.assertFalse(maxed.is_valid())


class RiskComputationTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.user = User.objects.create_user(
            username='u', email='u@example.com', password='pw')
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.user,
            status='active', consent_granted_at=timezone.now())

    def _checkin(self, days_ago, mood=4, craving=0):
        return DailyCheckIn.objects.create(
            user=self.user, date=timezone.now().date() - timedelta(days=days_ago),
            mood=mood, craving_level=craving, energy_level=3)

    def test_no_checkins_is_at_risk_disengaged(self):
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_AT_RISK)
        self.assertIn('disengaged', r['flags'])

    def test_recent_engaged_is_ok(self):
        self._checkin(0, mood=5, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_OK)
        self.assertEqual(r['flags'], [])

    def test_high_craving_is_at_risk(self):
        self._checkin(0, mood=4, craving=4)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_AT_RISK)
        self.assertIn('high_craving', r['flags'])

    def test_struggling_mood_is_at_risk(self):
        self._checkin(1, mood=1, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertIn('low_mood', r['flags'])

    def test_quiet_three_days_is_watch(self):
        self._checkin(3, mood=4, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_WATCH)

    def test_cohort_summary_counts_only_visible(self):
        # an invited (non-consented) member must not count
        other = User.objects.create_user(username='o', email='o@x.com', password='pw')
        FacilityMembership.objects.create(
            facility=self.facility, user=other, status='invited')
        summary = fs.cohort_summary(self.facility)
        self.assertEqual(summary['total'], 1)
        self.assertEqual(summary['at_risk'], 1)  # self.user has no check-ins
