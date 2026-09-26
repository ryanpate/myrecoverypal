"""HD Medallion Pack: fulfilment shared by the success page and the Stripe webhook."""
import logging

from celery import shared_task
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
        newly_paid = purchase.status == 'pending'
        if newly_paid:
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

    if newly_paid:
        queue_video_prerender(purchase.id)
    if should_email:
        _send_receipt(purchase)
    return purchase


def queue_video_prerender(purchase_id):
    """Queue the video render after commit. Never fails the caller: the render
    is only a speed-up (downloads fall back to rendering on demand), so a broker
    outage must not turn a completed payment into an error page."""
    def _queue():
        try:
            prerender_pack_video.delay(purchase_id)
        except Exception:
            logger.exception('Could not queue video pre-render for medallion pack %s', purchase_id)
    transaction.on_commit(_queue)


@shared_task(ignore_result=True)
def prerender_pack_video(purchase_id):
    """Render the pack's animated video on the worker so it's cached before download.

    The render takes several seconds of CPU; doing it here keeps it off the
    web workers. The download view still renders on demand if the cached copy
    has expired, so a failure here only costs speed.
    """
    from .medallion_video import generate_story_video
    purchase = MedallionPackPurchase.objects.filter(pk=purchase_id, status='paid').first()
    if not purchase:
        return
    try:
        generate_story_video(purchase.days, **purchase.badge_kwargs())
    except Exception:
        logger.exception('Pre-rendering video for medallion pack %s failed', purchase_id)


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


def _milestone_label(days):
    if days >= 365 and days % 365 == 0:
        years = days // 365
        return f'{years}-year'
    return f'{days}-day'


def send_premium_milestone_medallion(user, milestone_days):
    """Premium celebration: the member's medallion pack for this milestone, emailed.

    Uses the design of their most recently saved medallion (else Classic),
    pre-renders the animated video, and replaces the shop promo email for that
    milestone. Returns True once the email is sent; the MilestoneEmailSent row
    (shared with the shop email) makes it once per milestone, and is only
    written after a successful send so a failure retries the next day.
    """
    from apps.store.email_service import _build_unsubscribe_url
    from apps.store.models import MilestoneEmailSent
    from .models import SavedBadge

    if not user.email or MilestoneEmailSent.objects.filter(
            user=user, milestone_days=milestone_days).exists():
        return False

    pack = MedallionPackPurchase.objects.filter(
        user=user, days=milestone_days, amount_cents=0, status='paid').first()
    if not pack:
        badge = SavedBadge.objects.filter(user=user).order_by('-id').first()
        design = ({'style': badge.style, 'name': badge.name, 'time_format': badge.time_format,
                   'font_size': badge.font_size, 'color': badge.color, 'outline': badge.outline}
                  if badge else {'style': 'classic'})
        pack = MedallionPackPurchase.objects.create(
            user=user, email=user.email, status='paid', amount_cents=0,
            paid_at=timezone.now(), days=milestone_days, **design)
        queue_video_prerender(pack.id)

    site = settings.SITE_URL.rstrip('/')
    pack_url = site + reverse('accounts:medallion_pack', args=[pack.token])
    image_url = site + reverse('accounts:medallion_pack_file', args=[pack.token, 'square'])
    keepsake_url = site + reverse('accounts:milestone_badge_creator') + f'?days={milestone_days}'
    unsubscribe = _build_unsubscribe_url(user)
    label = _milestone_label(milestone_days)
    from django.utils.html import escape
    name = user.first_name or 'friend'
    plain = (
        f'Congratulations, {name}. {milestone_days} days.\n\n'
        f'Your {label} medallion is ready: the HD version, a story and phone wallpaper, '
        f'and an animated video to share.\n{pack_url}\n\n'
        f'Want to hold it? As a Premium member you get 20% off a mug or sticker: {keepsake_url}\n\n'
        f'Unsubscribe from milestone emails: {unsubscribe}'
    )
    html = (
        f'<p>Congratulations, {escape(name)}. <strong>{milestone_days} days.</strong></p>'
        f'<p><img src="{image_url}" alt="Your {label} medallion" width="320" '
        f'style="max-width:100%;border-radius:12px;"></p>'
        f'<p>Your {label} medallion is ready: HD, story and phone wallpaper, and an animated video to share.</p>'
        f'<p><a href="{pack_url}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">Get your medallion</a></p>'
        f'<p style="color:#555;">Want to hold it? Premium members get <a href="{keepsake_url}">20% off a mug or sticker</a>.</p>'
        f'<p style="color:#999;font-size:12px;"><a href="{unsubscribe}">Unsubscribe from milestone emails</a></p>'
    )
    try:
        send_email(subject=f'Your {label} medallion is ready', plain_message=plain,
                   html_message=html, recipient_email=user.email)
    except Exception:
        logger.exception('Premium milestone medallion email failed for user %s', user.pk)
        return False
    MilestoneEmailSent.objects.get_or_create(user=user, milestone_days=milestone_days)
    return True
