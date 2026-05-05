from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.accounts.models import RelapseLog

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LogSlipTruncationTests(TestCase):
    """
    Regression: Sentry was firing
        StringDataRightTruncation: value too long for type character varying(100)
    when users entered a substance value over 100 chars. The form had no
    maxlength attribute and the view passed POST data straight to
    RelapseLog.objects.create().
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='slipper', email='slipper@example.com', password='pw'
        )
        self.client.login(username='slipper', password='pw')

    def _post(self, **overrides):
        data = {
            'slip_date': '2026-05-01',
            'substance': '',
            'trigger': '',
            'notes': '',
        }
        data.update(overrides)
        return self.client.post(reverse('accounts:log_slip'), data)

    def test_overlong_substance_is_truncated_not_rejected(self):
        resp = self._post(substance='a' * 250)
        self.assertEqual(resp.status_code, 302)
        log = RelapseLog.objects.get(user=self.user)
        self.assertEqual(len(log.substance), 100)

    def test_overlong_trigger_is_truncated_not_rejected(self):
        resp = self._post(trigger='b' * 500)
        self.assertEqual(resp.status_code, 302)
        log = RelapseLog.objects.get(user=self.user)
        self.assertEqual(len(log.trigger), 200)

    def test_normal_input_passes_through_unchanged(self):
        self._post(substance='alcohol', trigger='stress')
        log = RelapseLog.objects.get(user=self.user)
        self.assertEqual(log.substance, 'alcohol')
        self.assertEqual(log.trigger, 'stress')
