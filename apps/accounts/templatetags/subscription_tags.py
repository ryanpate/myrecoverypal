"""
Template tags for subscription-related functionality
"""
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def days_remaining(trial_end):
    """Calculate days remaining until trial ends"""
    if not trial_end:
        return 0

    now = timezone.now()
    if trial_end <= now:
        return 0

    delta = trial_end - now
    return delta.days + (1 if delta.seconds > 0 else 0)  # Round up


@register.filter
def trial_urgency_class(days):
    """Return CSS class based on urgency (days remaining)"""
    if days <= 2:
        return 'trial-critical'  # Red
    elif days <= 5:
        return 'trial-warning'   # Orange
    else:
        return 'trial-normal'    # Blue/Purple
