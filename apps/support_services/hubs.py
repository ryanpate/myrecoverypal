"""City and state hub aggregation for the meeting directory.

The 6,451 meeting detail pages cannot rank for "aa meetings in houston" —
that query wants a list, and a page about one Tuesday 7pm group is not a
list. These helpers derive the list pages from the existing city/state
columns; there is no hub model and no migration.
"""
from django.db.models import Count
from django.utils.text import slugify

from apps.support_services.models import Meeting

# A hub listing one or two meetings is the thin content these pages exist
# to avoid. Cities below this still appear on their state page and keep
# their own detail pages.
MIN_MEETINGS_FOR_HUB = 3


def city_slug(city):
    return slugify(city)


def _base_qs():
    return (
        Meeting.objects
        .filter(is_approved=True, is_active=True)
        .exclude(city='')
        .exclude(state='')
    )


def hub_cities(state=None):
    """Cities with enough meetings to warrant their own page."""
    qs = _base_qs()
    if state:
        qs = qs.filter(state__iexact=state)
    rows = (
        qs.values('city', 'state')
          .annotate(count=Count('id'))
          .filter(count__gte=MIN_MEETINGS_FOR_HUB)
          .order_by('-count', 'city')
    )
    return [
        {'city': r['city'], 'state': r['state'],
         'slug': city_slug(r['city']), 'count': r['count']}
        for r in rows
    ]


def hub_states():
    """States with at least one qualifying city."""
    by_state = {}
    for c in hub_cities():
        s = by_state.setdefault(
            c['state'], {'state': c['state'], 'count': 0, 'city_count': 0})
        s['count'] += c['count']
        s['city_count'] += 1
    return sorted(by_state.values(), key=lambda s: (-s['count'], s['state']))


def resolve_city(state, slug):
    """Stored city name for a slug within a state, or None.

    `city` is free text from the feed with no slug column, so match by
    slugifying the candidates. Verified against production: no slug
    collisions within any state.
    """
    for c in hub_cities(state):
        if c['slug'] == slug:
            return c['city']
    return None
