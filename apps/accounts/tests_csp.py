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


@override_settings(**_TEST_SETTINGS)
class CspNonceTests(TestCase):
    """CSP_STRICT swaps script-src 'unsafe-inline' for a per-request nonce."""

    def _script_src(self, resp):
        return _directives(resp.headers['Content-Security-Policy'])['script-src']

    def test_default_policy_still_allows_inline_scripts(self):
        script_src = self._script_src(self.client.get('/accounts/login/'))
        self.assertIn("'unsafe-inline'", script_src)
        self.assertFalse([v for v in script_src if v.startswith("'nonce-")])

    @override_settings(CSP_STRICT=True)
    def test_strict_policy_uses_the_nonce_the_page_was_rendered_with(self):
        resp = self.client.get('/accounts/login/')
        script_src = self._script_src(resp)
        self.assertNotIn("'unsafe-inline'", script_src)
        nonces = [v[len("'nonce-"):-1] for v in script_src if v.startswith("'nonce-")]
        self.assertEqual(len(nonces), 1)
        self.assertIn(f'<script nonce="{nonces[0]}">', resp.content.decode())

    @override_settings(CSP_STRICT=True)
    def test_each_response_gets_its_own_nonce(self):
        first = self._script_src(self.client.get('/accounts/login/'))
        second = self._script_src(self.client.get('/accounts/login/'))
        self.assertNotEqual(first, second)

    @override_settings(CSP_STRICT=True)
    def test_summernote_editor_keeps_inline_scripts(self):
        resp = self.client.get('/summernote/editor/id_content/')
        self.assertIn("'unsafe-inline'", self._script_src(resp))


class InlineScriptTemplateTests(TestCase):
    """What a nonce policy would block, checked in the template source."""

    # Converted so far. Add a directory here when its last inline handler goes.
    HANDLER_FREE = [
        'templates', 'apps/core/templates', 'apps/blog/templates',
        'apps/support_services/templates', 'apps/journal/templates', 'resources/templates',
    ]
    # Has its own policy (EMBED_CSP) because other sites frame it.
    OWN_POLICY = {'apps/core/templates/core/embed_calculator.html'}

    def _templates(self, roots):
        import glob
        from django.conf import settings
        for root in roots:
            for path in glob.glob(f'{settings.BASE_DIR}/{root}/**/*.html', recursive=True):
                rel = path[len(str(settings.BASE_DIR)) + 1:]
                if rel not in self.OWN_POLICY:
                    with open(path, encoding='utf-8') as f:
                        yield rel, f.read()

    def test_every_inline_script_carries_the_nonce(self):
        import re
        untagged = []
        for rel, source in self._templates(['templates', 'apps', 'resources']):
            for tag in re.findall(r'<script(?:\s[^>]*)?>', source):
                if 'src=' in tag or 'nonce="{{ csp_nonce }}"' in tag or 'application/ld+json' in tag:
                    continue
                untagged.append(f'{rel}: {tag}')
        self.assertEqual(untagged, [])

    def test_converted_templates_have_no_inline_handlers(self):
        import re
        found = []
        for rel, source in self._templates(self.HANDLER_FREE):
            # Any on*= attribute, whatever precedes it (a space, a newline, a template tag).
            found += [f'{rel}: {m}' for m in
                      re.findall(r'''(?<![\w-])on[a-z]{3,}\s*=\s*(?:"[^"]*"|'[^']*')''', source)]
        self.assertEqual(found, [])
