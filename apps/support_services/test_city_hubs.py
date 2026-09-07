"""City/state hub aggregation."""
from datetime import time

from django.test import TestCase

from apps.support_services.hubs import (
    MIN_MEETINGS_FOR_HUB, city_slug, hub_cities, hub_states, resolve_city,
)
from apps.support_services.models import Meeting


def make_meetings(city, state, n, **extra):
    for i in range(n):
        defaults = dict(
            name=f'{city} Group {i}', slug=f'mtg-t-{city}-{state}-{i}'.lower().replace(' ', '-'),
            day=i % 7, time=time(19, 0), attendance_option='in_person',
            city=city, state=state, is_approved=True, is_active=True,
        )
        defaults.update(extra)
        Meeting.objects.create(**defaults)


class CitySlugTests(TestCase):
    def test_spaces_and_case(self):
        self.assertEqual(city_slug('League City'), 'league-city')

    def test_punctuation(self):
        self.assertEqual(city_slug('St. Petersburg'), 'st-petersburg')

    def test_hyphenated_name(self):
        self.assertEqual(city_slug('Cornwall-On-Hudson'), 'cornwall-on-hudson')


class HubCitiesTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Weimar', 'TX', 1)      # below threshold
        make_meetings('Seattle', 'WA', 4)

    def test_only_cities_at_or_above_threshold(self):
        names = [c['city'] for c in hub_cities()]
        self.assertIn('Houston', names)
        self.assertIn('Katy', names)
        self.assertNotIn('Weimar', names)

    def test_threshold_is_inclusive(self):
        self.assertEqual(MIN_MEETINGS_FOR_HUB, 3)
        self.assertIn('Katy', [c['city'] for c in hub_cities()])

    def test_ordered_by_count_desc(self):
        counts = [c['count'] for c in hub_cities()]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_filtered_by_state(self):
        self.assertEqual([c['city'] for c in hub_cities('TX')], ['Houston', 'Katy'])

    def test_state_filter_is_case_insensitive(self):
        self.assertEqual(hub_cities('tx'), hub_cities('TX'))

    def test_carries_a_slug(self):
        houston = [c for c in hub_cities() if c['city'] == 'Houston'][0]
        self.assertEqual(houston['slug'], 'houston')

    def test_inactive_and_unapproved_are_excluded(self):
        make_meetings('Austin', 'TX', 4, is_active=False)
        make_meetings('Dallas', 'TX', 4, is_approved=False)
        names = [c['city'] for c in hub_cities()]
        self.assertNotIn('Austin', names)
        self.assertNotIn('Dallas', names)

    def test_meetings_without_a_city_are_ignored(self):
        make_meetings('', '', 5, attendance_option='online')
        self.assertNotIn('', [c['city'] for c in hub_cities()])


class HubStatesTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Seattle', 'WA', 4)
        make_meetings('Trenton', 'NJ', 1)     # no qualifying city

    def test_only_states_with_a_qualifying_city(self):
        codes = [s['state'] for s in hub_states()]
        self.assertIn('TX', codes)
        self.assertIn('WA', codes)
        self.assertNotIn('NJ', codes)

    def test_counts_are_over_qualifying_cities_only(self):
        tx = [s for s in hub_states() if s['state'] == 'TX'][0]
        self.assertEqual(tx['city_count'], 2)
        self.assertEqual(tx['count'], 8)


class ResolveCityTests(TestCase):
    def setUp(self):
        make_meetings('League City', 'TX', 3)
        make_meetings('Montgomery', 'TX', 3)
        make_meetings('Montgomery', 'NY', 3)

    def test_resolves_slug_to_stored_name(self):
        self.assertEqual(resolve_city('TX', 'league-city'), 'League City')

    def test_same_slug_in_two_states_resolves_independently(self):
        self.assertEqual(resolve_city('TX', 'montgomery'), 'Montgomery')
        self.assertEqual(resolve_city('NY', 'montgomery'), 'Montgomery')

    def test_unknown_slug_returns_none(self):
        self.assertIsNone(resolve_city('TX', 'nowhere'))

    def test_below_threshold_city_does_not_resolve(self):
        make_meetings('Weimar', 'TX', 1)
        self.assertIsNone(resolve_city('TX', 'weimar'))


from django.test import override_settings                                # noqa: E402
from django.urls import reverse                                          # noqa: E402


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CityHubViewTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Weimar', 'TX', 1)
        self.url = reverse('support_services:city_hub',
                           kwargs={'state': 'tx', 'city_slug': 'houston'})

    def test_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_lists_the_city_meetings(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Houston Group 0', html)

    def test_title_targets_the_local_query(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('<title>AA Meetings in Houston, TX', html)

    def test_description_is_specific_not_boilerplate(self):
        html = self.client.get(self.url).content.decode()
        self.assertNotIn('Free recovery community. Track milestones', html)
        self.assertIn('Houston, TX', html)

    def test_canonical_is_self(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('/support/meetings/tx/houston/"', html)

    def test_links_to_its_state_hub(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn(reverse('support_services:state_hub',
                              kwargs={'state': 'tx'}), html)

    def test_below_threshold_city_404s(self):
        url = reverse('support_services:city_hub',
                      kwargs={'state': 'tx', 'city_slug': 'weimar'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_city_404s(self):
        url = reverse('support_services:city_hub',
                      kwargs={'state': 'tx', 'city_slug': 'atlantis'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_uppercase_state_in_url_still_resolves(self):
        self.assertEqual(self.client.get('/support/meetings/TX/houston/').status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class StateHubViewTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Weimar', 'TX', 1)
        self.url = reverse('support_services:state_hub', kwargs={'state': 'tx'})

    def test_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_lists_qualifying_cities_with_links(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Houston', html)
        self.assertIn('/support/meetings/tx/houston/', html)
        self.assertIn('/support/meetings/tx/katy/', html)

    def test_title_names_the_state(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('<title>AA Meetings in Texas', html)

    def test_state_with_no_qualifying_city_404s(self):
        make_meetings('Trenton', 'NJ', 1)
        url = reverse('support_services:state_hub', kwargs={'state': 'nj'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_meeting_detail_slug_route_still_works(self):
        """The 2-letter state route must not swallow meeting detail URLs."""
        m = Meeting.objects.filter(city='Houston').first()
        self.assertEqual(self.client.get(m.get_absolute_url()).status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DetailBacklinkTests(TestCase):
    def test_detail_page_links_to_its_city_hub(self):
        make_meetings('Houston', 'TX', 4)
        m = Meeting.objects.filter(city='Houston').first()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('/support/meetings/tx/houston/', html)

    def test_no_backlink_when_city_is_below_threshold(self):
        make_meetings('Weimar', 'TX', 1)
        m = Meeting.objects.get(city='Weimar')
        self.assertEqual(m.city_hub_url, '')

    def test_no_backlink_for_an_online_meeting(self):
        Meeting.objects.create(
            name='Online One', slug='mtg-t-online-1',
            attendance_option='online', conference_url='https://zoom.us/j/1',
            is_approved=True, is_active=True)
        self.assertEqual(Meeting.objects.get(slug='mtg-t-online-1').city_hub_url, '')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class HubSitemapTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Weimar', 'TX', 1)

    def test_city_hub_is_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/support/meetings/tx/houston/</loc>', xml)

    def test_state_hub_is_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/support/meetings/tx/</loc>', xml)

    def test_below_threshold_city_is_not_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/support/meetings/tx/weimar/', xml)
