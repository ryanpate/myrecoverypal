"""JSON-LD on meeting pages and hubs, and the sectioned sitemap index."""
import json
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting
from apps.support_services.schema import _next_start, ld_json


def _meeting(**kwargs):
    defaults = dict(
        name='Grateful Hearts', slug='grateful-hearts',
        day=4, time=time(19, 0), timezone='America/Chicago',
        attendance_option='in_person', location='First Church',
        address='100 Main St', city='Houston', state='TX', postal_code='77002',
        is_approved=True, is_active=True,
    )
    defaults.update(kwargs)
    return Meeting.objects.create(**defaults)


def _blocks(resp):
    html = resp.content.decode()
    found = []
    for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        data = json.loads(raw)
        found += data if isinstance(data, list) else [data]
    return {b.get('@type'): b for b in found}


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingEventSchemaTests(TestCase):

    def test_in_person_meeting_is_a_weekly_offline_event(self):
        _meeting()
        event = _blocks(self.client.get('/support/meetings/grateful-hearts/'))['Event']
        self.assertEqual(event['name'], 'Grateful Hearts')
        self.assertEqual(event['eventAttendanceMode'], 'https://schema.org/OfflineEventAttendanceMode')
        self.assertEqual(event['location']['@type'], 'Place')
        self.assertEqual(event['location']['address']['addressLocality'], 'Houston')
        self.assertEqual(event['eventSchedule'][0]['byDay'], 'https://schema.org/Thursday')
        self.assertEqual(event['eventSchedule'][0]['repeatFrequency'], 'P1W')
        self.assertTrue(event['isAccessibleForFree'])

    def test_online_meeting_never_puts_the_zoom_link_in_schema(self):
        _meeting(slug='zoom-one', attendance_option='online', city='', state='',
                 address='', location='', postal_code='',
                 conference_url='https://zoom.us/j/123456')
        resp = self.client.get('/support/meetings/zoom-one/')
        event = _blocks(resp)['Event']
        self.assertEqual(event['location']['@type'], 'VirtualLocation')
        self.assertTrue(event['location']['url'].endswith('/support/meetings/zoom-one/'))
        self.assertNotIn('zoom.us', json.dumps(event))

    def test_hybrid_meeting_has_both_locations(self):
        _meeting(slug='hybrid-one', attendance_option='hybrid',
                 conference_url='https://zoom.us/j/1')
        event = _blocks(self.client.get('/support/meetings/hybrid-one/'))['Event']
        self.assertEqual([l['@type'] for l in event['location']], ['Place', 'VirtualLocation'])

    def test_numeric_group_is_not_used_as_organizer(self):
        _meeting(slug='numbered', group='2209', program='AA')
        event = _blocks(self.client.get('/support/meetings/numbered/'))['Event']
        self.assertEqual(event['organizer']['name'], 'Alcoholics Anonymous')

    def test_named_group_is_the_organizer(self):
        _meeting(slug='named', group='Sunrise Group')
        event = _blocks(self.client.get('/support/meetings/named/'))['Event']
        self.assertEqual(event['organizer']['name'], 'Sunrise Group')

    def test_event_has_googles_recommended_fields(self):
        _meeting(slug='full', group='Sunrise Group', program='AA')
        event = _blocks(self.client.get('/support/meetings/full/'))['Event']
        self.assertTrue(event['image'][0].startswith('https://'))
        self.assertIn('validFrom', event['offers'])
        self.assertEqual(event['performer']['name'], 'Sunrise Group')
        self.assertEqual(event['organizer']['url'], 'https://www.aa.org/')
        # No end time in the feed -> an hour after the start.
        start = datetime.fromisoformat(event['startDate'])
        self.assertEqual(datetime.fromisoformat(event['endDate']) - start, timedelta(hours=1))

    def test_group_website_is_the_organizer_url(self):
        _meeting(slug='site', website='https://sunrisegroup.org/')
        event = _blocks(self.client.get('/support/meetings/site/'))['Event']
        self.assertEqual(event['organizer']['url'], 'https://sunrisegroup.org/')

    def test_end_time_past_midnight_ends_the_next_day(self):
        _meeting(slug='late', time=time(23, 30), end_time=time(0, 30))
        event = _blocks(self.client.get('/support/meetings/late/'))['Event']
        start = datetime.fromisoformat(event['startDate'])
        self.assertEqual(datetime.fromisoformat(event['endDate']) - start, timedelta(hours=1))

    def test_no_event_without_a_start_time(self):
        _meeting(slug='no-time', time=None)
        blocks = _blocks(self.client.get('/support/meetings/no-time/'))
        self.assertNotIn('Event', blocks)
        self.assertIn('BreadcrumbList', blocks)

    def test_feed_text_cannot_break_out_of_the_script_tag(self):
        _meeting(slug='evil', name='Bad </script><script>alert(1)</script>')
        html = self.client.get('/support/meetings/evil/').content.decode()
        self.assertNotIn('<script>alert(1)', html)
        self.assertIn('Bad </script>', json.loads(ld_json({'n': 'Bad </script>'}))['n'])

    def test_next_start_is_the_coming_weekday_in_meeting_time(self):
        m = Meeting(day=4, time=time(19, 0), timezone='America/Chicago')  # Thursday
        tz = ZoneInfo('America/Chicago')
        start = _next_start(m, now=datetime(2026, 11, 24, 12, 0, tzinfo=tz))  # a Tuesday
        self.assertEqual(start.isoformat(), '2026-11-26T19:00:00-06:00')
        # Already started this week -> next week.
        start = _next_start(m, now=datetime(2026, 11, 26, 20, 0, tzinfo=tz))
        self.assertEqual(start.date().isoformat(), '2026-12-03')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class HubSchemaTests(TestCase):
    def setUp(self):
        for i in range(3):
            _meeting(name=f'Houston Group {i}', slug=f'houston-{i}', day=i)

    def test_city_hub_lists_its_meetings_with_breadcrumbs(self):
        blocks = _blocks(self.client.get('/support/meetings/tx/houston/'))
        self.assertEqual(blocks['ItemList']['numberOfItems'], 3)
        self.assertEqual([c['name'] for c in blocks['BreadcrumbList']['itemListElement']],
                         ['Meetings', 'Texas', 'Houston'])

    def test_state_hub_lists_its_cities(self):
        blocks = _blocks(self.client.get('/support/meetings/tx/'))
        self.assertEqual([i['name'] for i in blocks['ItemList']['itemListElement']], ['Houston'])

    def test_detail_breadcrumbs_run_through_the_city_hub(self):
        blocks = _blocks(self.client.get('/support/meetings/houston-0/'))
        self.assertEqual([c['name'] for c in blocks['BreadcrumbList']['itemListElement']],
                         ['Meetings', 'Texas', 'Houston', 'Houston Group 0'])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SitemapIndexTests(TestCase):

    def test_index_lists_every_section_on_the_real_domain(self):
        from recovery_hub.sitemaps import sitemaps
        xml = self.client.get('/sitemap-index.xml').content.decode()
        self.assertIn('<sitemapindex', xml)
        for name in sitemaps:
            self.assertIn(f'<loc>https://www.myrecoverypal.com/sitemap-{name}.xml</loc>', xml)

    def test_section_serves_only_its_urls(self):
        _meeting()
        resp = self.client.get(reverse('sitemap-section', kwargs={'section': 'meetings'}))
        self.assertEqual(resp.status_code, 200)
        xml = resp.content.decode()
        self.assertIn('/support/meetings/grateful-hearts/', xml)
        self.assertNotIn('/sobriety-calculator/', xml)

    def test_unknown_section_404s(self):
        self.assertEqual(self.client.get('/sitemap-nope.xml').status_code, 404)

    def test_robots_points_at_the_index(self):
        resp = self.client.get('/robots.txt')  # served by WhiteNoise (streaming)
        body = b''.join(resp.streaming_content).decode()
        self.assertIn('Sitemap: https://www.myrecoverypal.com/sitemap-index.xml', body)
