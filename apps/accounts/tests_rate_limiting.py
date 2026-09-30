# apps/accounts/tests_rate_limiting.py
"""RateLimitMiddleware: who gets counted, and what gets counted.

In production the request path is client -> Cloudflare -> Railway edge ->
gunicorn. Railway rewrites X-Forwarded-For so its first entry is the address
that connected to Railway (a Cloudflare edge node, or the client itself when
someone bypasses Cloudflare and hits the origin directly). The real visitor
is in CF-Connecting-IP, which is only trustworthy when the peer is Cloudflare.
"""
import io
import os
import subprocess
import sys
import tempfile

from django.conf import settings
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}

CF_EDGE_A = '172.71.172.125'   # inside Cloudflare's 172.64.0.0/13
CF_EDGE_B = '162.158.110.82'   # inside Cloudflare's 162.158.0.0/15
RAILWAY_EDGE = '79.127.178.82'


def via_cloudflare(client_ip, edge=CF_EDGE_A):
    return {'HTTP_X_FORWARDED_FOR': f'{edge}, {RAILWAY_EDGE}',
            'HTTP_CF_CONNECTING_IP': client_ip}


def direct_to_origin(peer_ip, forged_cf_ip):
    return {'HTTP_X_FORWARDED_FOR': f'{peer_ip}, {RAILWAY_EDGE}',
            'HTTP_CF_CONNECTING_IP': forged_cf_ip}


@override_settings(**_TEST_SETTINGS)
class LoginRateLimitTests(TestCase):
    LOGIN = '/accounts/login/'
    BAD = {'username': 'nobody', 'password': 'wrong-password'}

    def setUp(self):
        caches['rate_limiting'].clear()

    def _attempt(self, **headers):
        return self.client.post(self.LOGIN, self.BAD, **headers).status_code

    def test_sixth_failed_login_from_one_visitor_is_blocked(self):
        visitor = via_cloudflare('203.0.113.5')
        for _ in range(5):
            self.assertEqual(self._attempt(**visitor), 200)
        self.assertEqual(self._attempt(**visitor), 403)

    def test_visitors_behind_the_same_cloudflare_node_are_counted_separately(self):
        for _ in range(6):
            self._attempt(**via_cloudflare('203.0.113.5'))
        self.assertEqual(self._attempt(**via_cloudflare('198.51.100.9')), 200)

    def test_one_visitor_is_counted_across_cloudflare_nodes(self):
        for _ in range(5):
            self._attempt(**via_cloudflare('203.0.113.5', edge=CF_EDGE_A))
        self.assertEqual(
            self._attempt(**via_cloudflare('203.0.113.5', edge=CF_EDGE_B)), 403)

    def test_forged_cf_header_on_direct_origin_request_does_not_evade_limit(self):
        for i in range(5):
            self._attempt(**direct_to_origin('192.0.2.77', f'10.9.8.{i}'))
        self.assertEqual(
            self._attempt(**direct_to_origin('192.0.2.77', '10.9.8.200')), 403)

    def test_viewing_the_login_page_does_not_use_up_attempts(self):
        visitor = via_cloudflare('203.0.113.5')
        for _ in range(10):
            self.assertEqual(self.client.get(self.LOGIN, **visitor).status_code, 200)
        self.assertEqual(self._attempt(**visitor), 200)

    def test_admin_login_is_rate_limited(self):
        visitor = via_cloudflare('203.0.113.5')
        url = reverse('admin:login')
        for _ in range(5):
            self.assertEqual(self.client.post(url, self.BAD, **visitor).status_code, 200)
        self.assertEqual(self.client.post(url, self.BAD, **visitor).status_code, 403)


class RateLimitCacheSettingsTests(TestCase):
    def test_counters_are_shared_across_workers_when_redis_is_configured(self):
        """Per-process memory counters multiply the limit by the number of
        gunicorn workers and reset whenever a worker is recycled."""
        env = dict(os.environ, REDIS_URL='redis://default:pw@localhost:6379',
                   DJANGO_SETTINGS_MODULE='recovery_hub.settings')
        out = subprocess.run(
            [sys.executable, '-c',
             'from django.conf import settings;'
             'print("backend=" + settings.CACHES["rate_limiting"]["BACKEND"])'],
            cwd=settings.BASE_DIR, env=env, capture_output=True, text=True)
        self.assertIn('backend=django_redis.cache.RedisCache', out.stdout, out.stderr[-500:])


@override_settings(**_TEST_SETTINGS)
class SummernoteUploadAuthTests(TestCase):
    def _png(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), 'white').save(buf, format='PNG')
        return SimpleUploadedFile('a.png', buf.getvalue(), content_type='image/png')

    def test_anonymous_visitor_cannot_upload_attachments(self):
        with tempfile.TemporaryDirectory() as media:
            with self.settings(MEDIA_ROOT=media):
                resp = self.client.post(
                    '/summernote/upload_attachment/', {'files': [self._png()]})
        self.assertEqual(resp.status_code, 403)
