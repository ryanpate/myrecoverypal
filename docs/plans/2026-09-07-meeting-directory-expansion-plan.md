# Meeting Directory Expansion (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the in-person and hybrid meetings already present in the three configured TSML feeds, instead of discarding them, without changing any existing meeting URL.

**Architecture:** Three functions in `apps/support_services/meeting_sync.py` change — `sync_source` (stop filtering to online), `_map` (branch on attendance, carry address fields), and slug/deactivation handling (dual-prefix namespace so existing rows update in place). The `Meeting` model already has every column TSML sends; no migration is needed. The SEO layer shipped 2026-09-07 already renders in-person correctly.

**Tech Stack:** Django 5.0.10, PostgreSQL (SQLite in tests), Celery Beat weekly sync, TSML / Meeting Guide API JSON feeds.

**Spec:** `docs/plans/2026-09-07-meeting-directory-expansion-design.md`

## Global Constraints

- **Never change an existing meeting slug.** The 1,565 `online-<key>-<slug>` rows are being indexed for the first time. Any change to `SLUG_PREFIX` or to how existing rows are keyed is a plan failure.
- **New import rows use prefix `mtg-<key>-<slug>`.** The prefix encodes import source, never attendance — a meeting that goes online→hybrid keeps its URL.
- **The `submitted_by__isnull=True` guard stays on every deactivation query.** Community-submitted meetings are never touched by a feed sync.
- **An empty feed never deactivates anything.** Existing behaviour; must not regress.
- Run tests with `python3 manage.py test` (not `python`). `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` is only needed for the court PDF suite, not this one.
- Test feeds are local JSON files via `feed_file(...)` in `apps/support_services/test_meeting_sync.py`. No HTTP mocking.
- Program-neutral copy throughout: "recovery meeting", never "AA meeting". The directory carries NA, SMART and secular groups.

---

### Task 1: Derive `attendance_option` when the feed omits it

`attendance_option` is a newer field in the Meeting Guide spec; older intergroup
feeds omit it entirely. Today those meetings are silently dropped. This task
adds the derivation helper on its own so the rest of the plan can rely on it.

**Files:**
- Modify: `apps/support_services/meeting_sync.py` (add helper near `_parse_time`, ~line 251)
- Test: `apps/support_services/test_meeting_sync.py`

**Interfaces:**
- Produces: `_attendance_option(m: dict) -> str` returning one of
  `"online"`, `"hybrid"`, `"in_person"`. Consumed by `_map` in Task 2 and
  `sync_source` in Task 3.

- [ ] **Step 1: Write the failing test**

Add to `apps/support_services/test_meeting_sync.py`:

```python
from apps.support_services.meeting_sync import _attendance_option


class AttendanceOptionDerivationTests(TestCase):
    """Older TSML feeds omit attendance_option; derive it from the payload."""

    def test_explicit_value_is_trusted(self):
        self.assertEqual(
            _attendance_option({"attendance_option": "hybrid"}), "hybrid")

    def test_conference_url_and_address_is_hybrid(self):
        self.assertEqual(
            _attendance_option({
                "conference_url": "https://zoom.us/j/1",
                "formatted_address": "123 Main St, Houston, TX",
            }),
            "hybrid",
        )

    def test_conference_url_only_is_online(self):
        self.assertEqual(
            _attendance_option({"conference_url": "https://zoom.us/j/1"}),
            "online",
        )

    def test_address_only_is_in_person(self):
        self.assertEqual(
            _attendance_option({"formatted_address": "123 Main St"}),
            "in_person",
        )

    def test_bare_address_field_counts_as_a_location(self):
        self.assertEqual(_attendance_option({"address": "123 Main St"}), "in_person")

    def test_no_signal_at_all_is_in_person(self):
        self.assertEqual(_attendance_option({}), "in_person")

    def test_unrecognised_explicit_value_is_derived_instead(self):
        self.assertEqual(
            _attendance_option({
                "attendance_option": "hybrid_but_typoed",
                "conference_url": "https://zoom.us/j/1",
            }),
            "online",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_meeting_sync.AttendanceOptionDerivationTests -v 2`
Expected: FAIL — `ImportError: cannot import name '_attendance_option'`

- [ ] **Step 3: Write minimal implementation**

Add to `apps/support_services/meeting_sync.py`, immediately after `_parse_time`:

```python
VALID_ATTENDANCE = {"online", "hybrid", "in_person"}


def _attendance_option(m):
    """Resolve a meeting's attendance option.

    `attendance_option` is a newer field in the Meeting Guide spec; plenty of
    intergroup feeds predate it. Derive from what the payload actually has:
    a join link plus a street address is hybrid, a join link alone is online,
    anything else is in-person.
    """
    explicit = (m.get("attendance_option") or "").strip()
    if explicit in VALID_ATTENDANCE:
        return explicit

    has_url = bool(m.get("conference_url"))
    has_address = bool(m.get("formatted_address") or m.get("address"))
    if has_url and has_address:
        return "hybrid"
    if has_url:
        return "online"
    return "in_person"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_meeting_sync.AttendanceOptionDerivationTests -v 2`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_sync.py apps/support_services/test_meeting_sync.py
git commit -m "feat(meetings): derive attendance_option for feeds that omit it"
```

---

### Task 2: Map address fields for in-person and hybrid meetings

`_map` currently hardcodes `attendance_option: "online"` and
`location: "Online Meeting"`, and drops every address field. The `Meeting`
model already has columns for all of them.

**Files:**
- Modify: `apps/support_services/meeting_sync.py:227-247` (`_map`)
- Test: `apps/support_services/test_meeting_sync.py`

**Interfaces:**
- Consumes: `_attendance_option(m)` from Task 1.
- Produces: `_map(m, approve, default_tz)` now returns a dict whose
  `attendance_option` reflects the meeting and which includes the keys
  `location`, `formatted_address`, `address`, `city`, `state`,
  `postal_code`, `country`, `latitude`, `longitude`, `region`, `website`.
  Consumed by `sync_source` in Task 3.

- [ ] **Step 1: Write the failing test**

Add to `apps/support_services/test_meeting_sync.py`. Put the new fixture next
to the existing `ONLINE_MEETING` / `IN_PERSON_MEETING` constants at the top:

```python
FULL_IN_PERSON_MEETING = {
    "name": "Downtown Noon",
    "slug": "downtown-noon",
    "day": 2,
    "time": "12:00",
    "end_time": "13:00",
    "attendance_option": "in_person",
    "location": "First Methodist Church",
    "formatted_address": "123 Main St, Houston, TX 77002, USA",
    "address": "123 Main St",
    "city": "Houston",
    "state": "TX",
    "postal_code": "77002",
    "country": "US",
    "latitude": "29.76043200",
    "longitude": "-95.36980300",
    "region": "Downtown",
    "website": "https://aahouston.org/",
    "types": ["O", "D"],
}

HYBRID_MEETING = {
    "name": "Bridge Group",
    "slug": "bridge-group",
    "day": 3,
    "time": "18:00",
    "attendance_option": "hybrid",
    "conference_url": "https://zoom.us/j/999",
    "location": "Community Hall",
    "formatted_address": "9 Oak Ave, Seattle, WA",
    "city": "Seattle",
    "state": "WA",
}
```

Then add the test class:

```python
from apps.support_services.meeting_sync import _map


class MapAddressFieldsTests(TestCase):
    def test_in_person_meeting_carries_its_address(self):
        d = _map(FULL_IN_PERSON_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "in_person")
        self.assertEqual(d["location"], "First Methodist Church")
        self.assertEqual(d["formatted_address"], "123 Main St, Houston, TX 77002, USA")
        self.assertEqual(d["address"], "123 Main St")
        self.assertEqual(d["city"], "Houston")
        self.assertEqual(d["state"], "TX")
        self.assertEqual(d["postal_code"], "77002")
        self.assertEqual(d["region"], "Downtown")
        self.assertEqual(d["website"], "https://aahouston.org/")
        self.assertEqual(str(d["latitude"]), "29.76043200")

    def test_in_person_meeting_has_no_conference_url(self):
        d = _map(FULL_IN_PERSON_MEETING, True, "America/Chicago")
        self.assertEqual(d["conference_url"], "")

    def test_hybrid_meeting_carries_both_address_and_join_link(self):
        d = _map(HYBRID_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "hybrid")
        self.assertEqual(d["conference_url"], "https://zoom.us/j/999")
        self.assertEqual(d["city"], "Seattle")

    def test_online_meeting_keeps_its_placeholder_location(self):
        """Online meetings must not look like somewhere you travel to."""
        d = _map(ONLINE_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "online")
        self.assertEqual(d["location"], "Online Meeting")
        self.assertEqual(d["formatted_address"], "")
        self.assertEqual(d["city"], "")

    def test_state_is_truncated_to_the_column_width(self):
        """Meeting.state is CharField(max_length=2); some feeds send
        full state names, which would raise DataError on Postgres."""
        d = _map({**FULL_IN_PERSON_MEETING, "state": "Texas"}, True, "UTC")
        self.assertEqual(d["state"], "Te")

    def test_missing_coordinates_become_none_not_empty_string(self):
        d = _map(HYBRID_MEETING, True, "America/Chicago")
        self.assertIsNone(d["latitude"])
        self.assertIsNone(d["longitude"])

    def test_meeting_without_a_name_is_still_skipped(self):
        self.assertIsNone(_map({"city": "Houston"}, True, "UTC"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_meeting_sync.MapAddressFieldsTests -v 2`
Expected: FAIL — `KeyError: 'formatted_address'` and
`AssertionError: 'online' != 'in_person'`

- [ ] **Step 3: Write minimal implementation**

Replace `_map` in `apps/support_services/meeting_sync.py` entirely:

```python
def _map(m, approve, default_tz):
    name = (m.get("name") or "").strip()
    if not name:
        return None

    attendance = _attendance_option(m)
    online_only = attendance == "online"

    mapped = {
        "name": name,
        "day": m.get("day"),
        "time": _parse_time(m.get("time")),
        "end_time": _parse_time(m.get("end_time")),
        "timezone": m.get("timezone") or default_tz,
        "attendance_option": attendance,
        "conference_url": "" if attendance == "in_person" else (m.get("conference_url") or ""),
        "conference_phone": (m.get("conference_phone") or "")[:30],
        "types": m.get("types") or [],
        "group": (m.get("group") or "")[:255],
        "notes": m.get("notes") or "",  # join instructions / passwords
        "website": (m.get("website") or "")[:200],
        "is_approved": approve,
        "is_active": True,
    }

    if online_only:
        # Online meetings have no physical location; keep address fields
        # blank so users don't think they need to travel.
        mapped.update({
            "location": "Online Meeting",
            "formatted_address": "",
            "address": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "region": "",
            "latitude": None,
            "longitude": None,
        })
    else:
        mapped.update({
            "location": (m.get("location") or "")[:255],
            "formatted_address": (m.get("formatted_address") or "")[:500],
            "address": (m.get("address") or "")[:255],
            "city": (m.get("city") or "")[:100],
            "state": (m.get("state") or "")[:2],
            "postal_code": (m.get("postal_code") or "")[:10],
            "region": (m.get("region") or "")[:100],
            "latitude": _decimal(m.get("latitude")),
            "longitude": _decimal(m.get("longitude")),
        })
    return mapped
```

And add the coordinate coercion helper next to `_parse_time`:

```python
def _decimal(value):
    """Coerce a feed coordinate to Decimal, or None if it is unusable.

    Feeds send coordinates as strings, sometimes empty, occasionally "0" for
    "unknown". A bad coordinate must not abort a whole sync.
    """
    if value in (None, "", "0", 0):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
```

Add the import at the top of `apps/support_services/meeting_sync.py`:

```python
from decimal import Decimal, InvalidOperation
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_meeting_sync.MapAddressFieldsTests -v 2`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_sync.py apps/support_services/test_meeting_sync.py
git commit -m "feat(meetings): map address fields for in-person and hybrid meetings"
```

---

### Task 3: Import every meeting, on a dual-prefix slug namespace

`sync_source` filters to online meetings and computes slugs as
`online-<key>-<base>`. This task stops the filter and introduces the
`mtg-<key>-<base>` namespace for new rows, resolving existing rows by either
prefix so no URL changes and no duplicate is created.

**Files:**
- Modify: `apps/support_services/meeting_sync.py:26` (`SLUG_PREFIX`), `:117-172` (`sync_source`), `:222-225` (`_slug`)
- Test: `apps/support_services/test_meeting_sync.py`

**Interfaces:**
- Consumes: `_map(m, approve, default_tz)` from Task 2.
- Produces:
  - `IMPORT_SLUG_PREFIXES: tuple[str, ...] = ("mtg", "online")` — resolution
    order, newest namespace first.
  - `_slug(key, m) -> str` now returns `mtg-<key>-<base>`.
  - `_resolve_slug(key, m) -> str` returns the slug of an existing imported
    row under either prefix, else the new `mtg-` slug.
  - `sync_source(...)` return dict is unchanged:
    `{"created", "updated", "skipped", "deactivated"}`.

- [ ] **Step 1: Write the failing test**

Add to `apps/support_services/test_meeting_sync.py`:

```python
class ImportsAllAttendanceTypesTests(TestCase):
    def test_in_person_meetings_are_imported(self):
        path = feed_file([ONLINE_MEETING, FULL_IN_PERSON_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 2)
        self.assertEqual(Meeting.objects.count(), 2)
        m = Meeting.objects.get(slug="mtg-test-downtown-noon")
        self.assertEqual(m.attendance_option, "in_person")
        self.assertEqual(m.city, "Houston")
        self.assertEqual(m.state, "TX")

    def test_new_online_meetings_use_the_mtg_prefix(self):
        path = feed_file([ONLINE_MEETING])
        sync_source("test", path)
        self.assertTrue(
            Meeting.objects.filter(slug="mtg-test-morning-serenity").exists())

    def test_existing_online_row_is_updated_in_place_not_duplicated(self):
        """The 1,565 legacy `online-` rows must keep their indexed URLs."""
        Meeting.objects.create(
            slug="online-test-morning-serenity",
            name="Morning Serenity",
            attendance_option="online",
            conference_url="https://zoom.us/j/OLD",
            is_approved=True, is_active=True,
        )
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(Meeting.objects.count(), 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.conference_url, "https://zoom.us/j/123")

    def test_online_meeting_that_becomes_hybrid_keeps_its_url(self):
        Meeting.objects.create(
            slug="online-test-bridge-group",
            name="Bridge Group",
            attendance_option="online",
            conference_url="https://zoom.us/j/999",
            is_approved=True, is_active=True,
        )
        path = feed_file([HYBRID_MEETING])
        sync_source("test", path)

        self.assertEqual(Meeting.objects.count(), 1)
        m = Meeting.objects.get(slug="online-test-bridge-group")
        self.assertEqual(m.attendance_option, "hybrid")
        self.assertEqual(m.city, "Seattle")

    def test_deactivation_covers_both_prefixes(self):
        Meeting.objects.create(
            slug="online-test-gone-legacy", name="Gone Legacy",
            is_approved=True, is_active=True)
        Meeting.objects.create(
            slug="mtg-test-gone-new", name="Gone New",
            is_approved=True, is_active=True)
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["deactivated"], 2)
        self.assertFalse(Meeting.objects.get(slug="online-test-gone-legacy").is_active)
        self.assertFalse(Meeting.objects.get(slug="mtg-test-gone-new").is_active)

    def test_community_submissions_are_never_deactivated(self):
        user = User.objects.create_user("c", "c@example.com", "pw")
        Meeting.objects.create(
            slug="mtg-test-community-run", name="Community Run",
            submitted_by=user, is_approved=True, is_active=True)
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(Meeting.objects.get(slug="mtg-test-community-run").is_active)

    def test_empty_feed_still_skips_deactivation(self):
        Meeting.objects.create(
            slug="mtg-test-survivor", name="Survivor",
            is_approved=True, is_active=True)
        result = sync_source("test", feed_file([]))

        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(Meeting.objects.get(slug="mtg-test-survivor").is_active)

    def test_meetings_without_a_name_are_skipped_not_imported(self):
        path = feed_file([ONLINE_MEETING, {"slug": "nameless", "day": 1}])
        result = sync_source("test", path)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_meeting_sync.ImportsAllAttendanceTypesTests -v 2`
Expected: FAIL — `Meeting.DoesNotExist: Meeting matching query does not exist`
for `mtg-test-downtown-noon` (in-person still filtered out).

- [ ] **Step 3: Write minimal implementation**

In `apps/support_services/meeting_sync.py`, replace the `SLUG_PREFIX` constant
(line 26):

```python
# Namespace for rows created by a feed import. "online" is the legacy prefix:
# ~1,565 rows were created under it when the importer was online-only, and
# they keep those slugs forever — they are indexed URLs. New rows use "mtg",
# which encodes the import source and NOT the attendance option, so a meeting
# that changes from online to hybrid keeps its URL.
SLUG_PREFIX = "mtg"
LEGACY_SLUG_PREFIX = "online"
IMPORT_SLUG_PREFIXES = (SLUG_PREFIX, LEGACY_SLUG_PREFIX)
```

Replace `_slug` (lines 222-225):

```python
def _slug(key, m):
    base = m.get("slug") or slugify(m.get("name", "meeting"))
    return f"{SLUG_PREFIX}-{key}-{base}"[:255]


def _resolve_slug(key, m):
    """Return the slug to upsert under.

    Prefers an existing imported row under any known prefix so legacy
    `online-` rows are updated in place rather than duplicated under `mtg-`.
    """
    base = m.get("slug") or slugify(m.get("name", "meeting"))
    for prefix in IMPORT_SLUG_PREFIXES:
        candidate = f"{prefix}-{key}-{base}"[:255]
        if Meeting.objects.filter(
            slug=candidate, submitted_by__isnull=True
        ).exists():
            return candidate
    return _slug(key, m)
```

Replace the filtering and slug lines in `sync_source`. The `online = [...]`
comprehension becomes:

```python
    data = load_feed(source)
    meetings = data if isinstance(data, list) else data.get("meetings", [])
    # Import every meeting the feed carries — in-person, hybrid and online.
    # The importer used to keep online meetings only, discarding the whole
    # in-person schedule of three metro intergroups.
    incoming = [m for m in meetings if (m.get("name") or "").strip()]
    if limit:
        incoming = incoming[:limit]

    if not incoming:
        logger.warning(
            "Feed %r returned no usable meetings; skipping deactivation "
            "to avoid wiping the source", key)
        return {"created": 0, "updated": 0, "skipped": 0, "deactivated": 0}
```

The upsert loop becomes:

```python
    created = updated = skipped = 0
    seen = []
    for m in incoming:
        defaults = _map(m, approve, default_tz)
        if defaults is None:
            skipped += 1
            continue
        slug = _resolve_slug(key, m)
        _, was_created = Meeting.objects.update_or_create(
            slug=slug, defaults=defaults
        )
        seen.append(slug)
        created += was_created
        updated += not was_created
```

And the deactivation query becomes:

```python
    # Deactivate imported rows that vanished from this source's feed, under
    # either namespace. submitted_by guard: community submissions always have
    # a submitter, imported rows never do — so a community meeting whose name
    # slugifies into this namespace can never be deactivated here.
    prefix_match = Q()
    for prefix in IMPORT_SLUG_PREFIXES:
        prefix_match |= Q(slug__startswith=f"{prefix}-{key}-")
    deactivated = (
        Meeting.objects
        .filter(prefix_match, submitted_by__isnull=True, is_active=True)
        .exclude(slug__in=seen)
        .update(is_active=False)
    )
```

Add the import at the top of the file (it is not currently imported):

```python
from django.db.models import Q
```

Finally, correct the module docstring at the top of `meeting_sync.py` — it
currently states the opposite of what the module now does. Replace its first
two paragraphs:

```python
"""Sync recovery meetings from public TSML/Meeting Guide JSON feeds.

Every meeting a feed carries is imported — in-person, hybrid and online.
The importer was online-only until 2026-09, which discarded the entire
in-person schedule of three metro intergroups.

Each source owns a slug namespace so feeds never collide with each other or
with community-submitted meetings. New rows use "mtg-<key>-...";
"online-<key>-..." is the legacy namespace and those rows keep their slugs
permanently, because they are indexed URLs. The prefix encodes the import
source, never the attendance option — a meeting that changes from online to
hybrid must keep its URL. Rows that disappear from their source feed are
deactivated — but only when that feed fetched successfully, so a down feed
never wipes out its meetings. Community submissions (submitted_by set) are
never touched.
"""
```

Finally, update `_deactivate_legacy_rows` so the one-time bare-prefix cleanup
does not sweep away the new `mtg-` namespace. Replace its queryset:

```python
def _deactivate_legacy_rows(keys):
    """One-time cleanup: the old seed used bare 'online-<slug>' rows with no
    source key. Once the namespaced re-import succeeds they are duplicates."""
    qs = Meeting.objects.filter(
        slug__startswith=f"{LEGACY_SLUG_PREFIX}-",
        submitted_by__isnull=True,
        is_active=True,
    )
    for key in keys:
        for prefix in IMPORT_SLUG_PREFIXES:
            qs = qs.exclude(slug__startswith=f"{prefix}-{key}-")
    return qs.update(is_active=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: PASS. The whole module must pass, not just the new class — several
existing tests assert the old `online-test-` slugs and the online-only filter.

Two pre-existing tests **will** fail and must be updated, because their asserted
behaviour is exactly what this task changes:

1. `SyncSourceTests.test_creates_online_meetings_with_namespaced_slug` — asserts
   `Meeting.objects.count() == 1` with the comment "In-person meetings from the
   feed are never imported." Change to expect 2 meetings, rename to
   `test_creates_meetings_with_namespaced_slug`, and look the online row up at
   `mtg-test-morning-serenity`.
2. Any test asserting a literal `online-test-...` slug for a **newly created**
   row — repoint to `mtg-test-...`. Tests that pre-create a row with an
   `online-` slug and assert it is updated in place are correct as written and
   must keep passing.

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_sync.py apps/support_services/test_meeting_sync.py
git commit -m "feat(meetings): import in-person and hybrid meetings from feeds"
```

---

### Task 4: Show a "Last verified" date on in-person meetings

An out-of-date Zoom link wastes a click. An out-of-date address wastes a
journey, at the moment someone decided to go to a meeting. In-person meetings
must show when the listing was last confirmed by its source feed.

**Files:**
- Modify: `apps/support_services/templates/support_services/meeting_detail.html` (inside the first `.meeting-detail-card`, after the Contact section, before the bookmark block at ~line 179)
- Test: `apps/support_services/test_meeting_seo.py`

**Interfaces:**
- Consumes: `Meeting.updated_at` (existing `auto_now=True` field) and
  `Meeting.attendance_option`.
- Produces: no Python interface. Template-only.

- [ ] **Step 1: Write the failing test**

Add to `apps/support_services/test_meeting_seo.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MeetingFreshnessTests(TestCase):
    """In-person listings send people somewhere physical — say how fresh."""

    def test_in_person_meeting_shows_last_verified(self):
        m = _meeting(slug='houston', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX',
                     formatted_address='123 Main St, Houston, TX')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('Last verified', html)

    def test_hybrid_meeting_shows_last_verified(self):
        m = _meeting(slug='hybrid', attendance_option='hybrid',
                     city='Austin', state='TX',
                     formatted_address='9 Oak Ave, Austin, TX')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('Last verified', html)

    def test_online_meeting_does_not_show_last_verified(self):
        """No journey to waste; the join link either works or it doesn't."""
        m = _meeting()
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertNotIn('Last verified', html)

    def test_source_website_is_credited_when_present(self):
        m = _meeting(slug='credited', attendance_option='in_person',
                     conference_url='', city='Houston', state='TX',
                     website='https://aahouston.org/')
        html = self.client.get(m.get_absolute_url()).content.decode()
        self.assertIn('https://aahouston.org/', html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.support_services.test_meeting_seo.MeetingFreshnessTests -v 2`
Expected: FAIL — `AssertionError: 'Last verified' not found in ...` on the
first two tests.

- [ ] **Step 3: Write minimal implementation**

In `apps/support_services/templates/support_services/meeting_detail.html`,
insert immediately before the `{% if user.is_authenticated %}` bookmark block:

```html
                {% if meeting.attendance_option != 'online' %}
                <div class="meeting-detail-section">
                    <p class="text-muted mb-0" style="font-size: 0.85rem;">
                        <i class="fas fa-clock" aria-hidden="true"></i>
                        Last verified {{ meeting.updated_at|date:"F j, Y" }} from
                        {% if meeting.website %}
                            <a href="{{ meeting.website }}" target="_blank" rel="noopener">the group's listing</a>.
                        {% else %}
                            the group's published schedule.
                        {% endif %}
                        Meeting times and locations change — call ahead if you can.
                    </p>
                </div>
                {% endif %}
```

Note: the existing Contact section already renders `meeting.website` when
present, so `test_source_website_is_credited_when_present` may pass on that
alone. That is acceptable — the assertion is that the source is credited
somewhere on the page, not that this block is the only place.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.support_services.test_meeting_seo -v 2`
Expected: PASS (whole module — 23 existing tests plus 4 new)

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/templates/support_services/meeting_detail.html apps/support_services/test_meeting_seo.py
git commit -m "feat(meetings): show last-verified date on in-person listings"
```

---

### Task 5: Measure the real volume before Phase 3

The design doc gates "add more feeds" on knowing what three metros actually
produce. This task runs the sync against production data and records the
number, because Phase 4 (sitemap index, query rewrite) is only needed above
roughly 40,000 URLs.

**Files:**
- Modify: `docs/plans/2026-09-07-meeting-directory-expansion-design.md` (Risks section)
- No code changes.

**Interfaces:**
- Consumes: the completed Tasks 1-4.
- Produces: a recorded meeting count that Phases 3 and 4 are gated on.

- [ ] **Step 1: Run the full test suite before touching production**

Run: `python3 manage.py test apps.support_services`
Expected: PASS, all modules.

- [ ] **Step 2: Dry-run one feed locally against the real endpoint**

```bash
python3 manage.py shell -c "
from apps.support_services.meeting_sync import sync_source, FEED_SOURCES
src = [s for s in FEED_SOURCES if s['key'] == 'houston'][0]
print(sync_source('houston', src['url'], limit=50, default_tz=src['timezone']))
"
```

Expected: a counts dict with a non-zero `created`, and no exception. `limit=50`
keeps the local database small; this is a shape check, not a full import.

- [ ] **Step 3: Inspect what came back**

```bash
python3 manage.py shell -c "
from apps.support_services.models import Meeting
from django.db.models import Count
print(Meeting.objects.values('attendance_option').annotate(n=Count('id')).order_by())
print('with city:', Meeting.objects.exclude(city='').count())
print('sample:', list(Meeting.objects.exclude(city='').values_list('name','city','state')[:5]))
"
```

Expected: a mix of `in_person` / `hybrid` / `online`, and non-empty
`city`/`state` on the physical ones. If every row still comes back `online`,
Task 3 did not take effect — stop and re-check `sync_source`.

- [ ] **Step 4: Run the real sync on Railway and record the total**

In a Railway shell against production:

```bash
python3 manage.py shell -c "
from apps.support_services.meeting_sync import sync_all
from apps.support_services.models import Meeting
from django.db.models import Count
print(sync_all())
print(Meeting.objects.filter(is_approved=True, is_active=True)
      .values('attendance_option').annotate(n=Count('id')).order_by())
print('total live:', Meeting.objects.filter(is_approved=True, is_active=True).count())
"
```

- [ ] **Step 5: Record the number and commit**

Replace the "Volume is unmeasured" paragraph in the design doc's Risks section
with the measured counts and the resulting go/no-go for Phases 3 and 4. Then:

```bash
git add docs/plans/2026-09-07-meeting-directory-expansion-design.md
git commit -m "docs(meetings): record measured meeting volume after in-person import"
```

- [ ] **Step 6: Verify the sitemap did not blow past its limit**

```bash
curl -s https://www.myrecoverypal.com/sitemap.xml | grep -c "<loc>"
```

Expected: under 40,000. A single flat sitemap is valid to 50,000 URLs; above
~40,000 open Phase 4 (sitemap index) before adding any feed in Phase 3.

---

## Self-Review

**Spec coverage:**

| Design decision | Task |
|---|---|
| Import in-person + hybrid from the three configured feeds | 3 |
| Never change existing slugs | 3 (`_resolve_slug`, tested) |
| `mtg-<key>-<slug>` for new rows, prefix ≠ attendance | 3 |
| Deactivation covers both prefixes, keeps `submitted_by` guard | 3 (tested) |
| Derive missing `attendance_option` | 1 |
| Carry address fields | 2 |
| "Last verified" on in-person | 4 |
| Credit the source intergroup | 4 |
| Measure volume before Phase 3 | 5 |
| No new feeds / no city pages / no sitemap index in Phase 1 | Enforced by task list — none present |

**Type consistency:** `_attendance_option` (Task 1) → consumed by `_map`
(Task 2) → consumed by `sync_source` (Task 3). `_slug` / `_resolve_slug` /
`IMPORT_SLUG_PREFIXES` are defined in Task 3 and used only there. `sync_source`'s
return dict keys are unchanged across the plan, so `tasks.py` and
`test_meeting_sync.py`'s existing `sync_all` assertions still hold.
