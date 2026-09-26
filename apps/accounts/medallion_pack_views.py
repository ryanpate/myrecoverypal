"""HD Medallion Pack: one-time $4.99 Stripe Checkout (free for Premium) and downloads."""
import logging
import re
from urllib.parse import urlencode

import stripe
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.analytics import queue_ga_event

from .medallion_models import MedallionPackPurchase
from .medallion_pack import PACK_KIND, PACK_PRICE_CENTS, fulfil_checkout_session
from .milestone_image import (
    BADGE_STYLES, TEXT_COLORS, TIME_FORMATS, generate_milestone_image, generate_story_image,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# format key -> (label, filename suffix, renderer)
PACK_FORMATS = {
    'hd': ('HD print quality (2048 × 2048)', 'hd',
           lambda p: generate_milestone_image(p.days, size=2048, watermark=False, **p.badge_kwargs())),
    'square': ('Square for posting (1080 × 1080)', 'square',
               lambda p: generate_milestone_image(p.days, watermark=False, **p.badge_kwargs())),
    'story': ('Story & phone wallpaper (1080 × 1920)', 'story',
              lambda p: generate_story_image(p.days, **p.badge_kwargs())),
}


def _is_premium(user):
    return (user.is_authenticated and hasattr(user, 'subscription')
            and user.subscription.is_premium())


def _badge_fields(data):
    """Validated badge parameters from the creator form (same rules as the image view)."""
    try:
        days = max(1, min(36500, int(data.get('days', 90))))
    except (TypeError, ValueError):
        days = 90
    try:
        font_size = max(24, min(160, int(data.get('font_size', 110))))
    except (TypeError, ValueError):
        font_size = 110
    style = data.get('style', 'classic')
    time_format = data.get('time_format', 'auto')
    color = data.get('color', 'white')
    if color not in TEXT_COLORS and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        color = 'white'
    return {
        'days': days,
        'style': style if style in BADGE_STYLES else 'classic',
        'name': re.sub(r'[^\w\s.\'-]', '', data.get('name', ''))[:30],
        'time_format': time_format if time_format in TIME_FORMATS else 'auto',
        'font_size': font_size,
        'color': color,
        'outline': data.get('outline', '1') == '1',
    }


@require_POST
def medallion_pack_checkout(request):
    """Start a pack purchase. Premium/Court members skip payment (it's included)."""
    fields = _badge_fields(request.POST)
    user = request.user if request.user.is_authenticated else None

    if _is_premium(request.user):
        purchase = MedallionPackPurchase.objects.create(
            user=user, email=user.email, status='paid', amount_cents=0, **fields)
        return redirect('accounts:medallion_pack', token=purchase.token)

    purchase = MedallionPackPurchase.objects.create(
        user=user, email=user.email if user else '', amount_cents=PACK_PRICE_CENTS, **fields)
    creator_url = request.build_absolute_uri(reverse('accounts:milestone_badge_creator'))
    params = {'days': fields['days'], 'style': fields['style']}
    session_kwargs = {
        'mode': 'payment',
        'line_items': [{
            'quantity': 1,
            'price_data': {
                'currency': 'usd',
                'unit_amount': PACK_PRICE_CENTS,
                'product_data': {
                    'name': f'HD Medallion Pack — {fields["days"]} days '
                            f'({BADGE_STYLES[fields["style"]]["label"]})',
                    'description': 'HD print-quality medallion, square post and '
                                   'story/phone-wallpaper versions.',
                },
            },
        }],
        'metadata': {'kind': PACK_KIND, 'purchase_id': str(purchase.id)},
        'client_reference_id': str(purchase.id),
        'success_url': request.build_absolute_uri(reverse('accounts:medallion_pack_success'))
                       + '?session_id={CHECKOUT_SESSION_ID}',
        'cancel_url': f'{creator_url}?{urlencode(params)}',
    }
    if user:
        session_kwargs['customer_email'] = user.email
    try:
        session = stripe.checkout.Session.create(**session_kwargs)
    except stripe.error.StripeError:
        logger.exception('Medallion pack checkout failed for purchase %s', purchase.id)
        purchase.delete()
        return redirect(f'{reverse("accounts:milestone_badge_creator")}?{urlencode(params)}')

    purchase.stripe_session_id = session.id
    purchase.save(update_fields=['stripe_session_id'])
    return _see_other(session.url)


def _see_other(url):
    """303 so the browser follows the POST with a GET to Stripe's hosted page."""
    response = HttpResponse(status=303)
    response['Location'] = url
    return response


def medallion_pack_success(request):
    """Stripe success redirect: confirm payment directly (don't wait on the webhook)."""
    session_id = request.GET.get('session_id', '')
    purchase = get_object_or_404(MedallionPackPurchase, stripe_session_id=session_id)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        logger.exception('Could not retrieve medallion pack session %s', session_id)
        session = None
    if session and fulfil_checkout_session(session) and not request.session.get(f'pack_ga_{purchase.pk}'):
        request.session[f'pack_ga_{purchase.pk}'] = True
        queue_ga_event(request, 'purchase', currency='USD',
                       value=purchase.amount_cents / 100, item_name='medallion_pack')
    return redirect('accounts:medallion_pack', token=purchase.token)


def medallion_pack(request, token):
    """The pack's download page. The unguessable token is the credential."""
    purchase = get_object_or_404(MedallionPackPurchase, token=token)
    formats = [
        {'key': key, 'label': label,
         'url': reverse('accounts:medallion_pack_file', args=[token, key])}
        for key, (label, _suffix, _render) in PACK_FORMATS.items()
    ]
    if purchase.status == 'paid':  # show buyers the clean version they paid for
        preview_url = reverse('accounts:medallion_pack_file', args=[token, 'square'])
    else:
        preview_url = (reverse('accounts:milestone_image', args=[purchase.days]) + '?'
                       + urlencode({**purchase.badge_kwargs(), 'outline': int(purchase.outline)}))
    return render(request, 'accounts/medallion_pack.html', {
        'purchase': purchase,
        'formats': formats,
        'preview_url': preview_url,
    })


def medallion_pack_file(request, token, fmt):
    purchase = get_object_or_404(MedallionPackPurchase, token=token, status='paid')
    if fmt not in PACK_FORMATS:
        raise Http404
    _label, suffix, render_format = PACK_FORMATS[fmt]
    response = HttpResponse(render_format(purchase), content_type='image/png')
    response['Content-Disposition'] = (
        f'attachment; filename="myrecoverypal-medallion-{purchase.days}-days-{suffix}.png"')
    response['Cache-Control'] = 'private, max-age=3600'
    return response
