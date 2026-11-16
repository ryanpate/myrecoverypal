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


US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
    'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida',
    'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota',
    'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming',
}

# Hubs come in two sets: NA meetings under /support/meetings/na/..., and
# everything else (AA feeds plus community submissions) at the original URLs.
PROGRAM_NAMES = {'AA': 'Alcoholics Anonymous', 'NA': 'Narcotics Anonymous'}


def hub_program(program):
    """Which hub set a meeting's program belongs to."""
    return 'NA' if program == 'NA' else 'AA'


def for_program(qs, program):
    """Narrow a Meeting queryset to one hub set."""
    return qs.filter(program='NA') if program == 'NA' else qs.exclude(program='NA')


def hub_url(program, state=None, slug=None):
    from django.urls import reverse
    prefix = 'na_' if program == 'NA' else ''
    if state is None:
        return reverse('support_services:na_home' if program == 'NA'
                       else 'support_services:meeting_list')
    if slug is None:
        return reverse(f'support_services:{prefix}state_hub', kwargs={'state': state.lower()})
    return reverse(f'support_services:{prefix}city_hub',
                   kwargs={'state': state.lower(), 'city_slug': slug})


def _base_qs(program='AA'):
    return for_program(
        Meeting.objects
        .filter(is_approved=True, is_active=True)
        .exclude(city='')
        .exclude(state=''),
        program,
    )


def hub_cities(state=None, program='AA'):
    """Cities with enough meetings to warrant their own page."""
    qs = _base_qs(program)
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
         'slug': city_slug(r['city']), 'count': r['count'],
         'url': hub_url(program, r['state'], city_slug(r['city']))}
        for r in rows
    ]


def hub_states(program='AA'):
    """States with at least one qualifying city."""
    by_state = {}
    for c in hub_cities(program=program):
        s = by_state.setdefault(
            c['state'], {'state': c['state'], 'count': 0, 'city_count': 0,
                         'url': hub_url(program, c['state'])})
        s['count'] += c['count']
        s['city_count'] += 1
    return sorted(by_state.values(), key=lambda s: (-s['count'], s['state']))


def resolve_city(state, slug, program='AA'):
    """Stored city name for a slug within a state, or None.

    `city` is free text from the feed with no slug column, so match by
    slugifying the candidates. Verified against production: no slug
    collisions within any state.
    """
    for c in hub_cities(state, program):
        if c['slug'] == slug:
            return c['city']
    return None
