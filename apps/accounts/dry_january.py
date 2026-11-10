"""Dry January: a free 31-day challenge that runs January 1-31.

Members join from the public /dry-january/ page. The progress home shows a
card for their entry: a countdown before January, "Day N of 31" with the
daily pledge during it, and a 31-day medallion plus a Premium offer in
February. All dates are the member's local dates (timezone.localdate()).
"""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.analytics import queue_ga_event

LENGTH = 31
# How long into February the finished card stays on the progress home.
FINISHED_CARD_UNTIL_DAY = 28


def signup_year(today):
    """The Dry January people are signing up for: this year's during January,
    otherwise next year's."""
    return today.year if today.month == 1 else today.year + 1


def card_state(entry_years, today):
    """What the progress-home card shows, or None.

    entry_years: the years this member joined.
    """
    if today.month == 1 and today.year in entry_years:
        return {'phase': 'active', 'year': today.year, 'day': today.day}
    if today.month == 2 and today.day <= FINISHED_CARD_UNTIL_DAY and today.year in entry_years:
        return {'phase': 'finished', 'year': today.year}
    upcoming = signup_year(today)
    if today.month != 1 and upcoming in entry_years:
        return {'phase': 'upcoming', 'year': upcoming,
                'days_until': (date(upcoming, 1, 1) - today).days}
    return None


def progress_card(user):
    """Context for the progress-home card, or None when there's nothing to show."""
    from .models import DailyPledge, DryJanuaryEntry
    today = timezone.localdate()
    years = set(DryJanuaryEntry.objects.filter(user=user).values_list('year', flat=True))
    state = card_state(years, today)
    if state and state['phase'] in ('active', 'finished'):
        state['pledged_days'] = DailyPledge.objects.filter(
            user=user, date__year=state['year'], date__month=1).count()
    return state


@login_required
@require_POST
def join(request):
    from .models import DryJanuaryEntry
    year = signup_year(timezone.localdate())
    _, created = DryJanuaryEntry.objects.get_or_create(user=request.user, year=year)
    if created:
        queue_ga_event(request, 'dry_january_join', year=year)
        messages.success(request, f"You're in for Dry January {year}. Your tracker is below.")
    return redirect('accounts:progress')
