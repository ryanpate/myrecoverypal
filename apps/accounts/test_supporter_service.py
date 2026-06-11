from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink
from apps.accounts.models import DailyCheckIn
from apps.accounts import supporter_service

User = get_user_model()

# energy_level is private check-in data not surfaced at any preset — excluded by design.
FORBIDDEN_KEYS = {'craving', 'craving_level', 'gratitude', 'challenge', 'goal',
                  'journal', 'notes', 'energy_level', 'energy'}


def _flatten_keys(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k)
            _flatten_keys(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten_keys(v, acc)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DashboardDataTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mm', email='mm@x.com', password='pw')
        self.member.sobriety_date = timezone.now().date() - timedelta(days=95)
        self.member.save()
        self.supporter = User.objects.create_user(username='ss', email='ss@x.com', password='pw')
        for i in range(7):
            if i == 3:
                continue
            DailyCheckIn.objects.create(
                user=self.member, date=timezone.now().date() - timedelta(days=i),
                mood=4, craving_level=3, energy_level=3, gratitude='private text',
            )
        self.link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='member', status='active',
        )

    def test_cheerleader_has_only_positive_signal(self):
        self.link.preset = 'cheerleader'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertEqual(data['days_sober'], 95)
        self.assertIn('next_milestone', data)
        self.assertNotIn('checkin_consistency', data)
        self.assertNotIn('mood_trend', data)

    def test_standard_adds_consistency_and_mood(self):
        self.link.preset = 'standard'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertEqual(data['checkin_consistency']['count'], 6)
        self.assertEqual(data['checkin_consistency']['window'], 7)
        self.assertTrue(all(isinstance(m, int) for m in data['mood_trend']))

    def test_close_adds_inactivity_status(self):
        self.link.preset = 'close'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertIn('inactivity', data)

    def test_no_preset_ever_leaks_craving_or_freetext(self):
        for preset in ('cheerleader', 'standard', 'close'):
            self.link.preset = preset
            data = supporter_service.get_dashboard_data(self.link)
            keys = set()
            _flatten_keys(data, keys)
            leaked = keys & FORBIDDEN_KEYS
            self.assertFalse(leaked, f"preset {preset} leaked {leaked}")

    def test_mood_trend_is_scalar_mood_values_only(self):
        # Value/shape guard: a craving scalar leaked as a tuple element would
        # bypass the key-name check above. mood_trend must be plain ints 1-6.
        self.link.preset = 'close'
        data = supporter_service.get_dashboard_data(self.link)
        for item in data['mood_trend']:
            self.assertIsInstance(item, int)
            self.assertIn(item, range(1, 7))

    def test_inactive_link_shares_nothing(self):
        # The read gate itself must refuse a non-active link.
        self.link.preset = 'standard'
        self.link.revoke()
        with self.assertRaises(ValueError):
            supporter_service.get_dashboard_data(self.link)
