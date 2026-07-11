"""Tests for the /relapse-prevention-plan/ SEO landing page."""
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RelapsePlanLandingTests(TestCase):
    def test_renders_with_template_preview_and_schema(self):
        resp = self.client.get(reverse("core:relapse_prevention_plan"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '"@type": "FAQPage"')
        # The six template sections are previewed on the page
        for section in ("My triggers", "early warning signs",
                        "Coping strategies", "support contacts",
                        "reasons for recovery", "emergency steps"):
            self.assertContains(resp, section)
        self.assertContains(resp, "988")

    def test_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/relapse-prevention-plan/")

    def test_anonymous_nav_links_to_landing_page(self):
        resp = self.client.get(reverse("core:relapse_prevention_plan"))
        self.assertContains(
            resp, 'href="' + reverse("core:relapse_prevention_plan") + '"')
