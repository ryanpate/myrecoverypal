from datetime import timedelta
from unittest.mock import patch
import pytz
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts import tasks
from apps.accounts.models import Notification
from apps.accounts.push_notifications import PushNotificationService
from apps.support_services.models import Meeting, UserBookmark

User = get_user_model()


class MeetingReminderNotificationTests(TestCase):
    def test_creates_notification_and_sends_push(self):
        user = User.objects.create_user(username='mo', password='x', email='mo@example.com')
        meeting = Meeting.objects.create(name='Noon Group', slug='noon-group')

        with patch('apps.accounts.push_notifications.send_push_to_user', return_value={}) as push:
            notification = PushNotificationService.notify_meeting_reminder(user, meeting)

        notification = Notification.objects.get(pk=notification.pk)
        self.assertEqual(notification.notification_type, 'meeting_reminder')
        self.assertEqual(notification.link, '/support/meetings/noon-group/')
        self.assertEqual(notification.message, 'Noon Group starts in 30 minutes')
        push.assert_called_once()
        self.assertEqual(push.call_args.args[2], 'Noon Group starts in 30 minutes')

    def test_task_sends_reminder_for_meeting_in_30_minutes(self):
        user = User.objects.create_user(username='jo', password='x', email='jo@example.com')
        start = timezone.now().astimezone(pytz.timezone('America/Chicago')) + timedelta(minutes=30)
        meeting = Meeting.objects.create(
            name='Evening Group', slug='evening-group',
            day=(start.weekday() + 1) % 7, time=start.time(), timezone='America/Chicago',
        )
        UserBookmark.objects.create(user=user, meeting=meeting, reminder_enabled=True)

        with patch('apps.accounts.push_notifications.send_push_to_user', return_value={}), \
                patch.object(tasks, 'send_email', return_value=(True, None)) as send_email, \
                patch.object(tasks.time, 'sleep'):
            self.assertEqual(tasks.send_meeting_reminders.run(), 1)

        send_email.assert_called_once()
        self.assertTrue(Notification.objects.filter(
            recipient=user, link='/support/meetings/evening-group/').exists())
