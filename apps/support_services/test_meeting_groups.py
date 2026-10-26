"""One indexable page per meeting group (docs/plans/2026-10-26-meeting-group-merge.md).

Feeds give each weekly slot its own slug. Slots of a group share a
group_key; one is the primary, every slot page canonicalizes to it, and only
primaries go in the sitemap.
"""
import json
import tempfile
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.grouping import assign_primaries, group_key, meeting_group_key
from apps.support_services.meeting_sync import sync_source
from apps.support_services.models import Meeting

User = get_user_model()
ADDRESS = '50 Perry St, New York, NY 10014, USA'


def _slot(slug, day, at=time(19, 0), name='Perry Street Workshop', **extra):
    fields = dict(name=name, slug=slug, day=day, time=at, attendance_option='in_person',
                  formatted_address=ADDRESS, city='New York', state='NY',
                  is_approved=True, is_active=True)
    fields.update(extra)
    return Meeting.objects.create(**fields)


class GroupKeyTests(TestCase):
    def test_slots_of_one_group_share_a_key(self):
        a = _slot('mtg-ny-perry-street-workshop', 1)
        b = _slot('mtg-ny-perry-street-workshop-27', 3, time(12, 0))
        self.assertEqual(a.group_key, b.group_key)
        self.assertTrue(a.group_key.startswith('ny-'))

    def test_same_name_at_another_address_is_another_group(self):
        a = _slot('mtg-ny-perry-street-workshop', 1)
        b = _slot('mtg-ny-perry-street-workshop-2', 1, formatted_address='1 Other Ave, New York, NY')
        self.assertNotEqual(a.group_key, b.group_key)

    def test_same_name_in_another_feed_is_another_group(self):
        self.assertNotEqual(_slot('mtg-ny-perry', 1).group_key, _slot('mtg-dc-perry', 1).group_key)

    def test_online_rooms_split_by_meeting_id_not_name(self):
        kw = dict(slug='mtg-ny-daily-reflections', name='Daily Reflections', attendance_option='online')
        room1 = group_key(conference_url='https://zoom.us/j/111?pwd=abc', **kw)
        room1_new_pwd = group_key(conference_url='https://zoom.us/j/111?pwd=xyz', **kw)
        room2 = group_key(conference_url='https://zoom.us/j/222', **kw)
        self.assertEqual(room1, room1_new_pwd)
        self.assertNotEqual(room1, room2)

    def test_community_submissions_are_always_their_own_group(self):
        user = User.objects.create_user('sub', 's@example.com', 'pw')
        a = _slot('mtg-ny-perry-street-workshop', 1)
        b = _slot('mtg-ny-perry-street-workshop-x', 2, submitted_by=user)
        self.assertNotEqual(a.group_key, b.group_key)
        self.assertTrue(b.group_key.startswith('single-'))
        self.assertTrue(b.is_group_primary)

    def test_key_fits_the_column(self):
        self.assertLessEqual(len(meeting_group_key({'slug': 'x' * 255, 'name': 'n'})), 100)


class AssignPrimariesTests(TestCase):
    def test_base_slug_wins(self):
        _slot('mtg-ny-perry-street-workshop-5', 2)
        base = _slot('mtg-ny-perry-street-workshop', 1)
        assign_primaries(Meeting)
        self.assertEqual(list(Meeting.objects.filter(is_group_primary=True)), [base])

    def test_lowest_number_wins_without_a_base_slug(self):
        _slot('mtg-ny-perry-street-workshop-12', 2)
        low = _slot('mtg-ny-perry-street-workshop-3', 1)
        assign_primaries(Meeting)
        self.assertEqual(list(Meeting.objects.filter(is_group_primary=True)), [low])

    def test_primary_moves_only_when_it_goes_inactive(self):
        base = _slot('mtg-ny-perry-street-workshop', 1)
        two = _slot('mtg-ny-perry-street-workshop-2', 2)
        assign_primaries(Meeting)
        self.assertEqual(assign_primaries(Meeting), 0)  # stable on rerun
        Meeting.objects.filter(pk=base.pk).update(is_active=False)
        assign_primaries(Meeting)
        self.assertEqual(list(Meeting.objects.filter(is_group_primary=True)), [two])

    def test_one_primary_per_group(self):
        for i in range(5):
            _slot(f'mtg-ny-perry-street-workshop-{i + 1}', i)
        _slot('mtg-ny-other', 1, name='Other Group')
        assign_primaries(Meeting)
        self.assertEqual(Meeting.objects.filter(is_group_primary=True).count(), 2)


class SyncAssignsGroupsTests(TestCase):
    def _feed(self, meetings):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(meetings, f)
        f.close()
        return f.name

    def _m(self, slug, day):
        return {'name': 'Perry Street Workshop', 'slug': slug, 'day': day, 'time': '19:00',
                'formatted_address': ADDRESS, 'attendance_option': 'in_person'}

    def test_sync_groups_slots_and_repicks_primary_when_one_vanishes(self):
        sync_source('ny', self._feed([self._m('perry-street-workshop', 1),
                                      self._m('perry-street-workshop-2', 3)]))
        rows = Meeting.objects.order_by('slug')
        self.assertEqual(len({m.group_key for m in rows}), 1)
        self.assertEqual(Meeting.objects.get(is_group_primary=True).slug, 'mtg-ny-perry-street-workshop')

        sync_source('ny', self._feed([self._m('perry-street-workshop-2', 3)]))
        self.assertEqual(Meeting.objects.get(is_group_primary=True).slug, 'mtg-ny-perry-street-workshop-2')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class GroupDetailPageTests(TestCase):
    def setUp(self):
        self.base = _slot('mtg-ny-perry-street-workshop', 1)
        self.wed = _slot('mtg-ny-perry-street-workshop-27', 3, time(12, 0))
        self.dupe = _slot('mtg-ny-perry-street-workshop-28', 3, time(12, 0))  # feed listed it twice
        assign_primaries(Meeting)

    def _html(self, meeting):
        return self.client.get(meeting.get_absolute_url()).content.decode()

    def test_every_slot_page_canonicalizes_to_the_primary(self):
        primary_url = f'http://testserver{self.base.get_absolute_url()}'
        for m in (self.base, self.wed):
            with self.subTest(slug=m.slug):
                self.assertIn(f'<link rel="canonical" href="{primary_url}">', self._html(m))

    def test_schedule_lists_each_slot_once_and_marks_this_page(self):
        html = self._html(self.wed)
        self.assertIn('Weekly schedule', html)
        self.assertEqual(html.count('class="meeting-schedule-row'), 2)  # duplicate slot collapsed
        self.assertIn('This page', html)
        self.assertIn(f'href="{self.base.get_absolute_url()}" class="meeting-schedule-link"', html)

    def test_primary_gets_a_group_level_title(self):
        html = self._html(self.base)
        self.assertIn('<title>Perry Street Workshop — Mon &amp; Wed Meetings, New York, NY', html)

    def test_single_slot_meeting_page_is_unchanged(self):
        solo = _slot('mtg-ny-solo-group', 5, name='Solo Group')
        assign_primaries(Meeting)
        html = self._html(solo)
        self.assertNotIn('Weekly schedule', html)
        self.assertIn(f'<title>{solo.seo_title}</title>', html)

    def test_nearby_meetings_skip_the_same_group(self):
        other = _slot('mtg-ny-other-group', 2, name='Other Group')
        html = self._html(self.base)
        nearby = html[html.index('nearby-meeting'):] if 'nearby-meeting' in html else ''
        self.assertIn(other.name, nearby)
        self.assertNotIn(self.wed.get_absolute_url() + '" class="nearby-meeting', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingSitemapTests(TestCase):
    def test_sitemap_lists_primaries_only(self):
        base = _slot('mtg-ny-perry-street-workshop', 1)
        other = _slot('mtg-ny-perry-street-workshop-2', 2)
        assign_primaries(Meeting)
        from recovery_hub.sitemaps import MeetingSitemap
        items = list(MeetingSitemap().items())
        self.assertIn(base, items)
        self.assertNotIn(other, items)


class BackfillMigrationTests(TestCase):
    def test_backfill_keys_and_primaries_existing_rows(self):
        import importlib
        from django.apps import apps as django_apps
        backfill = importlib.import_module(
            'apps.support_services.migrations.0008_backfill_meeting_groups').backfill
        base = _slot('mtg-ny-perry-street-workshop', 1)
        two = _slot('mtg-ny-perry-street-workshop-2', 2)
        # Simulate pre-migration rows: no keys, no primaries.
        Meeting.objects.update(group_key='', is_group_primary=False)
        backfill(django_apps, None)
        base.refresh_from_db()
        two.refresh_from_db()
        self.assertEqual(base.group_key, two.group_key)
        self.assertNotEqual(base.group_key, '')
        self.assertTrue(base.is_group_primary)
        self.assertFalse(two.is_group_primary)
