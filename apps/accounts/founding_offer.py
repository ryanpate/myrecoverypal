"""Founding-member offer: a discount on the first year of annual Premium.

Who: anyone who is a member by the time the offer ends (existing members
and people who join during the window), who isn't already paying for
Premium. A legacy signup trial (no card, no Stripe subscription) can claim
it. Web only: it's a Stripe coupon, so every surface is `.stripe-only` and
the iOS app never shows it (App Store Guideline 3.1).

Settings (env vars, so the deadline or size can change without a deploy of
new code):
    FOUNDING_OFFER_ENDS     last day, ISO date (default 2026-10-31)
    FOUNDING_OFFER_PERCENT  percent off the first year (default 40)

Stripe: a `repeating` coupon for 11 months. The first paid annual invoice
always falls inside that window (immediately, or after a 7-day card trial),
and the renewal a year later falls outside it, so exactly the first year is
discounted. (A `once` coupon could be used up by the $0 trial invoice.)
`redeem_by` makes Stripe enforce the deadline too. The coupon id includes the percent, so changing
FOUNDING_OFFER_PERCENT creates a new coupon instead of editing a used one.
"""
import logging
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_ENDS = '2026-10-31'
DEFAULT_PERCENT = 40


def ends_on():
    raw = getattr(settings, 'FOUNDING_OFFER_ENDS', '') or DEFAULT_ENDS
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        logger.error(f'Bad FOUNDING_OFFER_ENDS {raw!r}; using {DEFAULT_ENDS}')
        return date.fromisoformat(DEFAULT_ENDS)


def percent_off():
    try:
        pct = int(getattr(settings, 'FOUNDING_OFFER_PERCENT', '') or DEFAULT_PERCENT)
    except (TypeError, ValueError):
        pct = DEFAULT_PERCENT
    return max(1, min(pct, 90))


def coupon_id():
    return f'founding{percent_off()}_first_year'


def is_active(today=None):
    return (today or timezone.localdate()) <= ends_on()


def days_left(today=None):
    return max(0, (ends_on() - (today or timezone.localdate())).days)


def is_eligible(user, today=None):
    if not (getattr(user, 'is_authenticated', False) and user.is_active and is_active(today)):
        return False
    if user.date_joined.date() > ends_on():
        return False
    sub = getattr(user, 'subscription', None)
    if sub is None or not sub.is_premium():
        return True
    # A no-card signup trial is the one Premium state that can still claim it.
    return sub.status == 'trialing' and not sub.stripe_subscription_id


def discounted_price(plan):
    """First-year price of `plan` with the offer applied (Decimal, 2 dp)."""
    factor = (Decimal(100) - percent_off()) / Decimal(100)
    return (Decimal(plan.price) * factor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_coupon():
    """Get-or-create the Stripe coupon. Returns its id, or None on Stripe
    error (the caller then falls back to full price, never a dead end)."""
    import stripe
    cid = coupon_id()
    try:
        return stripe.Coupon.retrieve(cid).id
    except stripe.error.InvalidRequestError:
        try:
            redeem_by = int(timezone.make_aware(datetime.combine(ends_on(), time(23, 59, 59))).timestamp())
            return stripe.Coupon.create(
                id=cid, percent_off=percent_off(), duration='repeating', duration_in_months=11,
                redeem_by=redeem_by,
                name=f'Founding member: {percent_off()}% off your first year',
            ).id
        except Exception as e:
            logger.error(f'founding coupon create failed: {e}')
            return None
    except Exception as e:
        logger.error(f'founding coupon retrieve failed: {e}')
        return None


def context_for(user, yearly_plan):
    """Template context for offer banners (empty dict when not shown)."""
    if yearly_plan is None or not is_active():
        return {}
    eligible = is_eligible(user)
    if getattr(user, 'is_authenticated', False) and not eligible:
        return {}
    return {
        'founding_offer': {
            'percent': percent_off(),
            'price': discounted_price(yearly_plan),
            'full_price': yearly_plan.price,
            'ends': ends_on(),
            'days_left': days_left(),
            'eligible': eligible,
        }
    }
