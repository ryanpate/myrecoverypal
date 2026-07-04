import json
import re
from datetime import timedelta
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import DailyPledge
from apps.accounts.forms import UserProfileForm

User = get_user_model()


class PledgeStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ren', password='x')

    def _pledge_on(self, d):
        DailyPledge.objects.create(user=self.user, date=d)

    def test_no_pledges_is_zero(self):
        self.assertEqual(self.user.get_pledge_streak(), 0)

    def test_today_only_is_one(self):
        self._pledge_on(timezone.now().date())
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_three_consecutive_days(self):
        today = timezone.now().date()
        for i in range(3):
            self._pledge_on(today - timedelta(days=i))
        self.assertEqual(self.user.get_pledge_streak(), 3)

    def test_gap_breaks_streak(self):
        today = timezone.now().date()
        self._pledge_on(today)
        self._pledge_on(today - timedelta(days=2))
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_yesterday_only_still_active(self):
        self._pledge_on(timezone.now().date() - timedelta(days=1))
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_one_pledge_per_day(self):
        d = timezone.now().date()
        self._pledge_on(d)
        obj, created = DailyPledge.objects.get_or_create(user=self.user, date=d)
        self.assertFalse(created)
        self.assertEqual(DailyPledge.objects.filter(user=self.user, date=d).count(), 1)

    def test_duplicate_pledge_same_day_raises(self):
        from django.db import IntegrityError, transaction
        d = timezone.now().date()
        DailyPledge.objects.create(user=self.user, date=d)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DailyPledge.objects.create(user=self.user, date=d)


class PledgeFieldDefaultTests(TestCase):
    def test_fields_default_blank(self):
        u = User.objects.create_user(username='a', password='x')
        self.assertEqual(u.pledge_reason, '')
        self.assertFalse(u.pledge_photo)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PledgeTodayEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='p', password='x')
        self.client.force_login(self.user)
        self.url = reverse('accounts:pledge_today')

    def test_first_pledge_creates_row_and_returns_streak(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data['pledged'])
        self.assertEqual(data['streak'], 1)
        self.assertTrue(DailyPledge.objects.filter(
            user=self.user, date=timezone.now().date()).exists())

    def test_pledge_is_idempotent_same_day(self):
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(DailyPledge.objects.filter(user=self.user).count(), 1)

    def test_pledge_does_not_create_a_checkin(self):
        from apps.accounts.models import DailyCheckIn
        self.client.post(self.url)
        self.assertFalse(DailyCheckIn.objects.filter(user=self.user).exists())

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (302, 401, 403))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FullCheckinPledgeUpsertTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='f', password='x')
        self.client.force_login(self.user)

    def test_checkin_with_pledge_records_dailypledge(self):
        self.client.post(reverse('accounts:daily_checkin'), {
            'mood': '4', 'energy_level': '3', 'craving_level': '0',
            'pledge_taken': 'on',
        })
        self.assertTrue(DailyPledge.objects.filter(user=self.user).exists())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressPledgeContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='c', password='x')
        self.client.force_login(self.user)

    def test_context_has_pledge_keys(self):
        resp = self.client.get(reverse('accounts:progress'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('pledge_streak', resp.context)
        self.assertEqual(resp.context['pledged_today'], False)

    def test_pledged_today_true_after_pledge(self):
        self.client.post(reverse('accounts:pledge_today'))
        resp = self.client.get(reverse('accounts:progress'))
        self.assertTrue(resp.context['pledged_today'])
        self.assertEqual(resp.context['pledge_streak'], 1)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PledgeCardRenderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='render', password='x')
        self.client.force_login(self.user)

    def test_pledge_card_renders_with_unfulfilled_state(self):
        resp = self.client.get(reverse('accounts:progress'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('I pledge to stay sober today', content)
        self.assertIn('id="pledgeTodayBtn"', content)

    def test_pledge_card_renders_fulfilled_state_after_pledging(self):
        self.client.post(reverse('accounts:pledge_today'))
        resp = self.client.get(reverse('accounts:progress'))
        content = resp.content.decode()
        self.assertIn('id="pledgeDone"', content)
        # The fulfilled marker must be visible (not carry the `hidden` attribute).
        match = re.search(r'<div class="pledge-done" id="pledgeDone"[^>]*>', content)
        self.assertIsNotNone(match, "pledgeDone div not found")
        self.assertNotIn('hidden', match.group(0))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class OnboardingPledgeCaptureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='o', password='x')
        self.client.force_login(self.user)

    def test_step3_saves_pledge_reason_and_completes(self):
        url = reverse('accounts:onboarding') + '?step=3'
        resp = self.client.post(url, {'pledge_reason': 'my daughter'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.pledge_reason, 'my daughter')
        self.assertTrue(self.user.has_completed_onboarding)
        self.assertRedirects(resp, reverse('accounts:progress'),
                             fetch_redirect_response=False)


class UserProfileFormPledgeTests(TestCase):
    def test_form_includes_pledge_fields(self):
        self.assertIn('pledge_reason', UserProfileForm.Meta.fields)
        self.assertIn('pledge_photo', UserProfileForm.Meta.fields)
