"""Tests for the /craving-sos/ page."""
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CravingSOSPageTests(TestCase):
    def test_anonymous_gets_tools_but_no_anchor(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "id=\"sos-breathing\"")
        self.assertContains(resp, "id=\"sos-urge\"")
        self.assertContains(resp, "id=\"sos-grounding\"")
        self.assertContains(resp, "988")
        self.assertContains(resp, '"@type": "FAQPage"')
        self.assertNotContains(resp, "Talk to Anchor")

    def test_logged_in_gets_anchor_and_pledge_reason(self):
        user = User.objects.create_user(
            username="m", password="x", pledge_reason="For my daughter")
        self.client.force_login(user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Talk to Anchor")
        self.assertContains(resp, reverse("accounts:coach_start_sos"))
        self.assertContains(resp, "For my daughter")

    def test_soon_meetings_render_when_present(self):
        from unittest.mock import patch
        from apps.support_services.models import Meeting
        meeting = Meeting.objects.create(
            name="Wave Riders", slug="online-t-wave", day=1, time=time(19, 0),
            timezone="America/Chicago", attendance_option="online",
            conference_url="https://zoom.us/j/9",
            is_active=True, is_approved=True,
        )
        meeting.minutes_until = 25
        with patch("apps.core.views.starting_soon", return_value=[meeting]):
            resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Wave Riders")
        self.assertContains(resp, "25 min")

    def test_sos_pill_in_nav(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "sos-pill")

    def test_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/craving-sos/")
