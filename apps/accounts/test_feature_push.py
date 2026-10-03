"""send_feature_push: the one-off "guided audio is here" push."""
from datetime import datetime
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.management.commands.send_feature_push import KEY, local_hour
from apps.accounts.models import AnnouncementDelivery, DeviceToken

User = get_user_model()
SEND = 'apps.accounts.management.commands.send_feature_push.send_push_to_user'
OK = {'android': {'sent': 0, 'failed': 0}, 'ios': {'sent': 1, 'failed': 0}, 'web': {'sent': 0, 'failed': 0}}
NONE = {'android': {'sent': 0, 'failed': 0}, 'ios': {'sent': 0, 'failed': 1}, 'web': {'sent': 0, 'failed': 0}}


def member(name, tz='America/New_York', device=True, **fields):
    u = User.objects.create_user(name, f'{name}@example.com', 'pw12345!')
    User.objects.filter(pk=u.pk).update(timezone=tz, **fields)
    u.refresh_from_db()
    if device:
        DeviceToken.objects.create(user=u, token=f'tok-{name}', platform='ios')
    return u


class FeaturePushTests(TestCase):
    def run_cmd(self, *args, result=OK):
        out = StringIO()
        with patch(SEND, return_value=result) as send:
            call_command('send_feature_push', *args, '--sleep', '0', '--any-hour', stdout=out, stderr=StringIO())
        return out.getvalue(), send

    def setUp(self):
        self.app_user = member('appuser')
        member('noapp', device=False)
        member('muted', email_notifications=False)

    def test_dry_run(self):
        out, send = self.run_cmd()
        send.assert_not_called()
        self.assertIn('With the app: 1', out)

    def test_commit_once_with_deep_link(self):
        out, send = self.run_cmd('--commit')
        user, title, body, data = send.call_args.args
        self.assertEqual(user, self.app_user)
        self.assertIn('free', body)
        self.assertTrue(data['url'].startswith('/resources/audio/'))
        self.assertTrue(AnnouncementDelivery.objects.filter(user=self.app_user, key=KEY).exists())
        out, send = self.run_cmd('--commit')
        send.assert_not_called()

    def test_undelivered_is_retried_later(self):
        self.run_cmd('--commit', result=NONE)
        self.assertFalse(AnnouncementDelivery.objects.exists())

    def test_daytime_window(self):
        noon_ny = datetime(2026, 10, 3, 16, 0, tzinfo=ZoneInfo('UTC'))  # 12:00 in New York
        self.assertEqual(local_hour(self.app_user, noon_ny), 12)
        night = member('tokyo', tz='Asia/Tokyo')  # 01:00 in Tokyo
        self.assertEqual(local_hour(night, noon_ny), 1)
        self.assertEqual(local_hour(member('blank', tz=''), noon_ny), 12)  # falls back to Eastern

    def test_test_push_not_recorded(self):
        out = StringIO()
        with patch(SEND, return_value=OK) as send:
            call_command('send_feature_push', '--test', 'appuser', stdout=out)
        send.assert_called_once()
        self.assertFalse(AnnouncementDelivery.objects.exists())
