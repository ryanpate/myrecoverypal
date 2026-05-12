from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.accounts.payment_models import Promo, Subscription, PromoRedemption
from apps.accounts.invite_models import SystemSettings

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FaithJournalGetTests(TestCase):
    def test_get_renders_page(self):
        resp = self.client.get(reverse('core:faith_journal'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome')
        self.assertContains(resp, 'Start free trial')

    def test_default_promo_code_is_christian60(self):
        resp = self.client.get(reverse('core:faith_journal'))
        self.assertContains(resp, 'value="CHRISTIAN60"')

    def test_page_references_christian_journal(self):
        resp = self.client.get(reverse('core:faith_journal'))
        self.assertContains(resp, 'Christian')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FaithJournalPostTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='CHRISTIAN60',
            defaults={'trial_days': 60, 'active': True},
        )

    def test_post_with_new_email_redirects_to_register(self):
        resp = self.client.post(reverse('core:faith_journal'), {
            'email': 'newperson@example.com',
            'code': 'CHRISTIAN60',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/register/', resp.url)
        self.assertIn('email=newperson%40example.com', resp.url)
        self.assertEqual(self.client.session.get('journal_promo'), 'CHRISTIAN60')

    def test_post_with_existing_email_redirects_to_login(self):
        User.objects.create_user(
            username='returning', email='returning@example.com', password='x'
        )
        resp = self.client.post(reverse('core:faith_journal'), {
            'email': 'returning@example.com',
            'code': 'CHRISTIAN60',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
        self.assertEqual(self.client.session.get('journal_promo'), 'CHRISTIAN60')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FaithJournalEndToEndTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='CHRISTIAN60',
            defaults={'trial_days': 60, 'active': True},
        )
        SystemSettings.objects.update_or_create(
            pk=1,
            defaults={'invite_only_mode': False},
        )

    def test_full_signup_flow_grants_60_day_trial(self):
        self.client.post(reverse('core:faith_journal'), {
            'email': 'newuser@example.com',
            'code': 'CHRISTIAN60',
        })
        self.assertEqual(self.client.session.get('journal_promo'), 'CHRISTIAN60')

        register_resp = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!@',
            'password2': 'StrongPass123!@',
        })
        self.assertEqual(register_resp.status_code, 302)

        user = User.objects.get(username='newuser')
        sub = Subscription.objects.get(user=user)
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.status, 'trialing')
        self.assertEqual(sub.subscription_source, 'manual')
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((sub.trial_end - expected).total_seconds()), 120)

        self.assertTrue(
            PromoRedemption.objects.filter(user=user, promo__code='CHRISTIAN60').exists()
        )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class Christian60MigrationTests(TestCase):
    def test_migration_seeds_christian60_promo(self):
        promo = Promo.objects.get(code='CHRISTIAN60')
        self.assertEqual(promo.trial_days, 60)
        self.assertTrue(promo.active)
