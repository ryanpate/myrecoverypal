"""Tests for premium ongoing-value features (July 2026):
- weekly digest premium recap section
- coach memory: deeper history window + cross-session continuity for premium
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts import coach_service
from apps.accounts.models import CoachMessage, DailyCheckIn, RecoveryCoachSession
from apps.accounts.tasks import _build_premium_recap, send_weekly_digests

User = get_user_model()


def make_user(username, tier='free'):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='pw')
    user.subscription.tier = tier
    user.subscription.status = 'active' if tier != 'free' else 'active'
    user.subscription.save()
    return user


def add_checkins(user, days, mood=4, craving=1):
    today = timezone.now().date()
    for d in days:
        DailyCheckIn.objects.create(
            user=user, date=today - timedelta(days=d),
            mood=mood, craving_level=craving, energy_level=3,
        )


class PremiumRecapTests(TestCase):
    def test_free_user_gets_no_recap(self):
        user = make_user('freebie', tier='free')
        add_checkins(user, [1, 2, 3])
        self.assertIsNone(_build_premium_recap(user, timezone.now().date()))

    def test_premium_user_recap_stats(self):
        user = make_user('premmy', tier='premium')
        user.sobriety_date = timezone.now().date() - timedelta(days=25)
        user.save()
        add_checkins(user, [1, 2, 3], mood=5, craving=0)   # this week
        add_checkins(user, [8, 9], mood=3, craving=2)      # last week

        recap = _build_premium_recap(user, timezone.now().date())
        self.assertIsNotNone(recap)
        self.assertEqual(recap['checkin_count'], 3)
        self.assertEqual(recap['avg_mood'], 5.0)
        self.assertEqual(recap['mood_trend'], 'improving')
        self.assertEqual(recap['craving_trend'], 'improving')
        self.assertEqual(recap['days_sober'], 25)
        self.assertEqual(recap['next_milestone'], 30)
        self.assertEqual(recap['days_to_milestone'], 5)

    def test_court_tier_counts_as_premium(self):
        user = make_user('courtly', tier='court')
        add_checkins(user, [1])
        self.assertIsNotNone(_build_premium_recap(user, timezone.now().date()))

    @override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_digest_sent_to_premium_user_with_only_personal_activity(self, mock_send):
        """A premium user with check-ins but zero social activity must still
        get the digest (the recap IS the content); the email must contain
        the recap section."""
        user = make_user('quietprem', tier='premium')
        user.sobriety_date = timezone.now().date() - timedelta(days=10)
        user.save()
        add_checkins(user, [1, 2])

        sent = send_weekly_digests.si().apply().result if hasattr(
            send_weekly_digests, 'si') else send_weekly_digests()
        self.assertGreaterEqual(sent, 1)
        html = mock_send.call_args.kwargs['html_message']
        self.assertIn('Your Week in Review', html)
        self.assertIn('check-ins this week', html)

    @override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_free_user_with_no_activity_skipped(self, mock_send):
        make_user('quietfree', tier='free')
        send_weekly_digests.si().apply() if hasattr(
            send_weekly_digests, 'si') else send_weekly_digests()
        for call in mock_send.call_args_list:
            self.assertNotIn('quietfree@example.com',
                             call.kwargs.get('recipient_email', ''))


def _mock_anthropic(MockClient):
    """Configure the mocked Anthropic client to return a canned response and
    return the mock create() for call inspection."""
    create = MockClient.return_value.messages.create
    create.return_value = MagicMock(content=[MagicMock(text='I hear you.')])
    return create


@override_settings(ANTHROPIC_API_KEY='test-key-not-real')
class CoachMemoryTests(TestCase):
    def _session_with_messages(self, user, n, session=None):
        session = session or RecoveryCoachSession.objects.create(user=user)
        for i in range(n):
            CoachMessage.objects.create(
                session=session, role='user' if i % 2 == 0 else 'assistant',
                content=f'message {i}')
        return session

    def test_premium_gets_deeper_history_window(self):
        user = make_user('premchat', tier='premium')
        session = self._session_with_messages(user, 15)
        with patch('anthropic.Anthropic') as MockClient:
            create = _mock_anthropic(MockClient)
            coach_service.send_coach_message(user, session, 'hello')
        sent_messages = create.call_args.kwargs['messages']
        # All 15 stored + the new one (free tier would cap at 10 + 1)
        self.assertEqual(len(sent_messages), 16)

    def test_free_history_window_stays_at_10(self):
        user = make_user('freechat', tier='free')
        session = self._session_with_messages(user, 15)
        with patch('anthropic.Anthropic') as MockClient:
            create = _mock_anthropic(MockClient)
            coach_service.send_coach_message(user, session, 'hello')
        self.assertEqual(len(create.call_args.kwargs['messages']), 11)

    def test_premium_new_session_carries_previous_context(self):
        user = make_user('contprem', tier='premium')
        old = self._session_with_messages(user, 4)
        CoachMessage.objects.filter(session=old).update(
            content='I was struggling with sleep')
        new_session = RecoveryCoachSession.objects.create(user=user)
        with patch('anthropic.Anthropic') as MockClient:
            create = _mock_anthropic(MockClient)
            coach_service.send_coach_message(user, new_session, 'hi again')
        system = create.call_args.kwargs['system']
        self.assertIn('CONTINUITY', system)
        self.assertIn('struggling with sleep', system)

    def test_free_new_session_has_no_continuity_block(self):
        user = make_user('contfree', tier='free')
        self._session_with_messages(user, 4)
        new_session = RecoveryCoachSession.objects.create(user=user)
        with patch('anthropic.Anthropic') as MockClient:
            create = _mock_anthropic(MockClient)
            coach_service.send_coach_message(user, new_session, 'hi again')
        self.assertNotIn('CONTINUITY', create.call_args.kwargs['system'])

    def test_premium_first_ever_session_no_continuity_crash(self):
        user = make_user('firstprem', tier='premium')
        session = RecoveryCoachSession.objects.create(user=user)
        with patch('anthropic.Anthropic') as MockClient:
            create = _mock_anthropic(MockClient)
            text, err = coach_service.send_coach_message(user, session, 'hello')
        self.assertIsNone(err)
        self.assertNotIn('CONTINUITY', create.call_args.kwargs['system'])
