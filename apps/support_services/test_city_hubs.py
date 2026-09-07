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
