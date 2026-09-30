# apps/accounts/tests_csp.py
"""Content-Security-Policy header (ContentSecurityPolicyMiddleware)."""
from django.test import TestCase, override_settings

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


def _directives(header):
    out = {}
    for part in header.split(';'):
        tokens = part.split()
        if tokens:
            out[tokens[0]] = tokens[1:]
    return out


@override_settings(**_TEST_SETTINGS)
class ContentSecurityPolicyTests(TestCase):
    def _policy(self, path='/accounts/login/'):
        resp = self.client.get(path)
        self.assertIn('Content-Security-Policy', resp.headers, path)
        return _directives(resp.headers['Content-Security-Policy'])

    def test_pages_send_an_enforced_policy(self):
        resp = self.client.get('/accounts/login/')
        self.assertIn('Content-Security-Policy', resp.headers)
        self.assertNotIn('Content-Security-Policy-Report-Only', resp.headers)

    def test_locked_down_directives(self):
        policy = self._policy()
        self.assertEqual(policy['default-src'], ["'self'"])
        self.assertEqual(policy['object-src'], ["'none'"])
        self.assertEqual(policy['base-uri'], ["'self'"])
        self.assertEqual(policy['frame-ancestors'], ["'none'"])

    def test_scripts_only_from_known_hosts(self):
        scripts = self._policy()['script-src']
        self.assertNotIn('*', scripts)
        self.assertNotIn('https:', scripts)
        self.assertNotIn("'unsafe-eval'", scripts)
        for host in ("'self'", 'https://www.googletagmanager.com',
                     'https://cdn.jsdelivr.net', 'https://js.stripe.com'):
            self.assertIn(host, scripts)

    def test_cloudflare_web_analytics_beacon_is_allowed(self):
        """Cloudflare injects this script at the edge in production — it is
        not in any template, so it never shows up in local testing."""
        policy = self._policy()
        self.assertIn('https://static.cloudflareinsights.com', policy['script-src'])
        self.assertIn('https://cloudflareinsights.com', policy['connect-src'])

    def test_forms_may_post_to_stripe_checkout_redirects(self):
        """The checkout/portal views answer a form POST with a redirect to
        Stripe; browsers apply form-action to that redirect."""
        forms = self._policy()['form-action']
        self.assertIn("'self'", forms)
        self.assertIn('https://checkout.stripe.com', forms)
        self.assertIn('https://billing.stripe.com', forms)

    def test_summernote_editor_may_be_framed_by_our_own_pages(self):
        policy = self._policy('/summernote/editor/id_content/')
        self.assertEqual(policy['frame-ancestors'], ["'self'"])

    def test_summernote_editor_cdns_are_allowed_only_on_editor_pages(self):
        """django-summernote pulls jQuery and Bootstrap 3 from CDNs inside its iframe."""
        editor = self._policy('/summernote/editor/id_content/')['script-src']
        self.assertIn('https://code.jquery.com', editor)
        self.assertIn('https://stackpath.bootstrapcdn.com', editor)
        self.assertNotIn('https://code.jquery.com', self._policy()['script-src'])

    def test_error_pages_carry_the_policy_too(self):
        resp = self.client.get('/definitely-not-a-page/')
        self.assertEqual(resp.status_code, 404)
        self.assertIn('Content-Security-Policy', resp.headers)

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only_switch(self):
        resp = self.client.get('/accounts/login/')
        self.assertIn('Content-Security-Policy-Report-Only', resp.headers)
        self.assertNotIn('Content-Security-Policy', resp.headers)
