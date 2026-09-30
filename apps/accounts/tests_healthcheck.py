# apps/accounts/tests_healthcheck.py
"""Railway's deploy health check calls the container over plain HTTP with
Host: healthcheck.railway.app. It must get a 200 — not the HTTPS redirect,
the www redirect, or a DisallowedHost 400 — or every deploy would fail."""
from django.test import TestCase, override_settings


@override_settings(PREPEND_WWW=True, SECURE_SSL_REDIRECT=True)
class HealthCheckTests(TestCase):
    def test_healthz_answers_200_to_railways_probe(self):
        resp = self.client.get('/healthz/', HTTP_HOST='healthcheck.railway.app')
        self.assertEqual(resp.status_code, 200)

    def test_other_paths_still_redirect_to_https(self):
        resp = self.client.get('/about/', HTTP_HOST='www.myrecoverypal.com')
        self.assertEqual(resp.status_code, 301)
