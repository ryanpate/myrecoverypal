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


class EmailTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('mail', 'mail@example.com', 'pw', first_name='Sam')
        self.user.timezone = 'America/New_York'
        self.user.save()
        self.entry = DryJanuaryEntry.objects.create(user=self.user, year=2027)

    def _run(self, y, mo, d, hour_utc):
        from datetime import datetime, timezone as dt_tz
        from apps.accounts.dry_january import send_emails
        with patch('apps.accounts.email_service.send_email', return_value=(True, None)) as send:
            sent = send_emails(now=datetime(y, mo, d, hour_utc, 20, tzinfo=dt_tz.utc))
        return sent, send

    def test_start_email_goes_out_dec_31_at_9am_local_once(self):
        # 13:20 UTC = 8:20 AM in New York: too early.
        self.assertEqual(self._run(2026, 12, 31, 13)[0], 0)
        sent, send = self._run(2026, 12, 31, 14)
        self.assertEqual(sent, 1)
        self.assertEqual(send.call_args.kwargs['subject'], 'Dry January starts tomorrow')
        self.assertIn('It starts tomorrow, Sam', send.call_args.kwargs['html_message'])
        self.assertEqual(self._run(2026, 12, 31, 15)[0], 0)

    def test_local_date_decides_not_utc(self):
        # 03:20 UTC on Jan 1 is still Dec 31 evening in New York.
        self.assertEqual(self._run(2027, 1, 1, 3)[0], 1)

    def test_midmonth_email_reports_pledged_days(self):
        DailyPledge.objects.create(user=self.user, date=date(2027, 1, 3))
        sent, send = self._run(2027, 1, 15, 15)
        self.assertEqual(sent, 1)
        self.assertEqual(send.call_args.kwargs['subject'], 'Halfway through Dry January')
        self.assertIn('pledged <strong>1 day</strong>', send.call_args.kwargs['html_message'])
        self.assertEqual(self._run(2027, 1, 16, 15)[0], 0)

    def test_nothing_on_other_days_or_for_other_years(self):
        self.assertEqual(self._run(2026, 12, 30, 15)[0], 0)
        self.assertEqual(self._run(2027, 1, 14, 15)[0], 0)
        self.assertEqual(self._run(2027, 12, 31, 15)[0], 0)

    def test_respects_email_opt_out_and_retries_after_failure(self):
        from datetime import datetime, timezone as dt_tz
        from apps.accounts.dry_january import send_emails
        now = datetime(2026, 12, 31, 15, 20, tzinfo=dt_tz.utc)
        with patch('apps.accounts.email_service.send_email', return_value=(False, 'down')):
            self.assertEqual(send_emails(now=now), 0)
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.start_email_sent)
        self.user.email_notifications = False
        self.user.save()
        self.assertEqual(self._run(2026, 12, 31, 16)[0], 0)
