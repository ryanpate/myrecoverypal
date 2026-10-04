"""Card trial vs. no-card trial A/B test (apps/accounts/trial_experiment.py)."""
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts import trial_experiment as t
from apps.accounts.ab_testing import ABTestAssignment, ABTestConversion
from apps.accounts.payment_models import SubscriptionPlan

User = get_user_model()


def signup(name):
    return User.objects.create_user(name, f'{name}@example.com', 'pw12345!')


def variant_of(user):
    a = ABTestAssignment.objects.filter(user=user, test__name=t.TEST_NAME).first()
    return a.variant.name if a else None


def events(user):
    return set(ABTestConversion.objects.filter(assignment__user=user).values_list('conversion_type', flat=True))


class StripeObj(dict):
    __getattr__ = dict.get


class AssignmentTests(TestCase):
    def test_no_test_no_change(self):
        u = signup('plain')
        self.assertIsNone(variant_of(u))
        self.assertEqual((u.subscription.tier, u.subscription.status), ('free', 'active'))

    def test_split_and_no_card_trial(self):
        t.setup_test()
        users = [signup(f'u{i}') for i in range(40)]
        groups = {t.CONTROL: [], t.VARIANT: []}
        for u in users:
            groups[variant_of(u)].append(u)
        self.assertTrue(8 <= len(groups[t.VARIANT]) <= 32, groups)  # roughly half
        for u in groups[t.VARIANT]:
            u.subscription.refresh_from_db()
            sub = u.subscription
            self.assertEqual((sub.tier, sub.status), ('premium', 'trialing'))
            self.assertAlmostEqual((sub.trial_end - timezone.now()).total_seconds(), 7 * 86400, delta=120)
            self.assertTrue(sub.is_premium())
            self.assertFalse(sub.card_trial_eligible())  # no second (card) trial later
            self.assertEqual(events(u), {t.STARTED_TRIAL})
        for u in groups[t.CONTROL]:
            u.subscription.refresh_from_db()
            self.assertEqual(u.subscription.tier, 'free')
            self.assertTrue(u.subscription.card_trial_eligible())
            self.assertEqual(events(u), set())

    def test_existing_members_untouched_and_stop_works(self):
        before = signup('before')
        out = StringIO()
        call_command('init_trial_test', stdout=out)
        self.assertIn('is running', out.getvalue())
        self.assertIsNone(variant_of(before))
        call_command('init_trial_test', '--stop', stdout=StringIO())
        after = signup('after')
        self.assertIsNone(variant_of(after))
        self.assertEqual(after.subscription.tier, 'free')

    def test_experiment_errors_never_break_signup(self):
        t.setup_test()
        with patch('apps.accounts.ab_testing.ABTestingService.get_variant', side_effect=RuntimeError('db')):
            u = signup('safe')
        self.assertEqual(u.subscription.tier, 'free')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FunnelTrackingTests(TestCase):
    def setUp(self):
        t.setup_test()
        self.user = signup('funnel')
        self.plan, _ = SubscriptionPlan.objects.update_or_create(
            tier='premium', billing_period='yearly',
            defaults={'name': 'Premium Annual', 'price': Decimal('59.99'), 'is_active': True,
                      'stripe_price_id': 'price_y'})

    def test_began_checkout(self):
        from apps.accounts.payment_views import _build_checkout_session
        request = SimpleNamespace(user=self.user, build_absolute_uri=lambda p: 'https://x' + p)
        with patch('stripe.Customer.create', return_value=SimpleNamespace(id='cus_1')), \
                patch('stripe.checkout.Session.create', return_value=SimpleNamespace(id='cs_1', url='u')):
            _build_checkout_session(request, self.plan)
        self.assertIn(t.BEGAN_CHECKOUT, events(self.user))

    def test_checkout_completed_with_card_trial_then_first_payment(self):
        from apps.accounts.payment_views import handle_checkout_session_completed, handle_invoice_paid
        sub = self.user.subscription
        sub.stripe_customer_id = 'cus_9'
        sub.save()
        stripe_sub = StripeObj(status='trialing', metadata={'tier': 'premium'},
                               items={'data': [{'price': {'id': 'price_y'}}]})
        with patch('stripe.Subscription.retrieve', return_value=stripe_sub), \
                patch('apps.accounts.payment_views._subscription_period', return_value=(None, None)):
            handle_checkout_session_completed({'customer': 'cus_9', 'subscription': 'sub_9', 'metadata': {}})
        self.assertTrue({t.SUBSCRIBED, t.STARTED_TRIAL} <= events(self.user))
        self.assertNotIn(t.CONVERTED_PAID, events(self.user))
        handle_invoice_paid({'customer': 'cus_9', 'subscription': 'sub_9', 'amount_paid': 0, 'id': 'in_0'})
        self.assertNotIn(t.CONVERTED_PAID, events(self.user))  # $0 trial invoice isn't a payment
        handle_invoice_paid({'customer': 'cus_9', 'subscription': 'sub_9', 'amount_paid': 5999, 'id': 'in_1'})
        self.assertIn(t.CONVERTED_PAID, events(self.user))
        # A renewal a year later records nothing new and must not break the
        # webhook's transaction (ATOMIC_REQUESTS in production).
        from django.db import transaction
        with transaction.atomic():
            handle_invoice_paid({'customer': 'cus_9', 'subscription': 'sub_9', 'amount_paid': 5999, 'id': 'in_2'})
            self.assertEqual(ABTestConversion.objects.filter(
                assignment__user=self.user, conversion_type=t.CONVERTED_PAID).count(), 1)


class ReportTests(TestCase):
    def test_report_and_command(self):
        t.setup_test()
        for i in range(10):
            u = signup(f'r{i}')
            if i % 3 == 0:
                t.track(u, t.CONVERTED_PAID)
        r = t.report()
        total = r['rows'][t.CONTROL]['users'] + r['rows'][t.VARIANT]['users']
        self.assertEqual(total, 10)
        self.assertFalse(r['enough_data'])
        out = StringIO()
        call_command('trial_test_report', stdout=out)
        self.assertIn('Too early to call', out.getvalue())
        self.assertIn('Paid (first real payment)', out.getvalue())

    def test_p_value(self):
        self.assertLess(t._two_proportion_p(5, 200, 25, 200), 0.01)
        self.assertGreater(t._two_proportion_p(10, 200, 11, 200), 0.5)
        self.assertIsNone(t._two_proportion_p(0, 0, 1, 10))

    def test_week_two_retention(self):
        from apps.accounts.models import DailyCheckIn
        t.setup_test()
        u = signup('old')
        User.objects.filter(pk=u.pk).update(date_joined=timezone.now() - timedelta(days=20))
        u.refresh_from_db()
        DailyCheckIn.objects.create(user=u, mood=3, energy_level=3,
                                    date=(u.date_joined + timedelta(days=9)).date())
        row = t.report()['rows'][variant_of(u)]
        self.assertEqual((row['week2_eligible'], row['week2_retained']), (1, 1))


@override_settings(SITE_URL='https://www.myrecoverypal.com', FOUNDING_OFFER_ENDS='2099-12-31')
class TrialEndingEmailTests(TestCase):
    def test_no_card_trial_email_shows_usage_and_founding_price(self):
        from apps.accounts.models import RecoveryCoachSession, CoachMessage
        from apps.accounts.tasks import send_trial_ending_notifications
        SubscriptionPlan.objects.update_or_create(
            tier='premium', billing_period='yearly',
            defaults={'name': 'Premium Annual', 'price': Decimal('59.99'), 'is_active': True})
        t.setup_test()
        u = None
        for i in range(30):
            cand = signup(f'e{i}')
            if variant_of(cand) == t.VARIANT:
                u = cand
                break
        self.assertIsNotNone(u)
        sub = u.subscription
        sub.refresh_from_db()
        sub.trial_end = timezone.now() + timedelta(hours=30)
        sub.save()
        session = RecoveryCoachSession.objects.create(user=u)
        CoachMessage.objects.create(session=session, role='user', content='private words')
        with patch('apps.accounts.tasks.send_email', return_value=True) as send:
            send_trial_ending_notifications()
        html = next(c.kwargs['html_message'] for c in send.call_args_list if c.kwargs['recipient_email'] == u.email)
        self.assertIn('7-day Premium trial ends tomorrow', html)
        self.assertIn('You talked with Anchor 1 time', html)
        self.assertNotIn('private words', html)  # counts only, never content
        self.assertIn('/accounts/founding/', html)
        self.assertNotIn('14-day', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DashboardTests(TestCase):
    def test_dashboard_shows_trial_test(self):
        t.setup_test()
        signup('d1')
        staff = User.objects.create_user('staff', 'staff@example.com', 'pw12345!', is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get(reverse('admin_ab_test_results'))
        self.assertContains(resp, t.TEST_NAME)
        self.assertContains(resp, 'First real payment')
        self.assertContains(resp, 'Active in week 2')
        self.assertNotContains(resp, 'Completed Step 1')  # onboarding events not shown for this test
