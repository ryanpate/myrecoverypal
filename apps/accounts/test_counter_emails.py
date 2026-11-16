"""Milestone emails for calculator visitors with no account."""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts import counter_emails
from apps.accounts.counter_emails import milestone_for, request_emails, send_due
from apps.accounts.models import CounterEmail

User = get_user_model()
SEND = 'apps.accounts.counter_emails.send_email'


class MilestoneTests(SimpleTestCase):
    def test_day_milestones(self):
        start = date(2026, 1, 1)
        self.assertEqual(milestone_for(start, start + timedelta(days=7)), (7, '7 days'))
        self.assertEqual(milestone_for(start, start + timedelta(days=90)), (90, '90 days'))
        self.assertEqual(milestone_for(start, start + timedelta(days=180)), (180, '6 months'))
        self.assertEqual(milestone_for(start, start + timedelta(days=365)), (365, '1 year'))
        self.assertIsNone(milestone_for(start, start + timedelta(days=8)))
        self.assertIsNone(milestone_for(start, start))

    def test_later_years_are_calendar_anniversaries(self):
        self.assertEqual(milestone_for(date(2020, 3, 10), date(2026, 3, 10))[1], '6 years')
        self.assertIsNone(milestone_for(date(2020, 3, 10), date(2026, 3, 11)))
        # February 29 start: celebrated on the 28th in other years.
        self.assertEqual(milestone_for(date(2020, 2, 29), date(2026, 2, 28))[1], '6 years')


def _confirmed(email='a@example.com', start=date(2026, 1, 1), **extra):
    return CounterEmail.objects.create(
        email=email, start_date=start, confirmed_at=timezone.now(),
        timezone='America/Chicago', **extra)


def _at(day, hour_utc):
    return datetime(day.year, day.month, day.day, hour_utc, tzinfo=dt_timezone.utc)


class SendDueTests(TestCase):
    DAY_30 = date(2026, 1, 31)

    def test_sends_once_on_the_milestone_day_from_9am_local(self):
        row = _confirmed()
        with patch(SEND, return_value=(True, None)) as send:
            self.assertEqual(send_due(_at(self.DAY_30, 14)), 0)   # 8 AM Central
            self.assertEqual(send_due(_at(self.DAY_30, 15)), 1)   # 9 AM Central
            self.assertEqual(send_due(_at(self.DAY_30, 16)), 0)   # already sent
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['subject'], '30 days sober today')
        self.assertEqual(kwargs['recipient_email'], 'a@example.com')
        self.assertIn('sobriety-medallion-maker/?days=30', kwargs['html_message'])
        self.assertIn('register/?sobriety_date=2026-01-01', kwargs['html_message'])
        self.assertIn(f'/counter-email/{row.token}/stop/', kwargs['html_message'])
        row.refresh_from_db()
        self.assertEqual(row.last_sent_days, 30)

    def test_clean_wording(self):
        _confirmed(kind='clean')
        with patch(SEND, return_value=(True, None)) as send:
            send_due(_at(self.DAY_30, 18))
        self.assertEqual(send.call_args.kwargs['subject'], '30 days clean today')

    def test_nothing_on_ordinary_days_or_before_confirmation(self):
        _confirmed()
        CounterEmail.objects.create(email='p@example.com', start_date=date(2026, 1, 1))
        with patch(SEND, return_value=(True, None)) as send:
            self.assertEqual(send_due(_at(date(2026, 1, 20), 18)), 0)
            self.assertEqual(send_due(_at(self.DAY_30, 18)), 1)
        self.assertEqual(send.call_count, 1)

    def test_failed_send_is_retried_next_hour(self):
        _confirmed()
        with patch(SEND, return_value=(False, 'down')):
            self.assertEqual(send_due(_at(self.DAY_30, 18)), 0)
        with patch(SEND, return_value=(True, None)):
            self.assertEqual(send_due(_at(self.DAY_30, 19)), 1)

    def test_members_are_skipped(self):
        """Someone who went on to create an account has member milestone emails."""
        User.objects.create_user('m', 'A@example.com', 'pw-12345678')
        row = _confirmed()
        with patch(SEND, return_value=(True, None)) as send:
            self.assertEqual(send_due(_at(self.DAY_30, 18)), 0)
        send.assert_not_called()
        row.refresh_from_db()
        self.assertEqual(row.last_sent_days, 30)

    def test_old_unconfirmed_rows_are_purged(self):
        old = CounterEmail.objects.create(email='old@example.com', start_date=date(2026, 1, 1))
        CounterEmail.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=31))
        fresh = CounterEmail.objects.create(email='new@example.com', start_date=date(2026, 1, 1))
        kept = _confirmed()
        CounterEmail.objects.filter(pk=kept.pk).update(created_at=timezone.now() - timedelta(days=400))
        with patch(SEND, return_value=(True, None)):
            send_due()
        self.assertEqual(set(CounterEmail.objects.values_list('pk', flat=True)), {fresh.pk, kept.pk})


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SignupFlowTests(TestCase):
    def setUp(self):
        for cache in caches.all():
            cache.clear()
        self.url = reverse('accounts:counter_email_signup')
        self.start = (timezone.localdate() - timedelta(days=12)).isoformat()

    def _post(self, **data):
        fields = {'email': 'New@Example.com', 'start_date': self.start, 'kind': 'clean',
                  'timezone': 'America/Denver'}
        fields.update(data)
        return self.client.post(self.url, fields, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_signup_sends_a_confirmation_and_nothing_else(self):
        with patch(SEND, return_value=(True, None)) as send:
            resp = self._post()
        self.assertEqual(resp.json(), {'ok': True, 'message': counter_emails.SIGNUP_MESSAGE})
        row = CounterEmail.objects.get()
        self.assertEqual((row.email, row.kind, row.timezone, row.confirmed_at),
                         ('new@example.com', 'clean', 'America/Denver', None))
        self.assertEqual(send.call_args.kwargs['subject'], 'Confirm your milestone emails')
        self.assertIn(f'/counter-email/{row.token}/confirm/', send.call_args.kwargs['plain_message'])

    def test_confirm_then_stop_deletes_the_row(self):
        with patch(SEND, return_value=(True, None)):
            self._post()
        row = CounterEmail.objects.get()
        resp = self.client.get(reverse('accounts:counter_email_confirm', args=[row.token]))
        self.assertRedirects(resp, reverse('core:clean_time_calculator'), fetch_redirect_response=False)
        row.refresh_from_db()
        self.assertIsNotNone(row.confirmed_at)

        stop = reverse('accounts:counter_email_stop', args=[row.token])
        self.assertContains(self.client.get(stop), 'Stop your milestone emails?')
        self.assertTrue(CounterEmail.objects.exists())   # GET alone never deletes
        self.assertContains(self.client.post(stop), "deleted your email and date")
        self.assertFalse(CounterEmail.objects.exists())

    def test_repeat_signups_do_not_flood_the_inbox(self):
        with patch(SEND, return_value=(True, None)) as send:
            self._post()
            self._post()
        self.assertEqual(send.call_count, 1)
        self.assertEqual(CounterEmail.objects.count(), 1)

    def test_changing_the_date_needs_a_new_confirmation(self):
        with patch(SEND, return_value=(True, None)) as send:
            self.assertTrue(request_emails('a@example.com', date(2026, 1, 1), 'sober', ''))
            row = CounterEmail.objects.get()
            CounterEmail.objects.filter(pk=row.pk).update(confirmed_at=timezone.now(), last_sent_days=30)
            request_emails('a@example.com', date(2026, 1, 1), 'sober', '')   # same: nothing sent
            self.assertEqual(send.call_count, 1)
            request_emails('a@example.com', date(2026, 3, 1), 'sober', '')
        self.assertEqual(send.call_count, 2)
        row.refresh_from_db()
        self.assertEqual((row.start_date, row.confirmed_at, row.last_sent_days), (date(2026, 3, 1), None, None))

    def test_failed_confirmation_is_reported_and_can_be_retried_at_once(self):
        with patch(SEND, return_value=(False, 'down')):
            resp = self._post()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("couldn't send", resp.json()['message'])
        with patch(SEND, return_value=(True, None)) as send:
            self.assertTrue(self._post().json()['ok'])
        self.assertEqual(send.call_count, 1)

    def test_bad_input_is_rejected(self):
        with patch(SEND, return_value=(True, None)) as send:
            self.assertEqual(self._post(email='nope').status_code, 400)
            self.assertEqual(self._post(start_date='').status_code, 400)
            future = (timezone.localdate() + timedelta(days=30)).isoformat()
            self.assertEqual(self._post(start_date=future).status_code, 400)
            self.assertTrue(self._post(website='http://spam.example').json()['ok'])  # honeypot
        send.assert_not_called()
        self.assertFalse(CounterEmail.objects.exists())

    def test_form_post_without_javascript_redirects_back(self):
        with patch(SEND, return_value=(True, None)):
            resp = self.client.post(self.url, {'email': 'x@example.com', 'start_date': self.start, 'kind': 'sober'})
        self.assertRedirects(resp, reverse('core:sobriety_calculator'), fetch_redirect_response=False)

    def test_bad_token_links_are_harmless(self):
        resp = self.client.get(reverse('accounts:counter_email_confirm', args=['nope']))
        self.assertEqual(resp.status_code, 302)
        self.assertContains(self.client.get(reverse('accounts:counter_email_stop', args=['nope'])),
                            "won't get any more milestone emails")


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CalculatorFormTests(TestCase):
    def test_anonymous_visitors_see_the_email_form_on_both_calculators(self):
        for page, kind in (('core:sobriety_calculator', 'sober'), ('core:clean_time_calculator', 'clean')):
            html = self.client.get(reverse(page)).content.decode()
            self.assertIn(f'action="{reverse("accounts:counter_email_signup")}"', html)
            self.assertIn(f'name="kind" value="{kind}"', html)
            self.assertIn('Email me my milestones', html)

    def test_members_do_not(self):
        self.client.force_login(User.objects.create_user('m', 'm@example.com', 'pw-12345678'))
        html = self.client.get(reverse('core:sobriety_calculator')).content.decode()
        self.assertNotIn('calc-email-form"', html)
