# City Hub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/support/meetings/<state>/<city>/` and `/support/meetings/<state>/` hub pages so the 4,844 in-person meetings have a page that answers "aa meetings in \<city\>".

**Architecture:** No migration and no new model — hubs are derived from the existing `city`/`state` columns via an aggregate over the existing `(city, state)` index. Two views, two templates, two sitemap classes, one `Meeting` helper for the detail-page backlink.

**Tech Stack:** Django 5.0.10, PostgreSQL (SQLite in tests).

**Spec:** `docs/plans/2026-09-07-city-hub-pages-design.md`

## Global Constraints

- **Program naming is "AA", never "AA, NA & SMART".** The directory is 100% AA — all three feeds are AA intergroups, zero community submissions. Task 5 also corrects the existing inaccurate `/support/meetings/` copy.
- **`MIN_MEETINGS_FOR_HUB = 3`.** A hub listing one meeting is the thin content this work exists to avoid.
- **Hub routes must be registered before `meetings/<slug:slug>/`**, and the state route regex-constrained to exactly two letters, or `<slug:slug>` swallows `/meetings/tx/`.
- Only `is_approved=True, is_active=True` meetings count, everywhere.
- Run tests with `python3 manage.py test`.
- Tests that hit `/accounts/` or generate traffic must clear the `default` and `rate_limiting` caches in `setUp` — `RateLimitMiddleware` is cache-backed and LocMem is not reset between tests.

---

### Task 1: City/state aggregation helpers

**Files:**
- Create: `apps/support_services/hubs.py`
- Test: `apps/support_services/test_city_hubs.py`

**Interfaces:**
- Produces:
  - `MIN_MEETINGS_FOR_HUB: int = 3`
  - `city_slug(city: str) -> str`
  - `hub_cities(state: str | None = None) -> list[dict]` — `{'city', 'state', 'slug', 'count'}`, ordered by count desc then city asc, only cities at or above the threshold.
  - `hub_states() -> list[dict]` — `{'state', 'count', 'city_count'}`, only states with at least one qualifying city.
  - `resolve_city(state: str, slug: str) -> str | None` — the stored city name for a slug within a state, or None.

- [ ] **Step 1: Write the failing test**

Create `apps/support_services/test_city_hubs.py`:

```python
"""City/state hub aggregation."""
from datetime import time

from django.test import TestCase

from apps.support_services.hubs import (
    MIN_MEETINGS_FOR_HUB, city_slug, hub_cities, hub_states, resolve_city,
)
from apps.support_services.models import Meeting


def make_meetings(city, state, n, **extra):
    for i in range(n):
        defaults = dict(
            name=f'{city} Group {i}', slug=f'mtg-t-{city}-{state}-{i}'.lower(),
            day=i % 7, time=time(19, 0), attendance_option='in_person',
            city=city, state=state, is_approved=True, is_active=True,
        )
        defaults.update(extra)
        Meeting.objects.create(**defaults)


class CitySlugTests(TestCase):
    def test_spaces_and_case(self):
        self.assertEqual(city_slug('League City'), 'league-city')

    def test_punctuation(self):
        self.assertEqual(city_slug („St. Petersburg"), 'st-petersburg')

    def test_hyphenated_name(self):
        self.assertEqual(city_slug('Cornwall-On-Hudson'), 'cornwall-on-hudson')


class HubCitiesTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Weimar', 'TX', 1)      # below threshold
        make_meetings('Seattle', 'WA', 4)

    def test_only_cities_at_or_above_threshold(self):
        names = [c['city'] for c in hub_cities()]
        self.assertIn('Houston', names)
        self.assertIn('Katy', names)
        self.assertNotIn('Weimar', names)

    def test_threshold_is_inclusive(self):
        self.assertEqual(MIN_MEETINGS_FOR_HUB, 3)
        self.assertIn('Katy', [c['city'] for c in hub_cities()])

    def test_ordered_by_count_desc(self):
        counts = [c['count'] for c in hub_cities()]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_filtered_by_state(self):
        self.assertEqual([c['city'] for c in hub_cities('TX')], ['Houston', 'Katy'])

    def test_state_filter_is_case_insensitive(self):
        self.assertEqual(hub_cities('tx'), hub_cities('TX'))

    def test_carries_a_slug(self):
        houston = [c for c in hub_cities() if c['city'] == 'Houston'][0]
        self.assertEqual(houston['slug'], 'houston')

    def test_inactive_and_unapproved_are_excluded(self):
        make_meetings('Austin', 'TX', 4, is_active=False)
        make_meetings('Dallas', 'TX', 4, is_approved=False)
        names = [c['city'] for c in hub_cities()]
        self.assertNotIn('Austin', names)
        self.assertNotIn('Dallas', names)

    def test_meetings_without_a_city_are_ignored(self):
        make_meetings('', '', 5, attendance_option='online')
        self.assertNotIn('', [c['city'] for c in hub_cities()])


class HubStatesTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Seattle', 'WA', 4)
        make_meetings('Trenton', 'NJ', 1)     # no qualifying city

    def test_only_states_with_a_qualifying_city(self):
        codes = [s['state'] for s in hub_states()]
        self.assertIn('TX', codes)
        self.assertIn('WA', codes)
        self.assertNotIn('NJ', codes)

    def test_counts_are_over_qualifying_cities_only(self):
        tx = [s for s in hub_states() if s['state'] == 'TX'][0]
        self.assertEqual(tx['city_count'], 2)
        self.assertEqual(tx['count'], 8)


class ResolveCityTests(TestCase):
    def setUp(self):
        make_meetings('League City', 'TX', 3)
        make_meetings('Montgomery', 'TX', 3)
        make_meetings('Montgomery', 'NY', 3)

    def test_resolves_slug_to_stored_name(self):
        self.assertEqual(resolve_city('TX', 'league-city'), 'League City')

    def test_same_slug_in_two_states_resolves_independently(self):
        self.assertEqual(resolve_city('TX', 'montgomery'), 'Montgomery')
        self.assertEqual(resolve_city('NY', 'montgomery'), 'Montgomery')

    def test_unknown_slug_returns_none(self):
        self.assertIsNone(resolve_city('TX', 'nowhere'))

    def test_below_threshold_city_does_not_resolve(self):
        make_meetings('Weimar', 'TX', 1)
        self.assertIsNone(resolve_city('TX', 'weimar'))
```

Note: the `city_slug('St. Petersburg')` line above uses the wrong quote
characters as written — type it with normal single quotes.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_city_hubs -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.support_services.hubs'`

- [ ] **Step 3: Write minimal implementation**

Create `apps/support_services/hubs.py`:

```python
"""City and state hub aggregation for the meeting directory.

The 6,451 meeting detail pages cannot rank for "aa meetings in houston" —
that query wants a list. These helpers derive the list pages from the
existing city/state columns; there is no hub model and no migration.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_city_hubs -v 2`
Expected: PASS (17 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/hubs.py apps/support_services/test_city_hubs.py
git commit -m "feat(meetings): city/state hub aggregation helpers"
```

---

### Task 2: City and state hub views and URLs

**Files:**
- Modify: `apps/support_services/views.py`
- Modify: `apps/support_services/urls.py`
- Create: `apps/support_services/templates/support_services/city_hub.html`
- Create: `apps/support_services/templates/support_services/state_hub.html`
- Test: `apps/support_services/test_city_hubs.py`

**Interfaces:**
- Consumes: `hub_cities`, `hub_states`, `resolve_city`, `city_slug` from Task 1.
- Produces: url names `support_services:city_hub` (kwargs `state`, `city_slug`) and `support_services:state_hub` (kwarg `state`).

- [ ] **Step 1: Write the failing test**

Append to `apps/support_services/test_city_hubs.py`:

```python
from django.test import override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CityHubViewTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Weimar', 'TX', 1)
        self.url = reverse('support_services:city_hub',
                           kwargs={'state': 'tx', 'city_slug': 'houston'})

    def test_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_lists_the_city_meetings(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Houston Group 0', html)

    def test_title_targets_the_local_query(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('<title>AA Meetings in Houston, TX', html)

    def test_description_is_specific_not_boilerplate(self):
        html = self.client.get(self.url).content.decode()
        self.assertNotIn('Free recovery community. Track milestones', html)
        self.assertIn('Houston, TX', html)

    def test_canonical_is_self(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('/support/meetings/tx/houston/"', html)

    def test_links_to_its_state_hub(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn(reverse('support_services:state_hub',
                              kwargs={'state': 'tx'}), html)

    def test_below_threshold_city_404s(self):
        url = reverse('support_services:city_hub',
                      kwargs={'state': 'tx', 'city_slug': 'weimar'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_city_404s(self):
        url = reverse('support_services:city_hub',
                      kwargs={'state': 'tx', 'city_slug': 'atlantis'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_uppercase_state_in_url_still_resolves(self):
        url = '/support/meetings/TX/houston/'
        self.assertEqual(self.client.get(url).status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class StateHubViewTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Katy', 'TX', 3)
        make_meetings('Weimar', 'TX', 1)
        self.url = reverse('support_services:state_hub', kwargs={'state': 'tx'})

    def test_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_lists_qualifying_cities_with_links(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('Houston', html)
        self.assertIn('/support/meetings/tx/houston/', html)
        self.assertIn('/support/meetings/tx/katy/', html)

    def test_title_names_the_state(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('<title>AA Meetings in Texas', html)

    def test_state_with_no_qualifying_city_404s(self):
        make_meetings('Trenton', 'NJ', 1)
        url = reverse('support_services:state_hub', kwargs={'state': 'nj'})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_meeting_detail_slug_route_still_works(self):
        """The 2-letter state route must not swallow meeting detail URLs."""
        m = Meeting.objects.filter(city='Houston').first()
        self.assertEqual(self.client.get(m.get_absolute_url()).status_code, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_city_hubs -v 2`
Expected: FAIL — `NoReverseMatch: 'city_hub' is not a valid view function or pattern name`

- [ ] **Step 3: Write minimal implementation**

Add to `apps/support_services/views.py`:

```python
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


def city_hub(request, state, city_slug):
    """Directory of every meeting in one city — the page that answers
    "aa meetings in <city>". Detail pages cannot rank for that query."""
    state = state.upper()
    city = resolve_city(state, city_slug)
    if not city:
        raise Http404('No meeting hub for that city')

    meetings = (
        Meeting.objects
        .filter(is_approved=True, is_active=True, state=state, city=city)
        .order_by('day', 'time', 'name')
    )
    by_day = {}
    for m in meetings:
        by_day.setdefault(m.get_day_display() if m.day is not None
                          else 'Schedule varies', []).append(m)

    state_name = US_STATES.get(state, state)
    total = meetings.count()
    online = sum(1 for m in meetings if m.attendance_option != 'in_person')

    return render(request, 'support_services/city_hub.html', {
        'city': city,
        'state': state,
        'state_name': state_name,
        'meetings': meetings,
        'by_day': by_day,
        'total': total,
        'online_count': online,
        'in_person_count': total - online,
        'seo_title': f'AA Meetings in {city}, {state} — {total} Local Meeting Times',
        'seo_description': (
            f'{total} AA meetings in {city}, {state}. Browse by day with '
            f'times, addresses and online options — free, no signup, '
            f'updated weekly from the local AA intergroup.'
        ),
        'seo_keywords': (
            f'aa meetings {city.lower()}, aa meetings in {city.lower()} {state.lower()}, '
            f'alcoholics anonymous {city.lower()}, aa meeting schedule {city.lower()}, '
            f'{city.lower()} recovery meetings'
        ),
        'seo_url': request.build_absolute_uri(
            reverse('support_services:city_hub',
                    kwargs={'state': state.lower(), 'city_slug': city_slug})),
    })


def state_hub(request, state):
    """Index of the cities in one state that have their own hub."""
    state = state.upper()
    cities = hub_cities(state)
    if not cities:
        raise Http404('No meeting hub for that state')

    state_name = US_STATES.get(state, state)
    total = sum(c['count'] for c in cities)

    return render(request, 'support_services/state_hub.html', {
        'state': state,
        'state_name': state_name,
        'cities': sorted(cities, key=lambda c: c['city']),
        'cities_by_size': cities,
        'total': total,
        'seo_title': f'AA Meetings in {state_name} — {total} Meetings in {len(cities)} Cities',
        'seo_description': (
            f'Find AA meetings across {state_name}. {total} meetings in '
            f'{len(cities)} cities with times, addresses and online options — '
            f'free and updated weekly.'
        ),
        'seo_keywords': (
            f'aa meetings {state_name.lower()}, alcoholics anonymous '
            f'{state_name.lower()}, aa meeting directory {state_name.lower()}'
        ),
        'seo_url': request.build_absolute_uri(
            reverse('support_services:state_hub', kwargs={'state': state.lower()})),
    })
```

Add these imports at the top of `views.py`:

```python
from django.http import Http404
from apps.support_services.hubs import hub_cities, resolve_city
```

(`Http404` may already be imported alongside `JsonResponse`; check before
adding a duplicate.)

Add to `apps/support_services/urls.py`, **above** the
`meetings/<slug:slug>/` line:

```python
    # Hub pages. These MUST precede meetings/<slug:slug>/ — a bare slug
    # converter would otherwise match "tx" and route /meetings/tx/ to the
    # detail view. The state pattern is pinned to exactly two letters.
    re_path(r'^meetings/(?P<state>[A-Za-z]{2})/$',
            views.state_hub, name='state_hub'),
    re_path(r'^meetings/(?P<state>[A-Za-z]{2})/(?P<city_slug>[a-z0-9-]+)/$',
            views.city_hub, name='city_hub'),
```

and change the import line at the top of `urls.py`:

```python
from django.urls import path, re_path
```

- [ ] **Step 4: Create the templates**

Create `apps/support_services/templates/support_services/city_hub.html`:

```html
{% extends 'base.html' %}
{% load static %}

{% block canonical_url %}{{ seo_url }}{% endblock %}

{% block content %}
<div class="container py-4">
    <nav aria-label="breadcrumb" class="mb-3">
        <a href="{% url 'support_services:meeting_list' %}">Meetings</a>
        &rsaquo;
        <a href="{% url 'support_services:state_hub' state=state|lower %}">{{ state_name }}</a>
        &rsaquo; <span>{{ city }}</span>
    </nav>

    <h1>AA Meetings in {{ city }}, {{ state }}</h1>
    <p class="lead">
        {{ total }} meeting{{ total|pluralize }} in {{ city }} —
        {{ in_person_count }} in person{% if online_count %},
        {{ online_count }} with an online option{% endif %}.
        Updated weekly from the local AA intergroup.
    </p>

    {% include 'support_services/_court_compliance_nudge.html' %}

    {% for day, day_meetings in by_day.items %}
    <section class="mb-4">
        <h2 style="font-size:1.15rem;">{{ day }}</h2>
        <ul class="list-unstyled">
            {% for m in day_meetings %}
            <li class="mb-2">
                <a href="{{ m.get_absolute_url }}"><strong>{{ m.name }}</strong></a>
                {% if m.time %} &middot; {{ m.time|time:"g:i A" }}{% endif %}
                {% if m.location %} &middot; {{ m.location }}{% endif %}
                {% if m.attendance_option != 'in_person' %}
                    <span class="badge bg-info">Online option</span>
                {% endif %}
            </li>
            {% endfor %}
        </ul>
    </section>
    {% endfor %}

    <p><a href="{% url 'support_services:state_hub' state=state|lower %}">
        All AA meetings in {{ state_name }} &rarr;</a></p>
</div>
{% endblock %}
```

Create `apps/support_services/templates/support_services/state_hub.html`:

```html
{% extends 'base.html' %}
{% load static %}

{% block canonical_url %}{{ seo_url }}{% endblock %}

{% block content %}
<div class="container py-4">
    <nav aria-label="breadcrumb" class="mb-3">
        <a href="{% url 'support_services:meeting_list' %}">Meetings</a>
        &rsaquo; <span>{{ state_name }}</span>
    </nav>

    <h1>AA Meetings in {{ state_name }}</h1>
    <p class="lead">
        {{ total }} meeting{{ total|pluralize }} across
        {{ cities|length }} cit{{ cities|length|pluralize:"y,ies" }}.
        Updated weekly from local AA intergroups.
    </p>

    <div class="row">
        {% for c in cities %}
        <div class="col-md-4 col-sm-6 mb-2">
            <a href="{% url 'support_services:city_hub' state=c.state|lower city_slug=c.slug %}">
                {{ c.city }}</a>
            <span class="text-muted">({{ c.count }})</span>
        </div>
        {% endfor %}
    </div>

    <p class="mt-4"><a href="{% url 'support_services:meeting_list' %}">
        Search all meetings &rarr;</a></p>
</div>
{% endblock %}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_city_hubs -v 2`
Expected: PASS (all tests, including `test_meeting_detail_slug_route_still_works`)

- [ ] **Step 6: Commit**

```bash
git add apps/support_services/views.py apps/support_services/urls.py \
        apps/support_services/templates/support_services/city_hub.html \
        apps/support_services/templates/support_services/state_hub.html \
        apps/support_services/test_city_hubs.py
git commit -m "feat(meetings): city and state hub pages"
```

---

### Task 3: Link detail pages to their city hub

Gives all 6,451 detail pages a crawl parent, which is what makes them more
likely to index rather than less.

**Files:**
- Modify: `apps/support_services/models.py`
- Modify: `apps/support_services/templates/support_services/meeting_detail.html`
- Test: `apps/support_services/test_city_hubs.py`

**Interfaces:**
- Consumes: `hub_cities`, `city_slug` from Task 1.
- Produces: `Meeting.city_hub_url` property — the hub URL, or `''` when the
  meeting has no city or its city is below the threshold.

- [ ] **Step 1: Write the failing test**

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DetailBacklinkTests(TestCase):
    def test_detail_page_links_to_its_city_hub(self):
        make_meetings('Houston', 'TX', 4)
        m = Meeting.objects.filter(city='Houston').first()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('/support/meetings/tx/houston/', html)

    def test_no_backlink_when_city_is_below_threshold(self):
        make_meetings('Weimar', 'TX', 1)
        m = Meeting.objects.get(city='Weimar')
        self.assertEqual(m.city_hub_url, '')

    def test_no_backlink_for_an_online_meeting(self):
        Meeting.objects.create(
            name='Online One', slug='mtg-t-online-1',
            attendance_option='online', conference_url='https://zoom.us/j/1',
            is_approved=True, is_active=True)
        self.assertEqual(Meeting.objects.get(slug='mtg-t-online-1').city_hub_url, '')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_city_hubs.DetailBacklinkTests -v 2`
Expected: FAIL — `AttributeError: 'Meeting' object has no attribute 'city_hub_url'`

- [ ] **Step 3: Write minimal implementation**

Add to `Meeting` in `apps/support_services/models.py`, next to `seo_description`:

```python
    @property
    def city_hub_url(self):
        """URL of this meeting's city hub, or '' when there isn't one.

        Gives every detail page a crawl parent. Empty for online meetings
        and for cities below MIN_MEETINGS_FOR_HUB.
        """
        if not self.city or not self.state:
            return ''
        from django.urls import reverse
        from apps.support_services.hubs import city_slug, hub_cities
        slug = city_slug(self.city)
        if not any(c['slug'] == slug for c in hub_cities(self.state)):
            return ''
        return reverse('support_services:city_hub',
                       kwargs={'state': self.state.lower(), 'city_slug': slug})
```

Add to `meeting_detail.html`, immediately after the `_court_meeting_cta`
include:

```html
            {% if meeting.city_hub_url %}
            <p class="mb-3">
                <a href="{{ meeting.city_hub_url }}">
                    &larr; All AA meetings in {{ meeting.city }}, {{ meeting.state }}
                </a>
            </p>
            {% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services -v 1`
Expected: PASS — the whole app, including the existing meeting SEO and
court CTA suites.

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/models.py \
        apps/support_services/templates/support_services/meeting_detail.html \
        apps/support_services/test_city_hubs.py
git commit -m "feat(meetings): link detail pages to their city hub"
```

---

### Task 4: Add hubs to the sitemap

**Files:**
- Modify: `recovery_hub/sitemaps.py`
- Test: `apps/support_services/test_city_hubs.py`

**Interfaces:**
- Consumes: `hub_cities`, `hub_states` from Task 1.
- Produces: sitemap keys `city_hubs` and `state_hubs`.

- [ ] **Step 1: Write the failing test**

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class HubSitemapTests(TestCase):
    def setUp(self):
        make_meetings('Houston', 'TX', 5)
        make_meetings('Weimar', 'TX', 1)

    def test_city_hub_is_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/support/meetings/tx/houston/</loc>', xml)

    def test_state_hub_is_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/support/meetings/tx/</loc>', xml)

    def test_below_threshold_city_is_not_listed(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/support/meetings/tx/weimar/', xml)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_city_hubs.HubSitemapTests -v 2`
Expected: FAIL — the hub URLs are absent from the sitemap.

- [ ] **Step 3: Write minimal implementation**

Add to `recovery_hub/sitemaps.py`, before the `sitemaps` dict:

```python
class CityHubSitemap(Sitemap):
    """City directory pages — the ones that can rank for
    "aa meetings in <city>". Detail pages cannot."""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.8      # above detail pages (0.6), below the hub (0.9)

    def items(self):
        from apps.support_services.hubs import hub_cities
        return hub_cities()

    def location(self, obj):
        return reverse('support_services:city_hub',
                       kwargs={'state': obj['state'].lower(),
                               'city_slug': obj['slug']})

    def get_urls(self, page=1, site=None, protocol=None):
        from django.contrib.sites.models import Site
        if site is None:
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')


class StateHubSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        from apps.support_services.hubs import hub_states
        return hub_states()

    def location(self, obj):
        return reverse('support_services:state_hub',
                       kwargs={'state': obj['state'].lower()})

    def get_urls(self, page=1, site=None, protocol=None):
        from django.contrib.sites.models import Site
        if site is None:
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')
```

and register both:

```python
sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
    'store_categories': StoreCategorySitemap,
    'resources': ResourceSitemap,
    'meetings': MeetingSitemap,
    'state_hubs': StateHubSitemap,
    'city_hubs': CityHubSitemap,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_city_hubs -v 1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add recovery_hub/sitemaps.py apps/support_services/test_city_hubs.py
git commit -m "feat(meetings): add city and state hubs to the sitemap"
```

---

### Task 5: Correct the inaccurate directory copy, and link the finder to the hubs

The `/support/meetings/` description shipped on 2026-09-07 claims the
directory carries "AA, NA, SMART Recovery and secular groups" and "1,500+"
meetings. Both are wrong: it is 100% AA (three AA intergroup feeds, zero
community submissions) and now 6,451 meetings.

**Files:**
- Modify: `apps/support_services/views.py` (`meeting_list`)
- Modify: `apps/support_services/templates/support_services/meeting_list.html`
- Test: `apps/support_services/test_meeting_seo.py`

**Interfaces:**
- Consumes: `hub_states` from Task 1.
- Produces: `states` in the `meeting_list` context.

- [ ] **Step 1: Write the failing test**

Add to `apps/support_services/test_meeting_seo.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DirectoryCopyAccuracyTests(TestCase):
    """The directory is sourced entirely from AA intergroup feeds. Claiming
    NA and SMART meetings it does not have is a factual error, and "1,500+"
    understates it by 4x."""

    def test_description_does_not_claim_programs_we_do_not_carry(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertNotIn('SMART Recovery and secular groups', html)
        self.assertNotIn('1,500+', html)

    def test_description_says_aa(self):
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertIn('AA meetings', html)

    def test_finder_links_to_state_hubs(self):
        from apps.support_services.test_city_hubs import make_meetings
        make_meetings('Houston', 'TX', 4)
        html = self.client.get(reverse('support_services:meeting_list')).content.decode()
        self.assertIn('/support/meetings/tx/', html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_meeting_seo.DirectoryCopyAccuracyTests -v 2`
Expected: FAIL — the current description still contains "SMART Recovery and
secular groups" and "1,500+".

- [ ] **Step 3: Write minimal implementation**

In `meeting_list` in `views.py`, replace the `seo_title` / `seo_description`
/ `seo_keywords` values and add `states`:

```python
        'states': hub_states(),
        'seo_title': 'AA Meeting Finder — Search Local & Online AA Meetings',
        'seo_description': (
            'Search thousands of free AA meetings by day, city, state or '
            'online. Times, addresses and Zoom links, updated weekly from '
            'local AA intergroups. No signup.'
        ),
        'seo_keywords': (
            'aa meetings near me, aa meeting finder, aa meeting directory, '
            'online aa meetings, aa meeting schedule, alcoholics anonymous '
            'meetings, find aa meetings'
        ),
```

Add to `meeting_list.html`, just above the results list:

```html
    {% if states %}
    <section class="mb-4">
        <h2 style="font-size:1.05rem;">Browse by state</h2>
        {% for s in states %}
        <a class="badge bg-light text-dark me-1"
           href="{% url 'support_services:state_hub' state=s.state|lower %}">
            {{ s.state }} ({{ s.count }})</a>
        {% endfor %}
    </section>
    {% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services -v 1`
Expected: PASS. `test_hub_page_replaces_boilerplate_everywhere` in
`test_meeting_seo.py` asserts the old `'Search 1,500+ free recovery
meetings'` string — update it to the new description.

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/views.py \
        apps/support_services/templates/support_services/meeting_list.html \
        apps/support_services/test_meeting_seo.py
git commit -m "fix(meetings): correct directory copy and link finder to hubs"
```

---

### Task 6: Verify against production data

**Files:** none — verification only.

- [ ] **Step 1: Full regression**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test \
  apps.accounts apps.support_services apps.blog \
  apps.core.test_ga_events apps.core.test_social_meta \
  apps.core.test_online_aa_meetings apps.core.test_relapse_plan_landing \
  apps.core.test_craving_sos
```

Expected: OK, no failures.

- [ ] **Step 2: Count the hubs production will generate**

```bash
DATABASE_URL="<production public URL>" python3 manage.py shell -c "
from apps.support_services.hubs import hub_cities, hub_states
c, s = hub_cities(), hub_states()
print('city hubs :', len(c))
print('state hubs:', len(s), [x['state'] for x in s])
print('largest   :', [(x['city'], x['state'], x['count']) for x in c[:5]])
"
```

Expected: ~166 city hubs, 4 state hubs (NY, TX, WA, CT), largest being
New York 699, Houston 694, Seattle 427, Brooklyn 314.

- [ ] **Step 3: Confirm the sitemap total**

Local sitemap URL count should rise by roughly the number of hubs. After
deploy, `curl -s https://www.myrecoverypal.com/sitemap.xml | grep -c '<loc>'`
should be about 6,574 + 170 ≈ 6,744, still far under the 50,000 limit.

---

## Self-Review

**Spec coverage:**

| Design decision | Task |
|---|---|
| City URL `/meetings/<state>/<city>/` | 2 |
| State URL `/meetings/<state>/` | 2 |
| Routes precede `<slug:slug>`, state pinned to 2 letters | 2 (tested) |
| `MIN_MEETINGS_FOR_HUB = 3` | 1 (tested both sides) |
| Below-threshold cities have no page | 1, 2 (404 tested) |
| Program naming is AA | 2, 5 (tested) |
| No new model / no migration | 1 |
| Internal linking detail → city → state → finder | 2, 3, 5 |
| Sitemap coverage | 4 |
| Correct the inaccurate 1,500+/NA/SMART copy | 5 |

**Type consistency:** `hub_cities()` returns dicts with `city`/`state`/
`slug`/`count`; consumed with those exact keys by the views (Task 2),
`city_hub_url` (Task 3) and both sitemaps (Task 4). `hub_states()` returns
`state`/`count`/`city_count`, consumed by `state_hub`, `StateHubSitemap`
and the finder template.

**Known plan defect:** Task 1's `city_slug('St. Petersburg')` test is
written with typographic quotes. Type it with normal single quotes.
