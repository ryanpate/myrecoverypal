# Online AA Meeting Directory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate the existing meeting finder with self-maintaining online AA meeting data from multiple TSML feeds, and add a public `/online-aa-meetings/` SEO landing page that renders the live directory.

**Architecture:** Extract the import logic from the `seed_online_meetings` management command into a shared service (`apps/support_services/meeting_sync.py`) with multi-source support, per-source slug namespacing (`online-<key>-`), and stale-row deactivation with failure isolation. The existing Celery task `refresh_online_meetings_task` calls the service directly and moves from monthly to weekly. A new `TemplateView` in `apps.core` renders the landing page from live `Meeting` data, following the existing SEO landing-page pattern.

**Tech Stack:** Django 5.0.10, Celery 5.3.4, requests, Django sitemaps. No new dependencies, no model migrations.

**Spec:** `docs/superpowers/specs/2026-07-10-online-meeting-directory-design.md`

## Global Constraints

- No changes to the `Meeting` model schema (no migrations). The one model change is a read-only `@property`.
- Imported rows are identified by slug prefix `online-<sourcekey>-` **and** `submitted_by IS NULL`. Sync must never modify a row with `submitted_by` set (community-submitted).
- A failed feed fetch must never deactivate that source's meetings.
- Tests run with `python manage.py test <module> -v 2` from the repo root.
- Match existing code style (this codebase uses plain functions + module docstrings in services, `TemplateView` subclasses for landing pages).
- Commit after each task with a `feat:`/`refactor:`/`test:` prefix and the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` trailer.

---

### Task 1: Meeting sync service

**Files:**
- Create: `apps/support_services/meeting_sync.py`
- Create: `apps/support_services/test_meeting_sync.py`

**Interfaces:**
- Consumes: `apps.support_services.models.Meeting` (existing model, fields used: `slug`, `name`, `day`, `time`, `end_time`, `timezone`, `attendance_option`, `conference_url`, `conference_phone`, `types`, `location`, `group`, `notes`, `is_approved`, `is_active`, `submitted_by`).
- Produces (used by Tasks 2 and 5):
  - `FEED_SOURCES: list[dict]` — each `{"key": str, "url": str, "timezone": str}`
  - `sync_source(key: str, source: str, approve: bool = True, limit: int | None = None, default_tz: str = "America/Chicago") -> dict` — returns `{"created": int, "updated": int, "skipped": int, "deactivated": int}`. `source` is a URL or a local file path.
  - `sync_all(sources: list[dict] | None = None) -> dict` — keyed by source key, value is the `sync_source` result dict or `None` on failure; extra key `"legacy_deactivated": int` present only when every source succeeded. Raises `RuntimeError` if **all** sources fail.

- [ ] **Step 1: Write the failing tests**

Create `apps/support_services/test_meeting_sync.py`:

```python
"""Tests for the online-meeting sync service.

Feeds are exercised through local JSON files (sync_source accepts a file
path), so no HTTP mocking is needed except for the all-sources-failed case.
"""
import json
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.support_services.meeting_sync import sync_all, sync_source
from apps.support_services.models import Meeting

User = get_user_model()


def feed_file(meetings):
    """Write a TSML-shaped feed to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False)
    json.dump(meetings, f)
    f.close()
    return f.name


ONLINE_MEETING = {
    "name": "Morning Serenity",
    "slug": "morning-serenity",
    "day": 1,
    "time": "07:00",
    "end_time": "08:00",
    "attendance_option": "online",
    "conference_url": "https://zoom.us/j/123",
    "types": ["O", "D"],
    "group": "Serenity Group",
    "notes": "Passcode 1234",
}

IN_PERSON_MEETING = {
    "name": "Downtown Noon",
    "slug": "downtown-noon",
    "day": 2,
    "time": "12:00",
    "attendance_option": "in_person",
}


class SyncSourceTests(TestCase):
    def test_creates_online_meetings_with_namespaced_slug(self):
        path = feed_file([ONLINE_MEETING, IN_PERSON_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.attendance_option, "online")
        self.assertEqual(m.conference_url, "https://zoom.us/j/123")
        self.assertTrue(m.is_approved)
        self.assertTrue(m.is_active)
        # In-person meetings from the feed are never imported.
        self.assertEqual(Meeting.objects.count(), 1)

    def test_updates_existing_meeting_by_slug(self):
        path = feed_file([ONLINE_MEETING])
        sync_source("test", path)

        changed = dict(ONLINE_MEETING, name="Morning Serenity (Renamed)")
        result = sync_source("test", feed_file([changed]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.name, "Morning Serenity (Renamed)")

    def test_deactivates_meetings_missing_from_feed(self):
        other = dict(ONLINE_MEETING, name="Evening Hope",
                     slug="evening-hope")
        sync_source("test", feed_file([ONLINE_MEETING, other]))

        result = sync_source("test", feed_file([ONLINE_MEETING]))

        self.assertEqual(result["deactivated"], 1)
        self.assertFalse(
            Meeting.objects.get(slug="online-test-evening-hope").is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

    def test_reactivates_meeting_that_returns_to_feed(self):
        sync_source("test", feed_file([ONLINE_MEETING]))
        sync_source("test", feed_file([]))
        self.assertFalse(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

        sync_source("test", feed_file([ONLINE_MEETING]))
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

    def test_never_touches_community_submitted_meetings(self):
        user = User.objects.create_user(
            username="member", password="x")
        # A community meeting whose slug happens to match the namespace.
        community = Meeting.objects.create(
            name="Online Test Serenity",
            slug="online-test-serenity",
            submitted_by=user,
            is_approved=True,
            is_active=True,
        )
        sync_source("test", feed_file([ONLINE_MEETING]))

        community.refresh_from_db()
        self.assertTrue(community.is_active)

    def test_default_timezone_applied_when_feed_omits_it(self):
        path = feed_file([ONLINE_MEETING])  # no "timezone" key
        sync_source("test", path, default_tz="America/Los_Angeles")
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.timezone, "America/Los_Angeles")

    def test_skips_meetings_without_a_name(self):
        nameless = dict(ONLINE_MEETING, name="  ")
        result = sync_source("test", feed_file([nameless]))
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(Meeting.objects.count(), 0)


class SyncAllTests(TestCase):
    def test_failed_source_is_isolated_and_skips_deactivation(self):
        good = {"key": "good",
                "url": feed_file([ONLINE_MEETING]),
                "timezone": "America/Chicago"}
        # First run seeds a meeting under the "bad" namespace.
        sync_source("bad", feed_file(
            [dict(ONLINE_MEETING, slug="bad-meeting")]))
        bad = {"key": "bad", "url": "/nonexistent/feed.json",
               "timezone": "America/Chicago"}

        results = sync_all([good, bad])

        self.assertIsNone(results["bad"])
        self.assertEqual(results["good"]["created"], 1)
        # The bad source's existing meeting survives its feed being down.
        self.assertTrue(
            Meeting.objects.get(
                slug="online-bad-bad-meeting").is_active)
        # Legacy cleanup is skipped on partial failure.
        self.assertNotIn("legacy_deactivated", results)

    def test_all_sources_failed_raises(self):
        bad = {"key": "bad", "url": "/nonexistent/feed.json",
               "timezone": "America/Chicago"}
        with self.assertRaises(RuntimeError):
            sync_all([bad])

    def test_legacy_bare_prefix_rows_deactivated_when_all_succeed(self):
        # Row from the old single-source seed: bare "online-" prefix,
        # no source key, no submitter.
        legacy = Meeting.objects.create(
            name="Old Seattle Import",
            slug="online-old-seattle-import",
            is_approved=True,
            is_active=True,
        )
        good = {"key": "test",
                "url": feed_file([ONLINE_MEETING]),
                "timezone": "America/Chicago"}

        results = sync_all([good])

        # "online-old-..." does not match "online-test-", so it is legacy.
        self.assertEqual(results["legacy_deactivated"], 1)
        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: FAIL/ERROR on every test with `ModuleNotFoundError: No module named 'apps.support_services.meeting_sync'`

- [ ] **Step 3: Write the service**

Create `apps/support_services/meeting_sync.py`:

```python
"""Sync online meetings from public TSML/Meeting Guide JSON feeds.

Online meetings are location-independent: the conference URL works for anyone,
anywhere, and the source intergroup keeps those links current. We import only
the *online* subset of each feed so the meeting search returns accurate,
joinable results instead of an empty list.

Each source owns a slug namespace ("online-<key>-...") so feeds never collide
with each other or with community-submitted meetings. Rows that disappear from
their source feed are deactivated — but only when that feed fetched
successfully, so a down feed never wipes out its meetings. Community
submissions (submitted_by set) are never touched.
"""
import json
import logging
from datetime import datetime

import requests
from django.utils.text import slugify

from apps.support_services.models import Meeting

logger = logging.getLogger(__name__)

SLUG_PREFIX = "online"

# Verified TSML feeds. "timezone" is the fallback when a feed row omits its
# own — set it to the intergroup's home zone. Task 5 verifies and extends
# this list.
FEED_SOURCES = [
    {
        "key": "seattle",
        "url": "https://www.seattleaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
]


def load_feed(source):
    """Load a TSML feed from a URL or local file path."""
    if str(source).startswith("http"):
        resp = requests.get(
            source,
            headers={"User-Agent": "MyRecoveryPal/1.0"},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    with open(source) as f:
        return json.load(f)


def sync_source(key, source, approve=True, limit=None,
                default_tz="America/Chicago"):
    """Sync one feed: upsert its online meetings, deactivate vanished ones.

    Returns {"created", "updated", "skipped", "deactivated"} counts.
    Raises on fetch/parse failure — callers decide how to isolate that.
    """
    data = load_feed(source)
    meetings = data if isinstance(data, list) else data.get("meetings", [])
    online = [
        m for m in meetings
        if m.get("attendance_option") == "online" and m.get("conference_url")
    ]
    if limit:
        online = online[:limit]

    created = updated = skipped = 0
    seen = []
    for m in online:
        slug = _slug(key, m)
        defaults = _map(m, approve, default_tz)
        if defaults is None:
            skipped += 1
            continue
        _, was_created = Meeting.objects.update_or_create(
            slug=slug, defaults=defaults
        )
        seen.append(slug)
        created += was_created
        updated += not was_created

    # Deactivate imported rows that vanished from this source's feed.
    # submitted_by guard: community submissions always have a submitter,
    # imported rows never do — so a community meeting whose name slugifies
    # into this namespace can never be deactivated here.
    deactivated = (
        Meeting.objects
        .filter(
            slug__startswith=f"{SLUG_PREFIX}-{key}-",
            submitted_by__isnull=True,
        )
        .exclude(slug__in=seen)
        .update(is_active=False)
    )
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "deactivated": deactivated,
    }


def sync_all(sources=None):
    """Sync every configured feed, isolating per-source failures.

    Returns a dict keyed by source key (value: counts dict, or None if that
    source failed). Legacy bare-prefix cleanup runs only when every source
    succeeded. Raises RuntimeError only if ALL sources failed, so the Celery
    task's autoretry kicks in for total outages but not partial ones.
    """
    sources = sources if sources is not None else FEED_SOURCES
    results = {}
    failures = 0
    for src in sources:
        try:
            results[src["key"]] = sync_source(
                src["key"], src["url"],
                default_tz=src.get("timezone", "America/Chicago"),
            )
        except Exception:
            logger.exception(
                "Meeting feed sync failed for source %r", src["key"])
            results[src["key"]] = None
            failures += 1

    if sources and failures == len(sources):
        raise RuntimeError("All meeting feed sources failed to sync")
    if failures == 0:
        results["legacy_deactivated"] = _deactivate_legacy_rows(
            [s["key"] for s in sources])
    return results


def _deactivate_legacy_rows(keys):
    """One-time cleanup: the old seed used bare 'online-<slug>' rows with no
    source key. Once the namespaced re-import succeeds they are duplicates."""
    qs = Meeting.objects.filter(
        slug__startswith=f"{SLUG_PREFIX}-",
        submitted_by__isnull=True,
        is_active=True,
    )
    for key in keys:
        qs = qs.exclude(slug__startswith=f"{SLUG_PREFIX}-{key}-")
    return qs.update(is_active=False)


def _slug(key, m):
    base = m.get("slug") or slugify(m.get("name", "meeting"))
    return f"{SLUG_PREFIX}-{key}-{base}"[:255]


def _map(m, approve, default_tz):
    name = (m.get("name") or "").strip()
    if not name:
        return None
    return {
        "name": name,
        "day": m.get("day"),
        "time": _parse_time(m.get("time")),
        "end_time": _parse_time(m.get("end_time")),
        "timezone": m.get("timezone") or default_tz,
        "attendance_option": "online",
        "conference_url": m.get("conference_url") or "",
        "conference_phone": (m.get("conference_phone") or "")[:30],
        "types": m.get("types") or [],
        # Online meetings have no physical location; keep address fields
        # blank so users don't think they need to travel.
        "location": "Online Meeting",
        "group": (m.get("group") or "")[:255],
        "notes": m.get("notes") or "",  # join instructions / passwords
        "is_approved": approve,
        "is_active": True,
    }


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: OK, 10 tests passing

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_sync.py apps/support_services/test_meeting_sync.py
git commit -m "feat(meetings): multi-source online meeting sync with stale-row cleanup

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Rewire command, Celery task, and beat schedule

**Files:**
- Modify: `apps/support_services/management/commands/seed_online_meetings.py` (full rewrite as thin wrapper)
- Modify: `apps/support_services/tasks.py`
- Modify: `recovery_hub/settings.py` (the beat entry for `refresh_online_meetings_task`, around line 848–850)
- Test: `apps/support_services/test_meeting_sync.py` (append)

**Interfaces:**
- Consumes: `sync_all()`, `sync_source(key, source, approve, limit)` from Task 1.
- Produces: `seed_online_meetings` management command (no args → sync all configured sources; `--source URL --key KEY` → sync one); `refresh_online_meetings_task` Celery task unchanged in name (beat schedule keeps working).

- [ ] **Step 1: Write the failing tests**

Append to `apps/support_services/test_meeting_sync.py`:

```python
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command


class SeedCommandTests(TestCase):
    def test_single_source_mode_with_key(self):
        out = StringIO()
        call_command(
            "seed_online_meetings",
            source=feed_file([ONLINE_MEETING]),
            key="cli",
            stdout=out,
        )
        self.assertTrue(
            Meeting.objects.filter(
                slug="online-cli-morning-serenity").exists())
        self.assertIn("Done.", out.getvalue())

    def test_no_args_syncs_all_configured_sources(self):
        with patch(
            "apps.support_services.management.commands."
            "seed_online_meetings.sync_all",
            return_value={"seattle": {"created": 5, "updated": 0,
                                      "skipped": 0, "deactivated": 0},
                          "legacy_deactivated": 0},
        ) as mock_sync:
            out = StringIO()
            call_command("seed_online_meetings", stdout=out)
        mock_sync.assert_called_once_with()
        self.assertIn("seattle", out.getvalue())


class RefreshTaskTests(TestCase):
    def test_task_calls_sync_all(self):
        with patch(
            "apps.support_services.tasks.sync_all",
            return_value={"seattle": {"created": 1, "updated": 0,
                                      "skipped": 0, "deactivated": 0}},
        ) as mock_sync:
            from apps.support_services.tasks import (
                refresh_online_meetings_task,
            )
            refresh_online_meetings_task.apply()
        mock_sync.assert_called_once_with()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: the three new tests FAIL (`sync_all` not importable from the command/tasks modules, `--key` unknown argument); the 10 Task 1 tests still pass.

- [ ] **Step 3: Rewrite the command as a thin wrapper**

Replace the entire contents of `apps/support_services/management/commands/seed_online_meetings.py`:

```python
"""Sync online recovery meetings from configured TSML feeds.

The heavy lifting lives in apps.support_services.meeting_sync (shared with
the weekly Celery task). This command is the manual entry point.

Usage:
    python manage.py seed_online_meetings                     # all configured sources
    python manage.py seed_online_meetings --source <url> --key <key>   # one feed
    python manage.py seed_online_meetings --limit 100 --source <url> --key t  # testing
"""

from django.core.management.base import BaseCommand, CommandError

from apps.support_services.meeting_sync import sync_all, sync_source


class Command(BaseCommand):
    help = "Sync online meetings from TSML/Meeting Guide JSON feeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=str, default=None,
            help="URL or file path to a single feed (requires --key)",
        )
        parser.add_argument(
            "--key", type=str, default=None,
            help="Slug-namespace key for the single feed (with --source)",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Maximum meetings to import (single-source mode only)",
        )
        parser.add_argument(
            "--no-approve", action="store_true",
            help="Import as unapproved (default auto-approves)",
        )

    def handle(self, *args, **options):
        if options["source"]:
            if not options["key"]:
                raise CommandError("--source requires --key")
            results = {
                options["key"]: sync_source(
                    options["key"],
                    options["source"],
                    approve=not options["no_approve"],
                    limit=options["limit"],
                )
            }
        else:
            results = sync_all()

        for key, result in results.items():
            self.stdout.write(f"{key}: {result}")
        self.stdout.write(self.style.SUCCESS("Done."))
```

- [ ] **Step 4: Update the Celery task**

Replace the entire contents of `apps/support_services/tasks.py`:

```python
# apps/support_services/tasks.py
"""Celery tasks for support services.

Weekly online-meeting sync: refresh_online_meetings_task (Mondays, 4am UTC).
Re-imports every configured TSML feed so conference links stay current and
deactivates meetings that vanished from their source feed.
"""
import logging

from celery import shared_task

from apps.support_services.meeting_sync import sync_all

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # 60s, 120s, 240s
    retry_kwargs={'max_retries': 3},
)
def refresh_online_meetings_task(self):
    """Weekly re-sync of online meetings from all configured feeds.

    Per-source failures are isolated inside sync_all (a down feed never
    deactivates its own meetings); sync_all only raises — triggering
    autoretry — when every source fails.
    """
    results = sync_all()
    logger.info('Online meetings sync complete: %s', results)
```

- [ ] **Step 5: Move the beat schedule from monthly to weekly**

In `recovery_hub/settings.py`, find the beat entry whose `task` is `'apps.support_services.tasks.refresh_online_meetings_task'` (around line 849) and change its schedule line:

```python
        'schedule': crontab(hour=4, minute=0, day_of_week=1),  # Weekly, Mondays 4 AM UTC
```

(It currently reads `crontab(hour=4, minute=0, day_of_month=1),  # Monthly, 1st at 4 AM UTC`.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: OK, 13 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/support_services/management/commands/seed_online_meetings.py apps/support_services/tasks.py recovery_hub/settings.py apps/support_services/test_meeting_sync.py
git commit -m "refactor(meetings): command + weekly task delegate to meeting_sync service

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Timezone label on meeting times

**Files:**
- Modify: `apps/support_services/models.py` (add property to `Meeting`, after `to_meeting_guide_format`, ~line 206)
- Modify: `apps/support_services/templates/support_services/meeting_list.html` (~line 375)
- Modify: `apps/support_services/templates/support_services/meeting_detail.html` (~line 104)
- Test: `apps/support_services/test_meeting_sync.py` (append)

**Interfaces:**
- Produces: `Meeting.timezone_display` property (str) — short zone label like `"PDT"`, falling back to the raw stored string for unknown zones. Used by templates in this task and by the landing page template in Task 4.

- [ ] **Step 1: Write the failing test**

Append to `apps/support_services/test_meeting_sync.py`:

```python
class TimezoneDisplayTests(TestCase):
    def test_known_zone_returns_abbreviation(self):
        m = Meeting.objects.create(
            name="TZ Test", slug="tz-test",
            timezone="America/Los_Angeles",
        )
        # PST or PDT depending on date — both are acceptable.
        self.assertIn(m.timezone_display, ("PST", "PDT"))

    def test_unknown_zone_falls_back_to_raw_value(self):
        m = Meeting.objects.create(
            name="TZ Bad", slug="tz-bad", timezone="Not/AZone",
        )
        self.assertEqual(m.timezone_display, "Not/AZone")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.support_services.test_meeting_sync.TimezoneDisplayTests -v 2`
Expected: FAIL with `AttributeError: 'Meeting' object has no attribute 'timezone_display'`

- [ ] **Step 3: Add the property**

In `apps/support_services/models.py`, add inside the `Meeting` class, directly after the `to_meeting_guide_format` method (before the `SupportService` class):

```python
    @property
    def timezone_display(self):
        """Short label for the meeting's stored IANA zone (e.g. 'PDT').

        Online meeting times are meaningless without a zone; this gives
        templates a compact label. Falls back to the raw stored string if
        the zone name is invalid.
        """
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(self.timezone)).strftime("%Z")
        except Exception:
            return self.timezone
```

(Imports are local to the property to avoid touching the module's import block; `models.py` doesn't import `datetime` today.)

- [ ] **Step 4: Show the label in the list template**

In `apps/support_services/templates/support_services/meeting_list.html` (~line 375), change:

```django
                                            {% if meeting.time %}
                                                {{ meeting.time|time:"g:i A" }}
```

to:

```django
                                            {% if meeting.time %}
                                                {{ meeting.time|time:"g:i A" }} {{ meeting.timezone_display }}
```

- [ ] **Step 5: Show the label in the detail template**

In `apps/support_services/templates/support_services/meeting_detail.html` (~line 104), change:

```django
                    {% if meeting.time %}
                        {{ meeting.time|time:"g:i A" }}{% if meeting.end_time %} &ndash; {{ meeting.end_time|time:"g:i A" }}{% endif %}
```

to:

```django
                    {% if meeting.time %}
                        {{ meeting.time|time:"g:i A" }}{% if meeting.end_time %} &ndash; {{ meeting.end_time|time:"g:i A" }}{% endif %} {{ meeting.timezone_display }}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.support_services.test_meeting_sync -v 2`
Expected: OK, 15 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/support_services/models.py apps/support_services/templates/support_services/meeting_list.html apps/support_services/templates/support_services/meeting_detail.html apps/support_services/test_meeting_sync.py
git commit -m "feat(meetings): show timezone label next to meeting times

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: SEO landing page /online-aa-meetings/

**Files:**
- Modify: `apps/core/views.py` (add view; ensure `from datetime import datetime` is in the import block — add it if missing)
- Create: `apps/core/templates/core/online_aa_meetings.html`
- Modify: `apps/core/urls.py` (add path after `sobriety_calculator` entries, ~line 37)
- Modify: `recovery_hub/sitemaps.py` (add entry in the SEO landing pages block, ~line 49)
- Create: `apps/core/test_online_aa_meetings.py`

**Interfaces:**
- Consumes: `Meeting` model, `Meeting.DAY_CHOICES`, `Meeting.timezone_display` (Task 3).
- Produces: URL name `core:online_aa_meetings` at `/online-aa-meetings/`.

- [ ] **Step 1: Write the failing tests**

Create `apps/core/test_online_aa_meetings.py`:

```python
"""Tests for the /online-aa-meetings/ SEO landing page."""
from datetime import datetime, time

from django.test import TestCase
from django.urls import reverse

from apps.support_services.models import Meeting


def _today_meeting_day():
    # Python weekday: 0=Monday; Meeting model: 0=Sunday.
    return (datetime.now().weekday() + 1) % 7


class OnlineAAMeetingsPageTests(TestCase):
    def setUp(self):
        Meeting.objects.create(
            name="Today Online", slug="online-t-today",
            day=_today_meeting_day(), time=time(19, 0),
            attendance_option="online",
            conference_url="https://zoom.us/j/1",
            is_approved=True, is_active=True,
        )
        # Inactive and in-person meetings must not count.
        Meeting.objects.create(
            name="Dead Link", slug="online-t-dead",
            day=_today_meeting_day(), attendance_option="online",
            conference_url="https://zoom.us/j/2",
            is_approved=True, is_active=False,
        )
        Meeting.objects.create(
            name="In Person", slug="in-person-1",
            day=_today_meeting_day(), attendance_option="in_person",
            is_approved=True, is_active=True,
        )

    def test_page_renders_with_live_counts(self):
        resp = self.client.get(reverse("core:online_aa_meetings"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["online_count"], 1)
        self.assertContains(resp, "Today Online")
        self.assertNotContains(resp, "Dead Link")

    def test_page_contains_faq_schema(self):
        resp = self.client.get(reverse("core:online_aa_meetings"))
        self.assertContains(resp, '"@type": "FAQPage"')

    def test_page_is_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/online-aa-meetings/")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.core.test_online_aa_meetings -v 2`
Expected: FAIL with `NoReverseMatch: Reverse for 'online_aa_meetings' not found`

- [ ] **Step 3: Add the view**

In `apps/core/views.py`, first check the import block: if `from datetime import datetime` is not present, add it. Then add near the other SEO landing views (after `CleanTimeCalculatorView`):

```python
class OnlineAAMeetingsView(TemplateView):
    """SEO landing page targeting "online AA meetings" queries.

    Renders live directory data (counts + today's meetings) so the page
    stays fresh without manual maintenance; the weekly sync task keeps the
    underlying meetings current."""
    template_name = 'core/online_aa_meetings.html'

    def get_context_data(self, **kwargs):
        from apps.support_services.models import Meeting
        context = super().get_context_data(**kwargs)
        online = Meeting.objects.filter(
            is_active=True, is_approved=True, attendance_option='online',
        )
        # Python weekday: 0=Monday; Meeting model: 0=Sunday.
        today_meeting_day = (datetime.now().weekday() + 1) % 7
        context['online_count'] = online.count()
        context['todays_meetings'] = list(
            online.filter(day=today_meeting_day).order_by('time')[:12])
        context['today_name'] = dict(Meeting.DAY_CHOICES).get(
            today_meeting_day, '')
        return context
```

- [ ] **Step 4: Add the URL**

In `apps/core/urls.py`, after the `clean-time-calculator/` line (~line 36), add:

```python
    path('online-aa-meetings/', views.OnlineAAMeetingsView.as_view(), name='online_aa_meetings'),
```

- [ ] **Step 5: Create the template**

Create `apps/core/templates/core/online_aa_meetings.html`:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Online AA Meetings Today: Free Zoom AA Meetings, All Time Zones{% endblock %}
{% block meta_description %}Find free online AA meetings happening today. Searchable directory of Zoom AA meetings with join links, updated weekly — mornings, evenings & late night, every time zone.{% endblock %}
{% block meta_keywords %}online aa meetings, aa meetings online, zoom aa meetings, virtual aa meetings, online aa meetings today, aa zoom meetings near me, 24 hour aa meetings online{% endblock %}

{% block canonical_url %}https://www.myrecoverypal.com/online-aa-meetings/{% endblock %}

{% block structured_data %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Are online AA meetings free?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. AA meetings, including online meetings, are free to attend. There are no dues or fees — groups are self-supporting through voluntary contributions, and contributing is never required to attend."
      }
    },
    {
      "@type": "Question",
      "name": "How do I join an online AA meeting?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Pick a meeting from the directory and click its join link at the scheduled time. Most online AA meetings use Zoom. You can keep your camera off and just listen — many newcomers do exactly that for their first meetings."
      }
    },
    {
      "@type": "Question",
      "name": "Do online AA meetings count for court-ordered attendance?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Many courts and probation officers accept online meeting attendance, but requirements vary — always confirm with your PO or the court first. MyRecoveryPal's Court Compliance tools can log your attendance and generate verifiable PDF reports."
      }
    },
    {
      "@type": "Question",
      "name": "Can I attend an online AA meeting in another time zone?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Online meetings are open to anyone, anywhere. Because meetings run in every US time zone, you can almost always find one happening within the next few hours — including late at night."
      }
    },
    {
      "@type": "Question",
      "name": "Do I have to speak or turn my camera on?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. You can join with your camera off and simply listen. If a meeting does introductions, you can pass. Go at your own pace — showing up is what counts."
      }
    }
  ]
}
</script>
{% endblock %}

{% block extra_css %}
<style>
    .oam-hero {
        text-align: center;
        padding: 3rem 1rem 2rem;
        max-width: 800px;
        margin: 0 auto;
    }
    .oam-hero h1 { font-size: 2.2rem; margin-bottom: 1rem; }
    .oam-hero .oam-count {
        display: inline-block;
        background: var(--primary-color, #2c7a7b);
        color: #fff;
        border-radius: 999px;
        padding: 0.4rem 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .oam-section { max-width: 800px; margin: 0 auto; padding: 1.5rem 1rem; }
    .oam-meeting-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
    }
    .oam-meeting-card .oam-name { font-weight: 600; }
    .oam-meeting-card .oam-time { white-space: nowrap; opacity: 0.85; }
    .oam-cta {
        display: inline-block;
        background: var(--primary-color, #2c7a7b);
        color: #fff;
        padding: 0.8rem 1.8rem;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        margin-top: 1rem;
    }
    .oam-faq h3 { margin-top: 1.5rem; }
</style>
{% endblock %}

{% block content %}
<div class="oam-hero">
    <h1>Online AA Meetings — Join From Anywhere, Free</h1>
    {% if online_count %}
    <span class="oam-count">{{ online_count }} online meetings in the directory</span>
    {% endif %}
    <p>
        Every meeting below is a real AA meeting with a working join link,
        imported from intergroup schedules and re-verified weekly. No signup
        is needed to browse. Cameras optional — you can just listen.
    </p>
    <a class="oam-cta" href="{% url 'support_services:meeting_list' %}">Search All Meetings</a>
</div>

<div class="oam-section">
    <h2>Online AA Meetings Today{% if today_name %} ({{ today_name }}){% endif %}</h2>
    {% for meeting in todays_meetings %}
    <div class="oam-meeting-card">
        <div>
            <div class="oam-name">{{ meeting.name }}</div>
            {% if meeting.group %}<div>{{ meeting.group }}</div>{% endif %}
        </div>
        <div class="oam-time">
            {% if meeting.time %}{{ meeting.time|time:"g:i A" }} {{ meeting.timezone_display }}{% endif %}
        </div>
    </div>
    {% empty %}
    <p>
        The directory is being refreshed — use the full
        <a href="{% url 'support_services:meeting_list' %}">meeting search</a>
        to browse every day of the week.
    </p>
    {% endfor %}
    <a class="oam-cta" href="{% url 'support_services:meeting_list' %}?attendance=online">See every online meeting →</a>
</div>

<div class="oam-section">
    <h2>Why Online Meetings Work</h2>
    <p>
        Online AA meetings remove the two biggest barriers to getting
        support: distance and timing. Whether you're in a small town with
        one meeting a week, traveling, or it's 2 AM and a craving hit,
        there's a meeting you can join in the next few hours. They follow
        the same format as in-person AA — a reading, sharing, and fellowship
        — and the only requirement for membership is a desire to stop
        drinking.
    </p>
    <p>
        If you want more than meetings, MyRecoveryPal adds a daily
        sobriety pledge, a supportive community feed, an AI recovery coach
        for the moments between meetings, and tools to track your streak —
        <a href="{% url 'accounts:register' %}">free to join</a>.
    </p>
</div>

<div class="oam-section oam-faq">
    <h2>Frequently Asked Questions</h2>
    <h3>Are online AA meetings free?</h3>
    <p>Yes. AA meetings, including online meetings, are free to attend. There are no dues or fees — groups are self-supporting through voluntary contributions, and contributing is never required.</p>
    <h3>How do I join an online AA meeting?</h3>
    <p>Pick a meeting from the directory and click its join link at the scheduled time. Most use Zoom. You can keep your camera off and just listen — many newcomers do exactly that at first.</p>
    <h3>Do online AA meetings count for court-ordered attendance?</h3>
    <p>Many courts and probation officers accept online attendance, but requirements vary — confirm with your PO or the court first. Our <a href="{% url 'core:court_ordered_meeting_tracker' %}">Court Compliance tools</a> can log attendance and generate verifiable PDF reports.</p>
    <h3>Can I attend a meeting in another time zone?</h3>
    <p>Yes. Online meetings are open to anyone, anywhere. Meeting times above show their home time zone, and with meetings across every US time zone there's almost always one starting soon.</p>
    <h3>Do I have to speak or turn my camera on?</h3>
    <p>No. Join with your camera off and simply listen. If a meeting does introductions, you can pass. Showing up is what counts.</p>
</div>

{% include 'core/partials/_related_tools.html' with exclude='online_aa_meetings' %}
{% endblock %}
```

- [ ] **Step 6: Add to the sitemap**

In `recovery_hub/sitemaps.py`, in the SEO landing pages block after the `core:court_ordered_meeting_tracker` line (~line 48), add:

```python
            ('core:online_aa_meetings', 0.9),  # "online AA meetings" — live meeting directory
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test apps.core.test_online_aa_meetings -v 2`
Expected: OK, 3 tests passing

- [ ] **Step 8: Render check in the browser**

Run: `python manage.py runserver`, open `http://127.0.0.1:8000/online-aa-meetings/`.
Expected: page renders in both light and dark theme with hero, count badge (or hidden if 0), today's meetings (or the fallback line), FAQ, related-tools footer. Fix any layout glitches before committing.

- [ ] **Step 9: Commit**

```bash
git add apps/core/views.py apps/core/urls.py apps/core/templates/core/online_aa_meetings.html recovery_hub/sitemaps.py apps/core/test_online_aa_meetings.py
git commit -m "feat(seo): /online-aa-meetings/ landing page rendering the live directory

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Verify and expand feed sources

**Files:**
- Modify: `apps/support_services/meeting_sync.py` (the `FEED_SOURCES` list only)

**Interfaces:**
- Consumes: `FEED_SOURCES` shape from Task 1: `{"key", "url", "timezone"}`.
- Produces: a verified `FEED_SOURCES` list. Target: **150+ online meetings** total, covering all 7 days. Cap at ~4 sources to keep the weekly sync fast.

This task is verification-driven, not TDD: it edits a data list, and Task 1's tests already cover the machinery.

- [ ] **Step 1: Probe each candidate feed**

For each candidate, run this probe (swap the URL):

```bash
probe() {
  curl -s --max-time 60 -A "MyRecoveryPal/1.0" "$1" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception as e:
    print('UNPARSEABLE:', e); raise SystemExit
ms = d if isinstance(d, list) else d.get('meetings', [])
on = [m for m in ms if m.get('attendance_option') == 'online' and m.get('conference_url')]
days = sorted({m.get('day') for m in on})
tz = sorted({m.get('timezone') for m in on if m.get('timezone')})[:3]
print(f'{len(ms)} total | {len(on)} online | days={days} | tz sample={tz}')
"
}
probe 'https://www.seattleaa.org/wp-admin/admin-ajax.php?action=meetings'
probe 'https://aahouston.org/wp-admin/admin-ajax.php?action=meetings'
probe 'https://meetings.nyintergroup.org/wp-admin/admin-ajax.php?action=meetings'
probe 'https://aasfmarin.org/wp-admin/admin-ajax.php?action=meetings'
probe 'https://austinaa.org/wp-admin/admin-ajax.php?action=meetings'
```

Selection rules:
- Include a feed only if it returns ≥30 online meetings with join links.
- If `tz sample` is empty for a feed, its rows rely on the per-source `timezone` fallback — set it to the intergroup's home zone (Houston → `America/Chicago`, NYC → `America/New_York`, SF/Marin → `America/Los_Angeles`, Austin → `America/Chicago`).
- Stop at 4 sources or 150+ combined online meetings, whichever comes first.
- If a candidate URL 404s or is unparseable, drop it — do not hunt for alternates beyond this list. If the combined total falls short of 150, ship what works and note the shortfall in the commit message.

- [ ] **Step 2: Update FEED_SOURCES**

Edit the `FEED_SOURCES` list in `apps/support_services/meeting_sync.py` to include each verified source, e.g.:

```python
FEED_SOURCES = [
    {
        "key": "seattle",
        "url": "https://www.seattleaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "houston",
        "url": "https://aahouston.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    # ... only feeds that passed the probe
]
```

- [ ] **Step 3: Full local sync as verification**

```bash
python manage.py seed_online_meetings
```

Expected: per-source count lines, no tracebacks. Then confirm volume and coverage:

```bash
python manage.py shell -c "
from apps.support_services.models import Meeting
qs = Meeting.objects.filter(is_active=True, attendance_option='online')
print('active online:', qs.count())
print('days covered:', sorted(set(qs.values_list('day', flat=True))))
"
```

Expected: `active online:` ≥150 (or documented shortfall), `days covered:` includes all of 0–6.

- [ ] **Step 4: Run the full test suite for the touched apps**

Run: `python manage.py test apps.support_services.test_meeting_sync apps.core.test_online_aa_meetings -v 2`
Expected: OK, 18 tests passing

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_sync.py
git commit -m "feat(meetings): add verified online meeting feed sources

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Deploy and production verification

**Files:** none (runbook task)

- [ ] **Step 1: Push to deploy**

```bash
git push origin main
```

Railway auto-deploys `main` (web + celery-worker both pick up the new code; the beat schedule change takes effect when celery-worker restarts).

- [ ] **Step 2: Run the first sync in production**

In a Railway shell on the **web** service (Railway dashboard → web → shell, or `railway shell`):

```bash
python manage.py seed_online_meetings
```

Expected: per-source counts plus a `legacy_deactivated` line cleaning up the old bare-prefix Seattle rows.

- [ ] **Step 3: Verify the live pages**

- `https://www.myrecoverypal.com/support/meetings/` — populated list, search box works (try "serenity"), day/attendance filters work, times show timezone labels.
- `https://www.myrecoverypal.com/online-aa-meetings/` — count badge shows the real number, today's meetings render.
- `https://www.myrecoverypal.com/sitemap.xml` — contains `/online-aa-meetings/`.
- `https://www.myrecoverypal.com/robots.txt` — does NOT disallow `/online-aa-meetings/`.

- [ ] **Step 4: Search Console (manual, for Ryan)**

Submit `https://www.myrecoverypal.com/online-aa-meetings/` via the URL Inspection tool → Request Indexing.

---

## Self-Review Notes

- Spec coverage: import pipeline → Task 1; weekly sync + failure isolation + legacy cleanup + deactivation guard → Tasks 1–2; SEO landing page + sitemap → Task 4; timezone label → Task 3; source verification (150+ target) → Task 5; deploy verification + GSC → Task 6. Per-user timezone conversion and NA/SMART sources are explicit non-goals.
- Test count arithmetic: Task 1 = 10, Task 2 adds 3 (13), Task 3 adds 2 (15), Task 4 adds 3 in a separate module (18 across both).
- `refresh_online_meetings_task` keeps its name and dotted path, so the beat entry key in settings keeps working with only the schedule line changed.
