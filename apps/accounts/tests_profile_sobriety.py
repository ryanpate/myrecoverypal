from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

User = get_user_model()

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


@override_settings(**_TEST_SETTINGS)
class ProfileSobrietyCardTests(TestCase):
    """The profile's Sobriety Journey card counts in calendar years and months."""

    def _context(self, **ago):
        today = timezone.now().date()
        self.start = today - relativedelta(**ago)
        user = User.objects.create_user(
            username='longtimer', email='longtimer@example.com', password='x', sobriety_date=self.start)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:profile', args=['longtimer']))
        self.assertEqual(resp.status_code, 200)
        self.days = (today - self.start).days
        return resp.context

    def test_breakdown_uses_whole_calendar_years_and_months(self):
        ctx = self._context(years=8, months=8)
        self.assertEqual(ctx['sobriety_breakdown'], {
            'years': 8, 'months': 104, 'weeks': self.days // 7,
        })

    def test_next_milestone_is_the_next_anniversary(self):
        ctx = self._context(years=8, months=8)
        target = (self.start + relativedelta(years=9) - self.start).days
        milestone = ctx['next_sobriety_milestone']
        self.assertEqual(milestone['label'], '9 Years')
        self.assertEqual(milestone['days_until'], target - self.days)

    def test_first_year_keeps_day_milestones(self):
        ctx = self._context(days=45)
        milestone = ctx['next_sobriety_milestone']
        self.assertEqual(milestone['label'], '60 Days')
        self.assertEqual(milestone['days_until'], 15)
        self.assertEqual(ctx['sobriety_breakdown'],
                         {'years': 0, 'months': 1, 'weeks': 6})
