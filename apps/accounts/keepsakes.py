"""Printify keepsakes: the buyer's medallion printed on a mug or a round sticker.

Flow: Stripe Checkout (collects the US shipping address) -> fulfil_keepsake_session
(idempotent; success page and webhook both call it) -> Celery submit_keepsake_order
creates the Printify order -> send_keepsake_to_production pushes it to production
once Printify has finished cost calculation -> Printify's order:shipment:created
webhook marks it shipped and emails tracking.
"""
import logging
from io import BytesIO

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw

from . import printify
from .email_service import send_email
from .medallion_models import KeepsakeOrder
from .milestone_image import milestone_badge_image

logger = logging.getLogger(__name__)

KEEPSAKE_KIND = 'keepsake'

# Printify catalog ids were read from the live catalog (2026-09-26); US shipping
# is included in the price. Mug cost verified with a cancelled test order:
# $6.44 base + $7.29 shipping.
PRODUCTS = {
    'mug': {
        'label': 'Medallion Mug (11oz)', 'price_cents': 2499,
        'blueprint_id': 68, 'print_provider_id': 1, 'variant_id': 33719,
        'canvas': (2700, 1120), 'coin': 1000, 'centers': (675, 2025),
    },
    'sticker': {
        'label': 'Medallion Sticker (3" round)', 'price_cents': 799,
        'blueprint_id': 564, 'print_provider_id': 73, 'variant_id': 70876,
        'canvas': (1200, 1200), 'coin': 1200, 'centers': (600,),
    },
}

# Printify statuses meaning "created, but production can't be requested yet".
_NOT_READY = {'pending', 'cost-calculation'}
# Our statuses in which the Printify order can still be cancelled on refund.
_CANCELLABLE = {'paid', 'submitted'}


def _coin(order, diameter):
    """The medallion cropped to its round coin (no velvet corners) on transparency."""
    coin = milestone_badge_image(order.days, size=diameter, watermark=False,
                                 **order.badge_kwargs()).convert('RGBA')
    mask = Image.new('L', (diameter, diameter), 0)
    inset = round(diameter * 0.025)
    ImageDraw.Draw(mask).ellipse((inset, inset, diameter - inset, diameter - inset), fill=255)
    coin.putalpha(mask)
    return coin


def render_print_file(order):
    """PNG print file for Printify: transparent canvas with the coin(s) placed."""
    spec = PRODUCTS[order.product]
    width, height = spec['canvas']
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    coin = _coin(order, spec['coin'])
    for cx in spec['centers']:
        canvas.alpha_composite(coin, (cx - spec['coin'] // 2, (height - spec['coin']) // 2))
    buffer = BytesIO()
    canvas.save(buffer, 'PNG', optimize=True)
    return buffer.getvalue()


def _order_url(order):
    return settings.SITE_URL.rstrip('/') + reverse('accounts:keepsake_order', args=[order.token])


def _shipping_from_session(session):
    # Stripe moved shipping_details under collected_information in newer API versions.
    return (session.get('shipping_details')
            or (session.get('collected_information') or {}).get('shipping_details')
            or {})


def fulfil_keepsake_session(session):
    """Mark a paid keepsake checkout as paid, store the address and queue submission."""
    metadata = session.get('metadata') or {}
    if metadata.get('kind') != KEEPSAKE_KIND or session.get('payment_status') != 'paid':
        return None

    with transaction.atomic():
        try:
            order = KeepsakeOrder.objects.select_for_update().get(pk=metadata.get('order_id'))
        except (KeepsakeOrder.DoesNotExist, ValueError, TypeError):
            logger.error('Keepsake session %s has no matching order', session.get('id'))
            return None
        newly_paid = order.status == 'pending'
        if newly_paid:
            order.status = 'paid'
            order.paid_at = timezone.now()
            shipping = _shipping_from_session(session)
            details = session.get('customer_details') or {}
            order.shipping_name = shipping.get('name') or details.get('name') or ''
            order.shipping_address = shipping.get('address') or {}
            order.shipping_phone = details.get('phone') or ''
            order.email = order.email or details.get('email') or ''
            order.stripe_payment_intent_id = session.get('payment_intent') or ''
        should_email = order.email and not order.receipt_emailed and order.status != 'refunded'
        if should_email:
            order.receipt_emailed = True
        order.save()

    if newly_paid:
        transaction.on_commit(lambda: submit_keepsake_order.delay(order.id))
    if should_email:
        _email(order, 'Your medallion keepsake is on its way to the printer',
               f'Thank you! Your {PRODUCTS[order.product]["label"]} celebrating '
               f'{order.days} days is being made. We\'ll email you tracking as soon as it ships.')
    return order


def _printify_payload(order):
    spec = PRODUCTS[order.product]
    address = order.shipping_address or {}
    first, _, last = (order.shipping_name or 'Friend').partition(' ')
    return {
        'external_id': f'mrp-keepsake-{order.id}',
        'label': f'MRP keepsake #{order.id}',
        'line_items': [{
            'blueprint_id': spec['blueprint_id'],
            'print_provider_id': spec['print_provider_id'],
            'variant_id': spec['variant_id'],
            'print_areas': {
                'front': settings.SITE_URL.rstrip('/')
                         + reverse('accounts:keepsake_print_file', args=[order.token]),
            },
            'quantity': 1,
        }],
        'shipping_method': 1,
        'send_shipping_notification': False,
        'address_to': {
            'first_name': first,
            'last_name': last or first,
            'email': order.email,
            'phone': order.shipping_phone,
            'country': address.get('country', 'US'),
            'region': address.get('state', ''),
            'address1': address.get('line1', ''),
            'address2': address.get('line2') or '',
            'city': address.get('city', ''),
            'zip': address.get('postal_code', ''),
        },
    }


def submit_to_printify(order):
    """Create the Printify order once (it starts on hold)."""
    with transaction.atomic():
        order = KeepsakeOrder.objects.select_for_update().get(pk=order.pk)
        if order.printify_order_id or order.status != 'paid':
            return order
        order.printify_order_id = printify.create_order(_printify_payload(order))
        order.status = 'submitted'
        order.last_error = ''
        order.save(update_fields=['printify_order_id', 'status', 'last_error'])
    return order


def advance_to_production(order):
    """Send an on-hold Printify order to production. Returns 'sent', 'wait' or 'done'."""
    if order.status != 'submitted':
        return 'done'
    status = printify.get_order(order.printify_order_id).get('status')
    if status in _NOT_READY:
        return 'wait'
    if status == 'on-hold':
        printify.send_to_production(order.printify_order_id)
    order.status = 'in_production'
    order.save(update_fields=['status'])
    return 'sent'


def _mark_failed(order, error):
    order.status = 'failed'
    order.last_error = str(error)[:2000]
    order.save(update_fields=['status', 'last_error'])
    logger.error('Keepsake order %s failed: %s', order.pk, error)
    try:
        send_email(
            subject=f'Keepsake order #{order.pk} needs attention',
            plain_message=(f'Keepsake order #{order.pk} ({order.product}, {order.email}) could '
                           f'not be fulfilled automatically.\n\nError: {error}\n\n'
                           f'Printify order: {order.printify_order_id or "not created"}\n'
                           f'Stripe payment: {order.stripe_payment_intent_id}'),
            html_message=f'<pre>Keepsake order #{order.pk} failed: {error}</pre>',
            recipient_email=settings.SUPPORT_EMAIL,
        )
    except Exception:
        logger.exception('Could not send keepsake failure alert for %s', order.pk)


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def submit_keepsake_order(self, order_id):
    order = KeepsakeOrder.objects.get(pk=order_id)
    try:
        order = submit_to_printify(order)
    except printify.PrintifyError as exc:
        if self.request.retries >= self.max_retries:
            _mark_failed(order, exc)
            return
        raise self.retry(exc=exc)
    if order.status == 'submitted':
        send_keepsake_to_production.apply_async(args=[order.id], countdown=30)


@shared_task(bind=True, max_retries=20, default_retry_delay=60)
def send_keepsake_to_production(self, order_id):
    order = KeepsakeOrder.objects.get(pk=order_id)
    try:
        result = advance_to_production(order)
    except printify.PrintifyError as exc:
        result, error = 'wait', exc
    else:
        error = None
    if result == 'wait':
        if self.request.retries >= self.max_retries:
            _mark_failed(order, error or 'Printify order never left cost calculation')
            return
        raise self.retry(exc=error)


def handle_printify_event(event):
    """Printify webhook: mark shipped and email tracking on order:shipment:created."""
    if event.get('type') != 'order:shipment:created':
        return
    resource = event.get('resource') or {}
    carrier = (resource.get('data') or {}).get('carrier') or {}
    order = KeepsakeOrder.objects.filter(printify_order_id=resource.get('id')).first()
    if not order:
        return
    order.status = 'shipped'
    order.tracking_url = carrier.get('tracking_url') or ''
    order.tracking_number = carrier.get('tracking_number') or ''
    order.carrier = carrier.get('code') or ''
    notify = order.email and not order.shipped_emailed
    order.shipped_emailed = order.shipped_emailed or bool(notify)
    order.save()
    if notify:
        tracking = f'\n\nTrack it here: {order.tracking_url}' if order.tracking_url else ''
        _email(order, 'Your medallion keepsake has shipped',
               f'Your {PRODUCTS[order.product]["label"]} is on its way!{tracking}')


def refund_keepsake(payment_intent_id):
    """charge.refunded: mark refunded and cancel at Printify if it isn't printed yet."""
    order = KeepsakeOrder.objects.filter(stripe_payment_intent_id=payment_intent_id).first() \
        if payment_intent_id else None
    if not order:
        return False
    if order.status in _CANCELLABLE and order.printify_order_id:
        try:
            printify.cancel_order(order.printify_order_id)
        except printify.PrintifyError:
            logger.exception('Could not cancel Printify order for refunded keepsake %s', order.pk)
    elif order.status in ('in_production', 'shipped'):
        logger.warning('Keepsake %s refunded after production started; cost not recoverable', order.pk)
    order.status = 'refunded'
    order.save(update_fields=['status'])
    return True


def _email(order, subject, body):
    url = _order_url(order)
    try:
        send_email(
            subject=subject,
            plain_message=f'{body}\n\nOrder status: {url}\n\n— MyRecoveryPal',
            html_message=(f'<p>{body}</p><p><a href="{url}">View your order</a></p>'
                          '<p>— MyRecoveryPal</p>'),
            recipient_email=order.email,
        )
    except Exception:
        logger.exception('Failed to email keepsake order %s', order.pk)
