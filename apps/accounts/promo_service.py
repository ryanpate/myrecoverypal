"""
Promo code application service.

Single source of truth for the policy:
  - new / free users: grant trial_days of Premium
  - users currently trialing: extend trial_end if longer
  - active paid Premium/Pro users: no-op
  - already-redeemed: no-op (DB-enforced via unique_together)
  - unknown / inactive code: no-op
"""
from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone

from .payment_models import Promo, PromoRedemption, Subscription


def apply_promo_to_user(user, code):
    """
    Apply a promo code to a user's subscription.

    Returns:
        (applied: bool, message: str)
        applied=True only when the subscription was actually modified.
    """
    if not code:
        return False, 'invalid code'

    try:
        promo = Promo.objects.get(code=code, active=True)
    except Promo.DoesNotExist:
        return False, 'invalid code'

    if PromoRedemption.objects.filter(user=user, promo=promo).exists():
        return False, 'already redeemed'

    sub, _ = Subscription.objects.get_or_create(
        user=user,
        defaults={'tier': 'free', 'status': 'active'},
    )

    # Don't override an active paid subscription.
    if (
        sub.tier in ('premium', 'pro')
        and sub.status == 'active'
        and sub.subscription_source in ('stripe', 'apple')
    ):
        return False, 'already premium'

    new_trial_end = timezone.now() + timedelta(days=promo.trial_days)
    if sub.trial_end and sub.trial_end > new_trial_end:
        new_trial_end = sub.trial_end

    try:
        with transaction.atomic():
            sub.tier = 'premium'
            sub.status = 'trialing'
            sub.trial_end = new_trial_end
            sub.subscription_source = 'manual'
            sub.save()
            PromoRedemption.objects.create(user=user, promo=promo)
    except IntegrityError:
        # Race: another request redeemed the same code first.
        return False, 'already redeemed'

    return True, 'applied'
