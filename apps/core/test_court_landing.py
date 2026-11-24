"""The court landing page leads with free logging, not the $29.99 plan.

Since 2026-09-26 logging is free and a single verified report is $9.99, but
the page kept selling only the monthly plan: in the month after, no new user
logged a court meeting.
"""
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtLandingTests(TestCase):
    def setUp(self):
        self.html = self.client.get(reverse('core:court_ordered_meeting_tracker')).content.decode()

    def test_primary_cta_is_free_logging_via_signup(self):
        signup = f"{reverse('accounts:register')}?next={reverse('accounts:court_attendance_create')}"
        # Everything above the first section heading: title, lead, button, note.
        hero = self.html[self.html.index('<h1'):self.html.index('<h2', self.html.index('<h1'))]
        self.assertIn(signup, hero)
        self.assertIn('Start logging meetings free', hero)
        self.assertNotIn('/mo', hero)

    def test_single_report_price_is_shown(self):
        self.assertIn('$9.99', self.html)
        self.assertIn('Pay only for what your court needs', self.html)

    def test_meta_description_leads_with_free(self):
        self.assertIn('name="description" content="Log court-ordered AA, NA or SMART meetings free', self.html)

    def test_chair_faq_describes_the_shipped_qr_flow(self):
        self.assertNotIn('on the roadmap', self.html)
        self.assertIn('one-time QR code', self.html)

    def test_page_makes_no_claim_about_what_courts_must_allow(self):
        lowered = self.html.lower()
        self.assertNotIn('constitutionally', lowered)
        self.assertNotIn('cannot mandate', lowered)
        self.assertNotIn('perjury', lowered)

    def test_page_does_not_promise_an_android_app(self):
        # base.html mentions Android in its own meta tags, so look at the page body only.
        page = self.html[self.html.index('<div class="cmt">'):self.html.index('court_signup_click')]
        self.assertNotIn('Android', page)

    def test_page_shows_the_real_report_and_chair_screen(self):
        self.assertIn('images/court/sample-report', self.html)
        self.assertIn('images/court/chair-confirm', self.html)
        self.assertIn('made-up details', self.html)
