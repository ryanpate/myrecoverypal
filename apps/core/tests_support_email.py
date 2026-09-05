# apps/core/tests_support_email.py
"""The published contact address must reach a real inbox, on every page that
promises it does."""
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupportEmailRenderedTest(TestCase):

    def test_setting_is_not_an_unmonitored_noreply_address(self):
        self.assertNotIn('noreply', settings.SUPPORT_EMAIL)
        self.assertIn('@', settings.SUPPORT_EMAIL)

    def test_admins_receive_django_error_mail(self):
        self.assertEqual([addr for _, addr in settings.ADMINS], [settings.SUPPORT_EMAIL])

    def test_public_pages_render_the_support_address(self):
        for name in ['privacy', 'terms', 'for_probation_officers']:
            with self.subTest(page=name):
                response = self.client.get(reverse(f'core:{name}'))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, settings.SUPPORT_EMAIL)
                self.assertNotContains(response, 'mailto:"')
