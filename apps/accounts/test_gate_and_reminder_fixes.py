"""2026-10-26 fixes:

- The Premium analytics gate used tier == 'free', so a lapsed Premium/Court
  member (tier unchanged, status expired) kept Premium analytics.
- Check-in reminders ran once at 17:00 UTC with the UTC date. They now run
  hourly and reach each member at 5 PM in their own time zone, with "today"
  being the member's local date.
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import DailyCheckIn
from apps.accounts.tasks import send_checkin_reminders

User = get_user_model()


def _member(name, tier='free', status='active', tz=''):
    user = User.objects.create_user(name, f'{name}@example.com', 'pw')
    user.timezone = tz
    user.email_notifications = True
    user.save()
    user.subscription.tier = tier
    user.subscription.status = status
    user.subscription.save()
    return user


def _checkin(user, day):
    return DailyCheckIn.objects.create(user=user, date=day, mood=4, craving_level=0, energy_level=3)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class AnalyticsGateTests(TestCase):
    GATE = 'Unlock Your Full Analytics'

    def _progress(self, user):
        _checkin(user, date.today())  # the gate only renders once there's data
        self.client.force_login(user)
        return self.client.get(reverse('accounts:progress'))

    def test_lapsed_premium_member_sees_the_gate(self):
        self.assertContains(self._progress(_member('lapsed', 'premium', 'expired')), self.GATE)

    def test_lapsed_court_member_sees_the_gate(self):
        self.assertContains(self._progress(_member('lapsedcourt', 'court', 'canceled')), self.GATE)

    def test_active_premium_member_does_not(self):
        self.assertNotContains(self._progress(_member('active', 'premium')), self.GATE)

    def test_free_member_does(self):
        self.assertContains(self._progress(_member('free')), self.GATE)


def _at(utc_hour, day=date(2026, 10, 26)):
    return datetime(day.year, day.month, day.day, utc_hour, 0, tzinfo=dt_timezone.utc)


@patch('apps.accounts.tasks.time.sleep')
@patch('apps.accounts.push_notifications.PushNotificationService.notify_checkin_reminder')
@patch('apps.accounts.tasks.send_email', return_value=(True, None))
class LocalCheckinReminderTests(TestCase):
    def _run(self, when):
        with patch('django.utils.timezone.now', return_value=when):
            send_checkin_reminders.apply()

    def _sent_to(self, send):
        return {c.kwargs['recipient_email'] for c in send.call_args_list}

    def test_each_member_is_reminded_at_5pm_their_time(self, send, push, sleep):
        chicago = _member('chi', tz='America/Chicago')    # 5 PM CDT = 22:00 UTC
        tokyo = _member('tyo', tz='Asia/Tokyo')           # 5 PM JST = 08:00 UTC
        for u in (chicago, tokyo):
            _checkin(u, date(2026, 10, 20))
        self._run(_at(22))
        self.assertEqual(self._sent_to(send), {chicago.email})
        send.reset_mock()
        self._run(_at(8, date(2026, 10, 27)))
        self.assertEqual(self._sent_to(send), {tokyo.email})

    def test_members_without_a_zone_get_us_central(self, send, push, sleep):
        nozone = _member('nozone')
        _checkin(nozone, date(2026, 10, 20))
        self._run(_at(17))   # the old 17:00 UTC run: noon in Chicago, no reminder
        self.assertEqual(self._sent_to(send), set())
        self._run(_at(22))
        self.assertEqual(self._sent_to(send), {nozone.email})

    def test_already_checked_in_on_their_local_date_is_skipped(self, send, push, sleep):
        # 5 PM Oct 26 in Honolulu is 03:00 UTC on Oct 27. The old UTC-date
        # check saw no check-in "today" (Oct 27) and reminded someone who had
        # already checked in on their Oct 26.
        honolulu = _member('hnl', tz='Pacific/Honolulu')
        _checkin(honolulu, date(2026, 10, 26))
        self._run(_at(3, date(2026, 10, 27)))
        self.assertEqual(self._sent_to(send), set())

    def test_reminded_once_per_day(self, send, push, sleep):
        member = _member('once', tz='America/Chicago')
        _checkin(member, date(2026, 10, 20))
        self._run(_at(22))
        self._run(_at(22))  # rerun in the same hour
        self.assertEqual(send.call_count, 1)
