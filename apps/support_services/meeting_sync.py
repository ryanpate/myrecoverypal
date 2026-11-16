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
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.support_services.grouping import assign_primaries, group_key
from apps.support_services.hubs import US_STATES
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


class FeedBlockedError(FeedFetchError):
    """The feed's host answered with a bot challenge (captcha) instead of data.

    Expected and not ours to fix: we never try to get past a challenge. The
    source's existing meetings are kept; retrying would only hammer the host.
    """


# Markers of host-level bot challenges seen from Railway's IPs.
BOT_CHALLENGE_MARKERS = ("sgcaptcha", "cf-chl", "challenge-platform", "Just a moment...")


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
    {
        "key": "phoenix",
        "url": "https://www.aaphoenix.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Phoenix",
    },
    {
        "key": "atlanta",
        "url": "https://www.atlantaaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    # Added 2026-09-26 from a probe of 45 intergroups: metros with GA4 traffic
    # or coverage-gap searches and a public feed. Feeds answering 401 have
    # deliberately switched sharing off and are respected, not worked around.
    {
        "key": "denver",
        "url": "https://daccaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Denver",
    },
    {
        "key": "sandiego",
        "url": "https://aasandiego.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "orangecounty",
        "url": "https://oc-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "lasvegas",
        "url": "https://lvcentraloffice.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "dc",
        "url": "https://aa-dc.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "sanantonio",
        "url": "https://aasanantonio.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "nashville",
        "url": "https://aanashville.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "minneapolis",
        "url": "https://aaminneapolis.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "stlouis",
        "url": "https://aastl.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "cincinnati",
        "url": "https://aacincinnati.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "indianapolis",
        "url": "https://indyaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Indiana/Indianapolis",
    },
    {
        "key": "desmoines",
        "url": "https://aadesmoines.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "tucson",
        "url": "https://aatucson.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Phoenix",  # Arizona: no DST (the feed omits zones)
    },
    {
        "key": "richmond",
        "url": "https://aarichmond.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    # Added 2026-11-15 from a probe of 55 more intergroups (about 14,600
    # meetings). Left out because their feed answers 401 (sharing switched
    # off) or 403: Portland, Sacramento, Austin, Dallas, Fort Worth, Boston,
    # Philadelphia, Miami, Orlando, Charlotte, Detroit, Cleveland, Salt Lake,
    # Albuquerque, New Orleans, Buffalo, Rochester, Reno.
    {
        "key": "eastbay",
        "url": "https://eastbayaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "ventura",
        "url": "https://aaventuracounty.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "inlandempire",
        "url": "https://aainlandempire.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "fresno",
        "url": "https://fresnoaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "spokane",
        "url": "https://aaspokane.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Los_Angeles",
    },
    {
        "key": "honolulu",
        "url": "https://oahuaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "Pacific/Honolulu",
    },
    {
        "key": "kansascity",
        "url": "https://kc-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "oklahomacity",
        "url": "https://okcintergroup.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "tulsa",
        "url": "https://aaneok.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "memphis",
        "url": "https://memphis-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "omaha",
        "url": "https://omahaaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "madison",
        "url": "https://aamadisonwi.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/Chicago",
    },
    {
        "key": "columbus",
        "url": "https://aacentralohio.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "raleigh",
        "url": "https://raleighaa.com/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "jacksonville",
        "url": "https://neflaa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "palmbeach",
        "url": "https://aa-palmbeachcounty.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "nassau",
        "url": "https://nassauny-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "suffolk",
        "url": "https://suffolkny-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "connecticut",
        "url": "https://ct-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    {
        "key": "rhodeisland",
        "url": "https://rhodeisland-aa.org/wp-admin/admin-ajax.php?action=meetings",
        "timezone": "America/New_York",
    },
    # Chicago (chicagoaa.org) and Los Angeles (lacoaa.org) both sit behind a
    # Cloudflare bot challenge and cannot be fetched programmatically. Left
    # out deliberately rather than worked around.
]


# --- Narcotics Anonymous ----------------------------------------------------
# NA service bodies publish their lists through BMLT; the BMLT Aggregator
# (bmlt.app/aggregator) republishes them behind one public API. We ask it for
# the meetings around each metro below, in its native JSON, because that is
# the only format carrying the venue type and time zone.
BMLT_SEARCH_URL = (
    "https://aggregator.bmltenabled.org/main_server/client_interface/json/"
    "?switcher=GetSearchResults&lat_val={lat}&long_val={lng}&geo_width={miles}"
)
NA_AREA_RADIUS_MILES = 25
# (name, lat, lng, home time zone, state). `state` fills in rows that omit
# theirs; it is None where the radius crosses a state line, because guessing
# would put a meeting in the wrong state's directory.
NA_AREAS = [
    ("seattle", 47.6062, -122.3321, "America/Los_Angeles", "WA"),
    ("houston", 29.7604, -95.3698, "America/Chicago", "TX"),
    ("nyc", 40.7128, -74.0060, "America/New_York", None),
    ("phoenix", 33.4484, -112.0740, "America/Phoenix", "AZ"),
    ("atlanta", 33.7490, -84.3880, "America/New_York", "GA"),
    ("denver", 39.7392, -104.9903, "America/Denver", "CO"),
    ("sandiego", 32.7157, -117.1611, "America/Los_Angeles", "CA"),
    ("orangecounty", 33.7455, -117.8677, "America/Los_Angeles", "CA"),
    ("losangeles", 34.0522, -118.2437, "America/Los_Angeles", "CA"),
    ("lasvegas", 36.1699, -115.1398, "America/Los_Angeles", "NV"),
    ("dc", 38.9072, -77.0369, "America/New_York", None),
    ("sanantonio", 29.4241, -98.4936, "America/Chicago", "TX"),
    ("dallas", 32.7767, -96.7970, "America/Chicago", "TX"),
    ("nashville", 36.1627, -86.7816, "America/Chicago", "TN"),
    ("minneapolis", 44.9778, -93.2650, "America/Chicago", None),
    ("stlouis", 38.6270, -90.1994, "America/Chicago", None),
    ("chicago", 41.8781, -87.6298, "America/Chicago", None),
    ("cincinnati", 39.1031, -84.5120, "America/New_York", None),
    ("indianapolis", 39.7684, -86.1581, "America/Indiana/Indianapolis", "IN"),
    ("desmoines", 41.5868, -93.6250, "America/Chicago", "IA"),
    ("tucson", 32.2226, -110.9747, "America/Phoenix", "AZ"),
    ("richmond", 37.5407, -77.4360, "America/New_York", "VA"),
    ("philadelphia", 39.9526, -75.1652, "America/New_York", None),
    ("miami", 25.7617, -80.1918, "America/New_York", "FL"),
    ("boston", 42.3601, -71.0589, "America/New_York", "MA"),
]

# BMLT format keys we can state with confidence -> the codes the directory
# already displays. Keys differ between NA regions, so anything else is dropped.
BMLT_FORMATS = {
    "O": "O", "C": "C", "WC": "X", "W": "W", "M": "M", "D": "D",
    "ST": "ST", "ES": "S", "YP": "Y", "NS": "NS",
}

_STATE_BY_NAME = {name.upper(): code for code, name in US_STATES.items()}


def _state_code(value):
    """'Ohio', 'Il', 'CO,' -> 'OH', 'IL', 'CO'. Unknown values become ''."""
    value = re.sub(r"[^A-Za-z ]", "", value or "").strip().upper()
    if value in US_STATES:
        return value
    return _STATE_BY_NAME.get(value, "")


def _from_bmlt(row, default_tz, default_state):
    """One BMLT meeting as a Meeting Guide-shaped dict, or None to skip it.

    Skipped on purpose: an online meeting with no time zone (the aggregator
    returns worldwide virtual meetings, and a guessed zone would send someone
    at the wrong hour) or no way to join, and an in-person meeting with no
    street address.
    """
    name = (row.get("meeting_name") or "").strip()
    meeting_id = str(row.get("id_bigint") or "").strip()
    if not name or not meeting_id or str(row.get("published", "1")) != "1":
        return None

    street = (row.get("location_street") or "").strip()
    venue = str(row.get("venue_type") or "")
    tz = (row.get("time_zone") or "").strip()
    link = (row.get("virtual_meeting_link") or "").strip()
    phone = (row.get("phone_meeting_number") or "").strip()
    if venue == "2":
        if not tz or not (link or phone):
            return None
        attendance = "online"
    elif not street:
        return None
    else:
        attendance = "hybrid" if venue == "3" else "in_person"
        tz = tz or default_tz

    try:
        day = int(row.get("weekday_tinyint")) - 1  # BMLT: 1 = Sunday
    except (TypeError, ValueError):
        day = None
    if day not in range(7):
        day = None

    start = end = None
    try:
        begins = datetime.strptime(row.get("start_time") or "", "%H:%M:%S")
        start = begins.strftime("%H:%M")
        hours, minutes, _ = (row.get("duration_time") or "").split(":")
        end = (begins + timedelta(hours=int(hours), minutes=int(minutes))).strftime("%H:%M")
    except ValueError:
        pass

    city = (row.get("location_municipality") or "").strip()
    state = _state_code(row.get("location_province")) or default_state or ""
    postal = (row.get("location_postal_code_1") or "").strip()
    notes = [t.strip() for t in (row.get("comments"), row.get("location_info")) if t and t.strip()]
    join_info = (row.get("virtual_meeting_additional_info") or "").strip()

    codes = {c.strip().rstrip("*").upper() for c in (row.get("formats") or "").split(",")}
    return {
        "slug": f"{slugify(name)[:150] or 'meeting'}-{meeting_id}",
        "name": name,
        "day": day,
        "time": start,
        "end_time": end,
        "timezone": tz,
        "attendance_option": attendance,
        "conference_url": link,
        "conference_url_notes": join_info,
        "conference_phone": phone,
        "types": sorted({BMLT_FORMATS[c] for c in codes if c in BMLT_FORMATS}),
        "notes": " ".join(notes),
        "location": (row.get("location_text") or "").strip(),
        "formatted_address": ", ".join(filter(None, (street, city, f"{state} {postal}".strip()))),
        "address": street,
        "city": city,
        "state": state,
        "postal_code": postal,
        "region": (row.get("service_body_name") or "").strip(),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
    }


def load_na_meetings(areas=None):
    """Every NA meeting around the configured metros, deduplicated.

    Neighbouring radii overlap (Los Angeles / Orange County), so rows are
    merged on the aggregator's meeting id. Any area failing raises, which
    skips the whole NA sync for this run: a partial list would deactivate
    the missing metro's meetings as "vanished".
    """
    merged = {}
    for i, (_name, lat, lng, tz, state) in enumerate(areas or NA_AREAS):
        if i:
            time.sleep(1)  # one metro a second: a guest on a volunteer-run server
        rows = _fetch_json(BMLT_SEARCH_URL.format(lat=lat, lng=lng, miles=NA_AREA_RADIUS_MILES))
        for row in rows if isinstance(rows, list) else []:
            meeting = _from_bmlt(row, tz, state)
            if meeting:
                merged.setdefault(meeting["slug"], meeting)
    return list(merged.values())


NA_SOURCE = {"key": "na", "load": load_na_meetings, "program": "NA"}
ALL_SOURCES = FEED_SOURCES + [NA_SOURCE]


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
            if any(marker in resp.text[:2000] for marker in BOT_CHALLENGE_MARKERS):
                raise FeedBlockedError(
                    f"{url} served a bot challenge (HTTP {resp.status_code}); "
                    "the host is blocking automated requests from this server")
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
                default_tz="America/Chicago", program="AA"):
    """Sync one feed: upsert its online meetings, deactivate vanished ones.

    Returns {"created", "updated", "skipped", "deactivated"} counts.
    Raises on fetch/parse failure — callers decide how to isolate that.
    """
    data = source() if callable(source) else load_feed(source)
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
    touched_groups = set()
    known_slugs = _existing_import_slugs(key)
    for m in incoming:
        defaults = _map(m, approve, default_tz)
        if defaults is None:
            skipped += 1
            continue
        defaults["program"] = program
        slug = _resolve_slug(key, m, known_slugs)
        defaults["group_key"] = group_key(
            slug, defaults["name"], defaults["attendance_option"],
            defaults.get("formatted_address", ""), defaults.get("address", ""),
            defaults.get("location", ""), defaults.get("city", ""),
            defaults.get("state", ""), defaults.get("conference_url", ""), feed=key)
        touched_groups.add(defaults["group_key"])
        # known_slugs already tells us whether the row exists, so branch
        # instead of paying update_or_create's SELECT + savepoint round
        # trips on every meeting (~6 queries/row on 6,500 rows).
        if slug in known_slugs:
            _apply_update(slug, defaults)
            updated += 1
        else:
            try:
                Meeting.objects.create(slug=slug, **defaults)
                created += 1
            except IntegrityError:
                # The row appeared between the prefetch and now — another
                # sync running concurrently. Fall back to updating it.
                _apply_update(slug, defaults)
                updated += 1
        seen.append(slug)

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

    vanished = (
        Meeting.objects
        .filter(_import_slug_filter(key), submitted_by__isnull=True, is_active=True)
        .exclude(slug__in=seen)
    )
    touched_groups.update(vanished.values_list("group_key", flat=True))
    deactivated = vanished.update(is_active=False)
    # Re-pick each touched group's primary page (a group whose primary slot
    # vanished, or whose slots moved address, gets a new one).
    assign_primaries(Meeting, touched_groups)
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
    sources = sources if sources is not None else ALL_SOURCES
    if not sources:
        return {}
    results = {}
    failures = 0
    for src in sources:
        try:
            results[src["key"]] = sync_source(
                src["key"], src.get("load") or src["url"],
                default_tz=src.get("timezone", "America/Chicago"),
                program=src.get("program", "AA"),
            )
        except FeedBlockedError as exc:
            # A warning, not an error: expected, and not something a weekly
            # Sentry alert can fix. Its existing meetings are kept.
            logger.warning("Meeting feed %r skipped: %s", src["key"], exc)
            results[src["key"]] = None
            failures += 1
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
    # Full pass: catches a group left without a primary when its slot moved
    # address (and so changed group) or was deactivated as a legacy row.
    assign_primaries(Meeting)
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


def _apply_update(slug, defaults):
    """Update one imported row.

    QuerySet.update() bypasses save(), so `updated_at` (auto_now=True) would
    never advance — and that field is rendered as "Last verified" on every
    in-person meeting page. Set it explicitly.
    """
    Meeting.objects.filter(slug=slug).update(
        updated_at=timezone.now(), **defaults)


def _import_slug_filter(key):
    """Q matching every imported slug namespace for one source."""
    match = Q()
    for prefix in IMPORT_SLUG_PREFIXES:
        match |= Q(slug__startswith=f"{prefix}-{key}-")
    return match


def _existing_import_slugs(key):
    """Every imported slug already stored for this source, in ONE query.

    This used to be an .exists() per meeting per namespace — ~13,000 extra
    round trips on a 6,500-meeting sync, and the reason the first
    production run took 33 minutes.
    """
    return set(
        Meeting.objects
        .filter(_import_slug_filter(key), submitted_by__isnull=True)
        .values_list("slug", flat=True)
    )


def _resolve_slug(key, m, known_slugs):
    """Return the slug to upsert under.

    Prefers an existing imported row under any known prefix so legacy
    `online-` rows are updated in place rather than duplicated under `mtg-`.
    `known_slugs` comes from _existing_import_slugs() — resolution is a set
    membership test, not a query.
    """
    base = m.get("slug") or slugify(m.get("name", "meeting"))
    for prefix in IMPORT_SLUG_PREFIXES:
        candidate = f"{prefix}-{key}-{base}"[:255]
        if candidate in known_slugs:
            return candidate
    return _slug(key, m)


def _safe_url(value):
    """Keep only absolute http(s) URLs — these render as hrefs on our pages."""
    value = (value or "").strip()
    return value if re.match(r"https?://", value, re.IGNORECASE) else ""


def _map(m, approve, default_tz):
    name = (m.get("name") or "").strip()
    if not name:
        return None
    # Feeds mark retired meetings with attendance_option "inactive". That is
    # not one of our values, so _attendance_option would derive from the
    # payload and import a dead group as in-person — sending someone to a
    # meeting that no longer exists.
    if (m.get("attendance_option") or "").strip().lower() == "inactive":
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
        "conference_url": "" if attendance == "in_person" else _safe_url(m.get("conference_url")),
        "conference_url_notes": "" if attendance == "in_person" else (m.get("conference_url_notes") or ""),
        "conference_phone": (m.get("conference_phone") or "")[:30],
        "types": m.get("types") or [],
        "group": (m.get("group") or "")[:255],
        "notes": m.get("notes") or "",  # join instructions / passwords
        "website": _safe_url(m.get("website"))[:200],
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
        formatted = (m.get("formatted_address") or "")
        # Feeds send either discrete fields or a single formatted string.
        # Prefer whatever the feed states explicitly; fall back to parsing.
        parsed = _split_address(formatted)
        mapped.update({
            "location": (m.get("location") or "")[:255],
            "formatted_address": formatted[:500],
            "address": (m.get("address") or parsed["address"])[:255],
            "city": (m.get("city") or parsed["city"])[:100],
            "state": (m.get("state") or parsed["state"])[:2],
            "postal_code": (m.get("postal_code") or parsed["postal_code"])[:10],
            "region": (m.get("region") or "")[:100],
            "latitude": _decimal(m.get("latitude")),
            "longitude": _decimal(m.get("longitude")),
        })
    return mapped


US_STATE_RE = re.compile(r"^([A-Za-z]{2})(?:\s+(\d{5}(?:-\d{4})?))?$")


def _split_address(formatted):
    """Pull street / city / state / ZIP out of a formatted address.

    Real TSML feeds (aahouston.org, seattleaa.org, nyintergroup.org) send a
    single Google-geocoder string — "2111 Webster St, League City, TX 77573,
    USA" — and no discrete city or state fields. Without this, every
    in-person meeting lands with an empty city, which empties the SEO title
    and leaves nothing to build city pages on.

    Returns empty strings rather than guessing when the shape doesn't match;
    a non-US address must not have its last token forced into `state`.
    """
    blank = {"address": "", "city": "", "state": "", "postal_code": ""}
    parts = [p.strip() for p in (formatted or "").split(",") if p.strip()]
    if len(parts) < 3:
        return blank

    # Drop a trailing country token so "..., TX 77573, USA" and
    # "..., TX 77573" parse identically.
    if parts[-1].upper() in ("USA", "US", "UNITED STATES"):
        parts = parts[:-1]
    if len(parts) < 3:
        return blank

    m = US_STATE_RE.match(parts[-1])
    if not m:
        return blank

    return {
        "address": ", ".join(parts[:-2]),
        "city": parts[-2],
        "state": m.group(1).upper(),
        "postal_code": m.group(2) or "",
    }


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
