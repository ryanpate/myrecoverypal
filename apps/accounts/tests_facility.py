"""Tests for the treatment-center aftercare (Facility) feature."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.facility_models import (
    Facility, FacilityStaff, FacilityMembership, FacilityInvite,
)

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
