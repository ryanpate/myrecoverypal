from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User


def make_user(username):
    return User.objects.create_user(username, f'{username}@t.co', 'pw')


class IsActiveGateTest(TestCase):
    def test_trial_in_future_is_active_and_premium(self):
        user = make_user('future')
        sub = user.subscription  # premium / trialing / +14d
        sub.trial_end = timezone.now() + timedelta(days=5)
        sub.save()
        self.assertTrue(sub.is_active())
        self.assertTrue(sub.is_premium())

    def test_trial_in_past_is_not_active_or_premium(self):
        user = make_user('past')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(days=1)
        sub.save()
        self.assertFalse(sub.is_active())
        self.assertFalse(sub.is_premium())

    def test_trialing_with_no_trial_end_is_not_active(self):
        user = make_user('notrialend')
        sub = user.subscription
        sub.trial_end = None
        sub.save()
        self.assertFalse(sub.is_active())

    def test_paid_active_is_active(self):
        user = make_user('paid')
        sub = user.subscription
        sub.status = 'active'
        sub.trial_end = None
        sub.save()
        self.assertTrue(sub.is_active())
        self.assertTrue(sub.is_premium())
