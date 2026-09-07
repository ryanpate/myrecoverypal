"""Tests for meeting-directory SEO: sitemap coverage + per-page meta tags.

Before this, all ~1,565 meeting pages shared the site-wide boilerplate
meta description and none were in the sitemap, which is why the whole
section sat in GSC "Crawled - currently not indexed".
"""
from datetime import time

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting

BOILERPLATE = 'Free recovery community. Track milestones'


def _meeting(**kwargs):
    defaults = dict(
        name='Grateful Hearts', slug='grateful-hearts',
        day=4, time=time(19, 0), timezone='America/Chicago',
        attendance_option='online', conference_url='https://zoom.us/j/1',
        is_approved=True, is_active=True,
    )
    defaults.update(kwargs)
    return Meeting.objects.create(**defaults)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingSeoDescriptionTests(TestCase):
    """The per-meeting description must be factual for every field combo."""

    def test_online_meeting_with_day_and_time(self):
        m = _meeting()
        desc = m.seo_description
        self.assertIn('Grateful Hearts', desc)
        self.assertIn('free online recovery meeting', desc)
        self.assertIn('on Thursdays at 7:00 PM', desc)
        self.assertIn('Get the join link', desc)

    def test_in_person_meeting_includes_city_and_state(self):
        m = _meeting(slug='houston-group', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX')
        desc = m.seo_description
        self.assertIn('in Houston, TX', desc)
        self.assertIn('See the address', desc)
        # An in-person meeting must not advertise a join link.
        self.assertNotIn('join link', desc)

    def test_hybrid_meeting_says_both(self):
        m = _meeting(slug='hybrid-group', attendance_option='hybrid',
                     city='Austin', state='TX')
        self.assertIn('in person and online', m.seo_description)

    def test_online_meeting_omits_city(self):
        """An online meeting's stored city is not where attendees are."""
        m = _meeting(slug='online-with-city', city='Houston', state='TX')
        self.assertNotIn('Houston', m.seo_description)

    def test_missing_day_and_time_omits_schedule_clause(self):
        m = _meeting(slug='no-schedule', day=None, time=None)
        desc = m.seo_description
        self.assertNotIn(' on ', desc)
        self.assertNotIn(' at ', desc)
        self.assertTrue(desc.startswith('Grateful Hearts is a'))

    def test_day_without_time(self):
        m = _meeting(slug='day-only', time=None)
        self.assertIn('on Thursdays.', m.seo_description)

    def test_description_capped_at_160_chars(self):
        m = _meeting(slug='long-name', name='X' * 200)
        desc = m.seo_description
        self.assertLessEqual(len(desc), 160)
        self.assertTrue(desc.endswith('...'))

    def test_get_absolute_url(self):
        m = _meeting()
        self.assertEqual(m.get_absolute_url(), '/support/meetings/grateful-hearts/')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingSeoTitleTests(TestCase):
    def test_online_meeting_title(self):
        self.assertEqual(
            _meeting().seo_title,
            'Grateful Hearts \u2014 Thursdays 7:00 PM Online Recovery Meeting',
        )

    def test_in_person_title_uses_city_state(self):
        m = _meeting(slug='houston', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX')
        self.assertEqual(
            m.seo_title,
            'Grateful Hearts \u2014 Thursdays 7:00 PM Houston, TX Recovery Meeting',
        )

    def test_title_without_schedule(self):
        m = _meeting(slug='bare', day=None, time=None,
                     attendance_option='in_person', conference_url='')
        self.assertEqual(m.seo_title, 'Grateful Hearts \u2014 Recovery Meeting')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingPageMetaTests(TestCase):
    """The og:/twitter: tags read the same seo_* context keys as the
    <title> and meta description, so setting them in the view fixes all
    three at once. Assert every tag, not just meta description."""

    def test_detail_page_replaces_boilerplate_everywhere(self):
        m = _meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertNotIn(BOILERPLATE, html)
        for attr in ('name="description"', 'property="og:description"',
                     'name="twitter:description"'):
            with self.subTest(attr=attr):
                self.assertIn(f'{attr} content="{m.seo_description}"', html)

    def test_detail_page_title_carries_schedule_and_format(self):
        m = _meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn(f'<title>{m.seo_title}</title>', html)
        for attr in ('property="og:title"', 'name="twitter:title"'):
            with self.subTest(attr=attr):
                self.assertIn(f'{attr} content="{m.seo_title}"', html)

    def test_detail_page_canonical_is_self(self):
        m = _meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn(
            'rel="canonical" href="http://testserver/support/meetings/grateful-hearts/"',
            html,
        )

    def test_hub_page_replaces_boilerplate_everywhere(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertNotIn(BOILERPLATE, html)
        self.assertIn('Search thousands of free AA meetings', html)
        self.assertIn(
            '<title>AA Meeting Finder — Search Local &amp; Online AA Meetings</title>',
            html,
        )

    def test_hub_filtered_view_canonicalises_to_bare_url(self):
        """Filter permutations must not compete with the hub page."""
        html = self.client.get(
            reverse('support_services:meeting_list'), {'city': 'Houston'}
        ).content.decode()
        self.assertIn(
            'rel="canonical" href="http://testserver/support/meetings/"', html
        )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingFilterNoIndexTests(TestCase):
    """Meeting-finder filters are thin duplicates of the hub page."""

    def test_bare_hub_is_indexable(self):
        resp = self.client.get(reverse('support_services:meeting_list'))
        self.assertNotIn('X-Robots-Tag', resp)

    def test_detail_page_is_indexable(self):
        m = _meeting()
        resp = self.client.get(m.get_absolute_url())
        self.assertNotIn('X-Robots-Tag', resp)

    def test_filter_params_are_noindexed(self):
        url = reverse('support_services:meeting_list')
        for param, value in (
            ('day', '4'), ('city', 'Houston'), ('state', 'TX'),
            ('q', 'big book'), ('attendance', 'online'),
            ('page', '2'),
        ):
            with self.subTest(param=param):
                resp = self.client.get(url, {param: value})
                self.assertEqual(resp['X-Robots-Tag'], 'noindex, nofollow')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SitemapCoverageTests(TestCase):
    def test_sitemap_lists_approved_meetings(self):
        _meeting()
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn(
            '/support/meetings/grateful-hearts/</loc>', xml
        )

    def test_sitemap_excludes_unapproved_and_inactive_meetings(self):
        _meeting(slug='pending', is_approved=False)
        _meeting(slug='retired', is_active=False)
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/support/meetings/pending/', xml)
        self.assertNotIn('/support/meetings/retired/', xml)

    def test_sitemap_lists_meetings_hub(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/support/meetings/</loc>', xml)

    def test_sitemap_lists_medallion_maker(self):
        """Top click driver in GSC; was missing from the sitemap entirely."""
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn(
            '/sobriety-medallion-maker/</loc>', xml
        )


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingFreshnessTests(TestCase):
    """In-person listings send people somewhere physical — say how fresh."""

    def test_in_person_meeting_shows_last_verified(self):
        m = _meeting(slug='houston', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX',
                     formatted_address='123 Main St, Houston, TX')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('Last verified', html)

    def test_hybrid_meeting_shows_last_verified(self):
        m = _meeting(slug='hybrid', attendance_option='hybrid',
                     city='Austin', state='TX',
                     formatted_address='9 Oak Ave, Austin, TX')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('Last verified', html)

    def test_online_meeting_does_not_show_last_verified(self):
        """No journey to waste; the join link either works or it doesn't."""
        m = _meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertNotIn('Last verified', html)

    def test_source_website_is_credited_when_present(self):
        m = _meeting(slug='credited', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX',
                     website='https://aahouston.org/')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('https://aahouston.org/', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DirectoryCopyAccuracyTests(TestCase):
    """The directory is sourced entirely from AA intergroup feeds. Claiming
    NA and SMART meetings it does not have is a factual error, and "1,500+"
    understates it by 4x."""

    def test_description_does_not_claim_programs_we_do_not_carry(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertNotIn('SMART Recovery and secular groups', html)
        self.assertNotIn('1,500+', html)

    def test_description_says_aa(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertIn('AA meetings', html)

    def test_finder_links_to_state_hubs(self):
        from apps.support_services.test_city_hubs import make_meetings
        make_meetings('Houston', 'TX', 4)
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertIn('/support/meetings/tx/', html)
