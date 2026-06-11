from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink
from apps.accounts.models import DailyCheckIn, Notification
from apps.accounts.tasks import send_supporter_inactivity_alerts

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
@patch('apps.accounts.tasks.send_email')   # avoid real Resend/network calls
class InactivityAlertTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='im', email='im@x.com', password='pw')
        self.sup = User.objects.create_user(username='is', email='is@x.com', password='pw')
        self.link = SupporterLink.objects.create(member=self.member, supporter=self.sup,
            initiated_by='member', status='active', preset='close', inactivity_threshold_days=3)

    def test_alert_fires_when_inactive(self, mock_send):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=5),
                                    mood=3, craving_level=0, energy_level=3)
        sent = send_supporter_inactivity_alerts()
        self.assertEqual(sent, 1)
        self.assertTrue(Notification.objects.filter(
            recipient=self.sup, notification_type='member_inactive').exists())
        self.link.refresh_from_db()
        self.assertIsNotNone(self.link.last_inactivity_alert_sent)

    def test_no_alert_when_recent(self, mock_send):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date(),
                                    mood=3, craving_level=0, energy_level=3)
        self.assertEqual(send_supporter_inactivity_alerts(), 0)

    def test_cooldown_prevents_repeat(self, mock_send):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=5),
                                    mood=3, craving_level=0, energy_level=3)
        self.link.last_inactivity_alert_sent = timezone.now()
        self.link.save()
        self.assertEqual(send_supporter_inactivity_alerts(), 0)

    def test_non_close_presets_never_alert(self, mock_send):
        self.link.preset = 'standard'
        self.link.save()
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=10),
                                    mood=3, craving_level=0, energy_level=3)
        self.assertEqual(send_supporter_inactivity_alerts(), 0)
