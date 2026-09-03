"""Tests for the password reset email flow.

Regression guard for Sentry PYTHON-DJANGO-1G: django.contrib.admin ships its
own registration/password_reset_email.html and precedes apps.accounts in
INSTALLED_APPS, so with APP_DIRS=True it shadowed our branded template. The
admin copy reverses the un-namespaced 'password_reset_confirm', which this
project only registers as 'accounts:password_reset_confirm' -> NoReverseMatch
(a 500 on every reset request).
"""
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# Test fixture, not a real password. Marked to silence GitGuardian's secret scanner.
TEST_PW = 'a' * 12  # noqa: ggignore


# PREPEND_WWW/SECURE_SSL_REDIRECT are on in prod settings and turn every
# test request into a 301 before it reaches the view.
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PasswordResetEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetter', email='resetter@example.com', password=TEST_PW
        )

    def test_reset_request_succeeds_and_sends_email(self):
        """POSTing the reset form returns a redirect, not a 500."""
        response = self.client.post(
            reverse('accounts:password_reset'), {'email': 'resetter@example.com'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_email_contains_working_confirm_link(self):
        """The emailed link must resolve to our namespaced confirm view."""
        self.client.post(
            reverse('accounts:password_reset'), {'email': 'resetter@example.com'}
        )
        body = mail.outbox[0].body
        self.assertIn('/accounts/password-reset-confirm/', body)

    def test_email_body_is_plain_text_not_html_source(self):
        """The text/plain body must not be raw HTML markup."""
        self.client.post(
            reverse('accounts:password_reset'), {'email': 'resetter@example.com'}
        )
        body = mail.outbox[0].body
        self.assertNotIn('<!DOCTYPE html>', body)

    def test_email_has_branded_html_alternative(self):
        """The branded MyRecoveryPal template is attached as text/html."""
        self.client.post(
            reverse('accounts:password_reset'), {'email': 'resetter@example.com'}
        )
        alternatives = mail.outbox[0].alternatives
        self.assertEqual(len(alternatives), 1)
        html, mimetype = alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('MyRecoveryPal', html)
        self.assertIn('/accounts/password-reset-confirm/', html)

    def test_html_email_escapes_user_supplied_name(self):
        """first_name is attacker-controlled; the HTML part must escape it."""
        self.user.first_name = '<script>alert(1)</script>'
        self.user.save(update_fields=['first_name'])
        self.client.post(
            reverse('accounts:password_reset'), {'email': 'resetter@example.com'}
        )
        html = mail.outbox[0].alternatives[0][0]
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
