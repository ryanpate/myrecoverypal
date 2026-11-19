"""The community feed is the composer and the feed: the check-in prompt shows
only until today's check-in is done, and the daily thought lives on Today."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyCheckIn

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FeedLayoutTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='feed_layout', email='feed@example.com', password='pw')
        self.client.login(username='feed_layout', password='pw')

    def feed(self):
        return self.client.get(reverse('accounts:social_feed')).content.decode()

    def test_checkin_prompt_shows_before_todays_checkin(self):
        self.assertIn('id="ckNudgeGrid"', self.feed())

    def test_checkin_prompt_is_gone_once_checked_in(self):
        DailyCheckIn.objects.create(
            user=self.user, date=timezone.localdate(), mood=4, craving_level=0, energy_level=3)
        self.assertNotIn('id="ckNudgeGrid"', self.feed())

    def test_support_row_and_no_daily_thought_card(self):
        html = self.feed()
        self.assertIn('class="support-row"', html)
        self.assertIn('I need support', html)
        self.assertNotIn('Daily recovery thought', html)
