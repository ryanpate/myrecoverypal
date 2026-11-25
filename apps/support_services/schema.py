"""JSON-LD for the meeting directory.

Meeting pages and city/state hubs are 99% of the sitemap but carried only
the site-wide Organization/WebSite markup. Each detail page now describes
the meeting as a weekly Event, and every page gets a BreadcrumbList; hubs
also list what they link to as an ItemList.
"""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils.safestring import mark_safe

from apps.support_services.hubs import PROGRAM_NAMES, US_STATES, hub_program, hub_url

SCHEMA_DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
MODES = {
    'in_person': 'https://schema.org/OfflineEventAttendanceMode',
    'online': 'https://schema.org/OnlineEventAttendanceMode',
    'hybrid': 'https://schema.org/MixedEventAttendanceMode',
}


def ld_json(blocks):
    """Serialise for an inline <script type="application/ld+json">.

    Meeting names and notes come from outside feeds, so <, > and & are
    escaped to keep a stray "</script>" from ending the tag.
    """
    text = json.dumps(blocks, ensure_ascii=False)
    for ch, esc in (('<', '\\u003c'), ('>', '\\u003e'), ('&', '\\u0026')):
        text = text.replace(ch, esc)
    return mark_safe(text)


def breadcrumbs(request, crumbs):
    """crumbs: [(name, path), ...]; the last one is the current page."""
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name,
             'item': request.build_absolute_uri(path)}
            for i, (name, path) in enumerate(crumbs, start=1)
        ],
    }


def item_list(request, name, entries):
    """entries: [(name, path), ...]"""
    return {
        '@context': 'https://schema.org',
        '@type': 'ItemList',
        'name': name,
        'numberOfItems': len(entries),
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': n,
             'url': request.build_absolute_uri(path)}
            for i, (n, path) in enumerate(entries, start=1)
        ],
    }


def meeting_breadcrumbs(request, meeting):
    program = hub_program(meeting.program)
    label = 'NA Meetings' if program == 'NA' else 'Meetings'
    crumbs = [(label, hub_url(program))]
    if meeting.city_hub_url:
        crumbs.append((US_STATES.get(meeting.state, meeting.state),
                       hub_url(program, meeting.state)))
        crumbs.append((meeting.city, meeting.city_hub_url))
    crumbs.append((meeting.name, meeting.get_absolute_url()))
    return breadcrumbs(request, crumbs)


def _next_start(meeting, now=None):
    """The next time this slot starts, in the meeting's own time zone."""
    try:
        tz = ZoneInfo(meeting.timezone)
    except Exception:
        tz = ZoneInfo('America/Chicago')
    now = (now or datetime.now(tz)).astimezone(tz)
    # Model days start at Sunday=0; Python's weekday() starts at Monday=0.
    days_ahead = ((meeting.day - 1) % 7 - now.weekday()) % 7
    start = datetime.combine(now.date() + timedelta(days=days_ahead), meeting.time, tzinfo=tz)
    if start <= now:
        start += timedelta(days=7)
    return start


def _place(meeting):
    address = {'@type': 'PostalAddress', 'addressCountry': meeting.country or 'US'}
    if meeting.address:
        address['streetAddress'] = meeting.address
    if meeting.city:
        address['addressLocality'] = meeting.city
    if meeting.state:
        address['addressRegion'] = meeting.state
    if meeting.postal_code:
        address['postalCode'] = meeting.postal_code
    if not meeting.address and meeting.formatted_address:
        address = meeting.formatted_address
    place = {'@type': 'Place',
             'name': meeting.location or meeting.formatted_address or meeting.address or meeting.city,
             'address': address}
    if meeting.latitude is not None and meeting.longitude is not None:
        place['geo'] = {'@type': 'GeoCoordinates',
                        'latitude': float(meeting.latitude),
                        'longitude': float(meeting.longitude)}
    return place


def meeting_event(request, meeting, schedule, page_url, now=None):
    """A weekly Event for one meeting page, or None when Google's required
    fields (a start time and a location) aren't known."""
    if meeting.day is None or not meeting.time:
        return None
    has_place = bool(meeting.location or meeting.formatted_address
                     or meeting.address or meeting.city)
    mode = meeting.attendance_option
    if mode == 'in_person' and not has_place:
        return None

    # The virtual location points at our page, not the Zoom link: the link
    # is on the page for people, it doesn't need to be in a feed for bots.
    virtual = {'@type': 'VirtualLocation', 'url': page_url}
    if mode == 'online' or not has_place:
        location = virtual
    elif mode == 'hybrid':
        location = [_place(meeting), virtual]
    else:
        location = _place(meeting)

    start = _next_start(meeting, now)
    event = {
        '@context': 'https://schema.org',
        '@type': 'Event',
        'name': meeting.name,
        'description': meeting.seo_description,
        'url': page_url,
        'startDate': start.isoformat(),
        'eventStatus': 'https://schema.org/EventScheduled',
        'eventAttendanceMode': MODES.get(mode, MODES['in_person']),
        'location': location,
        'isAccessibleForFree': True,
        'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'USD',
                   'availability': 'https://schema.org/InStock', 'url': page_url},
        'organizer': {'@type': 'Organization',
                      'name': meeting.group or PROGRAM_NAMES.get(meeting.program, meeting.name)},
        'eventSchedule': [
            {'@type': 'Schedule',
             'byDay': f'https://schema.org/{SCHEMA_DAYS[slot.day]}',
             'startTime': slot.time.strftime('%H:%M'),
             **({'endTime': slot.end_time.strftime('%H:%M')} if slot.end_time else {}),
             'repeatFrequency': 'P1W',
             'scheduleTimezone': slot.timezone}
            for slot in schedule if slot.day is not None and slot.time
        ],
    }
    if meeting.end_time:
        end = datetime.combine(start.date(), meeting.end_time, tzinfo=start.tzinfo)
        if end > start:
            event['endDate'] = end.isoformat()
    return event
