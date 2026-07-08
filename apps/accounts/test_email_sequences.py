"""Tests for the onboarding + re-engagement email sequences."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import (
    User, DailyCheckIn, SocialPost, RecoveryCoachSession, CoachMessage,
)
from apps.journal.models import JournalEntry
from apps.accounts import email_sequences as seq


def make_user(username='pal', days_ago=0, **kwargs):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='x',
        **kwargs,
    )
    if days_ago:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=days_ago))
        user.refresh_from_db()
    return user


class EligibilityHelperTests(TestCase):
    def test_activation_requires_all_three_actions(self):
        user = make_user()
        self.assertFalse(seq.is_activated(user))
        DailyCheckIn.objects.create(user=user, mood=3, energy_level=3)
        JournalEntry.objects.create(user=user, content='one line')
        self.assertFalse(seq.is_activated(user))
        SocialPost.objects.create(author=user, content='hello')
        self.assertTrue(seq.is_activated(user))

    def test_has_used_anchor(self):
        user = make_user()
        self.assertFalse(seq.has_used_anchor(user))
        session = RecoveryCoachSession.objects.create(user=user)
        CoachMessage.objects.create(session=session, role='user', content='hi')
        self.assertTrue(seq.has_used_anchor(user))

    def test_crisis_suppression_window(self):
        user = make_user()
        self.assertFalse(seq.is_crisis_suppressed(user))
        session = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support')
        self.assertTrue(seq.is_crisis_suppressed(user))
        # Age the session past 48h
        RecoveryCoachSession.objects.filter(pk=session.pk).update(
            updated_at=timezone.now() - timedelta(hours=49))
        self.assertFalse(seq.is_crisis_suppressed(user))

    def test_get_last_activity_takes_most_recent_signal(self):
        user = make_user(days_ago=30)
        self.assertEqual(seq.get_last_activity(user), user.date_joined)
        user.last_seen = timezone.now() - timedelta(days=2)
        self.assertEqual(seq.get_last_activity(user), user.last_seen)

    def test_unsubscribe_url_contains_token_path(self):
        user = make_user()
        url = seq.marketing_unsubscribe_url(user)
        self.assertIn('/email/unsubscribe/', url)
        self.assertTrue(url.startswith('http'))
