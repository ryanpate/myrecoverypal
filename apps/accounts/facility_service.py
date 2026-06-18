"""
At-risk computation for treatment-center aftercare. Derives engagement signals
from DailyCheckIn — never exposes raw note text. Computed on read.
"""
from datetime import timedelta

from django.utils import timezone

DISENGAGED_DAYS = 5
WATCH_DAYS = 3
RISK_WINDOW_DAYS = 7
HIGH_CRAVING_LEVEL = 4   # Intense
LOW_MOOD_LEVEL = 1       # Struggling

RISK_OK = 'ok'
RISK_WATCH = 'watch'
RISK_AT_RISK = 'at_risk'


def _trend(values):
    """values chronological (oldest first). Returns up/down/flat/None."""
    if len(values) < 4:
        return None
    mid = len(values) // 2
    prior, recent = values[:mid], values[mid:]
    diff = (sum(recent) / len(recent)) - (sum(prior) / len(prior))
    if diff > 0.5:
        return 'up'
    if diff < -0.5:
        return 'down'
    return 'flat'


def compute_member_risk(membership):
    user = membership.user
    today = timezone.now().date()
    # Most recent 14 check-ins, newest first.
    checkins = list(user.daily_checkins.order_by('-date')[:14])
    last_date = checkins[0].date if checkins else None
    days_since = (today - last_date).days if last_date else None

    window_start = today - timedelta(days=RISK_WINDOW_DAYS)
    recent = [c for c in checkins if c.date >= window_start]

    flags = []
    if days_since is None or days_since >= DISENGAGED_DAYS:
        flags.append('disengaged')
    if any(c.craving_level >= HIGH_CRAVING_LEVEL for c in recent):
        flags.append('high_craving')
    if any(c.mood <= LOW_MOOD_LEVEL for c in recent):
        flags.append('low_mood')

    if flags:
        risk = RISK_AT_RISK
    elif days_since is not None and days_since >= WATCH_DAYS:
        risk = RISK_WATCH
    else:
        risk = RISK_OK

    chrono = list(reversed(checkins))  # oldest first
    return {
        'risk_level': risk,
        'flags': flags,
        'last_checkin_date': last_date,
        'checkin_streak': user.get_checkin_streak(),
        'days_sober': user.get_days_sober(),
        'craving_trend': _trend([c.craving_level for c in chrono]),
        'mood_trend': _trend([c.mood for c in chrono]),
    }


def visible_memberships(facility):
    """Active, consented members only — the privacy boundary."""
    return facility.memberships.filter(
        status='active', consent_granted_at__isnull=False
    ).select_related('user')


def cohort_summary(facility):
    counts = {'total': 0, RISK_OK: 0, RISK_WATCH: 0, RISK_AT_RISK: 0}
    for m in visible_memberships(facility):
        counts['total'] += 1
        counts[compute_member_risk(m)['risk_level']] += 1
    return counts
