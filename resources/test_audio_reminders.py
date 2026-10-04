"""Opt-in guided audio reminders and the evening card on the progress home."""
import shutil
import tempfile
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import DeviceToken
from resources.models import AudioReminder, AudioTrack
from resources.tasks import send_audio_reminders
from resources.test_audio import make_track
from resources.test_premium_gating import make_free

User = get_user_model()
OK = {'android': {'sent': 0, 'failed': 0}, 'ios': {'sent': 1, 'failed': 0}, 'web': {'sent': 0, 'failed': 0}}
NONE = {'android': {'sent': 0, 'failed': 0}, 'ios': {'sent': 0, 'failed': 1}, 'web': {'sent': 0, 'failed': 0}}
PUSH = 'apps.accounts.push_notifications.send_push_to_user'


class MediaMixin:
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        super().setUp()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)


def member(name, tz='America/New_York', device=True, **fields):
    u = User.objects.create_user(name, f'{name}@example.com', 'pw12345!')
    User.objects.filter(pk=u.pk).update(timezone=tz, **fields)
    u.refresh_from_db()
    make_free(u)
    if device:
        DeviceToken.objects.create(user=u, token=f'tok-{name}', platform='ios')
    return u


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReminderViewTests(MediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        make_track('evening-check-out', category='sleep')
        make_track('urge-surfing', free=True, category='cravings')
        self.user = member('rv', device=False)
        self.client.force_login(self.user)

    def test_card_on_remindable_session_only(self):
        resp = self.client.get(reverse('resources:audio_detail', args=['evening-check-out']))
        self.assertContains(resp, 'Make it a habit')
        self.assertContains(resp, '<option value="21" selected>9 PM</option>', html=True)
        self.assertContains(resp, 'Get the app')  # no device yet
        resp = self.client.get(reverse('resources:audio_detail', args=['urge-surfing']))
        self.assertNotContains(resp, 'Make it a habit')

    def test_turn_on_change_and_off(self):
        url = reverse('resources:audio_reminder', args=['evening-check-out'])
        resp = self.client.post(url, {'hour': '20'}, follow=True)
        self.assertContains(resp, 'every day at 8 PM')
        r = AudioReminder.objects.get(user=self.user, track_slug='evening-check-out')
        self.assertEqual((r.hour, r.enabled), (20, True))
        self.client.post(url, {'hour': '99'})  # invalid -> default
        r.refresh_from_db()
        self.assertEqual(r.hour, 21)
        self.client.post(url, {'action': 'off'})
        r.refresh_from_db()
        self.assertFalse(r.enabled)

    def test_not_for_other_sessions_and_needs_login(self):
        self.assertEqual(self.client.post(reverse('resources:audio_reminder', args=['urge-surfing'])).status_code, 404)
        self.client.logout()
        resp = self.client.post(reverse('resources:audio_reminder', args=['evening-check-out']))
        self.assertIn(reverse('accounts:login'), resp['Location'])


class ReminderTaskTests(MediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        make_track('evening-check-out', category='sleep')
        self.ny = member('ny')
        AudioReminder.objects.create(user=self.ny, track_slug='evening-check-out', hour=21)

    def at(self, utc_hour, day=4):
        return datetime(2026, 10, day, utc_hour, 0, tzinfo=ZoneInfo('UTC'))

    def test_sends_at_local_hour_once_a_day(self):
        with patch(PUSH, return_value=OK) as push:
            send_audio_reminders(now=self.at(0, day=5))   # 20:00 New York: not yet
            push.assert_not_called()
            send_audio_reminders(now=self.at(1, day=5))   # 21:00 New York
            self.assertEqual(push.call_count, 1)
            user, title, body, data = push.call_args.args
            self.assertIn('evening check-out', body)
            self.assertTrue(data['url'].startswith('/resources/audio/evening-check-out/'))
            send_audio_reminders(now=self.at(1, day=5))   # same local day again
            self.assertEqual(push.call_count, 1)

    def test_respects_time_zone(self):
        tokyo = member('tokyo', tz='Asia/Tokyo')
        AudioReminder.objects.create(user=tokyo, track_slug='evening-check-out', hour=21)
        with patch(PUSH, return_value=OK) as push:
            send_audio_reminders(now=self.at(12))  # 21:00 Tokyo, 08:00 New York
        self.assertEqual([c.args[0] for c in push.call_args_list], [tokyo])

    def test_skips_disabled_no_app_and_muted(self):
        AudioReminder.objects.filter(user=self.ny).update(enabled=False)
        AudioReminder.objects.create(user=member('noapp', device=False), track_slug='evening-check-out', hour=21)
        AudioReminder.objects.create(user=member('muted', email_notifications=False),
                                     track_slug='evening-check-out', hour=21)
        with patch(PUSH, return_value=OK) as push:
            send_audio_reminders(now=self.at(1, day=5))
        push.assert_not_called()

    def test_undelivered_not_marked_sent(self):
        with patch(PUSH, return_value=NONE):
            send_audio_reminders(now=self.at(1, day=5))
        self.assertIsNone(AudioReminder.objects.get(user=self.ny).last_sent_on)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EveningCardTests(MediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        make_track('evening-check-out', category='sleep')
        self.user = member('ev', device=False)
        self.client.force_login(self.user)

    def local_hour(self, h):
        from django.utils import timezone
        return patch('apps.accounts.views.timezone.localtime',
                     return_value=timezone.now().replace(hour=h, minute=0))

    def test_evening_session_after_six_only(self):
        from apps.accounts.views import _evening_session
        with self.local_hour(17):
            self.assertIsNone(_evening_session(self.user))
        with self.local_hour(19):
            s = _evening_session(self.user)
        self.assertEqual(s['track'].slug, 'evening-check-out')
        self.assertFalse(s['has_reminder'])

    def test_card_on_progress_home(self):
        with patch('apps.accounts.views._evening_session',
                   return_value={'track': AudioTrack.objects.get(slug='evening-check-out'),
                                 'has_reminder': False}):
            resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'Close the day')
        self.assertContains(resp, 'Remind me every evening')
        self.assertContains(resp, reverse('resources:audio_detail', args=['evening-check-out']))
