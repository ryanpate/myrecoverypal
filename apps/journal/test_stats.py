"""Journal statistics page (/journal/stats/)."""
import json
import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.journal.models import JournalEntry

User = get_user_model()

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


@override_settings(**_TEST_SETTINGS)
class JournalStatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='writer', email='w@example.com', password='x')
        self.client.force_login(self.user)

    def _chart_data(self, html):
        match = re.search(
            r'<script id="mood-trend-data" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match, 'mood trend JSON not found in page')
        return json.loads(match.group(1))

    def test_page_renders_with_no_entries(self):
        resp = self.client.get(reverse('journal:stats'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No mood data available yet')

    def test_page_renders_with_mood_entries_and_gives_the_chart_valid_json(self):
        JournalEntry.objects.create(user=self.user, title='a', content='x', mood_rating=4)
        JournalEntry.objects.create(user=self.user, title='b', content='y', mood_rating=8)
        resp = self.client.get(reverse('journal:stats'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="moodChart"', html)
        data = self._chart_data(html)
        self.assertEqual(len(data), 1)            # both entries are from today
        self.assertEqual(data[0]['avg_mood'], 6.0)
        self.assertRegex(data[0]['date'], r'^\d{4}-\d{2}-\d{2}$')
        # No Python reprs leaking into the script
        self.assertNotIn('datetime.date(', html)

    def test_other_members_entries_are_not_included(self):
        other = User.objects.create_user(username='other', email='o@example.com', password='x')
        JournalEntry.objects.create(user=other, title='secret', content='z', mood_rating=1)
        resp = self.client.get(reverse('journal:stats'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No mood data available yet')
