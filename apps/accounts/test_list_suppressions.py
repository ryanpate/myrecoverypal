from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from apps.accounts.outreach_models import ColdOutreachSuppression


class ListSuppressionsTest(TestCase):
    def test_prints_one_address_per_line_sorted(self):
        for e in ['zoe@example.com', 'amy@example.com']:
            ColdOutreachSuppression.objects.create(email=e)
        out = StringIO()
        call_command('list_suppressions', stdout=out)
        self.assertEqual(out.getvalue().split(), ['amy@example.com', 'zoe@example.com'])

    def test_empty_list_prints_nothing(self):
        out = StringIO()
        call_command('list_suppressions', stdout=out)
        self.assertEqual(out.getvalue(), '')

    def test_count_goes_to_stderr_not_stdout(self):
        ColdOutreachSuppression.objects.create(email='amy@example.com')
        out, err = StringIO(), StringIO()
        call_command('list_suppressions', stdout=out, stderr=err)
        self.assertEqual(out.getvalue().split(), ['amy@example.com'])
        self.assertIn('1 opt-out', err.getvalue())
