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
