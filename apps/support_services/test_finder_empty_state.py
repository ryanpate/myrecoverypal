"""The finder's empty state must explain itself.

The in-person directory covers three metros (NY, TX, WA). Searching any
other ZIP returns nothing, which is correct — but a bare "No meetings
found" tells someone in Springfield, Illinois nothing about why, and hides
the 1,584 online meetings that would actually work for them.
"""
from datetime import time

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting


def make_meeting(**extra):
    defaults = dict(
        name='Daily Bread Group', slug='mtg-t-daily-bread',
        day=1, time=time(6, 0), attendance_option='in_person',
        city='League City', state='TX', postal_code='77573',
        formatted_address='2111 Webster St, League City, TX 77573, USA',
        is_approved=True, is_active=True,
    )
    defaults.update(extra)
    return Meeting.objects.create(**defaults)


def make_online(n):
    for i in range(n):
        Meeting.objects.create(
            name=f'Online {i}', slug=f'mtg-t-online-{i}',
            attendance_option='online', conference_url='https://zoom.us/j/1',
            is_approved=True, is_active=True)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EmptyStateTests(TestCase):
    def setUp(self):
        make_meeting()
        make_online(4)
        self.url = reverse('support_services:meeting_list')

    def _miss(self):
        return self.client.get(self.url, {'q': '62704'})

    def test_names_the_states_actually_covered(self):
        html = self._miss().content.decode()
        self.assertIn('TX', html)
        self.assertIn('in-person', html.lower())

    def test_offers_online_meetings_with_a_real_count(self):
        html = self._miss().content.decode()
        self.assertIn('4 online', html)

    def test_links_to_the_online_meetings_page(self):
        html = self._miss().content.decode()
        self.assertIn(reverse('core:online_aa_meetings'), html)

    def test_echoes_what_was_searched(self):
        html = self._miss().content.decode()
        self.assertIn('62704', html)

    def test_keeps_the_existing_fallbacks(self):
        html = self._miss().content.decode()
        self.assertIn(reverse('support_services:meeting_finder'), html)
        self.assertIn(reverse('support_services:submit_meeting'), html)

    def test_coverage_note_absent_when_results_exist(self):
        html = self.client.get(self.url, {'q': '77573'}).content.decode()
        self.assertNotIn('No meetings found', html)

    def test_online_count_excludes_inactive(self):
        Meeting.objects.filter(slug='mtg-t-online-0').update(is_active=False)
        html = self._miss().content.decode()
        self.assertIn('3 online', html)

    def test_hybrid_meetings_count_as_joinable_online(self):
        Meeting.objects.create(
            name='Hybrid', slug='mtg-t-hybrid', attendance_option='hybrid',
            conference_url='https://zoom.us/j/2', city='Austin', state='TX',
            is_approved=True, is_active=True)
        html = self._miss().content.decode()
        self.assertIn('5 online', html)
