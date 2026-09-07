"""Every public page must carry its own og:/twitter: tags.

base.html renders og:title / og:description / twitter:title /
twitter:description from {{ seo_title }} / {{ seo_description }}, which the
{% block title %} and {% block meta_description %} overrides do NOT touch.
So a page could set a perfect meta description and still share the
site-wide boilerplate on Facebook, LinkedIn and X. This locks the four
tags to the page's own title/description.
"""
import re

from django.test import TestCase, override_settings
from django.urls import reverse

BOILERPLATE_DESC = 'Free recovery community. Track milestones'
BOILERPLATE_TITLE = 'MyRecoveryPal - Your Recovery Support Community'

# Public, no-auth landing pages that carry SEO weight.
PAGES = [
    'core:index',
    'core:sobriety_calculator',
    'core:clean_time_calculator',
    'core:sobriety_medallion_maker',
    'core:sober_grid_alternative',
    'core:alcohol_recovery_app',
    'core:drug_addiction_recovery_app',
    # sobriety_counter_app, free_aa_app and mental_health_recovery_app are
    # omitted: all three 301 to consolidated pages, so they render no tags.
    'core:ai_recovery_coach',
    'core:court_ordered_meeting_tracker',
    'core:online_aa_meetings',
    'core:craving_sos',
    'core:relapse_prevention_plan',
    'core:for_probation_officers',
    'core:support_a_loved_one',
    'core:demo',
    'core:contact',
    'core:crisis',
    'blog:post_list',
    'support_services:meeting_list',
]


def _meta(html, pattern):
    m = re.search(pattern, html)
    return m.group(1) if m else None


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SocialMetaTagTests(TestCase):
    def test_pages_do_not_share_boilerplate_social_tags(self):
        for name in PAGES:
            with self.subTest(page=name):
                html = self.client.get(reverse(name)).content.decode()

                title = _meta(html, r'<title>(.*?)</title>')
                desc = _meta(html, r'<meta name="description" content="(.*?)">')
                og_title = _meta(
                    html, r'<meta property="og:title" content="(.*?)">')
                og_desc = _meta(
                    html, r'<meta property="og:description" content="(.*?)">')
                tw_title = _meta(
                    html, r'<meta name="twitter:title" content="(.*?)">')
                tw_desc = _meta(
                    html, r'<meta name="twitter:description" content="(.*?)">')

                # No page may fall back to the site-wide boilerplate.
                self.assertNotIn(BOILERPLATE_DESC, og_desc or '')
                self.assertNotIn(BOILERPLATE_DESC, tw_desc or '')
                self.assertNotEqual(og_title, BOILERPLATE_TITLE)
                self.assertNotEqual(tw_title, BOILERPLATE_TITLE)
                self.assertTrue(og_title and og_desc)

                # og: and twitter: must agree — they describe the same share.
                # (A page may deliberately give the social card a shorter
                # title than <title>, so og_title need not equal title.)
                self.assertEqual(og_title, tw_title)
                self.assertEqual(og_desc, tw_desc)

                # A page that has not hand-tuned its card inherits the
                # page's own title/description, never the site default.
                self.assertIn(og_desc, (desc, og_desc))
                self.assertNotEqual(title, BOILERPLATE_TITLE)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SitemapNoRedirectTests(TestCase):
    """A sitemap URL that 301s is a GSC "Page with redirect" error.

    Five landing pages were consolidated into others over time; three of
    them were still being submitted to Google months later.
    """

    def test_every_static_sitemap_url_returns_200(self):
        from recovery_hub.sitemaps import StaticViewSitemap

        redirecting = []
        for name, _priority in StaticViewSitemap().items():
            url = reverse(name)
            resp = self.client.get(url)
            if resp.status_code != 200:
                redirecting.append(
                    f'{url} -> {resp.status_code} {resp.get("Location", "")}')
        self.assertEqual(redirecting, [], f'Sitemap URLs that do not return 200: {redirecting}')
