from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Subscription

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterTierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='supporter', email='s@example.com', password='pw'
        )
        # A free Subscription row is auto-created by a post_save signal.
        # Update it to the desired tier/status for each test.

    def test_supporter_tier_is_recognized(self):
        sub = Subscription.objects.get(user=self.user)
        sub.tier = 'supporter'
        sub.status = 'active'
        sub.save()
        self.assertTrue(sub.is_supporter())
        self.assertFalse(sub.is_premium())   # supporter is NOT a premium superset
        self.assertFalse(sub.is_court())

    def test_inactive_supporter_is_not_supporter(self):
        sub = Subscription.objects.get(user=self.user)
        sub.tier = 'supporter'
        sub.status = 'canceled'
        sub.save()
        self.assertFalse(sub.is_supporter())
