# apps/core/tests_landing_counter.py
"""The homepage hero lets a visitor start their day counter before signing up.

The calculators convert because the visitor sees their own number first and
"Save my counter" carries the date into signup. The homepage used to open with
a generic pitch and a screenshot of someone else's count."""
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LandingHeroCounterTest(TestCase):

    def setUp(self):
        self.html = self.client.get(reverse('core:index')).content.decode()
        start = self.html.index('id="ml-count"')
        self.widget = self.html[start:self.html.index('<ul class="ml-trust">')]

    def test_hero_has_a_date_input_and_a_day_one_button(self):
        self.assertIn('type="date" id="ml-count-date"', self.widget)
        self.assertIn('id="ml-count-today"', self.widget)

    def test_signup_button_carries_the_entered_date(self):
        self.assertIn(
            f'href="{reverse("accounts:register")}" id="ml-count-cta"', self.widget)
        self.assertIn('js-carry-date', self.widget)
        self.assertIn("searchParams.set('sobriety_date'", self.html)

    def test_date_and_spend_are_shared_with_the_calculators_and_pricing(self):
        # Same localStorage keys, so the pricing page's "days of what you used
        # to spend" line is already filled in when they get there.
        self.assertIn("'mrpCalcDate'", self.html)
        self.assertIn("'mrpCalcSpend'", self.html)

    def test_premium_line_is_hidden_in_the_ios_app_and_has_no_hardcoded_price(self):
        self.assertIn('class="ml-count-premium stripe-only"', self.widget)
        self.assertIn(reverse('accounts:pricing'), self.widget)
        self.assertNotIn('59.99', self.widget.replace('data-yearly="59.99"', ''))

    def test_text_comes_before_the_phone_on_small_screens(self):
        css = (settings.BASE_DIR / 'static/css/pages/core__index.css').read_text()
        self.assertIn('.ml-hero-inner', css)  # guards against reading the wrong file
        self.assertNotIn('.ml-hero-media { order:-1; }', css)
