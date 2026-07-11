"""Tests for the relapse-plan entry points on the Craving SOS page."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import RelapsePreventionPlan

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SosPlanEntryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sosplan", password="x")

    def test_member_with_plan_sees_my_plan_pill(self):
        RelapsePreventionPlan.objects.create(
            user=self.user, triggers="Payday fridays")
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "My relapse plan")
        self.assertContains(resp, reverse("accounts:relapse_plan"))

    def test_member_without_plan_sees_build_nudge(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Build your relapse prevention plan")
        self.assertNotContains(resp, "My relapse plan")

    def test_empty_plan_row_counts_as_no_plan(self):
        RelapsePreventionPlan.objects.create(user=self.user)  # all blank
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Build your relapse prevention plan")

    def test_anonymous_sees_neither(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertNotContains(resp, "My relapse plan")
        self.assertNotContains(resp, "Build your relapse prevention plan")
