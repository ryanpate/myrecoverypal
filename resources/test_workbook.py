"""Tests for the "My Recovery Workbook" PDF export."""
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyCheckIn, DailyPledge, Milestone, RelapseLog
from apps.accounts.plan_models import RelapsePreventionPlan
from apps.journal.models import JournalEntry
from resources.models import WorksheetEntry
from resources.test_premium_gating import make_free, make_premium
from resources.workbook import (
    default_sections, line_chart_svg, parse_options, render_workbook_html,
)

User = get_user_model()

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except Exception:
    HAS_WEASYPRINT = False


def seed(user):
    today = timezone.localdate()
    user.sobriety_date = today - timedelta(days=120)
    user.pledge_reason = 'MY-DAUGHTER'
    user.recovery_goals = 'Run a 5k'
    user.save()
    for i in range(0, 40, 3):
        DailyCheckIn.objects.create(
            user=user, date=today - timedelta(days=i), mood=2 + i % 4,
            craving_level=i % 5, energy_level=3,
            gratitude='GRATEFUL-RECENT' if i == 0 else '')
    DailyCheckIn.objects.create(
        user=user, date=today - timedelta(days=200), mood=1, craving_level=4,
        energy_level=1, gratitude='GRATEFUL-OLD')
    DailyPledge.objects.create(user=user, date=today)
    RelapsePreventionPlan.objects.create(
        user=user, triggers='PLAN-TRIGGERS',
        support_contacts=[{'name': 'Sam', 'phone': '555-0100', 'relationship': 'sponsor'}])
    WorksheetEntry.objects.create(
        user=user, worksheet_slug='urge-log', data={'when': 'WS-RECENT', 'intensity_start': 7})
    old = WorksheetEntry.objects.create(
        user=user, worksheet_slug='urge-log', data={'when': 'WS-OLD'})
    WorksheetEntry.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=200))
    Milestone.objects.create(user=user, title='MILESTONE-30', date_achieved=today - timedelta(days=60))
    RelapseLog.objects.create(user=user, relapse_date=today - timedelta(days=121), notes='SLIP-NOTE')
    JournalEntry.objects.create(user=user, title='JOURNAL-TITLE', content='JOURNAL-SECRET')


class ParseOptionsTests(TestCase):
    def test_defaults_when_nothing_selected(self):
        sections, rng = parse_options(QueryDict(''))
        self.assertEqual(sections, default_sections())
        self.assertNotIn('slips', sections)
        self.assertEqual(rng, '90')

    def test_unknown_values_ignored_and_order_fixed(self):
        sections, rng = parse_options(QueryDict('section=slips&section=evil&section=plan&range=999'))
        self.assertEqual(sections, ['plan', 'slips'])
        self.assertEqual(rng, '90')

    def test_chart_svg(self):
        from datetime import date
        svg = line_chart_svg([(date(2026, 1, 1), 2), (date(2026, 1, 8), 4)], 1, 6, [(1, 'Low')], '#123456')
        self.assertTrue(svg.startswith('<svg'))
        self.assertIn('polyline', svg)
        self.assertIn('Jan 8', svg)

    def test_chart_breaks_line_across_long_gaps(self):
        from datetime import date
        pts = [(date(2026, 1, 5), 2), (date(2026, 1, 12), 3),
               (date(2026, 6, 1), 4), (date(2026, 6, 8), 5)]
        svg = line_chart_svg(pts, 1, 6, [], '#123456')
        self.assertEqual(svg.count('<polyline'), 2)
        self.assertEqual(svg.count('<circle'), 4)


class WorkbookContentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='wb', email='wb@example.com', password='x')
        seed(self.user)

    def test_all_sections_all_time(self):
        html = render_workbook_html(
            self.user, ['reasons', 'checkins', 'plan', 'worksheets', 'milestones', 'slips'], 'all')
        for marker in ('MY-DAUGHTER', 'Run a 5k', 'GRATEFUL-RECENT', 'GRATEFUL-OLD', 'PLAN-TRIGGERS',
                       '555-0100', 'WS-RECENT', 'WS-OLD', 'MILESTONE-30', 'SLIP-NOTE',
                       '<svg', '120'):
            self.assertIn(marker, html, marker)

    def test_range_filters_dated_sections(self):
        html = render_workbook_html(
            self.user, ['checkins', 'worksheets', 'milestones', 'slips'], '90')
        self.assertIn('GRATEFUL-RECENT', html)
        self.assertNotIn('GRATEFUL-OLD', html)
        self.assertIn('WS-RECENT', html)
        self.assertNotIn('WS-OLD', html)
        self.assertIn('MILESTONE-30', html)
        self.assertNotIn('SLIP-NOTE', html)

    def test_unselected_sections_left_out(self):
        html = render_workbook_html(self.user, ['milestones'], 'all')
        self.assertNotIn('SLIP-NOTE', html)
        self.assertNotIn('PLAN-TRIGGERS', html)
        self.assertNotIn('MY-DAUGHTER', html)

    def test_journal_never_included(self):
        html = render_workbook_html(
            self.user, ['reasons', 'checkins', 'plan', 'worksheets', 'milestones', 'slips'], 'all')
        self.assertNotIn('JOURNAL-SECRET', html)
        self.assertNotIn('JOURNAL-TITLE', html)

    def test_empty_account_renders(self):
        empty = User.objects.create_user(username='empty', email='e@example.com', password='x')
        html = render_workbook_html(empty, default_sections(), '30')
        self.assertIn('No check-ins in this period', html)
        self.assertIn('No relapse prevention plan yet', html)
        self.assertFalse(RelapsePreventionPlan.objects.filter(user=empty).exists())

    def test_other_members_data_excluded(self):
        other = User.objects.create_user(username='o', email='o@example.com', password='x')
        WorksheetEntry.objects.create(user=other, worksheet_slug='urge-log', data={'when': 'NOT-MINE'})
        html = render_workbook_html(self.user, ['worksheets'], 'all')
        self.assertNotIn('NOT-MINE', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WorkbookViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='wbv', email='wbv@example.com', password='x')
        self.client.force_login(self.user)

    def test_builder_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('resources:workbook'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp['Location'])

    def test_builder_free_user_sees_locked(self):
        make_free(self.user)
        resp = self.client.get(reverse('resources:workbook'))
        self.assertContains(resp, 'Download my workbook (Premium)')
        self.assertContains(resp, 'disabled')

    def test_builder_premium_user(self):
        make_premium(self.user)
        resp = self.client.get(reverse('resources:workbook'))
        self.assertContains(resp, 'Download my workbook</button>')
        self.assertContains(resp, 'value="slips"')

    def test_pdf_free_user_redirected(self):
        make_free(self.user)
        resp = self.client.get(reverse('resources:workbook_pdf'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:pricing'), resp['Location'])

    def test_pdf_premium_user(self):
        make_premium(self.user)
        with patch('resources.workbook.render_workbook_pdf', return_value=b'%PDF-fake') as m:
            resp = self.client.get(reverse('resources:workbook_pdf') + '?section=plan&section=slips&range=all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('my-recovery-workbook.pdf', resp['Content-Disposition'])
        m.assert_called_once_with(self.user, ['plan', 'slips'], 'all')


@skipUnless(HAS_WEASYPRINT, 'WeasyPrint not available in this env')
class WorkbookRealPdfTests(TestCase):
    def test_renders_pdf(self):
        from resources.workbook import render_workbook_pdf
        user = User.objects.create_user(username='pdf', email='pdf@example.com', password='x')
        seed(user)
        pdf = render_workbook_pdf(
            user, ['reasons', 'checkins', 'plan', 'worksheets', 'milestones', 'slips'], 'all')
        self.assertTrue(pdf.startswith(b'%PDF'))
