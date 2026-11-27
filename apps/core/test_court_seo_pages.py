"""Court SEO pages: printable attendance sheet + online proof-of-attendance guide."""
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.views import _attendance_sheet_pdf_bytes


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class AttendanceSheetPageTests(TestCase):

    def test_page_offers_the_pdf_and_the_tracker(self):
        resp = self.client.get(reverse('core:court_attendance_sheet'))
        self.assertContains(resp, reverse('core:court_attendance_sheet_pdf'))
        self.assertContains(resp, '"@type": "FAQPage"')
        # Anonymous visitors go straight to signup with the logging form next.
        self.assertContains(resp, reverse('accounts:register') + '?next=' + reverse('accounts:court_attendance_create'))

    def test_report_price_is_hidden_in_the_ios_app(self):
        resp = self.client.get(reverse('core:court_attendance_sheet'))
        self.assertContains(resp, '<span class="stripe-only">A verified report is $')

    def test_pdf_downloads(self):
        _attendance_sheet_pdf_bytes.cache_clear()
        resp = self.client.get(reverse('core:court_attendance_sheet_pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class OnlineProofPageTests(TestCase):

    def test_page_renders_with_faq_and_links(self):
        resp = self.client.get(reverse('core:online_meeting_proof'))
        self.assertContains(resp, '"@type": "FAQPage"')
        self.assertContains(resp, reverse('core:online_aa_meetings'))
        self.assertContains(resp, reverse('core:court_attendance_sheet'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtSeoLinkingTests(TestCase):

    def test_pages_are_in_the_sitemap(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/court-ordered-meeting-attendance-sheet/', xml)
        self.assertIn('/online-meetings-proof-of-attendance/', xml)

    def test_court_landing_links_both_pages(self):
        resp = self.client.get(reverse('core:court_ordered_meeting_tracker'))
        self.assertContains(resp, reverse('core:court_attendance_sheet'))
        self.assertContains(resp, reverse('core:online_meeting_proof'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgramPartnerPageTests(TestCase):

    def test_page_renders_and_is_linked(self):
        resp = self.client.get(reverse('core:for_recovery_programs'))
        self.assertContains(resp, 'Nothing for your program')
        self.assertContains(resp, '<span class="stripe-only">A member pays $')
        self.assertContains(self.client.get(reverse('core:court_ordered_meeting_tracker')),
                            reverse('core:for_recovery_programs'))
        self.assertIn('/for-sober-living-and-dui-programs/', self.client.get('/sitemap.xml').content.decode())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProbationProofGuideTests(TestCase):

    def test_page_renders_comparison_and_faq(self):
        resp = self.client.get(reverse('core:probation_proof_guide'))
        self.assertContains(resp, '"@type": "FAQPage"')
        for name in ('12 Step Online', 'Cope Compass', 'My Meeting Card', 'MeetingMaker'):
            self.assertContains(resp, name)
        self.assertContains(resp, reverse('accounts:register') + '?next=' + reverse('accounts:court_attendance_create'))

    def test_where_it_runs_row_lists_the_android_apps(self):
        resp = self.client.get(reverse('core:probation_proof_guide'))
        self.assertContains(resp, '<td>Web and Android</td>')        # Cope Compass
        self.assertContains(resp, '<td>iPhone and Android</td>')     # MeetingMaker
        self.assertContains(resp, 'play.google.com/store/apps/details?id=com.copecompass.app')
        self.assertContains(resp, 'play.google.com/store/apps/details?id=com.girlcode.meetingmaker')

    def test_report_price_is_hidden_in_the_ios_app(self):
        resp = self.client.get(reverse('core:probation_proof_guide'))
        self.assertContains(resp, '<span class="stripe-only"> A report is $')

    def test_page_is_linked_and_in_the_sitemap(self):
        url = reverse('core:probation_proof_guide')
        self.assertIn(url, self.client.get('/sitemap.xml').content.decode())
        self.assertContains(self.client.get(reverse('core:court_ordered_meeting_tracker')), url)
        self.assertContains(self.client.get(reverse('core:online_meeting_proof')), url)
