"""Premium streak protection (2026-10-26).

About half of all broken pledge/check-in streaks in prod were one missed day.
Premium bridges a single missed day, at most once per 7 days; free members see
the streak it would have saved at the moment they lose it.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyPledge, streak_from_dates

User = get_user_model()
TODAY = date(2026, 10, 26)


def days(*offsets):
    return {TODAY - timedelta(days=o) for o in offsets}


class StreakFromDatesTests(TestCase):
    def test_unprotected_counts_unbroken_run_from_today_or_yesterday(self):
        self.assertEqual(streak_from_dates(days(0, 1, 2), TODAY), 3)
        self.assertEqual(streak_from_dates(days(1, 2), TODAY), 2)
        self.assertEqual(streak_from_dates(days(2, 3), TODAY), 0)
        self.assertEqual(streak_from_dates(days(0, 2, 3), TODAY), 1)

    def test_protection_bridges_one_missed_day(self):
        # Missed day 1: protected streak counts it and continues.
        self.assertEqual(streak_from_dates(days(0, 2, 3), TODAY, protect=True), 4)

    def test_missed_yesterday_is_bridged_while_today_can_still_be_logged(self):
        self.assertEqual(streak_from_dates(days(2, 3, 4), TODAY, protect=True), 4)

    def test_two_missed_days_in_a_row_still_end_it(self):
        self.assertEqual(streak_from_dates(days(0, 3, 4), TODAY, protect=True), 1)
        self.assertEqual(streak_from_dates(days(3, 4), TODAY, protect=True), 0)

    def test_only_one_bridge_per_seven_days(self):
        # Gaps at day 2 and day 5 (3 days apart): only the first is bridged.
        self.assertEqual(streak_from_dates(days(0, 1, 3, 4, 6, 7), TODAY, protect=True), 5)
        # Gaps at day 2 and day 9 (7 days apart): both bridged.
        dates = days(0, 1, *range(3, 9), *range(10, 13))
        self.assertEqual(streak_from_dates(dates, TODAY, protect=True), 13)


def _user(name, tier='free'):
    user = User.objects.create_user(name, f'{name}@example.com', 'pw')
    user.subscription.tier = tier
    user.subscription.status = 'active'
    user.subscription.save()
    return user


def _pledges(user, *offsets):
    today = timezone.localdate()
    for o in offsets:
        DailyPledge.objects.create(user=user, date=today - timedelta(days=o))


class MemberStreakTests(TestCase):
    def test_premium_streak_is_protected_free_is_not(self):
        free, prem = _user('free'), _user('prem', tier='premium')
        for u in (free, prem):
            _pledges(u, 0, 2, 3, 4)
        self.assertEqual(free.get_pledge_streak(), 1)
        self.assertEqual(prem.get_pledge_streak(), 5)

    def test_free_member_sees_the_streak_premium_would_have_saved(self):
        free = _user('lost')
        _pledges(free, 2, 3, 4, 5, 6)  # 5-day streak, missed yesterday
        self.assertEqual(free.streak_premium_would_save(), 6)
        _pledges(free, 0)  # restarted today: still a fresh loss
        self.assertEqual(free.streak_premium_would_save(), 7)

    def test_no_moment_for_short_streaks_old_breaks_or_premium(self):
        short = _user('short')
        _pledges(short, 2)
        self.assertEqual(short.streak_premium_would_save(), 0)
        old = _user('old')
        _pledges(old, 0, 1, 2, 3, 5, 6, 7)  # break 4 days ago, 4-day streak running now
        self.assertEqual(old.streak_premium_would_save(), 0)
        prem = _user('p', tier='premium')
        _pledges(prem, 2, 3, 4, 5)
        self.assertEqual(prem.streak_premium_would_save(), 0)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressHomeStreakTests(TestCase):
    def test_free_member_gets_the_saved_streak_card(self):
        user = _user('card')
        _pledges(user, 2, 3, 4, 5)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'Your 5-day streak ended on one missed day.')
        self.assertContains(resp, f'{reverse("accounts:pricing")}?from=streak')

    def test_premium_member_sees_protection_worked(self):
        user = _user('shield', tier='premium')
        _pledges(user, 0, 2, 3)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'Premium streak protection covered a missed day')
        self.assertNotContains(resp, 'ended on one missed day')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PricingLeadsWithTheHabitTests(TestCase):
    def test_premium_card_leads_with_streak_protection(self):
        html = self.client.get(reverse('accounts:pricing')).content.decode()
        premium = html[html.index('Everything in Free, plus:'):]
        self.assertLess(premium.index('Streak protection'), premium.index('Anchor, your AI recovery coach'))
        self.assertIn('mood, craving &amp; energy insights', premium)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PricingTopTests(TestCase):
    """The top of the pricing page sells the daily habit, not a therapy comparison."""

    def test_no_therapy_comparison(self):
        html = self.client.get(reverse('accounts:pricing')).content.decode()
        self.assertNotIn('therapy session', html)
        self.assertIn('Miss a day, keep your streak', html)

    def test_free_member_with_a_streak_gets_a_personal_heading(self):
        user = _user('streaky')
        _pledges(user, 0, 1, 2, 3)
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('accounts:pricing')),
                            'Your 4-day streak deserves a safety net')

    def test_premium_member_gets_the_general_heading(self):
        user = _user('premtop', tier='premium')
        _pledges(user, 0, 1, 2, 3)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:pricing'))
        self.assertNotContains(resp, 'deserves a safety net')
        self.assertContains(resp, 'Premium is built around the two minutes')
