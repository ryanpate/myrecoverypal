from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.accounts.payment_models import Subscription

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtComplianceNudgeTests(TestCase):
    """The meeting-finder Court nudge: shown to authenticated non-court users,
    hidden from court users (they already have it)."""

    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'pw')
        self.sub = Subscription.objects.get(user=self.user)

    def _get(self):
        return self.client.get(reverse('support_services:meeting_list'))

    def test_non_court_user_sees_nudge(self):
        self.client.force_login(self.user)
        self.assertContains(self._get(), 'courtNudge')

    def test_court_user_does_not_see_nudge(self):
        self.sub.tier = 'court'
        self.sub.status = 'active'
        self.sub.save()
        self.client.force_login(self.user)
        self.assertNotContains(self._get(), 'courtNudge')

    def test_anonymous_does_not_see_nudge(self):
        self.assertNotContains(self._get(), 'courtNudge')
