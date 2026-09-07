"""Password reset must use the same email transport as everything else.

Sentry PYTHON-DJANGO-50: SMTPServerDisconnected on /accounts/password-reset/.

Root cause: Django's stock PasswordResetForm.send_mail() builds an
EmailMultiAlternatives and calls .send(), which goes straight to the
configured SMTP backend. Every other email in this project goes through
apps.accounts.email_service.send_email(), which uses the Resend HTTP API
(more reliable on Railway) and only falls back to SMTP.

So password reset was the single email path still depending on SMTP — and
EMAIL_HOST pointed at SendGrid with a credential that no longer
authenticates. Nothing else broke, which is why it went unnoticed.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PasswordResetTransportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'resetter', 'resetter@example.com', 'pw')
        self.url = reverse('accounts:password_reset')

    def _post(self, email='resetter@example.com'):
        return self.client.post(self.url, {'email': email})

    def test_reset_email_goes_through_the_shared_email_service(self):
        with patch('apps.accounts.forms.send_email',
                   return_value=(True, None)) as send:
            resp = self._post()

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            send.called,
            'Password reset must use email_service.send_email(), not the '
            'SMTP backend directly.')

    def test_reset_email_does_not_use_djangos_mail_backend(self):
        """django.core.mail.outbox filling up means it went via SMTP."""
        with patch('apps.accounts.forms.send_email', return_value=(True, None)):
            self._post()
        self.assertEqual(len(mail.outbox), 0)

    def test_both_plain_and_html_bodies_are_sent(self):
        with patch('apps.accounts.forms.send_email',
                   return_value=(True, None)) as send:
            self._post()

        kwargs = send.call_args.kwargs
        self.assertIn('resetter@example.com', kwargs['recipient_email'])
        self.assertTrue(kwargs['plain_message'].strip())
        self.assertTrue(kwargs['html_message'].strip())
        # The reset link must survive into both bodies or the email is useless.
        self.assertIn('password-reset-confirm', kwargs['plain_message'])
        self.assertIn('password-reset-confirm', kwargs['html_message'])

    def test_subject_is_a_single_line_and_not_the_admin_default(self):
        """Django admin ships registration/password_reset_subject.txt and
        precedes this app in INSTALLED_APPS, so relying on that template is
        the same shadowing trap that caused PYTHON-DJANGO-1G. Render it
        explicitly instead."""
        with patch('apps.accounts.forms.send_email',
                   return_value=(True, None)) as send:
            self._post()

        subject = send.call_args.kwargs['subject']
        self.assertNotIn('\n', subject)
        self.assertTrue(subject.strip())
        self.assertIn('MyRecoveryPal', subject)

    def test_unknown_email_sends_nothing_but_still_succeeds(self):
        """Must not leak which addresses have accounts."""
        with patch('apps.accounts.forms.send_email',
                   return_value=(True, None)) as send:
            resp = self._post('nobody@example.com')

        self.assertEqual(resp.status_code, 302)
        self.assertFalse(send.called)

    def test_transport_failure_does_not_500(self):
        """A dead mail provider must not take the page down — that was the
        original Sentry event, an unhandled exception on a POST."""
        with patch('apps.accounts.forms.send_email',
                   return_value=(False, 'provider exploded')):
            resp = self._post()
        self.assertEqual(resp.status_code, 302)

    def test_transport_raising_does_not_500(self):
        with patch('apps.accounts.forms.send_email',
                   side_effect=OSError('connection closed')):
            resp = self._post()
        self.assertEqual(resp.status_code, 302)
