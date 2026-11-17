"""Gift a year of Premium: public landing, one-time Stripe Checkout, gift card, redeem."""
import logging

import segno
import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.analytics import queue_begin_checkout, queue_ga_event, queue_one_off_purchase

from . import gifts
from .checkout_guard import once_per_minute
from .gift_models import PremiumGift

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

ITEM_NAME = 'Gift: a year of Premium'


def gift_premium(request):
    """Landing page: who it's for, what they get, and the buy form."""
    cents = gifts.price_cents()
    return render(request, 'accounts/gift_premium.html', {
        'price': f'{cents / 100:.2f}',
        'per_week': f'{cents / 100 / 52:.2f}',
    })


@require_POST
@once_per_minute('gift')
def gift_checkout(request):
    cents = gifts.price_cents()
    gift = PremiumGift.objects.create(
        amount_cents=cents,
        from_name=request.POST.get('from_name', '').strip()[:40],
        message=' '.join(request.POST.get('message', '').split())[:280],
    )
    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[{
                'quantity': 1,
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': cents,
                    'product_data': {
                        'name': 'A year of MyRecoveryPal Premium (gift)',
                        'description': 'One payment. Never renews. You get a printable '
                                       'gift card and a link to give.',
                    },
                },
            }],
            metadata={'kind': gifts.GIFT_KIND, 'gift_id': str(gift.id)},
            client_reference_id=str(gift.id),
            success_url=request.build_absolute_uri(reverse('core:gift_success'))
                        + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('core:gift_premium')),
            idempotency_key=f'gift-{gift.id}',
        )
    except stripe.error.StripeError:
        logger.exception('Premium gift checkout failed for gift %s', gift.id)
        gift.delete()
        messages.error(request, "We couldn't start checkout. Please try again.")
        return redirect('core:gift_premium')

    gift.stripe_session_id = session.id
    gift.save(update_fields=['stripe_session_id'])
    queue_begin_checkout(request, cents, gifts.GIFT_KIND, ITEM_NAME)
    # 303 so the browser follows the POST with a GET to Stripe's hosted page.
    response = HttpResponse(status=303)
    response['Location'] = session.url
    return response


def gift_success(request):
    """Stripe success redirect: confirm payment directly (don't wait on the webhook)."""
    session_id = request.GET.get('session_id', '')
    gift = get_object_or_404(PremiumGift, stripe_session_id=session_id)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        logger.exception('Could not retrieve premium gift session %s', session_id)
        session = None
    if session and gifts.fulfil_checkout_session(session) and not request.session.get(f'gift_ga_{gift.pk}'):
        request.session[f'gift_ga_{gift.pk}'] = True
        queue_one_off_purchase(request, session_id, gift.amount_cents, gifts.GIFT_KIND, ITEM_NAME)
    return redirect(reverse('core:gift_card', args=[gift.token]) + '?giver=1')


def gift_card(request, token):
    """The gift itself. The giver (?giver=1) gets print and copy tools; the
    person it's for gets the redeem button."""
    gift = get_object_or_404(PremiumGift, token=token)
    card_path = reverse('core:gift_card', args=[token])
    card_url = request.build_absolute_uri(card_path)
    giver = request.GET.get('giver') == '1' and gift.redeemable
    return render(request, 'accounts/gift_card.html', {
        'gift': gift,
        'giver': giver,
        'card_url': card_url,
        'card_path': card_path,
        # The printed card carries a QR; on screen the recipient sees the seal.
        'qr_svg': segno.make(card_url, error='m').svg_inline(scale=4, dark='#16324f') if giver else '',
        'blocked_reason': gifts.blocked_reason(request.user) if request.user.is_authenticated else '',
    })


@login_required
@require_POST
def gift_redeem(request, token):
    ok, message = gifts.redeem(token, request.user)
    if not ok:
        messages.warning(request, message)
        return redirect('core:gift_card', token=token)
    queue_ga_event(request, 'gift_redeemed')
    messages.success(request, f'{message} Every program, the full audio library and Anchor are open.')
    return redirect('accounts:progress')
