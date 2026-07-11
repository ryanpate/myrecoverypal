"""Tests for the /online-aa-meetings/ SEO landing page."""
from datetime import datetime, time

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting


def _today_meeting_day():
    # Python weekday: 0=Monday; Meeting model: 0=Sunday.
    return (datetime.now().weekday() + 1) % 7


# PREPEND_WWW=True and SECURE_SSL_REDIRECT=True in production settings cause
# 301 redirects before requests ever reach the view. Override both so
# requests reach the view directly (same pattern as other core page tests).
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class OnlineAAMeetingsPageTests(TestCase):
    def setUp(self):
        Meeting.objects.create(
            name="Today Online", slug="online-t-today",
            day=_today_meeting_day(), time=time(19, 0),
            attendance_option="online",
            conference_url="https://zoom.us/j/1",
            is_approved=True, is_active=True,
        )
        # Inactive and in-person meetings must not count.
        Meeting.objects.create(
            name="Dead Link", slug="online-t-dead",
            day=_today_meeting_day(), attendance_option="online",
            conference_url="https://zoom.us/j/2",
            is_approved=True, is_active=False,
        )
        Meeting.objects.create(
            name="In Person", slug="in-person-1",
            day=_today_meeting_day(), attendance_option="in_person",
            is_approved=True, is_active=True,
        )

    def test_page_renders_with_live_counts(self):
        resp = self.client.get(reverse("core:online_aa_meetings"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["online_count"], 1)
        self.assertContains(resp, "Today Online")
        self.assertNotContains(resp, "Dead Link")

    def test_page_contains_faq_schema(self):
        resp = self.client.get(reverse("core:online_aa_meetings"))
        self.assertContains(resp, '"@type": "FAQPage"')

    def test_page_is_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/online-aa-meetings/")
