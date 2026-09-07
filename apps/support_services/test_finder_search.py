"""Meeting finder search, and template comments that must not render.

Reported from production: searching a ZIP code returned nothing even for
ZIPs we hold data for, and a Django template comment was rendering as
visible body text on the finder and on all 6,451 detail pages.
"""
from datetime import time

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting


def make_meeting(**extra):
    defaults = dict(
        name='Daily Bread Group', slug='mtg-t-daily-bread',
        day=1, time=time(6, 0), attendance_option='in_person',
        location='Bay Area Club',
        formatted_address='2111 Webster St, League City, TX 77573, USA',
        address='2111 Webster St', city='League City', state='TX',
        postal_code='77573', is_approved=True, is_active=True,
    )
    defaults.update(extra)
    return Meeting.objects.create(**defaults)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FinderSearchTests(TestCase):
    def setUp(self):
        make_meeting()
        self.url = reverse('support_services:meeting_list')

    def _results(self, q):
        return self.client.get(self.url, {'q': q}).context['meetings']

    def test_search_by_postal_code(self):
        self.assertEqual(len(self._results('77573')), 1)

    def test_search_by_partial_postal_code(self):
        self.assertEqual(len(self._results('775')), 1)

    def test_search_by_city(self):
        self.assertEqual(len(self._results('League City')), 1)

    def test_search_by_street_address(self):
        self.assertEqual(len(self._results('Webster St')), 1)

    def test_search_by_state_code(self):
        self.assertEqual(len(self._results('TX')), 1)

    def test_search_by_name_still_works(self):
        self.assertEqual(len(self._results('Daily Bread')), 1)

    def test_search_by_location_still_works(self):
        self.assertEqual(len(self._results('Bay Area Club')), 1)

    def test_unrelated_query_returns_nothing(self):
        self.assertEqual(len(self._results('62704')), 0)

    def test_state_match_is_exact_not_substring(self):
        """state__icontains would make a 2-letter query match half the
        directory — 'in' matching Indiana plus every name containing 'in'."""
        make_meeting(slug='mtg-t-indiana', name='Indiana Group',
                     city='Indianapolis', state='IN', postal_code='46201',
                     formatted_address='1 Main St, Indianapolis, IN 46201')
        results = self._results('IN')
        self.assertEqual([m.state for m in results], ['IN'])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class TemplateCommentTests(TestCase):
    """Django's {# #} is single-line only. A multi-line one renders as
    visible body text — it was showing on the finder and on every meeting
    detail page. Use {% comment %} for anything spanning lines."""

    def test_finder_does_not_leak_a_template_comment(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertNotIn('{#', html)
        self.assertNotIn('#}', html)
        self.assertNotIn('Contextual Court Compliance nudge', html)

    def test_detail_page_does_not_leak_a_template_comment(self):
        m = make_meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertNotIn('{#', html)
        self.assertNotIn('#}', html)
        self.assertNotIn('Court Compliance CTA for a single meeting page', html)

    def test_city_hub_does_not_leak_a_template_comment(self):
        for i in range(3):
            make_meeting(slug=f'mtg-t-lc-{i}', name=f'LC Group {i}')
        html = self.client.get('/support/meetings/tx/league-city/').content.decode()
        self.assertNotIn('{#', html)
        self.assertNotIn('#}', html)
