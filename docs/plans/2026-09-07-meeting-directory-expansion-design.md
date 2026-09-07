# Meeting Directory Expansion — Design

**Date:** 2026-09-07
**Status:** Approved direction; implementation plan in `2026-09-07-meeting-directory-expansion-plan.md`
**Analytics reference:** GSC (3mo to 2026-09-05) + GA4 (2026-08-10 → 2026-09-06)

---

## Goal

Turn the meeting directory from an online-AA-only list into the site's primary
organic acquisition surface, and connect it to the one thing on the site
anyone has ever paid for.

## Why this change

### The directory is the most-used thing on the site and the least optimised

GA4, 28 days:

| Page | Views | Users | Avg engagement |
|---|---|---|---|
| Find Recovery Meetings | 451 | 82 | **108 s** |
| My Progress | 270 | 53 | 65 s |
| Online AA Meetings (landing) | 142 | 107 | 28 s |
| Sobriety Calculator | 125 | 87 | 45 s |
| Recovery Blog | 6 | 6 | 2 s |

The directory is #1 by engagement time by a wide margin. Until 2026-09-07 it was
not in the sitemap, carried the site-wide boilerplate meta description, and sat
in GSC "Crawled — currently not indexed."

### We are throwing away most of the data we already fetch

`apps/support_services/meeting_sync.py::sync_source` filters every feed down to
online meetings before importing:

```python
online = [
    m for m in meetings
    if m.get("attendance_option") == "online" and m.get("conference_url")
]
```

The three configured feeds (Seattle, Houston, NY Intergroup) are full AA
intergroup schedules. We keep ~1,565 online meetings and discard every
in-person meeting in the same payload — for three large metros. `_map()`
then hardcodes `attendance_option: "online"` and `location: "Online Meeting"`,
and drops every address field the model already has columns for.

Nothing needs to be built to get this data. It is being parsed and thrown away.

### In-person is where the searchable volume is

Current organic footprint is a single national keyword cluster we rank poorly
in: "sobriety calculator" and its variants drive 20,146 impressions at
**0.44% CTR** from position 9 — Google answers that query itself. Meanwhile
`/court-ordered-meeting-tracker/` converts at 6.87% CTR but sees only 335
impressions, because that keyword cluster is genuinely small.

Local meeting queries are a different shape: "aa meetings in \[city\]" is
higher volume, far lower competition, and **scales per city** instead of
fighting one national SERP. It is also the right audience — a court order is
issued by a specific county court, and a court-ordered person must attend
in-person meetings and prove it.

## Approved direction

Locked decisions:

| Topic | Decision |
|---|---|
| Phase 1 scope | Import in-person + hybrid meetings from the **three feeds already configured**. No new feeds, no new page types. |
| Existing slugs | **Never change.** The 1,565 `online-<key>-<slug>` rows keep their URLs. They are about to be indexed for the first time; churning them would forfeit that. |
| Slug namespace for new rows | `mtg-<key>-<slug>`. Prefix encodes *import source*, never attendance — a meeting that goes online→hybrid must keep its URL. |
| Deactivation guard | Filters on **both** prefixes. The `submitted_by__isnull=True` guard stays — community submissions are never touched by a feed. |
| Missing `attendance_option` | Derive it: `conference_url` + address → `hybrid`; `conference_url` only → `online`; otherwise `in_person`. Older TSML feeds omit the field. |
| Freshness | In-person meetings show a "Last verified" date on the detail page. Sending someone in early recovery to an empty room is a safety failure, not a UX one. |
| Feed etiquette | Each imported meeting links back to its source intergroup. |
| Phase 1 non-goals | City hub pages, new feeds, sitemap index, `meeting_list` query rewrite. All deferred — see Future work. |

## Implementation shape

Three functions in `apps/support_services/meeting_sync.py` change:

1. **`sync_source`** — stop filtering to online. Import everything with a name.
2. **`_map`** — branch on attendance; carry the address fields
   (`formatted_address`, `address`, `city`, `state`, `postal_code`,
   `latitude`, `longitude`, `region`, `location`) that the model already
   defines and TSML already sends.
3. **`_slug` / deactivation** — dual-prefix namespace so existing rows are
   updated in place rather than duplicated.

The SEO work landed on 2026-09-07 already handles in-person correctly:
`Meeting.seo_title` uses `{City}, {ST}` and `Meeting.seo_description` says
"See the address" rather than "Get the join link". No changes needed there.

## Risks

**Volume is unmeasured.** Three metro AA schedules could be 3,000 or 15,000
in-person meetings. Phase 1 must measure before Phase 3 adds feeds. The
sitemap stays a single flat file below ~40,000 URLs; above that it needs a
sitemap index (`django.contrib.sitemaps.views.index`).

**Stale in-person data is a safety problem.** An out-of-date Zoom link wastes
a click. An out-of-date address wastes a bus ride, at a moment when someone
decided to go to a meeting. Hence the "Last verified" requirement in Phase 1
rather than later.

**`meeting_list` will not scale as written.** It uses a deprecated `.extra()`
raw-SQL select and sorts on an unindexed expression:

```python
meetings = meetings.extra(
    select={'is_today': f"day = {today_meeting_day}"}
).order_by('-is_today', 'day', 'time')
```

Fine at 1,565 rows. Not fine at 50,000. (The f-string is not an injection
risk — `today_meeting_day` is computed from `datetime.now().weekday()`.)
Deferred to Phase 4, gated on the Phase 1 volume measurement.

**Feed shape drift.** `attendance_option` is a newer field in the Meeting
Guide spec. The derivation fallback covers feeds that predate it.

## Future work (not this plan)

Each is independently shippable and should get its own plan.

- **Phase 2 — City hub pages.** `/support/meetings/<state>/<city>/` targeting
  "aa meetings in \[city\]". This is where the local SEO value actually lands;
  Phase 1 only makes the data exist. The `city, state` index already exists on
  the model.
- **Phase 3 — More feeds.** TSML ("12 Step Meeting List") is a WordPress plugin
  used by hundreds of AA intergroups, all exposing the same
  `admin-ajax.php?action=meetings` endpoint that `_map()` already parses.
  Adding a feed is one dict entry in `FEED_SOURCES`. Gate on Phase 1 volume.
- **Phase 4 — Scale.** Sitemap index, `meeting_list` query rewrite, pagination
  strategy.
- **Phase 5 — Verification loop.** Report-a-problem on each meeting, and a
  staleness sweep that deactivates meetings whose feed has not confirmed them
  in N syncs.
