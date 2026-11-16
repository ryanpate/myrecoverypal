"""Gift a year of Premium: pricing, fulfilment and redemption.

A redeemed gift is a prepaid year on the member's Subscription:
tier='premium', status='active', subscription_source='gift', and
current_period_end a year out. Nothing bills or renews, so a daily task
(`tasks.gifted_premium_daily`) emails a week before the end and moves the
member back to Free when it passes.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .email_service import send_email
from .gift_models import PremiumGift
from .payment_models import Subscription, SubscriptionPlan

logger = logging.getLogger(__name__)

GIFT_KIND = 'premium_gift'
GIFT_DAYS = 365
FALLBACK_PRICE_CENTS = 5999


def price_cents():
    """A gifted year costs what a year of Premium costs."""
    plan = SubscriptionPlan.objects.filter(
        tier='premium', billing_period='yearly', is_active=True).first()
    return int(plan.price * 100) if plan else FALLBACK_PRICE_CENTS


def fulfil_checkout_session(session):
    """Mark the gift behind a paid Checkout Session as paid and email the buyer.

    Called from both the success redirect and the webhook, in either order and
    possibly repeatedly, so it is idempotent (row lock + receipt_emailed flag).
    Returns the gift, or None if the session isn't a paid gift session.
    """
    metadata = session.get('metadata') or {}
    if metadata.get('kind') != GIFT_KIND or session.get('payment_status') != 'paid':
        return None

    with transaction.atomic():
        try:
            gift = PremiumGift.objects.select_for_update().get(pk=metadata.get('gift_id'))
        except (PremiumGift.DoesNotExist, ValueError, TypeError):
            logger.error('Premium gift session %s has no matching gift', session.get('id'))
            return None
        if gift.status == 'pending':
            gift.status = 'paid'
            gift.paid_at = timezone.now()
        gift.stripe_payment_intent_id = session.get('payment_intent') or gift.stripe_payment_intent_id
        email = (session.get('customer_details') or {}).get('email')
        if email and not gift.buyer_email:
            gift.buyer_email = email
        should_email = gift.status == 'paid' and gift.buyer_email and not gift.receipt_emailed
        if should_email:
            gift.receipt_emailed = True
        gift.save()

    if should_email:
        _send_receipt(gift)
    return gift


def _send_receipt(gift):
    url = settings.SITE_URL.rstrip('/') + reverse('core:gift_card', args=[gift.token])
    plain = (
        'Thank you. Your gift of a year of MyRecoveryPal Premium is ready.\n\n'
        f'Print the card or copy the link to give it:\n{url}?giver=1\n\n'
        f'Or forward them this link directly:\n{url}\n\n'
        'It can be redeemed once, by whoever opens it first, and it never '
        'renews or charges anyone.\n\n— MyRecoveryPal'
    )
    html = (
        '<p>Thank you. Your gift of <strong>a year of MyRecoveryPal Premium</strong> is ready.</p>'
        f'<p><a href="{url}?giver=1" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        'border-radius:8px;text-decoration:none;font-weight:600;">Print or share your gift</a></p>'
        f'<p>Or forward them this link directly:<br><a href="{url}">{url}</a></p>'
        '<p style="color:#666;font-size:13px;">It can be redeemed once, by whoever opens it '
        'first, and it never renews or charges anyone.</p>'
    )
    try:
        send_email(
            subject='Your gift is ready: a year of MyRecoveryPal Premium',
            plain_message=plain, html_message=html,
            recipient_email=gift.buyer_email,
        )
    except Exception:
        logger.exception('Failed to email premium gift %s', gift.pk)


def revoke_for_refund(payment_intent_id):
    """Cancel a refunded gift that hasn't been redeemed. Returns True if a gift
    matched the payment (a redeemed one is left to the member)."""
    if not payment_intent_id:
        return False
    gifts = PremiumGift.objects.filter(stripe_payment_intent_id=payment_intent_id)
    gifts.filter(redeemed_at__isnull=True).update(status='refunded')
    return gifts.exists()


def blocked_reason(user):
    """Why this member can't redeem a gift right now, or ''.

    A gift never stacks on a plan someone is paying for (or one that is past
    due): we can't pause Stripe or Apple billing for a year. A second gift on
    top of a gifted year is fine; it adds another year.
    """
    sub = getattr(user, 'subscription', None)
    if not sub or sub.subscription_source == 'gift':
        return ''
    paying = sub.tier != 'free' and sub.status in ('active', 'past_due', 'incomplete')
    card_trial = sub.status == 'trialing' and sub.stripe_subscription_id
    if paying or card_trial:
        return ('You already have a paid plan, so this gift is still unused. '
                'Pass the link on to someone else, or redeem it after your plan ends.')
    return ''


def redeem(token, user):
    """Give `user` the gifted year. Returns (ok, message)."""
    reason = blocked_reason(user)
    if reason:
        return False, reason

    with transaction.atomic():
        gift = PremiumGift.objects.select_for_update().filter(token=token).first()
        if not gift or not gift.redeemable:
            return False, 'This gift has already been redeemed or is no longer valid.'
        sub, _ = Subscription.objects.select_for_update().get_or_create(
            user=user, defaults={'tier': 'free', 'status': 'active'})
        now = timezone.now()
        start = now
        if sub.subscription_source == 'gift' and sub.is_premium() and sub.current_period_end:
            start = max(now, sub.current_period_end)  # a second gift adds a year
        else:
            sub.current_period_start = now
        sub.tier = 'premium'
        sub.status = 'active'
        sub.subscription_source = 'gift'
        sub.billing_period = None
        sub.canceled_at = None
        sub.current_period_end = start + timedelta(days=GIFT_DAYS)
        sub.save()
        gift.redeemed_by = user
        gift.redeemed_at = now
        gift.save(update_fields=['redeemed_by', 'redeemed_at'])
    return True, 'Your year of Premium has started.'


def _gifted_subscriptions():
    return Subscription.objects.filter(
        subscription_source='gift', tier='premium', status='active').select_related('user')


def send_ending_reminders(now=None):
    """Email members whose gifted year ends in a week. Run once a day: each
    member is inside the one-day window exactly once."""
    now = now or timezone.now()
    site_url = settings.SITE_URL.rstrip('/')
    sent = 0
    for sub in _gifted_subscriptions().filter(
            current_period_end__gte=now + timedelta(days=7),
            current_period_end__lt=now + timedelta(days=8)):
        user = sub.user
        name = user.first_name or user.username
        ends = timezone.localtime(sub.current_period_end).strftime('%B %-d')
        keep_url = f'{site_url}/accounts/keep-premium/'
        plain = (
            f'Hi {name},\n\n'
            f'Your gifted year of Premium ends on {ends}. Your account, counter, '
            'journal and the community stay yours, free, either way.\n\n'
            'To keep every program, the full audio library, your insights and '
            f'Anchor, continue here:\n{keep_url}\n\n— MyRecoveryPal'
        )
        html = (
            f'<p>Hi {name},</p>'
            f'<p>Your gifted year of Premium ends on <strong>{ends}</strong>. Your account, '
            'counter, journal and the community stay yours, free, either way.</p>'
            '<p>To keep every program, the full audio library, your insights and Anchor:</p>'
            f'<p><a href="{keep_url}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
            'border-radius:8px;text-decoration:none;font-weight:600;">Keep Premium</a></p>'
        )
        try:
            if send_email(subject=f'Your gifted year of Premium ends {ends}',
                          plain_message=plain, html_message=html, recipient_email=user.email):
                sent += 1
        except Exception:
            logger.exception('Failed to send gift-ending email to user %s', user.pk)
    return sent


def expire_ended(now=None):
    """Move members whose gifted year has passed back to Free."""
    from .models import Notification
    now = now or timezone.now()
    expired = 0
    for sub in _gifted_subscriptions().filter(current_period_end__lt=now):
        sub.tier = 'free'
        sub.status = 'expired'
        sub.save(update_fields=['tier', 'status', 'updated_at'])
        expired += 1
        try:
            Notification.objects.create(
                recipient=sub.user, sender=sub.user, notification_type='milestone',
                title='Your gifted year of Premium has ended',
                message='Your counter, journal and community stay free. Keep Premium any time.',
                link='/accounts/pricing/',
            )
        except Exception:
            logger.exception('Could not notify user %s that their gift ended', sub.user_id)
    return expired
