"""Court Compliance: free meeting logging, $9.99 single reports, chair QR confirmation."""
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.court_models import CourtReport, CourtReportPurchase, MeetingAttendance

User = get_user_model()


def _user(username, tier='free'):
    user = User.objects.create_user(username=username, email=f'{username}@example.com', password='pw')
    user.subscription.tier = tier
    user.subscription.status = 'active'
    user.subscription.save()
    return user


def _report(user):
    return CourtReport.objects.create(
        user=user, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
        pdf_hash='a' * 64, pdf_embedded_hash='b' * 64, pdf_data=b'%PDF-1.4 test',
        attendance_count=3)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FreeLoggingTest(TestCase):

    def test_free_user_can_use_court_pages(self):
        _user('free1')
        self.client.login(username='free1', password='pw')
        for name in ('court_dashboard', 'court_profile', 'court_attendance_list',
                     'court_attendance_create', 'court_report_list'):
            self.assertEqual(self.client.get(reverse(f'accounts:{name}')).status_code, 200, name)

    def test_free_user_can_log_a_meeting(self):
        user = _user('free2')
        self.client.login(username='free2', password='pw')
        self.client.post(reverse('accounts:court_attendance_create'), {
            'meeting_name': 'Nooners', 'meeting_date': '2026-09-20T12:00',
            'program': 'aa', 'meeting_type': 'open', 'verification_method': 'self'})
        self.assertEqual(MeetingAttendance.objects.filter(user=user).count(), 1)

    def test_report_page_prices_single_report_for_free_users(self):
        _user('free3')
        self.client.login(username='free3', password='pw')
        resp = self.client.get(reverse('accounts:court_report_list'))
        self.assertContains(resp, '$9.99')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SingleReportPurchaseTest(TestCase):
    PERIOD = {'period_start': '2026-09-01', 'period_end': '2026-09-30'}

    @patch('apps.accounts.court_views.stripe.checkout.Session.create')
    def test_free_user_generate_goes_to_checkout(self, create):
        user = _user('buyer')
        create.return_value = SimpleNamespace(id='cs_court', url='https://checkout.stripe.test/c')
        self.client.login(username='buyer', password='pw')
        resp = self.client.post(reverse('accounts:court_report_generate'), self.PERIOD)
        self.assertEqual((resp.status_code, resp['Location']), (303, 'https://checkout.stripe.test/c'))
        purchase = CourtReportPurchase.objects.get()
        self.assertEqual((purchase.user, purchase.status, purchase.amount_cents, purchase.period_start),
                         (user, 'pending', 999, date(2026, 9, 1)))
        kw = create.call_args.kwargs
        self.assertEqual(kw['mode'], 'payment')
        self.assertEqual(kw['line_items'][0]['price_data']['unit_amount'], 999)
        self.assertEqual(kw['metadata'], {'kind': 'court_report', 'purchase_id': str(purchase.id)})
        self.assertFalse(CourtReport.objects.exists())

    @patch('apps.accounts.court_views.generate_court_report')
    @patch('apps.accounts.court_views.stripe.checkout.Session.create')
    def test_court_subscriber_generates_directly(self, create, generate):
        user = _user('subscriber', tier='court')
        generate.return_value = _report(user)
        self.client.login(username='subscriber', password='pw')
        self.client.post(reverse('accounts:court_report_generate'), self.PERIOD)
        create.assert_not_called()
        generate.assert_called_once()

    @patch('apps.accounts.court_purchase.generate_court_report')
    def test_paid_session_generates_report_once(self, generate):
        from apps.accounts.court_purchase import fulfil_court_report_session
        user = _user('payer')
        generate.return_value = _report(user)
        purchase = CourtReportPurchase.objects.create(
            user=user, period_start=date(2026, 9, 1), period_end=date(2026, 9, 30),
            amount_cents=999, stripe_session_id='cs_pay')
        session = {'id': 'cs_pay', 'payment_status': 'paid', 'payment_intent': 'pi_c',
                   'metadata': {'kind': 'court_report', 'purchase_id': str(purchase.id)}}
        fulfil_court_report_session(session)
        fulfil_court_report_session(session)  # success page + webhook
        purchase.refresh_from_db()
        self.assertEqual((purchase.status, purchase.stripe_payment_intent_id), ('paid', 'pi_c'))
        self.assertIsNotNone(purchase.report)
        generate.assert_called_once_with(user, date(2026, 9, 1), date(2026, 9, 30))

    def test_webhook_routes_court_report_sessions(self):
        from apps.accounts.payment_views import handle_checkout_session_completed
        with patch('apps.accounts.court_purchase.fulfil_court_report_session') as fulfil:
            handle_checkout_session_completed({'metadata': {'kind': 'court_report', 'purchase_id': '1'}})
        fulfil.assert_called_once()

    def test_free_user_can_download_and_email_own_report(self):
        user = _user('owner')
        report = _report(user)
        self.client.login(username='owner', password='pw')
        resp = self.client.get(reverse('accounts:court_report_download', args=[report.id]))
        self.assertEqual(resp.status_code, 200)
        other = _user('stranger')
        self.client.login(username='stranger', password='pw')
        resp = self.client.get(reverse('accounts:court_report_download', args=[report.id]))
        self.assertEqual(resp.status_code, 404)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ChairQrConfirmationTest(TestCase):

    def setUp(self):
        self.member = _user('member')
        self.member.first_name, self.member.last_name = 'Jordan', 'Smith'
        self.member.save()
        self.attendance = MeetingAttendance.objects.create(
            user=self.member, meeting_name='Tuesday Step Study',
            meeting_date=timezone.now() - timedelta(minutes=30))

    def _qr_page(self):
        self.client.login(username='member', password='pw')
        resp = self.client.get(reverse('accounts:court_attendance_chair', args=[self.attendance.id]))
        self.client.logout()
        self.attendance.refresh_from_db()
        return resp

    def test_member_gets_a_qr_code_for_the_chair(self):
        resp = self._qr_page()
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<svg')
        self.assertTrue(self.attendance.chair_confirm_token)
        self.assertContains(resp, reverse('accounts:court_chair_confirm',
                                          args=[self.attendance.chair_confirm_token]))

    def test_chair_confirms_on_their_own_device(self):
        self._qr_page()
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        page = self.client.get(url)
        self.assertContains(page, 'Jordan S.')          # first name + last initial only
        self.assertNotContains(page, 'Smith')
        self.client.post(url, {'chair_name': 'Pat K.', 'chair_role': 'chair', 'attest': 'on'},
                         HTTP_USER_AGENT='ChairPhone/1.0')
        self.attendance.refresh_from_db()
        self.assertEqual((self.attendance.verification_method, self.attendance.chair_signature_name,
                          self.attendance.chair_role), ('qr', 'Pat K.', 'chair'))
        self.assertIsNotNone(self.attendance.chair_signature_at)
        self.assertEqual(self.attendance.chair_confirm_user_agent, 'ChairPhone/1.0')

    def test_member_cannot_confirm_their_own_attendance(self):
        self._qr_page()
        self.client.login(username='member', password='pw')
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        self.client.post(url, {'chair_name': 'Me', 'chair_role': 'chair', 'attest': 'on'})
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.verification_method, 'self')

    def test_confirmation_requires_attestation_and_name(self):
        self._qr_page()
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        self.client.post(url, {'chair_name': '', 'chair_role': 'chair', 'attest': 'on'})
        self.client.post(url, {'chair_name': 'Pat', 'chair_role': 'chair'})
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.verification_method, 'self')

    def test_link_only_works_around_meeting_time(self):
        self.attendance.meeting_date = timezone.now() - timedelta(days=2)
        self.attendance.save()
        self._qr_page()
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        self.client.post(url, {'chair_name': 'Pat', 'chair_role': 'chair', 'attest': 'on'})
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.verification_method, 'self')

    def test_confirmation_is_one_time(self):
        self._qr_page()
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        self.client.post(url, {'chair_name': 'Pat', 'chair_role': 'chair', 'attest': 'on'})
        self.client.post(url, {'chair_name': 'Someone Else', 'chair_role': 'secretary', 'attest': 'on'})
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.chair_signature_name, 'Pat')

    def test_editing_a_confirmed_meeting_voids_the_confirmation(self):
        self._qr_page()
        url = reverse('accounts:court_chair_confirm', args=[self.attendance.chair_confirm_token])
        self.client.post(url, {'chair_name': 'Pat', 'chair_role': 'chair', 'attest': 'on'})
        self.client.login(username='member', password='pw')
        self.client.post(reverse('accounts:court_attendance_edit', args=[self.attendance.id]), {
            'meeting_name': 'A different meeting', 'meeting_date': '2026-09-20T12:00',
            'program': 'aa', 'meeting_type': 'open', 'verification_method': 'qr'})
        self.attendance.refresh_from_db()
        self.assertEqual((self.attendance.verification_method, self.attendance.chair_signature_name),
                         ('self', ''))
