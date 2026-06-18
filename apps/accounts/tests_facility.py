"""Tests for the treatment-center aftercare (Facility) feature."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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


from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EnrollmentConsentTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.invite = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code())
        self.user = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')

    def test_join_requires_login(self):
        resp = self.client.get(
            reverse('accounts:facility_join', args=[self.invite.code]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.url)

    def test_consent_activates_membership(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]),
            {'consent': 'on'})
        self.assertEqual(resp.status_code, 302)
        m = FacilityMembership.objects.get(facility=self.facility, user=self.user)
        self.assertEqual(m.status, 'active')
        self.assertIsNotNone(m.consent_granted_at)
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.uses, 1)

    def test_join_without_consent_does_not_activate(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]), {})
        self.assertFalse(FacilityMembership.objects.filter(
            facility=self.facility, user=self.user, status='active').exists())

    def test_expired_invite_rejected(self):
        self.invite.expires_at = timezone.now() - timedelta(days=1)
        self.invite.save()
        self.client.force_login(self.user)
        self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]),
            {'consent': 'on'})
        self.assertFalse(FacilityMembership.objects.filter(
            facility=self.facility, user=self.user, status='active').exists())

    def test_member_can_revoke(self):
        self.client.force_login(self.user)
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.user,
            status='active', consent_granted_at=timezone.now())
        self.client.post(reverse('accounts:facility_leave', args=[m.id]))
        m.refresh_from_db()
        self.assertEqual(m.status, 'revoked')
        self.assertFalse(m.is_visible_to_staff)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class StaffDashboardTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.other = Facility.objects.create(name='Rival', slug='rival')
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='pw')
        FacilityStaff.objects.create(facility=self.facility, user=self.staff_user)
        self.alum = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.alum,
            status='active', consent_granted_at=timezone.now())

    def test_non_staff_blocked(self):
        self.client.force_login(self.alum)
        resp = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_staff_sees_dashboard(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'alum')

    def test_tenant_isolation_on_member_detail(self):
        # a membership in the rival facility must 404 for this staff
        rival_member = FacilityMembership.objects.create(
            facility=self.other, user=self.alum,
            status='active', consent_granted_at=timezone.now())
        self.client.force_login(self.staff_user)
        resp = self.client.get(
            reverse('accounts:facility_member', args=[rival_member.id]))
        self.assertEqual(resp.status_code, 404)

    def test_member_detail_hidden_without_consent(self):
        self.m.consent_granted_at = None
        self.m.status = 'invited'
        self.m.save()
        self.client.force_login(self.staff_user)
        resp = self.client.get(
            reverse('accounts:facility_member', args=[self.m.id]))
        self.assertEqual(resp.status_code, 404)

    def test_generate_invite(self):
        self.client.force_login(self.staff_user)
        resp = self.client.post(reverse('accounts:facility_generate_invite'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FacilityInvite.objects.filter(facility=self.facility).exists())


from unittest.mock import patch
from apps.accounts.tasks import send_facility_risk_digest


class DigestTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='pw')
        FacilityStaff.objects.create(facility=self.facility, user=self.staff_user)
        self.alum = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')
        # active + consented, no check-ins => at-risk (disengaged)
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.alum,
            status='active', consent_granted_at=timezone.now())

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_digest_emails_staff_about_newly_at_risk(self, mock_send):
        sent = send_facility_risk_digest()
        self.assertEqual(sent, 1)
        mock_send.assert_called_once()
        self.m.refresh_from_db()
        self.assertIsNotNone(self.m.risk_notified_at)

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_digest_does_not_repeat_already_notified(self, mock_send):
        self.m.risk_notified_at = timezone.now()
        self.m.save()
        sent = send_facility_risk_digest()
        self.assertEqual(sent, 0)
        mock_send.assert_not_called()

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_recovered_member_clears_notified_flag(self, mock_send):
        from apps.accounts.models import DailyCheckIn
        self.m.risk_notified_at = timezone.now()
        self.m.save()
        DailyCheckIn.objects.create(
            user=self.alum, date=timezone.now().date(),
            mood=5, craving_level=0, energy_level=4)  # now ok
        send_facility_risk_digest()
        self.m.refresh_from_db()
        self.assertIsNone(self.m.risk_notified_at)
