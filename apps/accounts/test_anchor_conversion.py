from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import (
    User, DailyCheckIn, RecoveryCoachSession, CoachMessage,
)


def make_free_user(username):
    u = User.objects.create_user(username, f'{username}@t.co', 'pw')
    sub = u.subscription
    sub.tier = 'free'
    sub.status = 'expired'
    sub.trial_end = None
    sub.save()
    return u


def make_premium_user(username):
    u = User.objects.create_user(username, f'{username}@t.co', 'pw')
    sub = u.subscription
    sub.tier = 'premium'
    sub.status = 'active'
    sub.trial_end = None
    sub.save()
    return u


def make_checkin(user, mood, craving, challenge=''):
    return DailyCheckIn.objects.create(
        user=user, mood=mood, craving_level=craving,
        energy_level=3, challenge=challenge,
    )


class NeedsSupportTest(TestCase):
    def setUp(self):
        self.user = make_free_user('ns')

    def test_low_mood_needs_support(self):
        self.assertTrue(make_checkin(self.user, mood=2, craving=0).needs_support())

    def test_okay_mood_no_craving_does_not(self):
        self.assertFalse(make_checkin(self.user, mood=3, craving=2).needs_support())

    def test_high_craving_needs_support(self):
        self.assertTrue(make_checkin(self.user, mood=5, craving=3).needs_support())

    def test_calm_does_not(self):
        self.assertFalse(make_checkin(self.user, mood=5, craving=0).needs_support())


from apps.accounts.coach_service import (
    can_send_message, get_message_count_today,
)


def add_user_messages(user, n, trigger='manual'):
    session = RecoveryCoachSession.objects.create(
        user=user, trigger=trigger, title='t')
    for i in range(n):
        CoachMessage.objects.create(session=session, role='user', content=f'm{i}')
    return session


class GatingTest(TestCase):
    def test_free_user_allowed_under_3_then_blocked(self):
        user = make_free_user('g1')
        add_user_messages(user, 2)
        allowed, reason = can_send_message(user)
        self.assertTrue(allowed)
        add_user_messages(user, 1)  # now 3 routine today
        allowed, reason = can_send_message(user)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'upgrade_required')

    def test_checkin_support_session_is_exempt(self):
        user = make_free_user('g2')
        add_user_messages(user, 5)  # well over the routine limit
        crisis = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support', title='c')
        allowed, reason = can_send_message(user, crisis)
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_checkin_support_messages_not_counted(self):
        user = make_free_user('g3')
        add_user_messages(user, 3, trigger='checkin_support')
        self.assertEqual(get_message_count_today(user), 0)
        allowed, _ = can_send_message(user)  # routine still open
        self.assertTrue(allowed)

    def test_premium_allowed_until_20(self):
        user = make_premium_user('g4')
        add_user_messages(user, 19)
        self.assertTrue(can_send_message(user)[0])
        add_user_messages(user, 1)  # 20
        self.assertFalse(can_send_message(user)[0])


from apps.accounts.coach_service import generate_checkin_opener


class OpenerTest(TestCase):
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_uses_api_text_when_available(self):
        user = make_free_user('o1')
        checkin = make_checkin(user, mood=1, craving=4, challenge='work stress')

        class FakeBlock:
            text = 'Hey, I can see today is really hard.'

        class FakeResp:
            content = [FakeBlock()]

        with patch('anthropic.Anthropic') as MockClient:
            MockClient.return_value.messages.create.return_value = FakeResp()
            text = generate_checkin_opener(user, checkin)
        self.assertEqual(text, 'Hey, I can see today is really hard.')

    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_falls_back_on_api_error(self):
        user = make_free_user('o2')
        checkin = make_checkin(user, mood=1, craving=4)
        with patch('anthropic.Anthropic', side_effect=Exception('boom')):
            text = generate_checkin_opener(user, checkin)
        self.assertIn("I'm here", text)

    @override_settings(ANTHROPIC_API_KEY='')
    def test_falls_back_with_no_api_key(self):
        user = make_free_user('o3')
        checkin = make_checkin(user, mood=2, craving=0)
        text = generate_checkin_opener(user, checkin)
        self.assertIn("I'm here", text)
