"""Each meeting in the list is one tappable row with readable type names."""
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.models import Meeting


class TypeLabelsTest(TestCase):
    def test_codes_become_names_and_unknown_codes_pass_through(self):
        self.assertEqual(Meeting(types=['O', 'D', 'ZZ']).type_labels, ['Open', 'Discussion', 'ZZ'])

    def test_no_types(self):
        self.assertEqual(Meeting(types=[]).type_labels, [])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingListRowTest(TestCase):
    def test_row_links_once_through_the_name(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertNotIn('View Details', html)
        self.assertNotIn('meeting-type-badge', html)
        self.assertIn('Search the worldwide network', html)
