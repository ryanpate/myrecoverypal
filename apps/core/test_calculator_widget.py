"""Embeddable calculator widget: the iframe page and the page that hands out the code."""
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.views import WIDGETS, widget_embed_code


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EmbedPageTests(TestCase):
    def _get(self, slug='sobriety-calculator'):
        return self.client.get(reverse('core:embed_calculator', args=[slug]))

    def test_both_calculators_render_standalone(self):
        for slug, widget in WIDGETS.items():
            html = self._get(slug).content.decode()
            self.assertIn(f'<h1>{widget["title"]}</h1>', html)
            self.assertIn(f"var KIND = '{widget['kind']}';", html)
            self.assertNotIn('<nav', html)           # not the site shell
            self.assertNotIn('googletagmanager', html)

    def test_any_site_may_frame_it_and_it_loads_nothing_external(self):
        resp = self._get()
        self.assertNotIn('X-Frame-Options', resp)
        csp = resp['Content-Security-Policy']
        self.assertIn('frame-ancestors *', csp)
        self.assertIn("default-src 'none'", csp)
        html = resp.content.decode()
        self.assertNotIn('<link rel="stylesheet"', html)
        self.assertNotIn('<script src', html)

    def test_it_sets_no_cookies_and_stays_out_of_the_index(self):
        resp = self._get()
        self.assertFalse(resp.cookies)
        self.assertIn('noindex', resp['X-Robots-Tag'])
        self.assertIn('<link rel="canonical" href="https://www.myrecoverypal.com/sobriety-calculator/">',
                      resp.content.decode())

    def test_links_open_outside_the_frame_with_referral_tags(self):
        html = self._get('clean-time-calculator').content.decode()
        self.assertIn('href="https://www.myrecoverypal.com/clean-time-calculator/'
                      '?utm_source=widget&amp;utm_medium=embed&amp;utm_campaign=clean"', html)
        self.assertEqual(html.count('target="_blank" rel="noopener"'), 2)

    def test_unknown_widget_is_404(self):
        self.assertEqual(self._get('medallion').status_code, 404)

    def test_the_rest_of_the_site_still_refuses_framing(self):
        resp = self.client.get(reverse('core:sobriety_calculator'))
        self.assertIn("frame-ancestors 'none'", resp['Content-Security-Policy'])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WidgetPageTests(TestCase):
    def test_embed_code_is_an_iframe_plus_a_plain_credit_link(self):
        code = widget_embed_code('sobriety-calculator')
        self.assertIn('<iframe src="https://www.myrecoverypal.com/embed/sobriety-calculator/"', code)
        self.assertIn('Sobriety Calculator by <a href="https://www.myrecoverypal.com/sobriety-calculator/">'
                      'MyRecoveryPal</a>', code)
        self.assertNotIn('<script', code)

    def test_page_shows_preview_and_escaped_code_for_both(self):
        html = self.client.get(reverse('core:calculator_widget')).content.decode()
        self.assertIn('<title>Free Sobriety Calculator Widget for Your Website</title>', html)
        for slug in WIDGETS:
            self.assertIn(f'<iframe src="/embed/{slug}/"', html)                       # live preview
            self.assertIn(f'&lt;iframe src=&quot;https://www.myrecoverypal.com/embed/{slug}/&quot;', html)

    def test_linked_from_both_calculators_and_the_sitemap(self):
        url = reverse('core:calculator_widget')
        for page in ('core:sobriety_calculator', 'core:clean_time_calculator'):
            self.assertContains(self.client.get(reverse(page)), f'href="{url}"')
        self.assertContains(self.client.get('/sitemap.xml'), f'{url}</loc>')
