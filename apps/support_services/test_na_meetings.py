"""Narcotics Anonymous meetings: the BMLT import, and the NA hub pages.

NA rows share the Meeting table with AA but live in their own hub set under
/support/meetings/na/, and must never show up labelled as AA.
"""
from datetime import time
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services import meeting_sync
from apps.support_services.meeting_sync import (
    NA_SOURCE, _from_bmlt, _state_code, load_na_meetings, sync_all, sync_source,
)
from apps.support_services.models import Meeting


def bmlt_row(**overrides):
    row = {
        'id_bigint': '19546', 'published': '1', 'meeting_name': 'A Wake Up Call',
        'weekday_tinyint': '1', 'venue_type': '1', 'start_time': '09:30:00',
        'duration_time': '01:15:00', 'time_zone': '', 'formats': 'CL,SD,WC,O,D',
        'location_text': 'Community Hall', 'location_street': '809 S Washington St',
        'location_municipality': 'Denver', 'location_province': 'CO',
        'location_postal_code_1': '80209', 'latitude': '39.7018019',
        'longitude': '-104.9795471', 'service_body_name': 'Mile High',
        'virtual_meeting_link': '', 'virtual_meeting_additional_info': '',
        'phone_meeting_number': '', 'comments': '', 'location_info': 'Side door',
    }
    row.update(overrides)
    return row


class FromBmltTests(TestCase):
    def test_in_person_row(self):
        m = _from_bmlt(bmlt_row(), 'America/Denver', 'CO')
        self.assertEqual(m['slug'], 'a-wake-up-call-19546')
        self.assertEqual(m['day'], 0)  # BMLT 1 = Sunday = our 0
        self.assertEqual((m['time'], m['end_time']), ('09:30', '10:45'))
        self.assertEqual(m['attendance_option'], 'in_person')
        self.assertEqual(m['timezone'], 'America/Denver')
        self.assertEqual(m['formatted_address'], '809 S Washington St, Denver, CO 80209')
        self.assertEqual(m['types'], ['D', 'O', 'X'])
        self.assertEqual(m['notes'], 'Side door')

    def test_virtual_and_hybrid(self):
        online = _from_bmlt(bmlt_row(
            venue_type='2', location_street='', time_zone='America/Denver',
            virtual_meeting_link='https://zoom.us/j/1'), 'America/Chicago', None)
        self.assertEqual(online['attendance_option'], 'online')
        self.assertEqual(online['timezone'], 'America/Denver')
        hybrid = _from_bmlt(bmlt_row(venue_type='3'), 'America/Denver', 'CO')
        self.assertEqual(hybrid['attendance_option'], 'hybrid')

    def test_online_meeting_without_a_time_zone_is_skipped(self):
        """The aggregator returns worldwide virtual meetings; a guessed zone
        would send someone at the wrong hour."""
        row = bmlt_row(venue_type='2', location_street='', virtual_meeting_link='https://zoom.us/j/1')
        self.assertIsNone(_from_bmlt(row, 'America/Denver', 'CO'))

    def test_unusable_rows_are_skipped(self):
        for row in (
            bmlt_row(location_street=''),                       # in person, nowhere to go
            bmlt_row(published='0'),
            bmlt_row(meeting_name=''),
            bmlt_row(venue_type='2', location_street='', time_zone='America/Denver'),  # no way to join
        ):
            self.assertIsNone(_from_bmlt(row, 'America/Denver', 'CO'))

    def test_state_is_normalised_and_falls_back_to_the_area(self):
        self.assertEqual(_state_code('Ohio'), 'OH')
        self.assertEqual(_state_code('Il'), 'IL')
        self.assertEqual(_state_code('CO,'), 'CO')
        self.assertEqual(_state_code('Ontario'), '')
        self.assertEqual(_from_bmlt(bmlt_row(location_province=''), 'x', 'CA')['state'], 'CA')
        self.assertEqual(_from_bmlt(bmlt_row(location_province=''), 'x', None)['state'], '')


AREAS = [('one', 1, 1, 'America/Denver', 'CO'), ('two', 2, 2, 'America/Chicago', None)]


@patch.object(meeting_sync.time, 'sleep', lambda s: None)
class NaSyncTests(TestCase):
    def test_overlapping_areas_are_merged_on_meeting_id(self):
        with patch.object(meeting_sync, '_fetch_json', return_value=[bmlt_row()]):
            self.assertEqual(len(load_na_meetings(AREAS)), 1)

    def test_one_failed_area_fails_the_whole_load(self):
        """A partial list would deactivate the missing metro as 'vanished'."""
        calls = iter([[bmlt_row()], meeting_sync.FeedFetchError('down')])

        def fetch(url):
            result = next(calls)
            if isinstance(result, Exception):
                raise result
            return result

        with patch.object(meeting_sync, '_fetch_json', side_effect=fetch):
            with self.assertRaises(meeting_sync.FeedFetchError):
                load_na_meetings(AREAS)

    def test_sync_creates_na_rows_and_leaves_aa_alone(self):
        aa = Meeting.objects.create(
            name='AA Group', slug='mtg-denver-aa-group', program='AA',
            is_approved=True, is_active=True)
        rows = [bmlt_row(), bmlt_row(id_bigint='2', meeting_name='Clean & Serene', weekday_tinyint='3')]
        result = sync_source('na', lambda: [_from_bmlt(r, 'America/Denver', 'CO') for r in rows],
                             program='NA')
        self.assertEqual(result['created'], 2)
        m = Meeting.objects.get(slug='mtg-na-a-wake-up-call-19546')
        self.assertEqual((m.program, m.city, m.state, m.time), ('NA', 'Denver', 'CO', time(9, 30)))
        self.assertTrue(m.is_approved and m.is_group_primary)
        self.assertEqual(m.seo_title, 'A Wake Up Call \u2014 Sundays 9:30 AM Denver, CO NA Meeting')
        self.assertIn('is a free NA meeting in Denver, CO', m.seo_description)
        aa.refresh_from_db()
        self.assertTrue(aa.is_active)

    def test_vanished_na_rows_are_deactivated_but_not_aa(self):
        aa = Meeting.objects.create(
            name='AA Group', slug='mtg-nashville-aa-group', program='AA',
            is_approved=True, is_active=True)
        both = [bmlt_row(), bmlt_row(id_bigint='2', meeting_name='Clean & Serene')]
        sync_source('na', lambda: [_from_bmlt(r, 'x', 'CO') for r in both], program='NA')
        sync_source('na', lambda: [_from_bmlt(both[0], 'x', 'CO')], program='NA')
        self.assertFalse(Meeting.objects.get(slug='mtg-na-clean-serene-2').is_active)
        aa.refresh_from_db()
        self.assertTrue(aa.is_active)  # "mtg-nashville-" is not in the "mtg-na-" namespace

    def test_na_source_runs_through_sync_all(self):
        with patch.dict(NA_SOURCE, {'load': lambda: [_from_bmlt(bmlt_row(), 'x', 'CO')]}):
            results = sync_all([NA_SOURCE])
        self.assertEqual(results['na']['created'], 1)

    def test_na_only_run_leaves_legacy_aa_online_rows_active(self):
        """Regression: the first production --na run deactivated 1,535 legacy
        "online-<feed>-" AA rows, because the legacy cleanup treated every
        source it wasn't given as gone."""
        legacy = Meeting.objects.create(
            name='Perry Street Workshop', slug='online-nyintergroup-perry-street-workshop',
            program='AA', attendance_option='online', is_approved=True, is_active=True)
        with patch.dict(NA_SOURCE, {'load': lambda: [_from_bmlt(bmlt_row(), 'x', 'CO')]}):
            results = sync_all([NA_SOURCE])
        self.assertEqual(results['legacy_deactivated'], 0)
        legacy.refresh_from_db()
        self.assertTrue(legacy.is_active)


def make_na(city, state, n, **extra):
    return [
        Meeting.objects.create(
            name=f'{city} NA {i}', slug=f'mtg-na-{city.lower()}-{i}', program='NA',
            day=i % 7, time=time(19, 0), city=city, state=state,
            address=f'{i} Main St', attendance_option='in_person',
            is_approved=True, is_active=True, is_group_primary=True, **extra)
        for i in range(n)
    ]


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class NaHubTests(TestCase):
    def setUp(self):
        from apps.support_services.test_city_hubs import make_meetings
        make_na('Denver', 'CO', 4)
        make_meetings('Denver', 'CO', 3)

    def test_na_city_hub_lists_only_na(self):
        html = self.client.get('/support/meetings/na/co/denver/').content.decode()
        self.assertIn('<title>NA Meetings in Denver, CO', html)
        self.assertIn('<h1>NA Meetings in Denver, CO</h1>', html)
        self.assertIn('4 meetings in Denver', html)
        self.assertIn('NA regional meeting list', html)
        self.assertIn('rel="canonical" href="http://testserver/support/meetings/na/co/denver/"', html)
        self.assertNotIn('Denver Group 0', html)

    def test_aa_city_hub_excludes_na(self):
        html = self.client.get('/support/meetings/co/denver/').content.decode()
        self.assertIn('<h1>AA Meetings in Denver, CO</h1>', html)
        self.assertIn('3 meetings in Denver', html)
        self.assertNotIn('Denver NA 0', html)

    def test_na_state_hub_and_home(self):
        html = self.client.get('/support/meetings/na/co/').content.decode()
        self.assertIn('<h1>NA Meetings in Colorado</h1>', html)
        self.assertIn('href="/support/meetings/na/co/denver/"', html)
        home = self.client.get(reverse('support_services:na_home'))
        self.assertEqual(home.status_code, 200)
        html = home.content.decode()
        self.assertIn('<title>NA Meetings Near Me: Find Narcotics Anonymous Meetings</title>', html)
        self.assertIn('href="/support/meetings/na/co/denver/"', html)

    def test_na_home_renders_with_no_na_meetings(self):
        Meeting.objects.filter(program='NA').delete()
        self.assertEqual(self.client.get(reverse('support_services:na_home')).status_code, 200)
        self.assertEqual(self.client.get('/support/meetings/na/co/').status_code, 404)

    def test_detail_page_links_to_the_na_hub(self):
        m = Meeting.objects.filter(program='NA').first()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('href="/support/meetings/na/co/denver/"', html)
        self.assertIn('All NA meetings in Denver, CO', html)
        self.assertNotIn('Denver Group 0', html)  # "nearby" stays within the program

    def test_finder_program_filter_is_noindexed(self):
        resp = self.client.get(reverse('support_services:meeting_list'), {'program': 'NA'})
        self.assertEqual(resp['X-Robots-Tag'], 'noindex, nofollow')
        html = resp.content.decode()
        self.assertIn('Denver NA 0', html)
        self.assertNotIn('Denver Group 0', html)

    def test_sitemap_lists_na_hubs(self):
        from recovery_hub.sitemaps import CityHubSitemap, StateHubSitemap
        cities = [CityHubSitemap().location(c) for c in CityHubSitemap().items()]
        self.assertIn('/support/meetings/na/co/denver/', cities)
        self.assertIn('/support/meetings/co/denver/', cities)
        states = [StateHubSitemap().location(s) for s in StateHubSitemap().items()]
        self.assertIn('/support/meetings/na/co/', states)
