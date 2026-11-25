# apps/core/tests_landing_dark.py
"""The homepage must stay readable in dark mode.

The site-wide dark rules (`[data-theme="dark"] h1`, `[data-theme="dark"] a` in
main.css) outrank the landing page's `.ml-*` classes. Without its own night
block the hero headline rendered light grey on white and the signup button
blue on green for every visitor whose device is in dark mode."""
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LandingDarkModeTest(TestCase):

    def setUp(self):
        # The landing page's styles live in their own stylesheet
        self.html = self.client.get(reverse('core:index')).content.decode()
        self.css = (settings.BASE_DIR / 'static/css/pages/core__index.css').read_text()

    def test_page_links_its_stylesheet(self):
        self.assertIn('css/pages/core__index', self.html)

    def test_landing_redefines_its_surfaces_for_dark_mode(self):
        self.assertIn('[data-theme="dark"] .ml {', self.css)
        self.assertIn('--ml-surface-card:#141c2b', self.css)

    def test_signup_buttons_keep_white_text_in_dark_mode(self):
        self.assertIn('[data-theme="dark"] .ml a.ml-btn--primary', self.css)
        self.assertIn('[data-theme="dark"] .ml a.ml-btn--light', self.css)
