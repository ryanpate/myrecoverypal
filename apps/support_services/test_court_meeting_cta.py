"""The Court Compliance CTA on individual meeting pages.

Meeting detail pages are now indexable (see test_meeting_seo), which makes
them the site's main organic landing surface. Someone under a court order
searches for a meeting first and needs proof of attendance second — so the
CTA has to reach anonymous visitors, not just logged-in ones.
"""
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.payment_models import Subscription
from apps.support_services.models import Meeting

User = get_user_model()


def _meeting(**kwargs):
    defaults = dict(
        name='Grateful Hearts', slug='grateful-hearts',
        day=4, time=time(19, 0), timezone='America/Chicago',
        attendance_option='online', conference_url='https://zoom.us/j/1',
        is_approved=True, is_active=True,
    )
    defaults.update(kwargs)
    return Meeting.objects.create(**defaults)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtMeetingCtaTests(TestCase):
    def setUp(self):
        self.meeting = _meeting()
        self.user = User.objects.create_user('u', 'u@example.com', 'pw')
        self.sub = Subscription.objects.get(user=self.user)

    def _get(self):
        return self.client.get(self.meeting.get_absolute_url())

    def _make_court_user(self):
        self.sub.tier = 'court'
        self.sub.status = 'active'
        self.sub.save()
        self.client.force_login(self.user)

    def test_anonymous_visitor_sees_the_pitch(self):
        resp = self._get()
        self.assertContains(resp, 'Court-ordered to attend meetings?')
        self.assertContains(resp, reverse('core:court_ordered_meeting_tracker'))

    def test_logged_in_non_court_user_sees_the_pitch(self):
        self.client.force_login(self.user)
        self.assertContains(self._get(), 'Court-ordered to attend meetings?')

    def test_court_user_gets_the_log_action_not_the_pitch(self):
        """A paying court user should get the useful action, not a sales pitch."""
        self._make_court_user()
        resp = self._get()
        self.assertContains(resp, 'Log this meeting')
        self.assertNotContains(resp, 'Court-ordered to attend meetings?')

    def test_log_link_carries_the_meeting_slug(self):
        self._make_court_user()
        self.assertContains(
            self._get(),
            f"{reverse('accounts:court_attendance_create')}?meeting=grateful-hearts",
        )

    def test_cta_is_hidden_in_the_ios_app(self):
        """Court is web-only per App Store Guideline 3.1; stripe-only hides it."""
        self.assertContains(self._get(), 'court-meeting-cta stripe-only')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class AttendancePrefillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'pw')
        sub = Subscription.objects.get(user=self.user)
        sub.tier = 'court'
        sub.status = 'active'
        sub.save()
        self.client.force_login(self.user)
        self.url = reverse('accounts:court_attendance_create')

    def test_online_meeting_prefills_name_and_platform(self):
        _meeting()
        html = self.client.get(self.url, {'meeting': 'grateful-hearts'}).content.decode()
        self.assertIn('value="Grateful Hearts"', html)
        self.assertIn('value="Zoom"', html)

    def test_in_person_meeting_prefills_address(self):
        _meeting(slug='houston', attendance_option='in_person', conference_url='',
                 formatted_address='123 Main St, Houston, TX')
        html = self.client.get(self.url, {'meeting': 'houston'}).content.decode()
        self.assertIn('value="123 Main St, Houston, TX"', html)

    def test_unknown_slug_renders_a_blank_form(self):
        resp = self.client.get(self.url, {'meeting': 'does-not-exist'})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['prefill_meeting'])

    def test_unapproved_meeting_is_not_used_for_prefill(self):
        _meeting(slug='pending', is_approved=False)
        resp = self.client.get(self.url, {'meeting': 'pending'})
        self.assertIsNone(resp.context['prefill_meeting'])

    def test_no_slug_still_renders_the_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['prefill_meeting'])

    def test_posting_links_the_attendance_to_the_meeting(self):
        meeting = _meeting()
        resp = self.client.post(
            self.url + '?meeting=grateful-hearts',
            {
                'meeting_name': 'Grateful Hearts',
                'meeting_date': '2026-09-03T19:00',
                'meeting_online': 'on',
                'meeting_platform': 'Zoom',
                'program': 'aa',
                'meeting_type': 'open',
                'verification_method': 'self',
            },
        )
        self.assertEqual(resp.status_code, 302)
        att = self.user.meeting_attendances.get()
        self.assertEqual(att.meeting, meeting)
