from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Subscription, Promo, PromoRedemption
from apps.accounts.promo_service import apply_promo_to_user

User = get_user_model()


class ApplyPromoTests(TestCase):
    def setUp(self):
        self.promo, _ = Promo.objects.get_or_create(
            code='PAL90',
            defaults={'trial_days': 60, 'active': True},
        )
        # Ensure promo is in the expected state (seed migration may set different values).
        self.promo.trial_days = 60
        self.promo.active = True
        self.promo.save()
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='x'
        )
        # The User post_save signal creates a default trialing Subscription.
        # Grab it so tests start from a known state.
        self.sub = self.user.subscription
        self.sub.tier = 'free'
        self.sub.status = 'active'
        self.sub.trial_end = None
        self.sub.subscription_source = 'stripe'
        self.sub.save()

    def test_applies_60_day_trial_to_free_user(self):
        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.assertEqual(msg, 'applied')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tier, 'premium')
        self.assertEqual(self.sub.status, 'trialing')
        self.assertEqual(self.sub.subscription_source, 'manual')
        # trial_end should be ~60 days from now (within 1 minute tolerance)
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((self.sub.trial_end - expected).total_seconds()), 60)
        # PromoRedemption row created
        self.assertTrue(
            PromoRedemption.objects.filter(user=self.user, promo=self.promo).exists()
        )

    def test_extends_existing_trial_only_if_longer(self):
        far_future = timezone.now() + timedelta(days=120)
        self.sub.tier = 'premium'
        self.sub.status = 'trialing'
        self.sub.trial_end = far_future
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.sub.refresh_from_db()
        # Should NOT shorten the existing 120-day trial
        self.assertEqual(
            self.sub.trial_end.replace(microsecond=0),
            far_future.replace(microsecond=0),
        )

    def test_extends_short_trial_to_60_days(self):
        soon = timezone.now() + timedelta(days=5)
        self.sub.tier = 'premium'
        self.sub.status = 'trialing'
        self.sub.trial_end = soon
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.sub.refresh_from_db()
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((self.sub.trial_end - expected).total_seconds()), 60)

    def test_skips_active_paid_premium(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.subscription_source = 'stripe'
        self.sub.stripe_subscription_id = 'sub_123'
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already premium')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tier, 'premium')
        self.assertEqual(self.sub.subscription_source, 'stripe')
        self.assertFalse(
            PromoRedemption.objects.filter(user=self.user, promo=self.promo).exists()
        )

    def test_skips_active_paid_apple_premium(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.subscription_source = 'apple'
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already premium')

    def test_rejects_already_redeemed(self):
        PromoRedemption.objects.create(user=self.user, promo=self.promo)

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already redeemed')

    def test_rejects_unknown_code(self):
        applied, msg = apply_promo_to_user(self.user, 'BOGUS')
        self.assertFalse(applied)
        self.assertEqual(msg, 'invalid code')

    def test_rejects_inactive_code(self):
        self.promo.active = False
        self.promo.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'invalid code')
