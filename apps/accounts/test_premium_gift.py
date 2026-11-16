"""Tests for gifting a year of Premium: checkout, fulfilment, redemption, expiry."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts import gifts
from apps.accounts.gift_models import PremiumGift
from apps.accounts.payment_models import SubscriptionPlan
from apps.accounts.payment_views import handle_charge_refunded, handle_checkout_session_completed

User = get_user_model()


def _gift(**overrides):
    fields = {'amount_cents': 5999, 'status': 'paid', 'from_name': 'Mom', 'message': 'Proud of you.'}
    fields.update(overrides)
    return PremiumGift.objects.create(**fields)


def _user(name='sam'):
    return User.objects.create_user(username=name, email=f'{name}@example.com', password='pw')


def _session(gift, status='paid'):
    return {
        'id': gift.stripe_session_id or 'cs_gift', 'payment_status': status, 'payment_intent': 'pi_gift',
        'metadata': {'kind': 'premium_gift', 'gift_id': str(gift.id)},
        'customer_details': {'email': 'buyer@example.com'},
    }


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class GiftCheckoutTest(TestCase):

    def test_landing_page_is_public_and_shows_yearly_price(self):
        SubscriptionPlan.objects.filter(tier='premium', billing_period='yearly').delete()
        SubscriptionPlan.objects.create(
            name='Premium Yearly', tier='premium', billing_period='yearly', price='49.00', is_active=True)
        resp = self.client.get(reverse('core:gift_premium'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '$49.00')
        self.assertContains(resp, reverse('core:gift_checkout'))

    @patch('apps.accounts.gift_views.stripe.checkout.Session.create')
    def test_anonymous_checkout_creates_pending_gift_and_redirects(self, create):
        create.return_value = SimpleNamespace(id='cs_g1', url='https://checkout.stripe.test/g1')
        resp = self.client.post(reverse('core:gift_checkout'), {
            'from_name': '  Mom  ', 'message': 'Proud\n of   you. ' + 'x' * 400})
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp['Location'], 'https://checkout.stripe.test/g1')
        gift = PremiumGift.objects.get()
        self.assertEqual((gift.status, gift.stripe_session_id, gift.from_name), ('pending', 'cs_g1', 'Mom'))
        self.assertTrue(gift.message.startswith('Proud of you. x'))
        self.assertEqual(len(gift.message), 280)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['mode'], 'payment')
        self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'], gifts.price_cents())
        self.assertEqual(kwargs['metadata'], {'kind': 'premium_gift', 'gift_id': str(gift.id)})
        [event] = self.client.session['ga_events']
        self.assertEqual(event['name'], 'begin_checkout')

    @patch('apps.accounts.gifts.send_email')
    @patch('apps.accounts.gift_views.stripe.checkout.Session.retrieve')
    def test_success_marks_paid_emails_buyer_once_and_shows_giver_tools(self, retrieve, send):
        gift = _gift(status='pending', stripe_session_id='cs_ok')
        retrieve.return_value = _session(gift)
        url = reverse('core:gift_success') + '?session_id=cs_ok'
        resp = self.client.get(url)
        card = reverse('core:gift_card', args=[gift.token])
        self.assertRedirects(resp, card + '?giver=1', fetch_redirect_response=False)
        self.client.get(url)  # reload must not double-email
        gift.refresh_from_db()
        self.assertEqual((gift.status, gift.buyer_email, gift.stripe_payment_intent_id),
                         ('paid', 'buyer@example.com', 'pi_gift'))
        self.assertEqual(send.call_count, 1)
        self.assertIn(card, send.call_args.kwargs['plain_message'])
        [event] = [e for e in self.client.session['ga_events'] if e['name'] == 'purchase']
        self.assertEqual(event['params']['transaction_id'], 'cs_ok')

        page = self.client.get(card + '?giver=1')
        self.assertContains(page, 'Print the card')
        self.assertContains(page, '<svg')  # QR for the printed card
        self.assertEqual(page.context['card_url'], 'http://testserver' + card)

    @patch('apps.accounts.gifts.send_email')
    def test_webhook_fulfils_gift_and_unpaid_session_does_not(self, send):
        gift = _gift(status='pending', stripe_session_id='cs_wh')
        handle_checkout_session_completed(_session(gift, status='unpaid'))
        gift.refresh_from_db()
        self.assertEqual(gift.status, 'pending')
        handle_checkout_session_completed(_session(gift))
        gift.refresh_from_db()
        self.assertEqual(gift.status, 'paid')
        self.assertEqual(send.call_count, 1)

    def test_refund_cancels_unredeemed_gift_only(self):
        unopened = _gift(stripe_payment_intent_id='pi_a')
        opened = _gift(stripe_payment_intent_id='pi_b', redeemed_at=timezone.now())
        handle_charge_refunded({'id': 'ch_a', 'payment_intent': 'pi_a'})
        handle_charge_refunded({'id': 'ch_b', 'payment_intent': 'pi_b'})
        unopened.refresh_from_db()
        opened.refresh_from_db()
        self.assertEqual((unopened.status, opened.status), ('refunded', 'paid'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class GiftRedeemTest(TestCase):

    def test_anonymous_recipient_is_sent_to_signup_and_back(self):
        gift = _gift()
        card = reverse('core:gift_card', args=[gift.token])
        resp = self.client.get(card)
        self.assertContains(resp, 'Mom gave you a year.')
        self.assertContains(resp, f'{reverse("accounts:register")}?next={card}')
        self.assertNotContains(resp, 'Print the card')
        self.assertNotContains(resp, 'buyer@example.com')
        resp = self.client.post(reverse('core:gift_redeem', args=[gift.token]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:login'), resp['Location'])

    def test_redeem_gives_a_year_of_premium_once(self):
        gift = _gift()
        user = _user()
        self.client.login(username='sam', password='pw')
        resp = self.client.post(reverse('core:gift_redeem', args=[gift.token]))
        self.assertRedirects(resp, reverse('accounts:progress'), fetch_redirect_response=False)
        sub = user.subscription
        sub.refresh_from_db()
        self.assertTrue(sub.is_premium())
        self.assertEqual((sub.tier, sub.status, sub.subscription_source), ('premium', 'active', 'gift'))
        self.assertAlmostEqual(sub.current_period_end, timezone.now() + timedelta(days=365),
                               delta=timedelta(minutes=1))
        gift.refresh_from_db()
        self.assertEqual(gift.redeemed_by, user)

        # The same link can't be used by someone else.
        other = _user('alex')
        ok, _message = gifts.redeem(gift.token, other)
        self.assertFalse(ok)
        other.subscription.refresh_from_db()
        self.assertFalse(other.subscription.is_premium())
        self.assertContains(self.client.get(reverse('core:gift_card', args=[gift.token])),
                            'This gift has been opened')

    def test_unpaid_or_refunded_gift_cannot_be_redeemed(self):
        user = _user()
        for status in ('pending', 'refunded'):
            ok, _message = gifts.redeem(_gift(status=status).token, user)
            self.assertFalse(ok, status)
        user.subscription.refresh_from_db()
        self.assertFalse(user.subscription.is_premium())

    def test_paying_member_keeps_gift_unused(self):
        gift = _gift()
        user = _user()
        sub = user.subscription
        sub.tier, sub.status, sub.subscription_source = 'premium', 'active', 'stripe'
        sub.stripe_subscription_id = 'sub_live'
        sub.save()
        self.client.login(username='sam', password='pw')
        self.assertContains(self.client.get(reverse('core:gift_card', args=[gift.token])),
                            'already have a paid plan')
        self.client.post(reverse('core:gift_redeem', args=[gift.token]))
        gift.refresh_from_db()
        sub.refresh_from_db()
        self.assertTrue(gift.redeemable)
        self.assertEqual((sub.subscription_source, sub.stripe_subscription_id), ('stripe', 'sub_live'))

    def test_second_gift_adds_a_second_year(self):
        user = _user()
        gifts.redeem(_gift().token, user)
        ok, _message = gifts.redeem(_gift().token, user)
        self.assertTrue(ok)
        user.subscription.refresh_from_db()
        self.assertAlmostEqual(user.subscription.current_period_end, timezone.now() + timedelta(days=730),
                               delta=timedelta(minutes=1))


class GiftLifecycleTest(TestCase):

    def _gifted(self, name, ends_in):
        user = _user(name)
        gifts.redeem(_gift().token, user)
        sub = user.subscription
        sub.refresh_from_db()
        sub.current_period_end = timezone.now() + ends_in
        sub.save()
        return sub

    @patch('apps.accounts.gifts.send_email', return_value=True)
    def test_reminder_goes_out_a_week_before_the_end_only(self, send):
        self._gifted('early', timedelta(days=30))
        due = self._gifted('due', timedelta(days=7, hours=5))
        self.assertEqual(gifts.send_ending_reminders(), 1)
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['recipient_email'], due.user.email)
        self.assertIn('/accounts/keep-premium/', kwargs['plain_message'])

    def test_expiry_moves_only_ended_gifts_to_free(self):
        ended = self._gifted('ended', -timedelta(hours=1))
        current = self._gifted('current', timedelta(days=3))
        payer = _user('payer').subscription
        payer.tier, payer.status, payer.subscription_source = 'premium', 'active', 'stripe'
        payer.current_period_end = timezone.now() - timedelta(days=1)  # webhook lag, not ours to expire
        payer.save()

        from apps.accounts.tasks import gifted_premium_daily
        gifted_premium_daily()
        for sub in (ended, current, payer):
            sub.refresh_from_db()
        self.assertEqual((ended.tier, ended.status), ('free', 'expired'))
        self.assertFalse(ended.is_premium())
        self.assertTrue(current.is_premium())
        self.assertTrue(payer.is_premium())

    def test_promo_code_does_not_shorten_a_gifted_year(self):
        from apps.accounts.payment_models import Promo
        from apps.accounts.promo_service import apply_promo_to_user
        sub = self._gifted('promo', timedelta(days=300))
        Promo.objects.create(code='TRY30', trial_days=30, active=True)
        applied, _message = apply_promo_to_user(sub.user, 'TRY30')
        self.assertFalse(applied)
        sub.refresh_from_db()
        self.assertEqual((sub.status, sub.subscription_source), ('active', 'gift'))
