from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import DailyCheckIn

User = get_user_model()


class PledgeStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ren', password='x')

    def _pledge_on(self, d):
        DailyCheckIn.objects.create(user=self.user, date=d, mood=4, energy_level=3,
                                    pledge_taken=True, pledge_time=timezone.now())

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
        self._pledge_on(today - timedelta(days=2))  # gap at day-1
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_checkin_without_pledge_does_not_count(self):
        DailyCheckIn.objects.create(user=self.user, date=timezone.now().date(),
                                    mood=4, energy_level=3, pledge_taken=False)
        self.assertEqual(self.user.get_pledge_streak(), 0)

    def test_yesterday_only_still_active(self):
        self._pledge_on(timezone.now().date() - timedelta(days=1))
        self.assertEqual(self.user.get_pledge_streak(), 1)
