from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Promo

User = get_user_model()


# PREPEND_WWW=True and SECURE_SSL_REDIRECT=True in production settings cause
# 301 redirects before requests ever reach the view. Override both for all
# tests in this module so requests reach the view directly.
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class JournalBonusGetTests(TestCase):
    def test_get_renders_page(self):
        resp = self.client.get(reverse('core:journal_bonus'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome')
        self.assertContains(resp, 'Start free trial')

    def test_default_promo_code_is_pal90(self):
        resp = self.client.get(reverse('core:journal_bonus'))
        self.assertContains(resp, 'value="PAL90"')

    def test_query_param_overrides_default_code(self):
        resp = self.client.get(reverse('core:journal_bonus') + '?code=OTHER')
        self.assertContains(resp, 'value="OTHER"')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class JournalBonusPostTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='PAL90',
            defaults={'trial_days': 60, 'active': True},
        )

    def test_post_with_new_email_redirects_to_register(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'newperson@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/register/', resp.url)
        self.assertIn('email=newperson%40example.com', resp.url)
        # Promo stashed in session
        self.assertEqual(self.client.session.get('journal_promo'), 'PAL90')

    def test_post_with_existing_email_redirects_to_login(self):
        User.objects.create_user(
            username='returning', email='returning@example.com', password='x'
        )
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'returning@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
        self.assertIn('next=', resp.url)
        self.assertEqual(self.client.session.get('journal_promo'), 'PAL90')

    def test_post_with_invalid_email_rerenders_with_error(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'not-an-email',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'valid email')

    def test_post_with_empty_email_rerenders_with_error(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': '',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'valid email')

    def test_email_lookup_is_case_insensitive(self):
        User.objects.create_user(
            username='returning', email='returning@example.com', password='x'
        )
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'RETURNING@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
