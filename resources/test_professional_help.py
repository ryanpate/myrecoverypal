"""Regression test: /resources/professional-help/ must render.

The page's JS fetches an optional facilities JSON that has never existed in
the repo and falls back to built-in sample data. Under
CompressedManifestStaticFilesStorage a {% static %} tag for a missing file
raises ValueError at render time — so the reference must be a literal URL,
not a manifest lookup (Sentry bdf2f07dfa4849af990b330463b420f4).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProfessionalHelpPageTests(TestCase):
    def test_page_renders_for_logged_in_user(self):
        user = User.objects.create_user(username="ph", password="x")
        self.client.force_login(user)
        resp = self.client.get(reverse("resources:professional_help"))
        self.assertEqual(resp.status_code, 200)
        # The optional data file is fetched by literal URL so the JS
        # fallback can handle its absence; a manifest lookup would 500.
        self.assertContains(
            resp, "/static/resources/data/my_facilities_example.json")
