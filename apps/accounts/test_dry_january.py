"""Dry January: public landing page, join, and the progress-home card."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.accounts.dry_january import card_state, signup_year
from apps.accounts.models import DailyPledge, DryJanuaryEntry

User = get_user_model()


class DateLogicTests(SimpleTestCase):

    def test_signup_year(self):
        self.assertEqual(signup_year(date(2026, 11, 10)), 2027)
        self.assertEqual(signup_year(date(2027, 1, 15)), 2027)
        self.assertEqual(signup_year(date(2027, 2, 1)), 2028)

    def test_upcoming_counts_down_to_january_1(self):
        self.assertEqual(card_state({2027}, date(2026, 12, 30)),
                         {'phase': 'upcoming', 'year': 2027, 'days_until': 2})

    def test_active_day_is_the_day_of_january(self):
        self.assertEqual(card_state({2027}, date(2027, 1, 9)),
                         {'phase': 'active', 'year': 2027, 'day': 9})

    def test_finished_in_february_then_gone(self):
        self.assertEqual(card_state({2027}, date(2027, 2, 3))['phase'], 'finished')
        self.assertIsNone(card_state({2027}, date(2027, 3, 1)))

    def test_no_card_without_an_entry(self):
        self.assertIsNone(card_state(set(), date(2027, 1, 9)))
        self.assertIsNone(card_state({2026}, date(2027, 1, 9)))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LandingPageTests(TestCase):

    def test_anonymous_gets_signup_that_returns_here(self):
        resp = self.client.get(reverse('core:dry_january'))
        self.assertContains(resp, '"@type": "FAQPage"')
        self.assertContains(resp, reverse('accounts:register') + '?next=' + reverse('core:dry_january'))
        self.assertContains(resp, 'talk to a doctor before you stop')

    def test_in_the_sitemap(self):
        self.assertIn('/dry-january/', self.client.get('/sitemap.xml').content.decode())

    def test_member_joins_once_and_sees_confirmation(self):
        user = User.objects.create_user('dj', 'dj@example.com', 'pw')
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('core:dry_january')), 'data-dj-cta="join"')
        for _ in range(2):
            resp = self.client.post(reverse('accounts:dry_january_join'))
            self.assertRedirects(resp, reverse('accounts:progress'), fetch_redirect_response=False)
        self.assertEqual(DryJanuaryEntry.objects.filter(user=user).count(), 1)
        self.assertContains(self.client.get(reverse('core:dry_january')), 'You&rsquo;re in for Dry January')

    def test_join_requires_login_and_post(self):
        self.assertEqual(self.client.post(reverse('accounts:dry_january_join')).status_code, 302)
        self.assertEqual(DryJanuaryEntry.objects.count(), 0)
        self.client.force_login(User.objects.create_user('g', 'g@example.com', 'pw'))
        self.assertEqual(self.client.get(reverse('accounts:dry_january_join')).status_code, 405)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressCardTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('card', 'card@example.com', 'pw')
        self.client.force_login(self.user)
        DryJanuaryEntry.objects.create(user=self.user, year=2027)

    def _progress(self, today):
        with patch('apps.accounts.dry_january.timezone.localdate', return_value=today):
            return self.client.get(reverse('accounts:progress'))

    def test_no_card_for_members_who_did_not_join(self):
        DryJanuaryEntry.objects.all().delete()
        self.assertNotContains(self._progress(date(2027, 1, 9)), 'id="dryJanuaryCard"')

    def test_countdown_before_january(self):
        self.assertContains(self._progress(date(2026, 12, 30)), 'Starts in 2 days')

    def test_day_counter_and_pledged_days_in_january(self):
        DailyPledge.objects.create(user=self.user, date=date(2027, 1, 1))
        DailyPledge.objects.create(user=self.user, date=date(2027, 1, 2))
        DailyPledge.objects.create(user=self.user, date=date(2026, 12, 31))
        resp = self._progress(date(2027, 1, 9))
        self.assertContains(resp, 'Day 9 of 31')
        self.assertContains(resp, 'pledged 2 days this month')

    def test_february_offers_the_31_day_medallion_and_premium(self):
        resp = self._progress(date(2027, 2, 2))
        self.assertContains(resp, 'milestone-badge/?days=31')
        self.assertContains(resp, '?from=dry_january')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CreatorDaysOverrideTests(TestCase):

    def test_explicit_days_wins_over_sobriety_date(self):
        """The Dry January link asks for a 31-day medallion whatever the member's date."""
        user = User.objects.create_user('m', 'm@example.com', 'pw')
        user.sobriety_date = date(2020, 1, 1)
        user.save()
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:milestone_badge_creator') + '?days=31')
        self.assertEqual(resp.context['days_sober'], 31)
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertGreater(resp.context['days_sober'], 31)
