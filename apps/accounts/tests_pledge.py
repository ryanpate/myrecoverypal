from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import DailyPledge

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
