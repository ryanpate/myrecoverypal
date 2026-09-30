# apps/accounts/tests_static_cache.py
"""WHITENOISE_MAX_AGE applies only to files WITHOUT a content hash in their
name (robots.txt, ads.txt and other root_files, unhashed /static/ paths).
Hashed files are always served immutable regardless. At one year, an edited
robots.txt stayed cached at Cloudflare and never reached crawlers."""
from django.conf import settings
from django.test import SimpleTestCase


class UnhashedFileCacheTests(SimpleTestCase):
    def test_unhashed_files_are_not_cached_for_more_than_an_hour(self):
        self.assertLessEqual(settings.WHITENOISE_MAX_AGE, 3600)
