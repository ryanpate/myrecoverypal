"""Coverage gaps: what people search for that we don't have.

The in-person directory only covers the metros we hold feeds for. Rather
than guess which to add next, record the searches that come back empty and
rank them. Feed acquisition needs a human (some intergroups sit behind a
bot challenge and have to be emailed), so this is a prioritised queue, not
an automatic fetch.

No user is attached to a row. A search is location data about someone
looking for a recovery meeting; the aggregate is what's useful, and the
identity is not ours to keep.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.support_services.coverage import record_coverage_gap
from apps.support_services.models import CoverageRequest, Meeting

User = get_user_model()


class RecordCoverageGapTests(TestCase):
    def test_records_a_miss(self):
        record_coverage_gap('62704')
        row = CoverageRequest.objects.get()
        self.assertEqual(row.query, '62704')
        self.assertEqual(row.postal_code, '62704')
        self.assertEqual(row.hits, 1)

    def test_repeat_searches_increment_rather_than_duplicate(self):
        for _ in range(3):
            record_coverage_gap('62704')
        row = CoverageRequest.objects.get()
        self.assertEqual(row.hits, 3)

    def test_normalises_case_and_whitespace(self):
        record_coverage_gap('  Springfield  ')
        record_coverage_gap('springfield')
        row = CoverageRequest.objects.get()
        self.assertEqual(row.query, 'springfield')
        self.assertEqual(row.hits, 2)

    def test_last_seen_advances(self):
        record_coverage_gap('62704')
        first = CoverageRequest.objects.get().last_seen
        record_coverage_gap('62704')
        self.assertGreaterEqual(CoverageRequest.objects.get().last_seen, first)

    def test_extracts_a_zip_from_a_longer_query(self):
        record_coverage_gap('Springfield IL 62704')
        self.assertEqual(CoverageRequest.objects.get().postal_code, '62704')

    def test_zip_plus_four_is_truncated_to_the_five_digit_prefix(self):
        record_coverage_gap('62704-1234')
        self.assertEqual(CoverageRequest.objects.get().postal_code, '62704')

    def test_non_zip_query_stores_no_postal_code(self):
        record_coverage_gap('springfield')
        self.assertEqual(CoverageRequest.objects.get().postal_code, '')

    def test_ignores_blank_and_whitespace(self):
        record_coverage_gap('')
        record_coverage_gap('   ')
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_ignores_single_character_noise(self):
        record_coverage_gap('x')
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_caps_absurdly_long_queries(self):
        """Bots were ~48% of GA4 traffic; junk must not grow the table."""
        record_coverage_gap('a' * 500)
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_never_raises(self):
        """Analytics must never break the page it is measuring."""
        record_coverage_gap(None)      # must not raise
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_does_not_store_who_searched(self):
        record_coverage_gap('62704')
        self.assertNotIn(
            'user', [f.name for f in CoverageRequest._meta.get_fields()])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FinderIntegrationTests(TestCase):
    def setUp(self):
        Meeting.objects.create(
            name='Covered Group', slug='mtg-t-covered',
            city='League City', state='TX', postal_code='77573',
            attendance_option='in_person', is_approved=True, is_active=True)
        self.url = reverse('support_services:meeting_list')

    def test_empty_search_is_recorded(self):
        self.client.get(self.url, {'q': '62704'})
        self.assertEqual(CoverageRequest.objects.get().query, '62704')

    def test_successful_search_is_not_recorded(self):
        self.client.get(self.url, {'q': '77573'})
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_browsing_without_a_query_is_not_recorded(self):
        self.client.get(self.url)
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_filter_only_miss_is_not_recorded(self):
        """A day/attendance filter returning nothing is not a coverage gap."""
        self.client.get(self.url, {'day': '3'})
        self.assertEqual(CoverageRequest.objects.count(), 0)

    def test_user_still_sees_the_page(self):
        resp = self.client.get(self.url, {'q': '62704'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No meetings found')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CoverageAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'root', 'root@example.com', 'pw')
        self.client.force_login(self.admin)

    def test_changelist_ranks_by_demand(self):
        record_coverage_gap('62704')
        for _ in range(5):
            record_coverage_gap('60614')
        resp = self.client.get(
            reverse('admin:support_services_coveragerequest_changelist'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertLess(body.index('60614'), body.index('62704'))
