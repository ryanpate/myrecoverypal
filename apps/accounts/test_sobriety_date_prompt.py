"""Progress-home prompt that asks users without a sobriety date for one.

56% of all users (92% of recent signups) had no sobriety date, so their day
counter and milestone emails were blank. The calculator carry-over only covers
people arriving from the calculators; this covers everyone else.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Milestone

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SobrietyDatePromptTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='nodate', email='n@example.com', password='pw')
        self.client.login(username='nodate', password='pw')
        self.url = reverse('accounts:set_sobriety_date')

    def test_prompt_shows_only_without_a_date(self):
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'id="sobrietyDatePrompt"')
        self.assertContains(resp, f'action="{self.url}"')
        self.user.sobriety_date = datetime.date(2026, 1, 1)
        self.user.save()
        resp = self.client.get(reverse('accounts:progress'))
        self.assertNotContains(resp, 'id="sobrietyDatePrompt"')

    def test_saving_a_date_starts_the_counter(self):
        resp = self.client.post(self.url, {'sobriety_date': '2026-06-01'})
        self.assertRedirects(resp, reverse('accounts:progress'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.sobriety_date, datetime.date(2026, 6, 1))
        self.assertEqual(self.user.recovery_start_date, datetime.date(2026, 6, 1))
        self.assertTrue(Milestone.objects.filter(user=self.user, days_sober=0).exists())

    def test_starting_today(self):
        self.client.post(self.url, {'start_today': '1'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.sobriety_date, timezone.localdate())

    def test_invalid_dates_are_rejected(self):
        future = (timezone.localdate() + datetime.timedelta(days=10)).isoformat()
        for bad in ('', 'garbage', '2026-02-30', '1850-01-01', future):
            self.client.post(self.url, {'sobriety_date': bad})
            self.user.refresh_from_db()
            self.assertIsNone(self.user.sobriety_date, bad)

    def test_does_not_overwrite_an_existing_date(self):
        # Changing a date is a deliberate act that belongs in settings (or the
        # slip log), never a side effect of a stale prompt in another tab.
        self.user.sobriety_date = datetime.date(2025, 1, 1)
        self.user.save()
        self.client.post(self.url, {'sobriety_date': '2026-06-01'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.sobriety_date, datetime.date(2025, 1, 1))

    def test_does_not_duplicate_the_start_milestone(self):
        Milestone.objects.create(user=self.user, title='Started My Recovery Journey',
                                 description='', date_achieved=datetime.date(2026, 6, 1),
                                 milestone_type='days', days_sober=0)
        self.client.post(self.url, {'sobriety_date': '2026-06-01'})
        self.assertEqual(Milestone.objects.filter(user=self.user, days_sober=0).count(), 1)

    def test_requires_login_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        resp = self.client.post(self.url, {'sobriety_date': '2026-06-01'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)
