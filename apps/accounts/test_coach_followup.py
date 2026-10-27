"""Anchor's next-day follow-up after a hard check-in (2026-10-26).

The morning after a check-in where needs_support() is true, Anchor opens a
'followup' session with a message, an in-app notification and a push, at
10 AM in the member's own time zone. Free for everyone, never rate-limited.
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.coach_service import can_send_message
from apps.accounts.models import (
    CoachMessage, DailyCheckIn, Notification, RecoveryCoachSession,
)
from apps.accounts.tasks import send_coach_followups

User = get_user_model()
OCT_26 = date(2026, 10, 26)


def _member(name, tz='America/Chicago'):
    user = User.objects.create_user(name, f'{name}@example.com', 'pw')
    user.timezone = tz
    user.save()
    return user


def _checkin(user, day, mood=4, craving=0):
    return DailyCheckIn.objects.create(
        user=user, date=day, mood=mood, craving_level=craving, energy_level=3)


def _at(utc_hour, day=date(2026, 10, 27)):
    return datetime(day.year, day.month, day.day, utc_hour, 0, tzinfo=dt_timezone.utc)


@patch('apps.accounts.push_notifications.PushNotificationService._send_push')
@patch('apps.accounts.coach_service.generate_followup_message',
       return_value='Thinking of you after yesterday. How are you today?')
class SendCoachFollowupsTests(TestCase):
    def _run(self, when):
        with patch('django.utils.timezone.now', return_value=when):
            send_coach_followups.apply()

    def test_hard_checkin_gets_a_followup_at_10am_local(self, gen, push):
        user = _member('hard')
        checkin = _checkin(user, OCT_26, mood=1)
        self._run(_at(14))  # 9 AM CDT: too early
        self.assertFalse(RecoveryCoachSession.objects.filter(trigger='followup').exists())
        self._run(_at(15))  # 10 AM CDT
        session = RecoveryCoachSession.objects.get(user=user, trigger='followup')
        self.assertEqual(session.triggering_checkin, checkin)
        self.assertFalse(session.is_active)
        self.assertEqual(CoachMessage.objects.get(session=session).role, 'assistant')
        note = Notification.objects.get(recipient=user, notification_type='coach_followup')
        self.assertEqual(note.link, f'/accounts/recovery-coach/session/{session.id}/')
        push.assert_called_once()

    def test_high_craving_counts_as_hard(self, gen, push):
        user = _member('craving')
        _checkin(user, OCT_26, mood=4, craving=3)
        self._run(_at(15))
        self.assertTrue(RecoveryCoachSession.objects.filter(user=user, trigger='followup').exists())

    def test_ok_checkin_gets_nothing(self, gen, push):
        user = _member('fine')
        _checkin(user, OCT_26, mood=4, craving=1)
        self._run(_at(15))
        self.assertFalse(RecoveryCoachSession.objects.filter(trigger='followup').exists())
        push.assert_not_called()

    def test_only_once_per_checkin(self, gen, push):
        user = _member('once')
        _checkin(user, OCT_26, mood=2)
        self._run(_at(15))
        self._run(_at(15))
        self.assertEqual(RecoveryCoachSession.objects.filter(user=user, trigger='followup').count(), 1)

    def test_follows_the_members_own_time_zone(self, gen, push):
        tokyo = _member('tyo', tz='Asia/Tokyo')
        _checkin(tokyo, OCT_26, mood=1)
        self._run(_at(1))  # 10 AM JST on Oct 27
        self.assertTrue(RecoveryCoachSession.objects.filter(user=tokyo, trigger='followup').exists())

    def test_only_the_morning_after(self, gen, push):
        user = _member('old')
        _checkin(user, OCT_26 - timedelta(days=1), mood=1)  # two days ago
        self._run(_at(15))
        self.assertFalse(RecoveryCoachSession.objects.filter(trigger='followup').exists())


class FollowupSessionLimitTests(TestCase):
    def test_free_member_can_always_reply_to_a_followup(self):
        user = _member('free')
        routine = RecoveryCoachSession.objects.create(user=user)
        for _ in range(3):
            CoachMessage.objects.create(session=routine, role='user', content='hi')
        self.assertFalse(can_send_message(user, routine)[0])
        followup = RecoveryCoachSession.objects.create(user=user, trigger='followup')
        self.assertTrue(can_send_message(user, followup)[0])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressFollowupCardTests(TestCase):
    def _followup(self, user, text='How are you doing today?'):
        session = RecoveryCoachSession.objects.create(
            user=user, trigger='followup', is_active=False)
        CoachMessage.objects.create(session=session, role='assistant', content=text)
        return session

    def test_unanswered_followup_shows_on_progress_home(self):
        user = _member('card')
        session = self._followup(user, 'I was thinking about yesterday.')
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'Anchor checked in on you')
        self.assertContains(resp, 'I was thinking about yesterday.')
        self.assertContains(resp, reverse('accounts:coach_load_session', args=[session.id]))

    def test_card_disappears_once_they_reply(self):
        user = _member('replied')
        session = self._followup(user)
        CoachMessage.objects.create(session=session, role='user', content='Better, thanks')
        self.client.force_login(user)
        self.assertNotContains(self.client.get(reverse('accounts:progress')),
                               'Anchor checked in on you')
