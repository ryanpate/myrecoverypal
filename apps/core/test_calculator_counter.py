"""Calculator -> counter: the save CTA on both calculators.

Anonymous visitors go to signup with their date carried; signed-in members
without a date can save it in one tap; members who already have a counter
are sent to it rather than pitched an account they already have.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()
PAGES = ('core:sobriety_calculator', 'core:clean_time_calculator')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CalculatorSaveCounterTests(TestCase):
    def _get(self, page):
        return self.client.get(reverse(page))

    def test_anonymous_visitor_gets_signup_that_carries_the_date(self):
        for page in PAGES:
            with self.subTest(page=page):
                resp = self._get(page)
                self.assertContains(resp, 'Save my counter: free')
                self.assertContains(
                    resp, f'href="{reverse("accounts:register")}" class="cta-button js-carry-date" id="calc-save-btn"')
                self.assertContains(resp, 'window.mrpCalcResult(date, totalDays, next)')

    def test_member_without_a_date_saves_it_in_one_tap(self):
        self.client.force_login(User.objects.create_user('nodate', 'n@example.com', 'pw'))
        for page in PAGES:
            with self.subTest(page=page):
                resp = self._get(page)
                self.assertContains(resp, f'action="{reverse("accounts:set_sobriety_date")}"')
                self.assertContains(resp, 'Save this date to my counter')
                self.assertNotContains(resp, 'id="calc-save-btn" class')

    def test_member_with_a_counter_is_sent_to_it(self):
        user = User.objects.create_user('hasdate', 'h@example.com', 'pw')
        user.sobriety_date = date(2026, 1, 1)
        user.save()
        self.client.force_login(user)
        for page in PAGES:
            with self.subTest(page=page):
                resp = self._get(page)
                self.assertContains(resp, 'Open my counter')
                self.assertContains(resp, f'href="{reverse("accounts:progress")}"')
                self.assertNotContains(resp, 'Save my counter: free')

    def test_calculator_pages_report_only_entered_dates(self):
        # The demo render must not call mrpCalcResult; entered/remembered dates do.
        for page in PAGES:
            with self.subTest(page=page):
                html = self._get(page).content.decode()
                demo = html[html.index('// Show 90-day demo'):]
                self.assertNotIn('reportResult(', demo[:400])
                self.assertIn("urlParams.get('date') || window.mrpCalcSavedDate()", html)
