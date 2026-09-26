"""HD Medallion Pack: fulfilment shared by the success page and the Stripe webhook."""
import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .email_service import send_email
from .medallion_models import MedallionPackPurchase

logger = logging.getLogger(__name__)

PACK_PRICE_CENTS = 499
PACK_KIND = 'medallion_pack'


def fulfil_checkout_session(session):
    """Mark the purchase behind a paid Checkout Session as paid and email the link.

    Called from both the success redirect and the webhook, in either order and
    possibly repeatedly — so it is idempotent (row lock + receipt_emailed flag).
    Returns the purchase, or None if the session isn't a paid pack session.
    """
    metadata = session.get('metadata') or {}
    if metadata.get('kind') != PACK_KIND or session.get('payment_status') != 'paid':
        return None

    with transaction.atomic():
        try:
            purchase = MedallionPackPurchase.objects.select_for_update().get(
                pk=metadata.get('purchase_id'))
        except (MedallionPackPurchase.DoesNotExist, ValueError, TypeError):
            logger.error('Medallion pack session %s has no matching purchase', session.get('id'))
            return None
        if purchase.status == 'pending':
            purchase.status = 'paid'
            purchase.paid_at = timezone.now()
        purchase.stripe_payment_intent_id = session.get('payment_intent') or purchase.stripe_payment_intent_id
        email = (session.get('customer_details') or {}).get('email')
        if email and not purchase.email:
            purchase.email = email
        should_email = purchase.status == 'paid' and purchase.email and not purchase.receipt_emailed
        if should_email:
            purchase.receipt_emailed = True
        purchase.save()

    if should_email:
        _send_receipt(purchase)
    return purchase


def _send_receipt(purchase):
    url = settings.SITE_URL.rstrip('/') + reverse('accounts:medallion_pack', args=[purchase.token])
    plain = (
        f'Thank you, and congratulations on {purchase.days} days.\n\n'
        f'Your HD Medallion Pack is ready. Download it any time here:\n{url}\n\n'
        'Keep this email: the link is your key to the pack.\n\n— MyRecoveryPal'
    )
    html = (
        f'<p>Thank you, and congratulations on <strong>{purchase.days} days</strong>.</p>'
        f'<p>Your HD Medallion Pack is ready:</p>'
        f'<p><a href="{url}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">Download your pack</a></p>'
        f'<p style="color:#666;font-size:13px;">Keep this email: the link is your key to the pack.</p>'
    )
    try:
        send_email(
            subject='Your HD Medallion Pack is ready',
            plain_message=plain, html_message=html,
            recipient_email=purchase.email,
        )
    except Exception:
        logger.exception('Failed to email medallion pack %s', purchase.pk)


def revoke_for_refund(payment_intent_id):
    """Disable a refunded pack. Returns True if a pack matched the payment."""
    if not payment_intent_id:
        return False
    return MedallionPackPurchase.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
    ).update(status='refunded') > 0
