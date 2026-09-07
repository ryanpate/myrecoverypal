"""Sync recovery meetings from public TSML/Meeting Guide JSON feeds.

Every meeting a feed carries is imported — in-person, hybrid and online. The
importer was online-only until 2026-09, which discarded the entire in-person
schedule of three metro intergroups.

Each source owns a slug namespace so feeds never collide with each other or
with community-submitted meetings. New rows use "mtg-<key>-...";
"online-<key>-..." is the legacy namespace and those rows keep their slugs
permanently, because they are indexed URLs. The prefix encodes the import
source, never the attendance option — a meeting that changes from online to
hybrid must keep its URL. Rows that disappear from their source feed are
deactivated — but only when that feed fetched
successfully, so a down feed never wipes out its meetings. Community
submissions (submitted_by set) are never touched.
"""
import json
import logging
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.db.models import Q
from django.utils.text import slugify

from apps.support_services.models import Meeting

logger = logging.getLogger(__name__)

# Namespace for rows created by a feed import. "online" is the legacy prefix:
# ~1,565 rows were created under it when the importer was online-only, and
# they keep those slugs forever — they are indexed URLs. New rows use "mtg",
# which encodes the import source and NOT the attendance option, so a meeting
# that changes from online to hybrid keeps its URL.
SLUG_PREFIX = "mtg"
LEGACY_SLUG_PREFIX = "online"
IMPORT_SLUG_PREFIXES = (SLUG_PREFIX, LEGACY_SLUG_PREFIX)

# Every feed we use is a WordPress admin-ajax.php endpoint, and those
# intermittently answer 200 with an empty body, an HTML error page, or a
# bare "0" instead of the feed. Retry briefly rather than let one blip
# leave a source stale until next week's run.
FETCH_ATTEMPTS = 3


class FeedFetchError(Exception):
    """A feed could not be fetched or did not return a usable JSON body."""


# Verified TSML feeds. "timezone" is the fallback when a feed row omits its
# own — set it to the intergroup's home zone. Task 5 verifies and extends
# this list.
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
    {
        "key": "nyintergroup",
        "url": "https://meetings.nyintergroup.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
]


def load_feed(source):
    """Load a TSML feed from a URL or local file path."""
    if str(source).startswith("http"):
        return _fetch_json(source)
    with open(source) as f:
        return json.load(f)


def _fetch_json(url):
    """GET a feed, retrying transient failures.

    Raises FeedFetchError naming the status, content type and body prefix.
    A bare JSONDecodeError from resp.json() reports only "Expecting value:
    line 1 column 1", which says nothing about what the server actually
    sent — and that is the one thing worth knowing when a feed misbehaves.
    """
    detail = None
    for attempt in range(FETCH_ATTEMPTS):
        resp = None
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "MyRecoveryPal/1.0"},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, (list, dict)):
                # admin-ajax.php answers an unroutable request with "0":
                # valid JSON, useless feed.
                raise ValueError(f"expected a list or object, got {data!r}")
            return data
        except (requests.RequestException, ValueError) as exc:
            detail = _describe(resp, exc)
            logger.warning(
                "Feed fetch attempt %d/%d failed for %s: %s",
                attempt + 1, FETCH_ATTEMPTS, url, detail)
            if attempt < FETCH_ATTEMPTS - 1:
                time.sleep(2 * (attempt + 1))  # Exponential backoff

    raise FeedFetchError(
        f"{url} did not return a usable JSON feed after "
        f"{FETCH_ATTEMPTS} attempts: {detail}")


def _describe(resp, exc):
    """Describe a failed fetch: what the server sent, or why it never got sent."""
    if resp is None:
        return repr(exc)
    return (
        f"HTTP {resp.status_code}, "
        f"Content-Type {resp.headers.get('Content-Type', 'unknown')!r}, "
        f"body starts {resp.text[:200]!r}"
    )


def sync_source(key, source, approve=True, limit=None,
                default_tz="America/Chicago"):
    """Sync one feed: upsert its online meetings, deactivate vanished ones.

    Returns {"created", "updated", "skipped", "deactivated"} counts.
    Raises on fetch/parse failure — callers decide how to isolate that.
    """
    data = load_feed(source)
    meetings = data if isinstance(data, list) else data.get("meetings", [])
    # Import every meeting the feed carries — in-person, hybrid and online.
    # The importer used to keep online meetings only, discarding the whole
    # in-person schedule of three metro intergroups.
    incoming = list(meetings)
    if limit:
        incoming = incoming[:limit]

    if not incoming:
        logger.warning(
            "Feed %r returned no meetings; skipping deactivation "
            "to avoid wiping the source", key)
        return {"created": 0, "updated": 0, "skipped": 0, "deactivated": 0}

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

    # Deactivate imported rows that vanished from this source's feed.
    # submitted_by guard: community submissions always have a submitter,
    # imported rows never do — so a community meeting whose name slugifies
    # into this namespace can never be deactivated here.
    if not seen:
        logger.warning(
            "Feed %r returned %d meetings but none were usable; skipping "
            "deactivation to avoid wiping the source", key, len(incoming))
        return {"created": created, "updated": updated,
                "skipped": skipped, "deactivated": 0}

    prefix_match = Q()
    for prefix in IMPORT_SLUG_PREFIXES:
        prefix_match |= Q(slug__startswith=f"{prefix}-{key}-")
    deactivated = (
        Meeting.objects
        .filter(prefix_match, submitted_by__isnull=True, is_active=True)
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
    if not sources:
        return {}
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
        slug__startswith=f"{LEGACY_SLUG_PREFIX}-",
        submitted_by__isnull=True,
        is_active=True,
    )
    for key in keys:
        for prefix in IMPORT_SLUG_PREFIXES:
            qs = qs.exclude(slug__startswith=f"{prefix}-{key}-")
    return qs.update(is_active=False)


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


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        return None
