# apps/accounts/tests_court.py
"""Tests for Court Compliance feature."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.payment_models import Subscription

User = get_user_model()


class TierRenameTest(TestCase):
    """The unused `pro` tier should be renamed to `court` for semantic clarity."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='court_user', email='c@example.com', password='pw'
        )

    def test_court_is_a_valid_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertIn('court', valid_tiers)

    def test_pro_is_no_longer_a_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertNotIn('pro', valid_tiers)

    def test_is_court_returns_true_for_active_court_subscription(self):
        # A Subscription is auto-created by signal on user creation; update it.
        sub = self.user.subscription
        sub.tier = 'court'
        sub.status = 'active'
        sub.save()
        self.assertTrue(sub.is_court())
        self.assertTrue(sub.is_premium())  # court is a superset of premium

    def test_is_court_returns_false_for_premium_user(self):
        sub = self.user.subscription
        sub.tier = 'premium'
        sub.status = 'active'
        sub.save()
        self.assertFalse(sub.is_court())

    def test_is_court_returns_false_for_canceled_court(self):
        sub = self.user.subscription
        sub.tier = 'court'
        sub.status = 'canceled'
        sub.save()
        self.assertFalse(sub.is_court())


from apps.accounts.court_models import (
    CourtReportProfile, MeetingAttendance, CourtReport,
    PROGRAM_CHOICES, MEETING_TYPE_CHOICES, VERIFICATION_CHOICES,
)


class CourtReportProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='court_u', email='cu@example.com', password='pw'
        )

    def test_profile_has_sensible_defaults(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertEqual(profile.required_meetings_per_week, 3)
        self.assertFalse(profile.auto_email_monthly)
        self.assertEqual(profile.legal_name, '')

    def test_profile_is_one_to_one_with_user(self):
        CourtReportProfile.objects.create(user=self.user)
        with self.assertRaises(Exception):
            CourtReportProfile.objects.create(user=self.user)

    def test_profile_str_includes_username(self):
        profile = CourtReportProfile.objects.create(
            user=self.user, legal_name='Court User', case_number='2026-CR-0042'
        )
        self.assertIn('court_u', str(profile))

    def test_default_period_start_set_on_save_when_empty(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertIsNotNone(profile.report_period_start)
        self.assertLessEqual(profile.report_period_start, timezone.now().date())


class MeetingAttendanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='att_user', email='att@example.com', password='pw'
        )

    def _attendance(self, **overrides):
        kwargs = dict(
            user=self.user,
            meeting_name='Tuesday Big Book',
            meeting_date=timezone.now(),
            meeting_address='123 Main St, Austin, TX',
            program='aa',
            meeting_type='open',
            verification_method='self',
        )
        kwargs.update(overrides)
        return MeetingAttendance.objects.create(**kwargs)

    def test_attendance_str_shows_user_name_and_date(self):
        att = self._attendance()
        self.assertIn('att_user', str(att))
        self.assertIn('Big Book', str(att))

    def test_attendance_program_display(self):
        att = self._attendance(program='smart')
        self.assertEqual(att.get_program_display(), 'SMART Recovery')

    def test_attendance_ordering_descending_by_date(self):
        early = self._attendance(meeting_date=timezone.now() - timedelta(days=5))
        late = self._attendance(meeting_date=timezone.now())
        results = list(MeetingAttendance.objects.filter(user=self.user))
        self.assertEqual(results[0], late)
        self.assertEqual(results[1], early)

    def test_attendance_default_verification_is_self(self):
        att = MeetingAttendance.objects.create(
            user=self.user,
            meeting_name='Daily',
            meeting_date=timezone.now(),
            program='aa',
            meeting_type='open',
        )
        self.assertEqual(att.verification_method, 'self')


class CourtReportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rep_user', email='rep@example.com', password='pw'
        )

    def test_report_str(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='deadbeef' * 8,
            attendance_count=12,
        )
        self.assertIn('rep_user', str(report))
        self.assertIn('2026-05', str(report))

    def test_short_hash_property_returns_first_8_chars(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='abc123def456' + '0' * 52,
            attendance_count=0,
        )
        self.assertEqual(report.short_hash, 'abc123de')


from io import BytesIO
import hashlib

from apps.accounts import court_service


class CourtServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pdf_user', email='pdf@example.com', password='pw',
            first_name='Pat'
        )
        self.profile = CourtReportProfile.objects.create(
            user=self.user,
            legal_name='Pat Doe',
            case_number='2026-CR-0007',
            court_name='Travis County Court 4',
            probation_officer_name='Officer Smith',
            probation_officer_email='smith@travisco.gov',
            required_meetings_per_week=3,
        )
        # Three attendances in May 2026
        for day in [3, 10, 17]:
            MeetingAttendance.objects.create(
                user=self.user,
                meeting_name=f'May {day} Group',
                meeting_date=timezone.make_aware(datetime(2026, 5, day, 19, 0)),
                meeting_address=f'{day} Recovery Way',
                program='aa',
                meeting_type='open',
                verification_method='self',
            )

    def test_render_pdf_returns_bytes_and_hash(self):
        pdf_bytes, sha256 = court_service.render_court_report_pdf(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)  # real PDFs are >1KB
        self.assertEqual(len(sha256), 64)
        self.assertEqual(sha256, hashlib.sha256(pdf_bytes).hexdigest())

    def test_render_pdf_starts_with_pdf_magic_bytes(self):
        pdf_bytes, _ = court_service.render_court_report_pdf(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_generate_creates_court_report_row(self):
        report = court_service.generate_court_report(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertEqual(report.attendance_count, 3)
        self.assertEqual(report.legal_name_snapshot, 'Pat Doe')
        self.assertEqual(report.case_number_snapshot, '2026-CR-0007')
        self.assertEqual(len(report.pdf_hash), 64)
        self.assertTrue(report.pdf.name.endswith('.pdf'))

    def test_attendance_outside_period_excluded(self):
        # Add an April attendance — should NOT count toward May report
        MeetingAttendance.objects.create(
            user=self.user,
            meeting_name='April outlier',
            meeting_date=timezone.make_aware(datetime(2026, 4, 25, 19, 0)),
            program='aa',
            meeting_type='open',
        )
        report = court_service.generate_court_report(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertEqual(report.attendance_count, 3)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class VerifyEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ver_user', email='ver@example.com', password='pw'
        )
        CourtReportProfile.objects.create(
            user=self.user, legal_name='Verify User', case_number='V-1',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='M', meeting_date=timezone.now(),
            program='aa', meeting_type='open',
        )
        self.report = court_service.generate_court_report(
            user=self.user,
            period_start=timezone.now().date().replace(day=1),
            period_end=timezone.now().date(),
        )

    def test_verify_with_full_hash_returns_200(self):
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verified')

    def test_verify_with_short_hash_returns_200(self):
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash[:8]}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verified')

    def test_verify_with_unknown_hash_returns_404(self):
        resp = self.client.get('/verify/court/deadbeefdeadbeef/')
        self.assertEqual(resp.status_code, 404)

    def test_verify_response_does_not_leak_legal_name(self):
        """Public endpoint should NOT reveal personal information."""
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash}/')
        self.assertNotContains(resp, 'Verify User')
        self.assertNotContains(resp, 'V-1')


from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)


class CourtFormsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='form_u', email='f@example.com', password='pw'
        )

    def test_profile_form_accepts_minimal_input(self):
        form = CourtReportProfileForm(data={
            'legal_name': 'Real Name',
            'required_meetings_per_week': 3,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_rejects_zero_required_meetings(self):
        form = CourtReportProfileForm(data={
            'legal_name': 'Real Name',
            'required_meetings_per_week': 0,
        })
        self.assertFalse(form.is_valid())

    def test_attendance_form_requires_meeting_name_and_date(self):
        form = MeetingAttendanceForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('meeting_name', form.errors)
        self.assertIn('meeting_date', form.errors)

    def test_attendance_form_accepts_valid_input(self):
        form = MeetingAttendanceForm(data={
            'meeting_name': 'Tuesday Big Book',
            'meeting_date': '2026-05-20T19:00',
            'program': 'aa',
            'meeting_type': 'open',
            'verification_method': 'self',
            'meeting_address': '1 Main St',
            'meeting_online': False,
        })
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtViewsGatingTest(TestCase):
    """All authenticated court views must require the `court` subscription."""

    def setUp(self):
        self.free_user = User.objects.create_user(
            username='free', email='free@example.com', password='pw'
        )
        # User signal auto-creates Subscription; mutate it.
        self.free_user.subscription.tier = 'free'
        self.free_user.subscription.status = 'active'
        self.free_user.subscription.save()

        self.court_user = User.objects.create_user(
            username='court', email='court@example.com', password='pw'
        )
        self.court_user.subscription.tier = 'court'
        self.court_user.subscription.status = 'active'
        self.court_user.subscription.save()

    def _urls(self):
        return [
            reverse('accounts:court_dashboard'),
            reverse('accounts:court_profile'),
            reverse('accounts:court_attendance_list'),
            reverse('accounts:court_attendance_create'),
            reverse('accounts:court_report_list'),
        ]

    def test_anonymous_redirects_to_login(self):
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} did not redirect')
            self.assertIn('/login', resp.url)

    def test_free_user_redirected_to_pricing(self):
        self.client.login(username='free', password='pw')
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} did not redirect')
            self.assertIn('pricing', resp.url)

    def test_court_user_can_load_dashboard(self):
        self.client.login(username='court', password='pw')
        resp = self.client.get(reverse('accounts:court_dashboard'))
        self.assertEqual(resp.status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtAttendanceCrudTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='crud', email='crud@example.com', password='pw'
        )
        self.user.subscription.tier = 'court'
        self.user.subscription.status = 'active'
        self.user.subscription.save()
        self.client.login(username='crud', password='pw')

    def test_create_attendance_via_post(self):
        resp = self.client.post(reverse('accounts:court_attendance_create'), {
            'meeting_name': 'Wednesday Speaker',
            'meeting_date': '2026-05-22T19:30',
            'meeting_address': '1 Main St',
            'program': 'aa',
            'meeting_type': 'speaker',
            'verification_method': 'self',
            'meeting_online': False,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MeetingAttendance.objects.filter(user=self.user).count(), 1)

    def test_attendance_list_shows_only_own_attendances(self):
        other = User.objects.create_user(username='other', email='o@x.com', password='pw')
        MeetingAttendance.objects.create(
            user=other, meeting_name='Their meeting',
            meeting_date=timezone.now(), program='aa', meeting_type='open',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='My meeting',
            meeting_date=timezone.now(), program='aa', meeting_type='open',
        )
        resp = self.client.get(reverse('accounts:court_attendance_list'))
        self.assertContains(resp, 'My meeting')
        self.assertNotContains(resp, 'Their meeting')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtReportGenerationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='gen', email='gen@example.com', password='pw'
        )
        self.user.subscription.tier = 'court'
        self.user.subscription.status = 'active'
        self.user.subscription.save()
        CourtReportProfile.objects.create(
            user=self.user, legal_name='Gen User', case_number='G-1',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='M', meeting_date=timezone.now(),
            program='aa', meeting_type='open',
        )
        self.client.login(username='gen', password='pw')

    def test_generate_report_post_creates_pdf(self):
        today = timezone.now().date()
        resp = self.client.post(reverse('accounts:court_report_generate'), {
            'period_start': today.replace(day=1).isoformat(),
            'period_end': today.isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CourtReport.objects.filter(user=self.user).count(), 1)
        report = CourtReport.objects.get(user=self.user)
        self.assertEqual(len(report.pdf_hash), 64)
