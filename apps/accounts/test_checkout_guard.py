"""A repeated checkout POST must not create a second order or Stripe session."""
from itertools import count
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.gift_models import PremiumGift

CREATE = 'apps.accounts.gift_views.stripe.checkout.Session.create'


def _fake_sessions():
    ids = count(1)

    def create(**kwargs):
        n = next(ids)
        return SimpleNamespace(id=f'cs_test_{n}', url=f'https://checkout.stripe.com/c/pay/{n}')
    return create


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CheckoutOncePerMinuteTests(TestCase):
    URL = '/gift/checkout/'

    def setUp(self):
        cache.clear()

    def test_identical_repeat_gets_the_first_session(self):
        with patch(CREATE, side_effect=_fake_sessions()) as create:
            first = self.client.post(self.URL, {'from_name': 'Sam', 'message': 'Proud of you'})
            second = self.client.post(self.URL, {'from_name': 'Sam', 'message': 'Proud of you'})
        self.assertEqual(first.status_code, 303)
        self.assertEqual(second.status_code, 303)
        self.assertEqual(first['Location'], second['Location'])
        self.assertEqual(create.call_count, 1)
        self.assertEqual(PremiumGift.objects.count(), 1)

    def test_different_details_start_a_new_checkout(self):
        with patch(CREATE, side_effect=_fake_sessions()) as create:
            first = self.client.post(self.URL, {'from_name': 'Sam'})
            second = self.client.post(self.URL, {'from_name': 'Alex'})
        self.assertNotEqual(first['Location'], second['Location'])
        self.assertEqual(create.call_count, 2)

    def test_failed_checkout_is_not_remembered(self):
        with patch(CREATE, side_effect=stripe.error.APIConnectionError('down')):
            failed = self.client.post(self.URL, {'from_name': 'Sam'})
        self.assertEqual(failed.status_code, 302)
        with patch(CREATE, side_effect=_fake_sessions()) as create:
            retry = self.client.post(self.URL, {'from_name': 'Sam'})
        self.assertEqual(retry.status_code, 303)
        self.assertEqual(create.call_count, 1)

    def test_stripe_call_carries_the_orders_idempotency_key(self):
        with patch(CREATE, side_effect=_fake_sessions()) as create:
            self.client.post(self.URL, {'from_name': 'Sam'})
        gift = PremiumGift.objects.get()
        self.assertEqual(create.call_args.kwargs['idempotency_key'], f'gift-{gift.id}')
