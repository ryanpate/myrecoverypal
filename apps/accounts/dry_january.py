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


EMAIL_LOCAL_HOUR = 9
EMAIL_FALLBACK_TZ = 'America/Chicago'
MIDMONTH_DAYS = (15, 16)  # the 16th is a catch-up if the 15th's runs were missed


def email_due(entry, local_now):
    """Which email this entry should get at the member's local time, or None.

    'start': December 31, the day before their Dry January.
    'midmonth': January 15 (or 16), halfway.
    Both go out from 9 AM local; the sent flags make each a one-off."""
    if local_now.hour < EMAIL_LOCAL_HOUR:
        return None
    today = local_now.date()
    if (today.month, today.day) == (12, 31) and entry.year == today.year + 1:
        return None if entry.start_email_sent else 'start'
    if today.month == 1 and today.day in MIDMONTH_DAYS and entry.year == today.year:
        return None if entry.midmonth_email_sent else 'midmonth'
    return None


SUBJECTS = {
    'start': 'Dry January starts tomorrow',
    'midmonth': "Halfway through Dry January",
}


def send_emails(now=None):
    """Send the two Dry January emails to members who joined. Runs hourly
    (tasks.send_dry_january_emails); returns how many were sent."""
    from zoneinfo import ZoneInfo

    from django.conf import settings
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    from .email_service import send_email
    from .models import DailyPledge, DryJanuaryEntry

    now = now or timezone.now()
    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    entries = DryJanuaryEntry.objects.filter(
        year__in=(now.year, now.year + 1), user__is_active=True,
        user__email_notifications=True,
    ).exclude(start_email_sent=True, midmonth_email_sent=True).select_related('user')

    sent = 0
    for entry in entries:
        user = entry.user
        if not user.email:
            continue
        try:
            zone = ZoneInfo(user.timezone or EMAIL_FALLBACK_TZ)
        except Exception:
            zone = ZoneInfo(EMAIL_FALLBACK_TZ)
        kind = email_due(entry, now.astimezone(zone))
        if not kind:
            continue
        context = {
            'kind': kind, 'year': entry.year, 'site_url': site_url,
            'first_name': user.first_name or 'there',
        }
        if kind == 'midmonth':
            context['pledged_days'] = DailyPledge.objects.filter(
                user=user, date__year=entry.year, date__month=1).count()
        html = render_to_string('emails/dry_january.html', context)
        ok, _ = send_email(subject=SUBJECTS[kind], plain_message=strip_tags(html),
                           html_message=html, recipient_email=user.email)
        if ok:
            setattr(entry, f'{kind}_email_sent', True)
            entry.save(update_fields=[f'{kind}_email_sent'])
            sent += 1
    return sent


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
