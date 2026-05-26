# apps/store/email_service.py
"""Shop email service — featured product selection, milestone matching,
and orchestration of send-to-many for weekly digests and per-user
milestone celebration emails.

All `send_*` functions use apps.accounts.email_service.send_email under
the hood, which handles Resend HTTP API + SMTP fallback.
"""
import logging
from datetime import date
from typing import List, Optional, Tuple

from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from apps.accounts.email_service import send_email
from apps.store.models import MilestoneEmailSent, Product

User = get_user_model()
logger = logging.getLogger(__name__)

# Milestones (in days) that trigger a celebration email.
FIXED_MILESTONES = [7, 30, 90, 180, 365]

# Map each milestone bucket to a product category slug. Year anniversaries
# (730, 1095, ...) always fall through to 'apparel'.
MILESTONE_PRODUCT_CATEGORIES = {
    7:   'stickers',
    30:  'journals',
    90:  'journals',
    180: 'apparel',
    365: 'apparel',
}


def select_featured_products(limit: int = 3) -> List[Product]:
    """Top featured products, falling back to newest active if not enough."""
    featured = list(
        Product.objects.filter(is_active=True, is_featured=True).order_by('-updated_at')[:limit]
    )
    if len(featured) >= limit:
        return featured
    # Fallback: top up with newest non-featured active products
    remaining = limit - len(featured)
    fallback = list(
        Product.objects
        .filter(is_active=True, is_featured=False)
        .exclude(pk__in=[p.pk for p in featured])
        .order_by('-created_at')[:remaining]
    )
    return featured + fallback


def select_milestone_product(milestone_days: int) -> Optional[Product]:
    """Pick one Product for a milestone email. Falls back to any featured."""
    if milestone_days >= 365 and milestone_days % 365 == 0:
        category_slug = 'apparel'
    else:
        category_slug = MILESTONE_PRODUCT_CATEGORIES.get(milestone_days, 'apparel')

    product = (
        Product.objects
        .filter(is_active=True, category__slug=category_slug)
        .order_by('-is_featured', '-updated_at')
        .first()
    )
    if product:
        return product
    return Product.objects.filter(is_active=True).order_by('-is_featured', '-updated_at').first()


def find_users_hitting_milestone_today() -> List[Tuple]:
    """Returns [(user, milestone_days), ...] for users hitting a milestone today.

    Excludes users with marketing_emails_enabled=False, inactive users,
    users without a sobriety_date, and users who have already been emailed
    for that specific milestone."""
    today = date.today()
    results = []

    qs = User.objects.filter(
        sobriety_date__isnull=False,
        marketing_emails_enabled=True,
        is_active=True,
    )

    for user in qs:
        days_sober = (today - user.sobriety_date).days
        is_fixed = days_sober in FIXED_MILESTONES
        is_yearly = days_sober > 365 and days_sober % 365 == 0
        if not (is_fixed or is_yearly):
            continue
        if MilestoneEmailSent.objects.filter(user=user, milestone_days=days_sober).exists():
            continue
        results.append((user, days_sober))

    return results


def _build_unsubscribe_url(user) -> str:
    token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}{reverse('unsubscribe_marketing', args=[token])}"


def _profile_settings_url() -> str:
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}{reverse('accounts:edit_profile')}"


def _shop_url() -> str:
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}/store/"


def _milestone_message(milestone_days: int) -> Tuple[str, str]:
    """Return (subject, body_intro) for a milestone email."""
    if milestone_days == 7:
        return (
            'You hit 7 days. We see you.',
            "First week sober. The hardest stretch — and you did it."
        )
    if milestone_days == 30:
        return (
            'You hit 30 days. We see you.',
            "A full month. The brain chemistry shifts started about 5 days ago."
        )
    if milestone_days == 90:
        return (
            'You hit 90 days. We see you.',
            "90 days. Strong evidence the change is sticking."
        )
    if milestone_days == 180:
        return (
            'You hit 180 days. We see you.',
            "Half a year. Most people who relapse never get this far."
        )
    if milestone_days == 365:
        return (
            'One year sober. Today is the anniversary.',
            "One year. Today is the anniversary."
        )
    # Yearly anniversaries
    years = milestone_days // 365
    return (
        f'{years} years sober. That\'s a life.',
        f'{years} years sober. That\'s a life.'
    )


def send_weekly_shop_digest() -> int:
    """Send the Friday weekly shop digest. Returns count of emails sent."""
    products = select_featured_products(limit=3)
    if not products:
        logger.info('Weekly shop digest skipped — no active products to feature')
        return 0

    recipients = User.objects.filter(
        is_active=True,
        marketing_emails_enabled=True,
    ).exclude(email='').exclude(email__isnull=True)

    sent = 0
    for user in recipients:
        ctx = {
            'user': user,
            'first_name': user.first_name or 'Friend',
            'featured': products[0],
            'others': list(products[1:]),
            'unsubscribe_url': _build_unsubscribe_url(user),
            'profile_settings_url': _profile_settings_url(),
            'shop_url': _shop_url(),
        }
        html = render_to_string('store/emails/weekly_digest.html', ctx)
        plain = strip_tags(html)
        success, err = send_email(
            subject='New in the Recovery Shop this week',
            plain_message=plain,
            html_message=html,
            recipient_email=user.email,
        )
        if success:
            sent += 1
        else:
            logger.warning('Weekly digest send failed for %s: %s', user.email, err)

    return sent


def send_milestone_celebration_email(user, milestone_days: int) -> bool:
    """Send a single milestone celebration email. Returns True on success.

    Only creates the MilestoneEmailSent dedup row if send_email succeeds —
    so a transient failure can be retried by the next daily run."""
    if not user.email:
        return False

    product = select_milestone_product(milestone_days)
    subject, intro = _milestone_message(milestone_days)

    ctx = {
        'user': user,
        'first_name': user.first_name or 'Friend',
        'milestone_days': milestone_days,
        'milestone_intro': intro,
        'product': product,
        'unsubscribe_url': _build_unsubscribe_url(user),
        'profile_settings_url': _profile_settings_url(),
        'shop_url': _shop_url(),
    }
    html = render_to_string('store/emails/milestone_celebration.html', ctx)
    plain = strip_tags(html)
    success, err = send_email(
        subject=subject,
        plain_message=plain,
        html_message=html,
        recipient_email=user.email,
    )
    if success:
        MilestoneEmailSent.objects.get_or_create(user=user, milestone_days=milestone_days)
        return True
    logger.warning('Milestone email send failed for %s @ %dd: %s', user.email, milestone_days, err)
    return False
