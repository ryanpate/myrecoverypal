"""Tests for court-tier engagement tasks (July 2026):
- send_court_meeting_reminders: evening nudge when behind weekly requirement
- send_court_monthly_po_reports: opt-in auto-email of last month's report
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)
from apps.accounts.models import Notification
from apps.accounts.tasks import (
    send_court_meeting_reminders, send_court_monthly_po_reports,
)

User = get_user_model()


def make_court_user(username, required=3, auto_email=False, po_email='po@example.gov'):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='pw')
    user.subscription.tier = 'court'
    user.subscription.status = 'active'
    user.subscription.save()
    profile = CourtReportProfile.objects.create(
        user=user, legal_name=f'{username} Legal', case_number='C-1',
        required_meetings_per_week=required,
        auto_email_monthly=auto_email,
        probation_officer_email=po_email,
    )
    return user, profile


def log_meeting(user, dt):
    return MeetingAttendance.objects.create(
        user=user, meeting_name='Test Group', meeting_date=dt,
        meeting_address='123 Way', program='aa', meeting_type='open',
        verification_method='self',
    )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtMeetingReminderTests(TestCase):
    def test_behind_pace_user_gets_reminder_once(self):
        user, profile = make_court_user('behind', required=3)
        sent = send_court_meeting_reminders()
        self.assertEqual(sent, 1)
        note = Notification.objects.get(recipient=user)
        self.assertEqual(note.notification_type, 'meeting_reminder')
        self.assertIn('/accounts/court/attendance/', note.link)
        # Second run same day: deduped
        self.assertEqual(send_court_meeting_reminders(), 0)

    def test_user_who_logged_today_not_reminded(self):
        user, profile = make_court_user('loggedtoday', required=3)
        log_meeting(user, timezone.now())
        self.assertEqual(send_court_meeting_reminders(), 0)
        self.assertFalse(Notification.objects.filter(recipient=user).exists())

    def test_user_on_pace_not_reminded(self):
        user, profile = make_court_user('onpace', required=2)
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        # Log requirement-met meetings earlier this week (not today)
        if now.weekday() >= 2:
            log_meeting(user, week_start)
            log_meeting(user, week_start + timedelta(days=1))
        else:
            # Early in the week: logging "today" also covers the
            # logged-today skip, so just require 0 to force on-pace
            profile.required_meetings_per_week = 1
            profile.save()
            log_meeting(user, now - timedelta(hours=1))
        self.assertEqual(send_court_meeting_reminders(), 0)

    def test_non_court_user_not_reminded(self):
        user, profile = make_court_user('freeuser')
        user.subscription.tier = 'free'
        user.subscription.save()
        self.assertEqual(send_court_meeting_reminders(), 0)

    def test_expired_compliance_window_not_reminded(self):
        user, profile = make_court_user('doneuser')
        profile.report_period_end = timezone.now().date() - timedelta(days=5)
        profile.save()
        self.assertEqual(send_court_meeting_reminders(), 0)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtMonthlyPoReportTests(TestCase):
    def _last_month_meeting(self, user):
        today = timezone.now().date()
        prev_end = today.replace(day=1) - timedelta(days=1)
        dt = timezone.make_aware(
            datetime(prev_end.year, prev_end.month, min(prev_end.day, 15), 19, 0))
        log_meeting(user, dt)

    @patch('apps.accounts.email_service.send_email', return_value=(True, None))
    def test_opted_in_user_report_generated_and_emailed(self, mock_send):
        user, profile = make_court_user('autopo', auto_email=True)
        self._last_month_meeting(user)
        sent = send_court_monthly_po_reports()
        self.assertEqual(sent, 1)

        report = CourtReport.objects.get(user=user)
        today = timezone.now().date()
        prev_end = today.replace(day=1) - timedelta(days=1)
        self.assertEqual(report.period_start, prev_end.replace(day=1))
        self.assertEqual(report.period_end, prev_end)
        self.assertEqual(report.attendance_count, 1)
        self.assertIn('po@example.gov', report.emailed_to)
        self.assertIsNotNone(report.emailed_at)

        # Email actually attempted with an attachment to the PO
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['recipient_email'], 'po@example.gov')
        self.assertTrue(kwargs['attachments'][0][0].endswith('.pdf'))

        # User notified of the send
        note = Notification.objects.get(recipient=user)
        self.assertIn('Report sent', note.title)

        # Rerun this month: deduped
        self.assertEqual(send_court_monthly_po_reports(), 0)

    @patch('apps.accounts.email_service.send_email', return_value=(True, None))
    def test_not_opted_in_user_skipped(self, mock_send):
        user, profile = make_court_user('noauto', auto_email=False)
        self._last_month_meeting(user)
        self.assertEqual(send_court_monthly_po_reports(), 0)
        mock_send.assert_not_called()

    @patch('apps.accounts.email_service.send_email', return_value=(True, None))
    def test_missing_po_email_skipped(self, mock_send):
        user, profile = make_court_user('nopo', auto_email=True, po_email='')
        self.assertEqual(send_court_monthly_po_reports(), 0)
        mock_send.assert_not_called()

    @patch('apps.accounts.email_service.send_email', return_value=(False, 'smtp down'))
    def test_failed_send_notifies_user_and_does_not_mark_sent(self, mock_send):
        user, profile = make_court_user('failpo', auto_email=True)
        self._last_month_meeting(user)
        self.assertEqual(send_court_monthly_po_reports(), 0)
        profile.refresh_from_db()
        self.assertIsNone(profile.last_auto_po_email_sent)
        note = Notification.objects.get(recipient=user)
        self.assertIn('could not be sent', note.title)
