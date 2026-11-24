"""GA4 events along the court funnel: signup -> first logged meeting ->
chair confirmation -> report (apps/core/analytics.py queues them)."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.court_models import CourtReport, MeetingAttendance

User = get_user_model()

MEETING = {
    'meeting_name': 'Wednesday Speaker', 'meeting_date': '2026-05-22T19:30',
    'meeting_address': '1 Main St', 'program': 'aa', 'meeting_type': 'speaker',
    'verification_method': 'self',
}


def queued(client, name):
    return [e for e in client.session.get('ga_events', []) if e['name'] == name]


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtFunnelEventsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='funnel', email='funnel@example.com', password='pw')
        self.client.login(username='funnel', password='pw')

    def test_first_logged_meeting_is_flagged_first(self):
        self.client.post(reverse('accounts:court_attendance_create'), MEETING)
        [event] = queued(self.client, 'court_meeting_logged')
        self.assertEqual(event['params'], {'first_meeting': 'yes', 'online': 'no'})

    def test_later_meetings_are_not_flagged_first(self):
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='Earlier', meeting_date=timezone.now())
        self.client.post(reverse('accounts:court_attendance_create'), MEETING)
        [event] = queued(self.client, 'court_meeting_logged')
        self.assertEqual(event['params']['first_meeting'], 'no')

    def test_chair_confirmation_fires_on_the_chairs_page(self):
        att = MeetingAttendance.objects.create(
            user=self.user, meeting_name='Tonight', meeting_date=timezone.now())
        self.client.get(reverse('accounts:court_attendance_chair', args=[att.id]))
        att.refresh_from_db()
        chair = Client()
        resp = chair.post(
            reverse('accounts:court_chair_confirm', args=[att.chair_confirm_token]),
            {'chair_name': 'Pat R.', 'chair_role': 'chair', 'attest': 'on'})
        self.assertContains(resp, 'court_chair_confirmed')

    def test_subscriber_report_and_email_are_tracked(self):
        self.user.subscription.tier = 'court'
        self.user.subscription.status = 'active'
        self.user.subscription.save()
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='Tonight', meeting_date=timezone.now())
        today = date.today()
        self.client.post(reverse('accounts:court_report_generate'), {
            'period_start': today.replace(day=1).isoformat(),
            'period_end': today.isoformat()})
        [event] = queued(self.client, 'court_report_generated')
        self.assertEqual(event['params'], {'meetings': 1})

        report = CourtReport.objects.get(user=self.user)
        with patch('apps.accounts.court_service.email_report_to_po', return_value=(True, None)):
            self.client.post(reverse('accounts:court_report_email', args=[report.id]),
                             {'recipient': 'po@example.gov'})
        self.assertEqual(len(queued(self.client, 'court_report_emailed')), 1)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtSignupIntentTest(TestCase):
    def setUp(self):
        from apps.accounts.invite_models import SystemSettings
        settings_row = SystemSettings.get_settings()
        settings_row.invite_only_mode = False
        settings_row.save()
        from django.core.cache import caches
        for name in ('rate_limiting', 'default'):
            try:
                caches[name].clear()
            except Exception:
                pass

    def _sign_up(self, email, next_url=''):
        url = reverse('accounts:register')
        if next_url:
            self.client.get(url, {'next': next_url})
        self.client.post(url, {'email': email, 'password': 'a' * 12})
        [event] = queued(self.client, 'sign_up')
        return event['params']

    def test_signup_from_a_court_page_is_tagged_court(self):
        params = self._sign_up('court@example.com', reverse('accounts:court_attendance_create'))
        self.assertEqual(params.get('intent'), 'court')

    def test_ordinary_signup_has_no_court_intent(self):
        self.assertNotIn('intent', self._sign_up('plain@example.com'))

    def test_court_landing_cta_tags_the_tracker_page(self):
        resp = self.client.get(reverse('core:court_ordered_meeting_tracker'))
        self.assertContains(resp, "page: 'tracker'")

    def test_home_card_links_are_tagged(self):
        user = User.objects.create_user(username='card', email='card@example.com', password='pw')
        MeetingAttendance.objects.create(
            user=user, meeting_name='Tonight', meeting_date=timezone.now())
        self.client.login(username='card', password='pw')
        resp = self.client.get(reverse('accounts:progress'))
        for target in ('log', 'report', 'profile'):
            self.assertContains(resp, f'data-court-card="{target}"')
        self.assertContains(resp, 'court_card_click')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtPageClaimsTest(TestCase):
    """Court pages never say a court accepts the report, and they agree with
    each other that the behind-pace reminder is free."""

    def test_tracker_page_makes_no_acceptance_claim(self):
        resp = self.client.get(reverse('core:court_ordered_meeting_tracker'))
        body = resp.content.decode('utf-8').lower()
        self.assertNotIn('court-acceptable', body)
        self.assertNotIn('most courts now accept', body)
        self.assertIn('ask your probation officer', body)

    def test_tracker_page_lists_the_reminder_as_free(self):
        resp = self.client.get(reverse('core:court_ordered_meeting_tracker'))
        self.assertContains(resp, "and an evening reminder when you're behind.")
        self.assertNotContains(resp, 'behind-pace reminders')

    def test_pricing_page_makes_no_acceptance_claim(self):
        resp = self.client.get(reverse('accounts:pricing'))
        self.assertNotContains(resp, 'Court-acceptable')


class CourtPlanTextTest(TestCase):
    """Stored plan text carries no acceptance claim (migration 0081)."""

    def test_seeded_court_plans_make_no_acceptance_claim(self):
        from apps.accounts.payment_models import SubscriptionPlan
        plans = list(SubscriptionPlan.objects.filter(tier='court'))
        self.assertTrue(plans)
        for plan in plans:
            text = ' '.join([plan.description, *plan.features]).lower()
            self.assertNotIn('court-acceptable', text)
            self.assertIn('verifiable pdf', text)

    def test_reword_leaves_other_text_alone(self):
        from importlib import import_module
        reword = import_module('apps.accounts.migrations.0081_reword_court_plan_text').reword
        self.assertEqual(reword('Everything in Premium'), 'Everything in Premium')
        self.assertEqual(
            reword('Save 25% vs monthly. Court-acceptable PDF attendance reports'),
            'Save 25% vs monthly. Verifiable PDF attendance reports')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ChairConfirmTimeZoneTest(TestCase):
    """The chair has no account, so the meeting time shows in the member's zone."""

    def test_chair_sees_the_meeting_time_in_the_members_zone(self):
        from datetime import datetime, timezone as dt_timezone
        from unittest.mock import patch
        user = User.objects.create_user(
            username='chairtz', email='chairtz@example.com', password='pw', first_name='Jordan')
        user.timezone = 'America/Chicago'
        user.save()
        # 7:00 PM Chicago on Monday Nov 23 is 01:00 UTC on Tuesday Nov 24.
        meeting = datetime(2026, 11, 24, 1, 0, tzinfo=dt_timezone.utc)
        att = MeetingAttendance.objects.create(
            user=user, meeting_name='Monday Night', meeting_date=meeting,
            chair_confirm_token='tz-test-token')
        with patch('django.utils.timezone.now', return_value=meeting):
            resp = Client().get(reverse('accounts:court_chair_confirm', args=[att.chair_confirm_token]))
        self.assertContains(resp, 'Monday, Nov 23 at 7:00 PM')
