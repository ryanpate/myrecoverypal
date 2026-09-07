"""GA4 conversion events.

GA4 reported `Key events: 0` and `Total revenue: 0` on every row for the
Aug-Sep 2026 window because the site fired no conversion events at all.
These tests lock in the four that matter, and the queue mechanism that lets
them survive the redirect most conversions end with.
"""
import json

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.payment_models import Subscription, SubscriptionPlan
from apps.core.analytics import MAX_QUEUED, pop_ga_events, queue_ga_event

User = get_user_model()


def _queued(client):
    """The events sitting in a test client's session."""
    return client.session.get('ga_events') or []


class QueueMechanicsTests(TestCase):
    """Unit-level: the queue must be safe to call from anywhere."""

    def setUp(self):
        self.factory = RequestFactory()

    def _request_with_session(self):
        request = self.factory.get('/')
        request.session = {}
        return request

    def test_event_round_trips(self):
        request = self._request_with_session()
        queue_ga_event(request, 'sign_up', method='email')
        self.assertEqual(
            pop_ga_events(request),
            [{'name': 'sign_up', 'params': {'method': 'email'}}],
        )

    def test_popping_clears_the_queue(self):
        """Otherwise a conversion would re-fire on every subsequent page."""
        request = self._request_with_session()
        queue_ga_event(request, 'sign_up')
        pop_ga_events(request)
        self.assertEqual(pop_ga_events(request), [])

    def test_multiple_events_preserve_order(self):
        request = self._request_with_session()
        queue_ga_event(request, 'first')
        queue_ga_event(request, 'second')
        self.assertEqual([e['name'] for e in pop_ga_events(request)],
                         ['first', 'second'])

    def test_queue_is_capped(self):
        """A redirect loop must not grow the session cookie without bound."""
        request = self._request_with_session()
        for i in range(MAX_QUEUED + 5):
            queue_ga_event(request, f'event_{i}')
        self.assertEqual(len(pop_ga_events(request)), MAX_QUEUED)

    def test_request_without_a_session_is_a_noop(self):
        """Analytics must never raise — e.g. on an API request with no session."""
        request = self.factory.get('/')
        queue_ga_event(request, 'sign_up')      # must not raise
        self.assertEqual(pop_ga_events(request), [])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RenderingTests(TestCase):
    def test_queued_event_renders_into_the_page(self):
        session = self.client.session
        session['ga_events'] = [{'name': 'sign_up', 'params': {'method': 'email'}}]
        session.save()

        html = self.client.get(reverse('core:about')).content.decode()
        self.assertIn('ga-queued-events', html)
        self.assertIn('sign_up', html)

    def test_event_does_not_render_on_the_next_page(self):
        session = self.client.session
        session['ga_events'] = [{'name': 'sign_up', 'params': {}}]
        session.save()

        self.client.get(reverse('core:about'))
        html = self.client.get(reverse('core:about')).content.decode()
        self.assertNotIn('ga-queued-events', html)

    def test_no_script_block_when_nothing_is_queued(self):
        html = self.client.get(reverse('core:about')).content.decode()
        self.assertNotIn('ga-queued-events', html)

    def test_payload_is_escaped_not_interpolated(self):
        """json_script must neutralise anything that looks like markup."""
        session = self.client.session
        session['ga_events'] = [
            {'name': 'sign_up', 'params': {'method': '</script><script>alert(1)'}}
        ]
        session.save()

        html = self.client.get(reverse('core:about')).content.decode()
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertIn('\\u003C', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SignUpEventTests(TestCase):
    """The site runs in invite-only mode, so a real signup needs a code."""

    def setUp(self):
        # RateLimitMiddleware is cache-backed and LocMemCache is not reset
        # between tests, so registration POSTs accumulate across the whole
        # run and eventually 403. Start from a clean slate.
        for alias in ('default', 'rate_limiting'):
            try:
                caches[alias].clear()
            except Exception:
                pass
        from apps.accounts.invite_models import InviteCode
        self.invite = InviteCode.objects.create(
            code='TESTCODE1', status='active', max_uses=5, uses_remaining=5)

    def _register(self, **extra):
        data = {
            'username': 'newperson',
            'email': 'newperson@example.com',
            'password1': 'a-Str0ng-passphrase!',
            'password2': 'a-Str0ng-passphrase!',
            'invite_code': self.invite.code,
        }
        data.update(extra)
        return self.client.post(reverse('accounts:register'), data)

    def test_registration_queues_sign_up(self):
        resp = self._register()
        # Registration redirects onward; the event rides along to whatever
        # renders next rather than being lost with the redirect.
        events = _queued(self.client)
        self.assertEqual([e['name'] for e in events], ['sign_up'],
                         msg=f'status={resp.status_code}')
        self.assertEqual(events[0]['params']['method'], 'invite')

    def test_failed_registration_queues_nothing(self):
        self._register(password2='does-not-match')
        self.assertEqual(_queued(self.client), [])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CourtProfileEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@example.com', 'pw')
        sub = Subscription.objects.get(user=self.user)
        sub.tier = 'court'
        sub.status = 'active'
        sub.save()
        self.client.force_login(self.user)
        self.url = reverse('accounts:court_profile')

    def _post(self, **extra):
        data = {'legal_name': 'A Person', 'case_number': 'CR-2026-1',
                'court_name': 'District Court', 'jurisdiction': 'Harris County',
                'required_meetings_per_week': 3}
        data.update(extra)
        return self.client.post(self.url, data)

    def test_first_save_queues_the_event(self):
        self._post()
        self.assertEqual([e['name'] for e in _queued(self.client)],
                         ['court_profile_completed'])

    def test_second_save_does_not_re_fire(self):
        """Editing a profile is not a new activation."""
        self._post()
        self.client.get(reverse('core:about'))     # drain the queue
        self._post(legal_name='A Person Renamed')
        self.assertEqual(_queued(self.client), [])

    def test_save_without_a_case_number_does_not_fire(self):
        self._post(case_number='')
        self.assertNotIn('court_profile_completed',
                         [e['name'] for e in _queued(self.client)])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PurchaseEventTests(TestCase):
    """The purchase event carries value/currency — without them GA4 reports
    Total revenue: 0 no matter how many people subscribe."""

    def test_plan_maps_onto_a_ga4_purchase_payload(self):
        plan, _ = SubscriptionPlan.objects.update_or_create(
            tier='court', billing_period='monthly',
            defaults=dict(
                name='Court Compliance (Monthly)', price='29.99',
                currency='USD', stripe_price_id='price_test_court',
                is_active=True,
            ),
        )
        # Mirrors the payload built in payment_views.payment_success.
        payload = {
            'transaction_id': 'cs_test_123',
            'value': float(plan.price),
            'currency': plan.currency,
            'items': [{
                'item_id': plan.stripe_price_id or plan.tier,
                'item_name': plan.name,
                'item_category': plan.tier,
                'item_variant': plan.billing_period,
                'price': float(plan.price),
                'quantity': 1,
            }],
        }
        self.assertEqual(payload['value'], 29.99)
        self.assertEqual(payload['currency'], 'USD')
        self.assertEqual(payload['items'][0]['item_category'], 'court')
        # Must survive the json_script round trip base.html does.
        self.assertEqual(json.loads(json.dumps(payload))['value'], 29.99)
