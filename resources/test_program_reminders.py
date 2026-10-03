"""Tests for daily program lesson reminders."""
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Notification, RecoveryCoachSession
from resources.models import ProgramDayCompletion, ProgramEnrollment
from resources.programs import FREE_DAYS
from resources.tasks import remind_enrollment, send_program_reminders
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()
NY = ZoneInfo('America/New_York')


def at(day, hour, minute=10):
    """An aware datetime at local New York time."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=NY)


@patch('apps.accounts.push_notifications.send_push_to_user', return_value={})
@patch('apps.accounts.email_service.send_email', return_value=(True, None))
class RemindEnrollmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rem', email='rem@example.com', password='x', timezone='America/New_York')
        make_premium(self.user)
        self.enrollment = ProgramEnrollment.objects.create(user=self.user, program_slug='first-30-days')
        self.started = date(2026, 3, 1)
        ProgramEnrollment.objects.filter(pk=self.enrollment.pk).update(started_at=at(self.started, 8))
        self.enrollment.refresh_from_db()

    def complete(self, day, on):
        ProgramDayCompletion.objects.create(enrollment=self.enrollment, day=day, completed_on=on)

    def test_push_at_nine_local_only(self, send_email, push):
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 8)), set())
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 9)), {'push'})
        n = Notification.objects.get(recipient=self.user)
        self.assertEqual(n.notification_type, 'program_reminder')
        self.assertIn('Day 1', n.title)
        self.assertEqual(n.link, reverse('resources:program_day', args=['first-30-days', 1]))
        push.assert_called_once()
        send_email.assert_not_called()

    def test_once_per_local_day(self, send_email, push):
        remind_enrollment(self.enrollment, at(self.started, 9, 5))
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 9, 50)), set())
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started + timedelta(days=1), 9)), {'push'})

    def test_nothing_while_waiting_for_tomorrow(self, send_email, push):
        self.complete(1, self.started + timedelta(days=1))
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started + timedelta(days=1), 9)), set())
        # Next morning Day 2 is open.
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started + timedelta(days=2), 9)), {'push'})

    def test_email_after_two_days_then_every_three(self, send_email, push):
        day = lambda n: self.started + timedelta(days=n)  # noqa: E731
        self.assertEqual(remind_enrollment(self.enrollment, at(day(1), 9)), {'push'})
        self.assertEqual(remind_enrollment(self.enrollment, at(day(2), 9)), {'push', 'email'})
        self.assertEqual(remind_enrollment(self.enrollment, at(day(3), 9)), {'push'})
        self.assertEqual(remind_enrollment(self.enrollment, at(day(4), 9)), {'push'})
        self.assertEqual(remind_enrollment(self.enrollment, at(day(5), 9)), {'push', 'email'})
        self.assertEqual(send_email.call_count, 2)
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs['recipient_email'], 'rem@example.com')
        self.assertIn('Day 1 of First 30 Days', kwargs['subject'])
        self.assertIn('/email/unsubscribe/', kwargs['html_message'])

    def test_push_stops_after_a_week_and_all_stops_after_two(self, send_email, push):
        day = lambda n: self.started + timedelta(days=n)  # noqa: E731
        self.assertNotIn('push', remind_enrollment(self.enrollment, at(day(8), 9)))
        self.assertEqual(remind_enrollment(self.enrollment, at(day(20), 9)), set())

    def test_no_email_without_marketing_consent(self, send_email, push):
        self.user.marketing_emails_enabled = False
        self.user.save()
        self.enrollment.refresh_from_db()
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started + timedelta(days=2), 9)), {'push'})
        send_email.assert_not_called()

    def test_skipped_when_disabled_notifications_off_or_finished(self, send_email, push):
        self.enrollment.reminders_enabled = False
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 9)), set())
        self.enrollment.reminders_enabled = True
        self.user.email_notifications = False
        self.user.save()
        self.enrollment.refresh_from_db()
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 9)), set())

    def test_crisis_suppression(self, send_email, push):
        RecoveryCoachSession.objects.create(user=self.user, trigger='checkin_support')
        self.assertEqual(remind_enrollment(self.enrollment, at(self.started, 9)), set())

    def test_free_member_gets_one_premium_nudge(self, send_email, push):
        make_free(self.user)
        for d in range(1, FREE_DAYS + 1):
            self.complete(d, self.started + timedelta(days=d - 1))
        day = self.started + timedelta(days=FREE_DAYS + 1)
        self.enrollment.refresh_from_db()
        self.assertEqual(remind_enrollment(self.enrollment, at(day, 9)), {'premium'})
        self.enrollment.refresh_from_db()
        self.assertTrue(self.enrollment.premium_nudge_sent)
        self.assertEqual(remind_enrollment(self.enrollment, at(day + timedelta(days=1), 9)), set())
        self.assertEqual(Notification.objects.count(), 1)

    def test_fallback_timezone_for_members_without_one(self, send_email, push):
        self.user.timezone = ''
        self.user.save()
        self.enrollment.refresh_from_db()
        chicago = ZoneInfo('America/Chicago')
        nine_central = datetime(2026, 3, 1, 9, 10, tzinfo=chicago)
        self.assertEqual(remind_enrollment(self.enrollment, nine_central), {'push'})

    def test_task_runs_over_all_enrollments(self, send_email, push):
        with patch('resources.tasks.remind_enrollment', return_value={'push'}) as m:
            counts = send_program_reminders()
        self.assertEqual(counts['push'], 1)
        m.assert_called_once()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReminderToggleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tog', email='tog@example.com', password='x')
        self.client.force_login(self.user)

    def test_toggle(self):
        e = ProgramEnrollment.objects.create(user=self.user, program_slug='first-30-days')
        url = reverse('resources:program_reminders', args=['first-30-days'])
        resp = self.client.get(reverse('resources:program_detail', args=['first-30-days']))
        self.assertContains(resp, 'Daily reminders are on')
        self.client.post(url, {'enabled': '0'})
        e.refresh_from_db()
        self.assertFalse(e.reminders_enabled)
        resp = self.client.get(reverse('resources:program_detail', args=['first-30-days']))
        self.assertContains(resp, 'Daily reminders are off')
        self.client.post(url, {'enabled': '1'})
        e.refresh_from_db()
        self.assertTrue(e.reminders_enabled)

    def test_toggle_requires_enrollment(self):
        resp = self.client.post(reverse('resources:program_reminders', args=['first-30-days']), {'enabled': '0'})
        self.assertEqual(resp.status_code, 404)

    def test_restart_keeps_reminder_choice(self):
        ProgramEnrollment.objects.create(user=self.user, program_slug='first-30-days', reminders_enabled=False)
        self.client.post(reverse('resources:program_restart', args=['first-30-days']))
        self.assertFalse(ProgramEnrollment.objects.get(user=self.user).reminders_enabled)
