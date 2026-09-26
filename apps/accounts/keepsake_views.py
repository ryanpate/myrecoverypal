"""Printify keepsakes: Stripe Checkout, order status page, print file, Printify webhook."""
import hashlib
import hmac
import json
import logging
from urllib.parse import urlencode

import stripe
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.analytics import queue_ga_event

from .keepsakes import (
    KEEPSAKE_KIND, PRODUCTS, fulfil_keepsake_session, handle_printify_event, render_print_file,
)
from .medallion_models import KeepsakeOrder
from .medallion_pack_views import _badge_fields, _see_other
from .milestone_image import BADGE_STYLES

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@require_POST
def keepsake_checkout(request):
    product = request.POST.get('product')
    if product not in PRODUCTS:
        return HttpResponseBadRequest('Unknown product')
    spec = PRODUCTS[product]
    fields = _badge_fields(request.POST)
    user = request.user if request.user.is_authenticated else None

    order = KeepsakeOrder.objects.create(
        user=user, email=user.email if user else '', product=product,
        amount_cents=spec['price_cents'], **fields)
    params = {'days': fields['days'], 'style': fields['style']}
    creator_url = request.build_absolute_uri(reverse('accounts:milestone_badge_creator'))
    session_kwargs = {
        'mode': 'payment',
        'line_items': [{
            'quantity': 1,
            'price_data': {
                'currency': 'usd',
                'unit_amount': spec['price_cents'],
                'product_data': {
                    'name': f'{spec["label"]}: {fields["days"]} days '
                            f'({BADGE_STYLES[fields["style"]]["label"]})',
                    'description': 'Your custom recovery medallion, printed and shipped. '
                                   'Free US shipping.',
                },
            },
        }],
        'shipping_address_collection': {'allowed_countries': ['US']},
        'phone_number_collection': {'enabled': True},
        'metadata': {'kind': KEEPSAKE_KIND, 'order_id': str(order.id)},
        'client_reference_id': str(order.id),
        'success_url': request.build_absolute_uri(reverse('accounts:keepsake_success'))
                       + '?session_id={CHECKOUT_SESSION_ID}',
        'cancel_url': f'{creator_url}?{urlencode(params)}',
    }
    if user:
        session_kwargs['customer_email'] = user.email
    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError:
        logger.exception('Keepsake checkout failed for order %s', order.id)
        order.delete()
        return redirect(f'{reverse("accounts:milestone_badge_creator")}?{urlencode(params)}')

    order.stripe_session_id = session.id
    order.save(update_fields=['stripe_session_id'])
    return _see_other(session.url)


def keepsake_success(request):
    """Stripe success redirect: confirm payment directly rather than waiting on the webhook."""
    session_id = request.GET.get('session_id', '')
    order = get_object_or_404(KeepsakeOrder, stripe_session_id=session_id)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        logger.exception('Could not retrieve keepsake session %s', session_id)
        session = None
    if session and fulfil_keepsake_session(session) and not request.session.get(f'keep_ga_{order.pk}'):
        request.session[f'keep_ga_{order.pk}'] = True
        queue_ga_event(request, 'purchase', currency='USD',
                       value=order.amount_cents / 100, item_name=f'keepsake_{order.product}')
    return redirect('accounts:keepsake_order', token=order.token)


def keepsake_order(request, token):
    order = get_object_or_404(KeepsakeOrder, token=token)
    preview_url = (reverse('accounts:milestone_image', args=[order.days]) + '?'
                   + urlencode({**order.badge_kwargs(), 'outline': int(order.outline)}))
    return render(request, 'accounts/keepsake_order.html', {
        'order': order,
        'product': PRODUCTS[order.product],
        'preview_url': preview_url,
    })


def keepsake_print_file(request, token):
    """The print file Printify downloads. Only exists once the order is paid."""
    order = get_object_or_404(KeepsakeOrder, token=token)
    if order.status in ('pending', 'refunded'):
        raise Http404
    response = HttpResponse(render_print_file(order), content_type='image/png')
    response['Cache-Control'] = 'private, max-age=3600'
    return response


@csrf_exempt
@require_POST
def printify_webhook(request):
    secret = settings.PRINTIFY_WEBHOOK_SECRET
    expected = 'sha256=' + hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(request.headers.get('X-Pfy-Signature', ''), expected):
        return HttpResponseForbidden('Bad signature')
    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest('Invalid JSON')
    handle_printify_event(event)
    return HttpResponse(status=200)
