"""Premium copy must match what Premium actually is (2026-10-26 cleanup).

Groups and challenges are free (and currently hidden), the journal is
unlimited for everyone, free members get 3 coach messages a day (not 3 trial
messages) and Premium gets 20 a day (not unlimited).
"""
from django.test import TestCase, override_settings
from django.urls import reverse

PAGES = ('core:alcohol_recovery_app', 'core:drug_addiction_recovery_app', 'core:free_aa_app',
         'core:gambling_addiction_app', 'core:opioid_recovery_app', 'core:sober_grid_alternative',
         'core:sobriety_counter_app', 'core:ai_recovery_coach', 'accounts:pricing')
STALE = ('unlimited groups', 'trial messages', 'Unlimited AI Coach messages',
         'unlimited journal access')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PremiumClaimsTests(TestCase):
    def test_public_pages_make_no_stale_premium_claims(self):
        for page in PAGES:
            html = self.client.get(reverse(page)).content.decode()
            for claim in STALE:
                with self.subTest(page=page, claim=claim):
                    self.assertNotIn(claim.lower(), html.lower())

    def test_seo_pages_lead_premium_with_streak_protection(self):
        html = self.client.get(reverse('core:alcohol_recovery_app')).content.decode()
        self.assertIn('Premium ($9.99/month) adds streak protection', html)
