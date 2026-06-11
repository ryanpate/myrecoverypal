"""
Read model + actions for the supporter dashboard.

get_dashboard_data() is the SINGLE place the preset -> fields mapping lives.
No other code should read member recovery data for a supporter. It never
queries craving levels, journal entries, or any free-text check-in field.
"""
from datetime import timedelta
from django.utils import timezone

MILESTONE_DAYS = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1460, 1825]
CHECKIN_WINDOW_DAYS = 7
MOOD_TREND_DAYS = 7


def _next_milestone(days_sober):
    for target in MILESTONE_DAYS:
        if target > days_sober:
            return {'target': target, 'days_to': target - days_sober}
    years = days_sober // 365 + 1
    target = years * 365
    return {'target': target, 'days_to': target - days_sober}


def _milestones_hit(days_sober):
    return [d for d in MILESTONE_DAYS if d <= days_sober]


def _checkin_consistency(member):
    cutoff = timezone.now().date() - timedelta(days=CHECKIN_WINDOW_DAYS - 1)
    count = member.daily_checkins.filter(date__gte=cutoff).count()
    return {'count': count, 'window': CHECKIN_WINDOW_DAYS}


def _mood_trend(member):
    cutoff = timezone.now().date() - timedelta(days=MOOD_TREND_DAYS - 1)
    qs = member.daily_checkins.filter(date__gte=cutoff).order_by('date')
    return list(qs.values_list('mood', flat=True))


def _inactivity_status(member, link):
    last = member.daily_checkins.order_by('-date').first()
    if not last:
        return {'days_since_checkin': None, 'over_threshold': True}
    days = (timezone.now().date() - last.date).days
    return {'days_since_checkin': days, 'over_threshold': days >= link.inactivity_threshold_days}


def get_dashboard_data(link):
    """Build the supporter-visible payload for a link, gated by preset.

    This is the single read gate. It enforces consent status itself so no
    caller can render data for a paused/revoked/pending link by forgetting
    to check.
    """
    if not link.is_live():
        raise ValueError(
            f"SupporterLink {link.pk} is not active (status={link.status!r}); no data is shared."
        )
    member = link.member
    days_sober = member.get_days_sober()
    data = {
        'member_name': member.get_full_name() or member.username,
        'preset': link.preset,
        'days_sober': days_sober,
        'milestone_label': member.get_sobriety_milestone(),
        'next_milestone': _next_milestone(days_sober),
        'milestones_hit': _milestones_hit(days_sober),
    }
    if link.preset in ('standard', 'close'):
        data['checkin_consistency'] = _checkin_consistency(member)
        data['mood_trend'] = _mood_trend(member)
    if link.preset == 'close':
        data['inactivity'] = _inactivity_status(member, link)
    return data


ENCOURAGEMENT_MESSAGES = {
    'proud': 'is proud of you 💪',
    'thinking': 'is thinking of you ❤️',
    'here': 'is here if you need them 🤝',
}


def record_support_request(member):
    """Member taps 'I need support' -> notify only their Close supporters.

    Returns the number of supporters notified. Content never auto-fires;
    this is an explicit, member-initiated ping.
    """
    from apps.accounts.views import create_notification
    links = member.supporter_links.filter(
        status='active', preset='close'
    ).select_related('supporter')
    name = member.get_full_name() or member.username
    notified = 0
    for link in links:
        if not link.supporter:
            continue
        create_notification(
            recipient=link.supporter,
            sender=member,
            notification_type='member_support_request',
            title='Support requested',
            message=f"{name} asked for support.",
        )
        notified += 1
    return notified


def send_encouragement(link, key):
    """Send a canned supportive notification from supporter -> member."""
    if key not in ENCOURAGEMENT_MESSAGES or not link.is_live() or not link.supporter:
        return False
    from apps.accounts.views import create_notification
    sender = link.supporter
    name = sender.get_full_name() or sender.username
    create_notification(
        recipient=link.member,
        sender=sender,
        notification_type='supporter_encouragement',
        title='Encouragement',
        message=f"{name} {ENCOURAGEMENT_MESSAGES[key]}",
    )
    return True
