import importlib
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.payment_models import Subscription


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


class ResetTrialsMigrationTest(TestCase):
    def _run_reset(self):
        # The data migration's forward function uses apps.get_model, which works
        # with the real app registry too, so we can call it directly.
        from django.apps import apps as global_apps
        mod = importlib.import_module('apps.accounts.migrations.0047_reset_trials')
        mod.reset_trials(global_apps, None)

    def test_resets_trialing_subs_to_14_days_out(self):
        user = make_user('stale')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(days=90)
        sub.save()

        self._run_reset()

        sub.refresh_from_db()
        remaining = sub.trial_end - timezone.now()
        self.assertGreater(remaining, timedelta(days=13))
        self.assertLessEqual(remaining, timedelta(days=14))

    def test_leaves_paid_active_subs_untouched(self):
        user = make_user('payer')
        sub = user.subscription
        sub.status = 'active'
        sub.trial_end = None
        sub.save()

        self._run_reset()

        sub.refresh_from_db()
        self.assertIsNone(sub.trial_end)
        self.assertEqual(sub.status, 'active')
