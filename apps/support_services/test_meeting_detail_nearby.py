"""The "Nearby Meetings" sidebar must stay bounded on every detail page.

The `[:5]` slice used to live inside `if meeting.city:`, so a meeting with a
blank city (every online meeting) fell through with an unsliced queryset and
rendered all ~1,565 approved meetings — a full-table scan plus a URL reverse
per row, turning an 11 KB page into 218 KB. With only 2 sync gunicorn workers
that was enough for a directory crawl to saturate the site.
"""
from datetime import time

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting


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
class NearbyMeetingsBoundedTests(TestCase):

    def test_online_meeting_does_not_render_the_whole_directory(self):
        """A city-less meeting must not fall through the slice."""
        target = _meeting(slug='target-online')
        for i in range(12):
            _meeting(name=f'Other {i}', slug=f'other-{i}')

        resp = self.client.get(
            reverse('support_services:meeting_detail', args=['target-online']))

        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.context['nearby_meetings']), 5)
        self.assertNotIn(target, resp.context['nearby_meetings'])

    def test_in_person_meeting_is_still_capped_at_five(self):
        _meeting(slug='target-houston', attendance_option='in_person',
                 conference_url='', city='Houston', state='TX')
        for i in range(12):
            _meeting(name=f'Houston {i}', slug=f'houston-{i}',
                     attendance_option='in_person', conference_url='',
                     city='Houston', state='TX')

        resp = self.client.get(
            reverse('support_services:meeting_detail', args=['target-houston']))

        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.context['nearby_meetings']), 5)
