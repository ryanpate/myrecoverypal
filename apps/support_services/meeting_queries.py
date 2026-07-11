"""Read-side queries over the meeting directory.

Meetings store day + time in their home IANA timezone, so "starting soon"
must be computed per zone: local-now differs between the Seattle, Houston,
and NYC feeds, and a window that crosses local midnight has to look at the
next day's meetings too.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apps.support_services.models import Meeting


def starting_soon(hours=3, limit=6):
    """Active online meetings starting within `hours`, soonest first.

    Each returned Meeting gets a `minutes_until` int attribute. Meetings
    with no day/time, or an unparseable timezone, are skipped.
    """
    online = (
        Meeting.objects
        .filter(is_active=True, is_approved=True, attendance_option='online')
        .exclude(time__isnull=True)
        .exclude(day__isnull=True)
    )

    results = []
    zones = online.values_list('timezone', flat=True).distinct()
    for tz_name in zones:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            continue
        now_local = datetime.now(tz)
        end_local = now_local + timedelta(hours=hours)
        today = (now_local.weekday() + 1) % 7  # Meeting model: 0=Sunday
        crosses_midnight = end_local.date() != now_local.date()

        zone_qs = online.filter(timezone=tz_name)

        # Today's slice of the window.
        today_qs = zone_qs.filter(day=today, time__gte=now_local.time())
        if not crosses_midnight:
            today_qs = today_qs.filter(time__lt=end_local.time())
        for meeting in today_qs:
            results.append(_annotate(meeting, now_local, days_ahead=0))

        # Spillover past local midnight.
        if crosses_midnight:
            tomorrow = (today + 1) % 7
            for meeting in zone_qs.filter(day=tomorrow,
                                          time__lt=end_local.time()):
                results.append(_annotate(meeting, now_local, days_ahead=1))

    results.sort(key=lambda m: m.minutes_until)
    return results[:limit]


def _annotate(meeting, now_local, days_ahead):
    starts = now_local.replace(
        hour=meeting.time.hour, minute=meeting.time.minute,
        second=0, microsecond=0,
    ) + timedelta(days=days_ahead)
    meeting.minutes_until = max(0, int((starts - now_local).total_seconds() // 60))
    return meeting
