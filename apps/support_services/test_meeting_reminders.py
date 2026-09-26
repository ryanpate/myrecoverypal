"""Email reminders for meetings, open to logged-out visitors (double opt-in)."""
from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting, MeetingReminder

User = get_user_model()
CHICAGO = ZoneInfo('America/Chicago')


def _meeting(**kw):
    fields = dict(name='Nooners', slug=f'mtg-test-{Meeting.objects.count()}', day=1,
                  time=time(12, 0), timezone='America/Chicago', attendance_option='online',
                  conference_url='https://zoom.us/j/1', is_approved=True, is_active=True)
    fields.update(kw)
    return Meeting.objects.create(**fields)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReminderSignupTest(TestCase):

    def setUp(self):
        from django.core.cache import caches
        for name in ('rate_limiting', 'default'):
            try:
                caches[name].clear()
            except Exception:
                pass
        self.meeting = _meeting()
        self.url = reverse('support_services:meeting_reminder_signup', args=[self.meeting.slug])

    @patch('apps.support_services.reminders.send_email')
    def test_signup_creates_unconfirmed_reminder_and_sends_confirmation(self, send):
        resp = self.client.post(self.url, {'email': 'Visitor@Example.com'})
        self.assertRedirects(resp, reverse('support_services:meeting_detail', args=[self.meeting.slug]),
                             fetch_redirect_response=False)
        r = MeetingReminder.objects.get()
        self.assertEqual((r.email, r.meeting, r.confirmed_at), ('visitor@example.com', self.meeting, None))
        self.assertEqual(send.call_count, 1)
        body = send.call_args.kwargs['plain_message']
        self.assertIn(reverse('support_services:meeting_reminder_confirm', args=[r.token]), body)

    @patch('apps.support_services.reminders.send_email')
    def test_repeat_signup_does_not_duplicate(self, send):
        self.client.post(self.url, {'email': 'a@example.com'})
        self.client.post(self.url, {'email': 'a@example.com'})
        self.assertEqual(MeetingReminder.objects.count(), 1)

    @patch('apps.support_services.reminders.send_email')
    def test_invalid_email_rejected(self, send):
        self.client.post(self.url, {'email': 'not-an-email'})
        self.assertFalse(MeetingReminder.objects.exists())
        send.assert_not_called()

    @patch('apps.support_services.reminders.send_email')
    def test_per_email_cap(self, send):
        from apps.support_services.reminders import MAX_REMINDERS_PER_EMAIL
        for i in range(MAX_REMINDERS_PER_EMAIL + 2):
            m = _meeting()
            self.client.post(reverse('support_services:meeting_reminder_signup', args=[m.slug]),
                             {'email': 'cap@example.com'})
        self.assertEqual(MeetingReminder.objects.filter(email='cap@example.com').count(),
                         MAX_REMINDERS_PER_EMAIL)

    def test_confirm_link_confirms(self):
        r = MeetingReminder.objects.create(email='c@example.com', meeting=self.meeting)
        self.client.get(reverse('support_services:meeting_reminder_confirm', args=[r.token]))
        r.refresh_from_db()
        self.assertIsNotNone(r.confirmed_at)

    def test_unsubscribe_deletes_the_record(self):
        r = MeetingReminder.objects.create(email='u@example.com', meeting=self.meeting)
        url = reverse('support_services:meeting_reminder_unsubscribe', args=[r.token])
        self.assertEqual(self.client.get(url).status_code, 200)   # GET only shows a button
        self.assertTrue(MeetingReminder.objects.exists())
        self.client.post(url)
        self.assertFalse(MeetingReminder.objects.exists())

    def test_detail_page_offers_reminder_to_logged_out_visitors_only(self):
        detail = reverse('support_services:meeting_detail', args=[self.meeting.slug])
        self.assertContains(self.client.get(detail), 'id="meeting-reminder-form"')
        User.objects.create_user(username='m', email='m@example.com', password='pw')
        self.client.login(username='m', password='pw')
        self.assertNotContains(self.client.get(detail), 'id="meeting-reminder-form"')


class ReminderSendingTest(TestCase):
    """Monday 12:00 Chicago meeting; the task runs every 15 minutes."""

    def setUp(self):
        self.meeting = _meeting(day=1, time=time(12, 0))
        self.reminder = MeetingReminder.objects.create(
            email='r@example.com', meeting=self.meeting,
            confirmed_at=datetime(2026, 9, 1, tzinfo=CHICAGO))

    def _run(self, local_dt):
        from apps.support_services.reminders import send_due_reminders
        with patch('apps.support_services.reminders.send_email') as send, \
                patch('apps.support_services.reminders.timezone.now', return_value=local_dt):
            send_due_reminders()
        return send

    def test_sends_about_an_hour_before(self):
        send = self._run(datetime(2026, 9, 28, 11, 0, tzinfo=CHICAGO))   # a Monday
        self.assertEqual(send.call_count, 1)
        body = send.call_args.kwargs['plain_message']
        self.assertIn('https://zoom.us/j/1', body)
        self.assertIn(reverse('support_services:meeting_reminder_unsubscribe',
                              args=[self.reminder.token]), body)
        self.reminder.refresh_from_db()
        self.assertIsNotNone(self.reminder.last_sent_at)

    def test_not_sent_twice_the_same_week(self):
        self._run(datetime(2026, 9, 28, 11, 0, tzinfo=CHICAGO))
        send = self._run(datetime(2026, 9, 28, 11, 15, tzinfo=CHICAGO))
        send.assert_not_called()

    def test_not_sent_outside_the_window_or_wrong_day(self):
        self.assertEqual(self._run(datetime(2026, 9, 28, 8, 0, tzinfo=CHICAGO)).call_count, 0)
        self.assertEqual(self._run(datetime(2026, 9, 29, 11, 0, tzinfo=CHICAGO)).call_count, 0)

    def test_unconfirmed_or_inactive_meeting_skipped(self):
        self.reminder.confirmed_at = None
        self.reminder.save()
        self.assertEqual(self._run(datetime(2026, 9, 28, 11, 0, tzinfo=CHICAGO)).call_count, 0)
        self.reminder.confirmed_at = datetime(2026, 9, 1, tzinfo=CHICAGO)
        self.reminder.save()
        self.meeting.is_active = False
        self.meeting.save()
        self.assertEqual(self._run(datetime(2026, 9, 28, 11, 0, tzinfo=CHICAGO)).call_count, 0)

    def test_meeting_timezone_is_respected(self):
        # Same wall-clock meeting in New York: 11:00 Chicago is 12:00 there, too late.
        self.meeting.timezone = 'America/New_York'
        self.meeting.save()
        self.assertEqual(self._run(datetime(2026, 9, 28, 11, 0, tzinfo=CHICAGO)).call_count, 0)
        self.assertEqual(self._run(datetime(2026, 9, 28, 10, 0, tzinfo=CHICAGO)).call_count, 1)
