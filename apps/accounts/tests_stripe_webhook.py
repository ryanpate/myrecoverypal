# apps/accounts/tests_stripe_webhook.py
"""Tests for Stripe webhook subscription handling across API versions."""
import inspect
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts import payment_views
from apps.accounts.payment_models import Transaction
from apps.accounts.payment_views import (
    handle_charge_refunded,
    handle_checkout_session_completed,
    handle_dispute_created,
    handle_invoice_paid,
    handle_payment_action_required,
    handle_subscription_updated,
)

User = get_user_model()


class SubscriptionUpdatedPeriodTest(TestCase):
    """Stripe's Basil release (2025-03-31) moved current_period_start/end off
    the subscription and onto its items. The webhook must handle both shapes."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='sub_user', email='s@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_subscription_id = 'sub_test_periods'
        sub.tier = 'premium'
        sub.status = 'active'
        sub.save()

        self.start_ts = 1757000000
        self.end_ts = self.start_ts + 30 * 86400

    def _expected(self, ts):
        return datetime.fromtimestamp(ts, tz=dt_timezone.utc)

    def test_legacy_payload_with_top_level_periods(self):
        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'active',
            'current_period_start': self.start_ts,
            'current_period_end': self.end_ts,
        })

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_basil_payload_with_item_level_periods(self):
        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'active',
            'items': {'data': [{
                'current_period_start': self.start_ts,
                'current_period_end': self.end_ts,
            }]},
        })

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_payload_without_any_periods_keeps_existing_values(self):
        existing_start = self._expected(self.start_ts)
        existing_end = self._expected(self.end_ts)
        sub = self.user.subscription
        sub.current_period_start = existing_start
        sub.current_period_end = existing_end
        sub.save()

        handle_subscription_updated({
            'id': 'sub_test_periods',
            'status': 'past_due',
        })

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'past_due')
        self.assertEqual(sub.current_period_start, existing_start)
        self.assertEqual(sub.current_period_end, existing_end)


class FakeStripeObject(dict):
    """Minimal stand-in for stripe.StripeObject: dict access plus attributes."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class InvoicePaidPaymentIdsTest(TestCase):
    """Basil removed the invoice's top-level charge/payment_intent; the ids now
    live on invoice.payments. Transactions should record them from either shape."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='invoice_user', email='i@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_customer_id = 'cus_invoice_test'
        sub.tier = 'premium'
        sub.save()

    def _invoice(self, **extra):
        return dict({
            'id': 'in_test_001',
            'customer': 'cus_invoice_test',
            'amount_paid': 499,
            'currency': 'usd',
        }, **extra)

    def test_legacy_payload_records_charge_and_payment_intent(self):
        handle_invoice_paid(self._invoice(
            charge='ch_legacy_001',
            payment_intent='pi_legacy_001',
        ))

        txn = Transaction.objects.get(stripe_invoice_id='in_test_001')
        self.assertEqual(txn.stripe_charge_id, 'ch_legacy_001')
        self.assertEqual(txn.stripe_payment_intent_id, 'pi_legacy_001')
        self.assertEqual(txn.amount, Decimal('4.99'))

    def test_basil_payload_records_payment_intent_from_payments(self):
        handle_invoice_paid(self._invoice(payments={'data': [{
            'status': 'paid',
            'payment': {'type': 'payment_intent', 'payment_intent': 'pi_basil_001'},
        }]}))

        txn = Transaction.objects.get(stripe_invoice_id='in_test_001')
        self.assertEqual(txn.stripe_payment_intent_id, 'pi_basil_001')
        self.assertIsNone(txn.stripe_charge_id)

    def test_basil_payload_records_charge_when_payment_is_a_charge(self):
        handle_invoice_paid(self._invoice(payments={'data': [{
            'status': 'paid',
            'payment': {'type': 'charge', 'charge': 'ch_basil_001'},
        }]}))

        txn = Transaction.objects.get(stripe_invoice_id='in_test_001')
        self.assertEqual(txn.stripe_charge_id, 'ch_basil_001')

    def test_basil_payload_skips_unpaid_payments(self):
        handle_invoice_paid(self._invoice(payments={'data': [
            {'status': 'canceled',
             'payment': {'type': 'payment_intent', 'payment_intent': 'pi_canceled'}},
            {'status': 'paid',
             'payment': {'type': 'payment_intent', 'payment_intent': 'pi_paid'}},
        ]}))

        txn = Transaction.objects.get(stripe_invoice_id='in_test_001')
        self.assertEqual(txn.stripe_payment_intent_id, 'pi_paid')

    def test_payload_without_payment_details_still_records_transaction(self):
        handle_invoice_paid(self._invoice())

        txn = Transaction.objects.get(stripe_invoice_id='in_test_001')
        self.assertIsNone(txn.stripe_charge_id)
        self.assertIsNone(txn.stripe_payment_intent_id)


class CheckoutCompletedPeriodTest(TestCase):
    """stripe.Subscription.retrieve() returns whichever shape the SDK's pinned
    API version renders, so the checkout handler must read both."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='checkout_user', email='co@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_customer_id = 'cus_checkout_test'
        sub.tier = 'free'
        sub.save()

        self.start_ts = 1757000000
        self.end_ts = self.start_ts + 30 * 86400

    def _retrieved(self, **extra):
        return FakeStripeObject(dict({
            'id': 'sub_checkout_test',
            'status': 'active',
            'metadata': {'tier': 'premium'},
            'items': {'data': [{'price': {'id': 'price_test'}}]},
        }, **extra))

    def _expected(self, ts):
        return datetime.fromtimestamp(ts, tz=dt_timezone.utc)

    def _complete(self, stripe_subscription):
        with patch('apps.accounts.payment_views.stripe.Subscription.retrieve',
                   return_value=stripe_subscription):
            handle_checkout_session_completed({
                'customer': 'cus_checkout_test',
                'subscription': 'sub_checkout_test',
            })

    def test_legacy_shape_sets_period(self):
        self._complete(self._retrieved(
            current_period_start=self.start_ts,
            current_period_end=self.end_ts,
        ))

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_basil_shape_sets_period_from_items(self):
        self._complete(self._retrieved(items={'data': [{
            'price': {'id': 'price_test'},
            'current_period_start': self.start_ts,
            'current_period_end': self.end_ts,
        }]}))

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.current_period_start, self._expected(self.start_ts))
        self.assertEqual(sub.current_period_end, self._expected(self.end_ts))

    def test_missing_period_does_not_abort_the_tier_update(self):
        self._complete(self._retrieved())

        sub = self.user.subscription
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.stripe_subscription_id, 'sub_checkout_test')
        self.assertIsNone(sub.current_period_end)


class RefundAndDisputeEventTest(TestCase):
    """Money leaving the business needs to be recorded and, for disputes,
    escalated to a human — Stripe won't chase us about the response deadline."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='refund_user', email='r@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_customer_id = 'cus_refund_test'
        sub.tier = 'premium'
        sub.save()

    def test_refund_records_a_refund_transaction(self):
        handle_charge_refunded({
            'id': 'ch_refund_001',
            'customer': 'cus_refund_test',
            'payment_intent': 'pi_refund_001',
            'amount': 499,
            'amount_refunded': 499,
            'currency': 'usd',
        })

        txn = Transaction.objects.get(transaction_type='refund')
        self.assertEqual(txn.user, self.user)
        self.assertEqual(txn.status, 'refunded')
        self.assertEqual(txn.amount, Decimal('4.99'))
        self.assertEqual(txn.stripe_charge_id, 'ch_refund_001')
        self.assertEqual(txn.stripe_payment_intent_id, 'pi_refund_001')

    def test_repeated_refund_events_do_not_duplicate_the_record(self):
        payload = {
            'id': 'ch_refund_002',
            'customer': 'cus_refund_test',
            'amount': 499,
            'amount_refunded': 200,
            'currency': 'usd',
        }
        handle_charge_refunded(payload)
        handle_charge_refunded(dict(payload, amount_refunded=499))

        txn = Transaction.objects.get(transaction_type='refund')
        self.assertEqual(txn.amount, Decimal('4.99'))

    @patch('apps.accounts.payment_views.send_email')
    def test_dispute_alerts_the_support_inbox(self, mock_send):
        handle_dispute_created({
            'id': 'dp_001',
            'charge': 'ch_refund_001',
            'amount': 499,
            'currency': 'usd',
            'reason': 'fraudulent',
            'status': 'warning_needs_response',
            'evidence_details': {'due_by': 1757600000},
        })

        self.assertEqual(mock_send.call_count, 1)
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['recipient_email'], settings.SUPPORT_EMAIL)
        self.assertIn('dp_001', kwargs['plain_message'])
        self.assertIn('fraudulent', kwargs['plain_message'])
        # Resend rejects a null html body, so the alert must carry one.
        self.assertTrue(kwargs['html_message'])
        self.assertIn('dp_001', kwargs['html_message'])

    @patch('apps.accounts.payment_views.send_email')
    def test_payment_action_required_emails_the_customer(self, mock_send):
        handle_payment_action_required({
            'id': 'in_action_001',
            'customer': 'cus_refund_test',
            'amount_due': 499,
            'currency': 'usd',
            'hosted_invoice_url': 'https://invoice.stripe.com/i/test',
        })

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs['recipient_email'], 'r@example.com')


class WebhookDispatchTest(TestCase):
    """Every event we ask Stripe to send should reach a handler."""

    HANDLED = [
        'checkout.session.completed',
        'invoice.paid',
        'invoice.payment_failed',
        'invoice.payment_action_required',
        'customer.subscription.updated',
        'customer.subscription.deleted',
        'customer.subscription.trial_will_end',
        'charge.refunded',
        'charge.dispute.created',
    ]

    def test_all_expected_events_are_dispatched(self):
        source = inspect.getsource(payment_views.stripe_webhook)
        for event_type in self.HANDLED:
            self.assertIn(f"'{event_type}'", source, f'{event_type} is not handled')

    @patch('apps.accounts.payment_views.stripe.Webhook.construct_event')
    def test_unknown_event_is_acknowledged_not_500ed(self, mock_construct):
        mock_construct.return_value = {
            'type': 'invoice.upcoming',
            'data': {'object': {'id': 'in_x'}},
        }

        # Prod forces https + www; Stripe posts to that canonical URL, but the
        # test client speaks plain http to `testserver`.
        with override_settings(STRIPE_WEBHOOK_SECRET='whsec_test',
                               PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
            response = self.client.post(
                reverse('accounts:stripe_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='t=1,v1=sig',
            )

        self.assertEqual(response.status_code, 200)


class CancelSubscriptionTest(TestCase):
    """Cancellation is confirmed by Stripe before we render the message, so
    rendering must not be able to fail the request."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cancel_user', email='ca@example.com', password='pw'
        )
        sub = self.user.subscription
        sub.stripe_subscription_id = 'sub_cancel_test'
        sub.tier = 'premium'
        sub.current_period_end = None
        sub.save()
        self.client.force_login(self.user)

    @override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
    @patch('apps.accounts.payment_views.stripe.Subscription.modify')
    def test_cancel_succeeds_without_a_known_period_end(self, mock_modify):
        response = self.client.post(reverse('accounts:cancel_subscription'), follow=True)

        mock_modify.assert_called_once_with('sub_cancel_test', cancel_at_period_end=True)
        texts = [m.message for m in response.context['messages']]
        self.assertTrue(any('scheduled for cancellation' in t for t in texts), texts)
        self.assertFalse(any('error' in t.lower() for t in texts), texts)

        self.user.subscription.refresh_from_db()
        self.assertIsNotNone(self.user.subscription.canceled_at)
