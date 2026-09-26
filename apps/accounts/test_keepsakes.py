"""Tests for Printify keepsakes (medallion mug + round sticker, auto-fulfilled)."""
import hashlib
import hmac
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.medallion_models import KeepsakeOrder

User = get_user_model()

DESIGN = {'days': '90', 'style': 'classic', 'name': 'Sam', 'time_format': 'auto',
          'font_size': '110', 'color': 'gold', 'outline': '1'}

SHIPPING = {
    'name': 'Sam Rivera',
    'address': {'line1': '100 Congress Ave', 'line2': 'Apt 4', 'city': 'Austin',
                'state': 'TX', 'postal_code': '78701', 'country': 'US'},
}


def _order(**kw):
    fields = dict(product='mug', days=90, style='classic', name='Sam', color='gold',
                  amount_cents=2499, status='paid', email='buyer@example.com',
                  shipping_name='Sam Rivera', shipping_address=SHIPPING['address'])
    fields.update(kw)
    return KeepsakeOrder.objects.create(**fields)


def _paid_session(order, **extra):
    session = {
        'id': 'cs_keep', 'payment_status': 'paid', 'payment_intent': 'pi_keep',
        'metadata': {'kind': 'keepsake', 'order_id': str(order.id)},
        'customer_details': {'email': 'buyer@example.com', 'phone': None},
        'shipping_details': SHIPPING,
    }
    session.update(extra)
    return session


class PrintFileTest(TestCase):

    def setUp(self):
        cache.clear()

    def test_mug_print_is_transparent_wrap_with_two_coins(self):
        from apps.accounts.keepsakes import render_print_file
        img = Image.open(BytesIO(render_print_file(_order(product='mug'))))
        self.assertEqual((img.size, img.mode), ((2700, 1120), 'RGBA'))
        self.assertEqual(img.getpixel((5, 5))[3], 0)            # background transparent
        self.assertEqual(img.getpixel((1350, 560))[3], 0)       # gap between the two coins
        self.assertEqual(img.getpixel((675, 560))[3], 255)      # coin on each side
        self.assertEqual(img.getpixel((2025, 560))[3], 255)

    def test_sticker_print_is_round_coin(self):
        from apps.accounts.keepsakes import render_print_file
        img = Image.open(BytesIO(render_print_file(_order(product='sticker'))))
        self.assertEqual((img.size, img.mode), ((1200, 1200), 'RGBA'))
        self.assertEqual(img.getpixel((3, 3))[3], 0)
        self.assertEqual(img.getpixel((600, 600))[3], 255)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class KeepsakeCheckoutTest(TestCase):

    @patch('apps.accounts.keepsake_views.stripe.checkout.Session.create')
    def test_checkout_collects_us_shipping_and_charges_product_price(self, create):
        create.return_value = SimpleNamespace(id='cs_k1', url='https://checkout.stripe.test/k1')
        resp = self.client.post(reverse('accounts:keepsake_checkout'), {**DESIGN, 'product': 'mug'})
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp['Location'], 'https://checkout.stripe.test/k1')
        order = KeepsakeOrder.objects.get()
        self.assertEqual((order.status, order.product, order.amount_cents, order.stripe_session_id),
                         ('pending', 'mug', 2499, 'cs_k1'))
        kw = create.call_args.kwargs
        self.assertEqual(kw['mode'], 'payment')
        self.assertEqual(kw['shipping_address_collection'], {'allowed_countries': ['US']})
        self.assertEqual(kw['line_items'][0]['price_data']['unit_amount'], 2499)
        self.assertEqual(kw['metadata'], {'kind': 'keepsake', 'order_id': str(order.id)})

    @patch('apps.accounts.keepsake_views.stripe.checkout.Session.create')
    def test_sticker_price(self, create):
        create.return_value = SimpleNamespace(id='cs_k2', url='https://checkout.stripe.test/k2')
        self.client.post(reverse('accounts:keepsake_checkout'), {**DESIGN, 'product': 'sticker'})
        self.assertEqual(KeepsakeOrder.objects.get().amount_cents, 799)

    @patch('apps.accounts.keepsake_views.stripe.checkout.Session.create')
    def test_unknown_product_rejected(self, create):
        resp = self.client.post(reverse('accounts:keepsake_checkout'), {**DESIGN, 'product': 'yacht'})
        self.assertEqual(resp.status_code, 400)
        create.assert_not_called()
        self.assertFalse(KeepsakeOrder.objects.exists())


class KeepsakeFulfilmentTest(TestCase):

    @patch('apps.accounts.keepsakes.send_email')
    @patch('apps.accounts.keepsakes.submit_keepsake_order')
    def test_paid_session_stores_address_and_submits_once(self, submit, send):
        from apps.accounts.keepsakes import fulfil_keepsake_session
        order = _order(status='pending', email='', shipping_name='', shipping_address={})
        with self.captureOnCommitCallbacks(execute=True):
            fulfil_keepsake_session(_paid_session(order))
            fulfil_keepsake_session(_paid_session(order))  # webhook + success page both fire
        order.refresh_from_db()
        self.assertEqual((order.status, order.email, order.shipping_name),
                         ('paid', 'buyer@example.com', 'Sam Rivera'))
        self.assertEqual(order.shipping_address['city'], 'Austin')
        submit.delay.assert_called_once_with(order.id)
        self.assertEqual(send.call_count, 1)

    @patch('apps.accounts.keepsakes.send_email')
    @patch('apps.accounts.keepsakes.submit_keepsake_order')
    def test_newer_stripe_api_shipping_location_is_read(self, submit, send):
        from apps.accounts.keepsakes import fulfil_keepsake_session
        order = _order(status='pending', shipping_name='', shipping_address={})
        session = _paid_session(order, shipping_details=None,
                                collected_information={'shipping_details': SHIPPING})
        fulfil_keepsake_session(session)
        order.refresh_from_db()
        self.assertEqual(order.shipping_address['postal_code'], '78701')

    def test_webhook_routes_keepsake_sessions(self):
        from apps.accounts.payment_views import handle_checkout_session_completed
        order = _order(status='pending')
        with patch('apps.accounts.keepsakes.fulfil_keepsake_session') as inner:
            handle_checkout_session_completed(_paid_session(order))
        inner.assert_called_once()


@override_settings(SITE_URL='https://www.myrecoverypal.com', PRINTIFY_SHOP_ID=27555231)
class PrintifySubmitTest(TestCase):

    @patch('apps.accounts.keepsakes.printify.create_order', return_value='pf_123')
    def test_submit_creates_printify_order_with_print_url_and_address(self, create):
        from apps.accounts.keepsakes import submit_to_printify
        order = _order()
        submit_to_printify(order)
        order.refresh_from_db()
        self.assertEqual((order.printify_order_id, order.status), ('pf_123', 'submitted'))
        payload = create.call_args.args[0]
        item = payload['line_items'][0]
        self.assertEqual((item['blueprint_id'], item['print_provider_id'], item['variant_id']),
                         (68, 1, 33719))
        self.assertEqual(item['print_areas']['front'],
                         'https://www.myrecoverypal.com'
                         + reverse('accounts:keepsake_print_file', args=[order.token]))
        addr = payload['address_to']
        self.assertEqual((addr['first_name'], addr['last_name'], addr['region'], addr['zip']),
                         ('Sam', 'Rivera', 'TX', '78701'))
        self.assertEqual(payload['external_id'], f'mrp-keepsake-{order.id}')

    @patch('apps.accounts.keepsakes.printify.create_order')
    def test_submit_is_idempotent(self, create):
        from apps.accounts.keepsakes import submit_to_printify
        order = _order(status='submitted', printify_order_id='pf_existing')
        submit_to_printify(order)
        create.assert_not_called()

    @patch('apps.accounts.keepsakes.printify.send_to_production')
    @patch('apps.accounts.keepsakes.printify.get_order', return_value={'status': 'on-hold'})
    def test_on_hold_order_is_sent_to_production(self, get, send):
        from apps.accounts.keepsakes import advance_to_production
        order = _order(status='submitted', printify_order_id='pf_1')
        self.assertEqual(advance_to_production(order), 'sent')
        send.assert_called_once_with('pf_1')
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_production')

    @patch('apps.accounts.keepsakes.printify.send_to_production')
    @patch('apps.accounts.keepsakes.printify.get_order', return_value={'status': 'cost-calculation'})
    def test_order_still_calculating_waits(self, get, send):
        from apps.accounts.keepsakes import advance_to_production
        order = _order(status='submitted', printify_order_id='pf_2')
        self.assertEqual(advance_to_production(order), 'wait')
        send.assert_not_called()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class KeepsakePagesTest(TestCase):

    def setUp(self):
        cache.clear()

    def test_print_file_only_for_paid_orders(self):
        paid = _order(product='sticker')
        resp = self.client.get(reverse('accounts:keepsake_print_file', args=[paid.token]))
        self.assertEqual((resp.status_code, resp['Content-Type']), (200, 'image/png'))
        pending = _order(status='pending')
        resp = self.client.get(reverse('accounts:keepsake_print_file', args=[pending.token]))
        self.assertEqual(resp.status_code, 404)

    def test_order_page_shows_status_and_tracking(self):
        order = _order(status='shipped', tracking_url='https://track.example/1Z')
        resp = self.client.get(reverse('accounts:keepsake_order', args=[order.token]))
        self.assertContains(resp, 'https://track.example/1Z')
        self.assertContains(resp, 'noindex')

    def test_creator_offers_keepsakes(self):
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertContains(resp, 'id="keepsake-form"')
        self.assertContains(resp, '$24.99')
        self.assertContains(resp, '$7.99')


@override_settings(PRINTIFY_WEBHOOK_SECRET='whsec_test', PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PrintifyWebhookTest(TestCase):

    def _post(self, body, secret='whsec_test'):
        raw = json.dumps(body).encode()
        sig = 'sha256=' + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return self.client.post(reverse('accounts:printify_webhook'), raw,
                                content_type='application/json', HTTP_X_PFY_SIGNATURE=sig)

    def _shipment(self, printify_id):
        return {'type': 'order:shipment:created', 'resource': {
            'id': printify_id, 'type': 'order',
            'data': {'carrier': {'code': 'USPS', 'tracking_number': '9400',
                                 'tracking_url': 'https://track.example/9400'}}}}

    @patch('apps.accounts.keepsakes.send_email')
    def test_shipment_marks_shipped_and_emails_tracking(self, send):
        order = _order(status='in_production', printify_order_id='pf_ship')
        resp = self._post(self._shipment('pf_ship'))
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual((order.status, order.tracking_url), ('shipped', 'https://track.example/9400'))
        self.assertEqual(send.call_count, 1)

    def test_bad_signature_rejected(self):
        order = _order(status='in_production', printify_order_id='pf_bad')
        resp = self._post(self._shipment('pf_bad'), secret='wrong')
        self.assertEqual(resp.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, 'in_production')


class KeepsakeRefundTest(TestCase):

    @patch('apps.accounts.keepsakes.printify.cancel_order')
    def test_refund_before_production_cancels_printify_order(self, cancel):
        from apps.accounts.payment_views import handle_charge_refunded
        order = _order(status='submitted', printify_order_id='pf_r', stripe_payment_intent_id='pi_r')
        handle_charge_refunded({'id': 'ch_r', 'customer': None, 'amount_refunded': 2499,
                                'payment_intent': 'pi_r', 'currency': 'usd'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'refunded')
        cancel.assert_called_once_with('pf_r')
