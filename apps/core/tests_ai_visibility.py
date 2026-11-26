import json
import re

from django.test import TestCase


def _ld_blocks(html):
    return [json.loads(m) for m in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class LlmsTxtTest(TestCase):
    # Served by WhiteNoise from root_files/ (WHITENOISE_ROOT), like robots.txt.
    def test_llms_txt_is_plain_text_summary(self):
        resp = self.client.get('/llms.txt', secure=True, HTTP_HOST='www.myrecoverypal.com')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/plain', resp['Content-Type'])
        body = b''.join(resp.streaming_content).decode()
        self.assertTrue(body.startswith('# MyRecoveryPal'))
        self.assertIn('/court-ordered-meeting-tracker/', body)
        self.assertNotIn('noindex', resp.get('X-Robots-Tag', ''))


class OrganizationSchemaTest(TestCase):
    def test_organization_names_app_store_and_alternate_name(self):
        resp = self.client.get('/', secure=True, HTTP_HOST='www.myrecoverypal.com')
        org = next(b for b in _ld_blocks(resp.content.decode()) if b.get('@type') == 'Organization')
        self.assertIn('My Recovery Pal', org['alternateName'])
        self.assertIn('https://apps.apple.com/us/app/myrecoverypal/id6760084657', org['sameAs'])
