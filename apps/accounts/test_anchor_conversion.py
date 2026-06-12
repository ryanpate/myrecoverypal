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
