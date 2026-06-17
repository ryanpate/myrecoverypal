from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.accounts.payment_models import Subscription
from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PremiumUpsellCardTests(TestCase):
    """The progress-home upsell card shows only for free/expired users."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='u', email='u@example.com', password='pw'
        )
        self.client.force_login(self.user)
        self.sub = Subscription.objects.get(user=self.user)

    def _get(self):
        return self.client.get(reverse('accounts:progress'))

    def test_free_user_sees_card(self):
        self.sub.tier = 'free'
        self.sub.status = 'expired'
        self.sub.save()
        resp = self._get()
        self.assertTrue(resp.context['show_premium_cta'])
        self.assertContains(resp, 'premiumUpsellCard')

    def test_premium_user_does_not_see_card(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.save()
        resp = self._get()
        self.assertFalse(resp.context['show_premium_cta'])
        self.assertNotContains(resp, 'premiumUpsellCard')

    def test_supporter_does_not_see_card(self):
        self.sub.tier = 'supporter'
        self.sub.status = 'active'
        self.sub.save()
        resp = self._get()
        self.assertFalse(resp.context['show_premium_cta'])

    def test_court_user_does_not_see_card(self):
        self.sub.tier = 'court'
        self.sub.status = 'active'
        self.sub.save()
        resp = self._get()
        self.assertFalse(resp.context['show_premium_cta'])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterInviteCardTests(TestCase):
    """The supporter invite card: shown to paid users (who can't be upsold to
    Premium) who haven't invited anyone yet. Mutually exclusive with the
    Premium card so a user sees at most one."""

    def setUp(self):
        self.user = User.objects.create_user('m', 'm@example.com', 'pw')
        self.client.force_login(self.user)
        self.sub = Subscription.objects.get(user=self.user)

    def _get(self):
        return self.client.get(reverse('accounts:progress'))

    def test_free_user_sees_premium_not_supporter(self):
        self.sub.tier = 'free'
        self.sub.status = 'expired'
        self.sub.save()
        resp = self._get()
        self.assertTrue(resp.context['show_premium_cta'])
        self.assertFalse(resp.context['show_supporter_cta'])  # one card max

    def test_premium_user_without_link_sees_supporter_card(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.save()
        resp = self._get()
        self.assertFalse(resp.context['show_premium_cta'])
        self.assertTrue(resp.context['show_supporter_cta'])
        self.assertContains(resp, 'supporterInviteCard')

    def test_premium_user_with_active_link_does_not_see_card(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.save()
        SupporterLink.objects.create(member=self.user, initiated_by='member', status='active')
        resp = self._get()
        self.assertFalse(resp.context['show_supporter_cta'])
