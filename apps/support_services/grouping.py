"""Group a meeting's weekly time slots so each group has one indexable page.

TSML feeds give every slot its own slug, so one group can be dozens of
near-identical pages (NYC's Perry Street Workshop was 66). Slots of a group
share a group_key; one of them is the group's primary page, and every slot
page points rel=canonical at it. Slot pages keep working for reminders,
bookmarks and court logging. See docs/plans/2026-10-26-meeting-group-merge.md.
"""
import hashlib
import re
from collections import defaultdict
from urllib.parse import urlsplit

_FEED_SLUG = re.compile(r'^(?:mtg|online)-([a-z0-9]+)-')
_NUMBERED = re.compile(r'-(\d+)$')


def _norm(value):
    return re.sub(r'[^a-z0-9]+', ' ', (value or '').lower()).strip()


def _single(slug):
    """Key for a row that is always its own group (fits the 100-char column)."""
    return f'single-{hashlib.sha1((slug or "").encode()).hexdigest()[:24]}'


def group_key(slug, name, attendance_option='', formatted_address='', address='',
              location='', city='', state='', conference_url='', feed=None):
    """Same feed + same name + same place = same group.

    Online meetings are keyed by their room (URL host + path, query dropped so
    a ?pwd= change doesn't split a group), never by name alone, so generic
    names like "Daily Reflections" don't merge different Zoom rooms. Rows that
    aren't from a feed (community submissions) are always their own group.
    """
    if feed is None:
        match = _FEED_SLUG.match(slug or '')
        if not match:
            return _single(slug)
        feed = match.group(1)
    if attendance_option == 'online':
        parts = urlsplit((conference_url or '').strip().lower())
        place = f'online {parts.netloc}{parts.path.rstrip("/")}' if parts.netloc else 'online'
    else:
        place = ' '.join(filter(None, (
            _norm(formatted_address or address or location), _norm(city), _norm(state))))
    raw = f'{feed}|{_norm(name)}|{place}'
    return f'{feed}-{hashlib.sha1(raw.encode()).hexdigest()[:24]}'


def meeting_group_key(meeting, feed=None):
    """group_key for a Meeting instance (or a dict of its fields)."""
    get = meeting.get if isinstance(meeting, dict) else lambda f: getattr(meeting, f, '')
    if get('submitted_by_id'):  # community submission: never merged with a feed group
        return _single(get('slug'))
    return group_key(
        get('slug'), get('name'), get('attendance_option'), get('formatted_address'),
        get('address'), get('location'), get('city'), get('state'),
        get('conference_url'), feed=feed)


def _primary_rank(slug, pk):
    """Base slug first (it's the URL that already ranks), then lowest number."""
    match = _NUMBERED.search(slug)
    return (1, int(match.group(1)), pk) if match else (0, 0, pk)


def assign_primaries(meeting_model, keys=None):
    """Mark exactly one active, approved slot per group as primary.

    `keys` limits the pass to those groups (a sync passes the groups it
    touched); None recomputes everything. Inactive rows are never primary.
    Returns the number of rows whose flag changed.
    """
    qs = meeting_model.objects.exclude(group_key='')
    if keys is not None:
        qs = qs.filter(group_key__in=list(keys))
    groups = defaultdict(list)
    for pk, slug, key, active, approved, primary in qs.values_list(
            'pk', 'slug', 'group_key', 'is_active', 'is_approved', 'is_group_primary'):
        groups[key].append((pk, slug, active and approved, primary))

    make_primary, clear = [], []
    for rows in groups.values():
        live = [r for r in rows if r[2]]
        winner = min(live, key=lambda r: _primary_rank(r[1], r[0]))[0] if live else None
        for pk, _slug, _live, primary in rows:
            if pk == winner and not primary:
                make_primary.append(pk)
            elif pk != winner and primary:
                clear.append(pk)
    for chunk_start in range(0, len(make_primary), 1000):
        meeting_model.objects.filter(pk__in=make_primary[chunk_start:chunk_start + 1000]) \
            .update(is_group_primary=True)
    for chunk_start in range(0, len(clear), 1000):
        meeting_model.objects.filter(pk__in=clear[chunk_start:chunk_start + 1000]) \
            .update(is_group_primary=False)
    return len(make_primary) + len(clear)


_DAY_ABBR = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')


def _days_summary(days):
    if len(days) == 7:
        return 'Daily'
    if days == {1, 2, 3, 4, 5}:
        return 'Weekdays'
    names = [_DAY_ABBR[d] for d in sorted(days)]
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' & ' + names[-1]


def group_seo(primary, schedule):
    """Title and meta description for a group page with several weekly slots."""
    days = {m.day for m in schedule if m.day is not None and 0 <= m.day <= 6}
    when = _days_summary(days) if days else 'Weekly'
    if primary.attendance_option == 'online':
        where, kind = 'Online', 'online recovery meeting'
    else:
        where = f'{primary.city}, {primary.state}' if primary.city and primary.state else (primary.city or '')
        kind = 'recovery meeting held in person and online' if primary.attendance_option == 'hybrid' \
            else 'recovery meeting'
    title = f'{primary.name} — {when} Meetings' + (f', {where}' if where else '')
    count = len(schedule)
    text = (f'{primary.name} is a free {kind}' + (f' in {where}' if where and where != 'Online' else '')
            + f' with {count} meetings a week ({when.lower() if when in ("Daily", "Weekdays") else when}). '
            + ('See every time, the join link and the format.' if primary.attendance_option == 'online'
               else 'See every time, the address and the format.'))
    return title, (text if len(text) <= 160 else text[:157].rstrip() + '...')
