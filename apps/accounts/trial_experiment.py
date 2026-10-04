"""A/B test: card-required Premium trial vs. a no-card ("reverse") trial.

    card_trial     (control)  New members start on Free. Premium's 7-day trial
                              starts at Stripe Checkout and needs a card.
    no_card_trial  (variant)  New members get 7 days of Premium at signup, no
                              card. When it ends they drop back to Free.

Why test it again: until 2026-09-26 every signup got a 14-day no-card trial,
and 1 of 411 signups paid. The product is much richer now (programs, audio,
reflections, worksheets), the trial is shorter, and the trial-ending email
now shows what each member used. So the question is whether letting people
try it first beats asking for a card first. Judge it on PAID conversion and
week-2 retention, not trial starts.

Only members who sign up while the test is running are assigned (deterministic
50/50 on user id, see ABTestingService). Everyone already here is unaffected.
The no-card trial reuses the existing no-card trial funnel: trial countdown
banners, `send_trial_ending_notifications` (the day before), `expire_ended_trials`
(back to Free), and `send_winback_offers` (24h-30d after).

Turn it on:   python manage.py init_trial_test           (creates and starts it)
Results:      python manage.py trial_test_report         (or /admin/dashboard/ab-tests/)
Stop it:      python manage.py init_trial_test --stop    (or untick is_active in admin)
"""
import logging
import math
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

TEST_NAME = 'premium_trial_type'
CONTROL = 'card_trial'
VARIANT = 'no_card_trial'
NO_CARD_TRIAL_DAYS = 7

# Funnel events, in order (ABTestConversion.conversion_type).
STARTED_TRIAL = 'started_trial'      # no-card: at signup; card: Stripe trial started
BEGAN_CHECKOUT = 'began_checkout'    # opened Stripe Checkout for Premium
SUBSCRIBED = 'subscribed'            # Stripe subscription created (card on file) or Apple purchase
CONVERTED_PAID = 'converted_paid'    # first real (non-zero) Stripe payment
FUNNEL = [STARTED_TRIAL, BEGAN_CHECKOUT, SUBSCRIBED, CONVERTED_PAID]


def setup_test():
    """Create (or re-activate) the test with two equally weighted variants."""
    from .ab_testing import ABTest, ABTestVariant
    test, _ = ABTest.objects.get_or_create(
        name=TEST_NAME,
        defaults={'description': 'Card-required 7-day Premium trial at checkout (control) vs. '
                                 'a 7-day no-card Premium trial at signup.'},
    )
    ABTestVariant.objects.get_or_create(
        test=test, name=CONTROL,
        defaults={'weight': 1, 'description': 'Start on Free; 7-day trial at Stripe Checkout, card required.'})
    ABTestVariant.objects.get_or_create(
        test=test, name=VARIANT,
        defaults={'weight': 1, 'description': f'{NO_CARD_TRIAL_DAYS} days of Premium at signup, no card.',
                  'config': {'trial_days': NO_CARD_TRIAL_DAYS}})
    return test


def assign_at_signup(user, subscription):
    """Called once, right after a new account's Subscription is created.
    Never raises: an experiment must not be able to break signup."""
    try:
        from .ab_testing import ABTestingService
        variant = ABTestingService.get_variant(user, TEST_NAME)
        if variant != VARIANT:
            return variant
        subscription.tier = 'premium'
        subscription.status = 'trialing'
        subscription.trial_end = timezone.now() + timedelta(days=NO_CARD_TRIAL_DAYS)
        subscription.save(update_fields=['tier', 'status', 'trial_end'])
        track(user, STARTED_TRIAL, {'kind': 'no_card'})
        return variant
    except Exception as e:
        logger.error(f'trial experiment assignment failed for user {user.pk}: {e}')
        return None


def track(user, event, metadata=None):
    """Record a funnel event for `user` if they're in the test. Never raises."""
    if user is None:
        return False
    try:
        from .ab_testing import ABTestingService
        return ABTestingService.track_conversion(user, TEST_NAME, event, metadata or {})
    except Exception as e:
        logger.error(f'trial experiment track({event}) failed for user {getattr(user, "pk", None)}: {e}')
        return False


def is_no_card_trial(user):
    from .ab_testing import ABTestAssignment
    return ABTestAssignment.objects.filter(user=user, test__name=TEST_NAME, variant__name=VARIANT).exists()


def usage_summary(user, since):
    """What `user` used since `since`, for the trial-ending email. Only
    counts, never content (journal and coach text stay private)."""
    from apps.accounts.models import CoachMessage
    from resources.models import ProgramDayCompletion, ReflectionFavorite, WorksheetEntry
    return {
        'lessons': ProgramDayCompletion.objects.filter(enrollment__user=user, created_at__gte=since).count(),
        'worksheets': WorksheetEntry.objects.filter(user=user, updated_at__gte=since).count(),
        'anchor_messages': CoachMessage.objects.filter(session__user=user, role='user', created_at__gte=since).count(),
        'favorites': ReflectionFavorite.objects.filter(user=user, created_at__gte=since).count(),
    }


def _active_in_week_two(user):
    """Did the member come back in days 8-14 after joining (a check-in, a
    pledge or a lesson)? A guardrail: a trial that converts but drives people
    away afterwards isn't a win."""
    from apps.accounts.models import DailyCheckIn, DailyPledge
    from resources.models import ProgramDayCompletion
    start = (user.date_joined + timedelta(days=7)).date()
    end = (user.date_joined + timedelta(days=14)).date()
    return (DailyCheckIn.objects.filter(user=user, date__gte=start, date__lt=end).exists()
            or DailyPledge.objects.filter(user=user, date__gte=start, date__lt=end).exists()
            or ProgramDayCompletion.objects.filter(enrollment__user=user, completed_on__gte=start,
                                                   completed_on__lt=end).exists())


def _two_proportion_p(x1, n1, x2, n2):
    """Two-sided p-value for a difference in proportions (normal approx)."""
    if min(n1, n2) == 0:
        return None
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = abs(x1 / n1 - x2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def report(now=None):
    """Per-variant funnel, week-2 retention, and a significance check on paid
    conversion. Returns None if the test doesn't exist."""
    from .ab_testing import ABTest, ABTestAssignment, ABTestConversion
    test = ABTest.objects.filter(name=TEST_NAME).first()
    if test is None:
        return None
    now = now or timezone.now()
    rows = {}
    for variant in (CONTROL, VARIANT):
        assignments = ABTestAssignment.objects.filter(test=test, variant__name=variant).select_related('user')
        users = [a.user for a in assignments]
        n = len(users)
        events = {e: ABTestConversion.objects.filter(assignment__in=assignments, conversion_type=e).count()
                  for e in FUNNEL}
        mature = [u for u in users if u.date_joined <= now - timedelta(days=14)]
        retained = sum(1 for u in mature if _active_in_week_two(u))
        rows[variant] = {
            'users': n,
            'events': events,
            'rates': {e: (events[e] / n if n else 0) for e in FUNNEL},
            'week2_eligible': len(mature),
            'week2_retained': retained,
            'week2_rate': (retained / len(mature)) if mature else 0,
        }
    c, v = rows[CONTROL], rows[VARIANT]
    p_paid = _two_proportion_p(c['events'][CONVERTED_PAID], c['users'], v['events'][CONVERTED_PAID], v['users'])
    return {
        'test': test,
        'rows': rows,
        'p_paid': p_paid,
        'significant': p_paid is not None and p_paid < 0.05,
        'enough_data': min(c['users'], v['users']) >= 100,
    }
