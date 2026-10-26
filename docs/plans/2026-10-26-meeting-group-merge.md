# Meeting page merge: one indexable page per group

**Date:** 2026-10-26 · **Status:** built 2026-10-26 (awaiting deploy)

## Problem

Every weekly time slot of a meeting is its own page. TSML feeds give each slot
its own slug, so NYC's Perry Street Workshop is 66 near-identical pages
(`…-perry-street-workshop`, `…-2`, … `…-118`).

Prod, 2026-10-26:

| | Count |
|---|---|
| Active, approved meeting pages | 22,415 |
| Real groups (same feed + name + place) | ~10,841 |
| Groups with one slot | 8,245 |
| Groups with 2–66 slots | ~2,600 |
| Same group, same day and time (true dupes) | 97 |

GSC (last 3 months):

- All 4,293 "Discovered – currently not indexed" URLs are meeting pages. Google
  won't spend crawl on thousands of thin near-duplicates.
- Meeting detail pages still earn 40% of all site clicks, at 3.7% CTR.
- Of those clicks, 200 landed on base slugs and 94 on numbered slot slugs
  (`-27` and so on). The fix must pass the numbered pages' value on, not drop it.

## Approach (recommended): canonical to a primary slot, no new URLs

Keep every slot page working. Reminders, bookmarks and the court
"log this meeting" prefill are all per slot, and existing links keep resolving.
Each group gets one **primary** slot. The primary's URL becomes the group's
indexable page, and every other slot points its `rel=canonical` at it.

Why this approach, not new `/meetings/group/<slug>/` URLs with 301s:

- **The pages that already rank keep their URLs.** The primary is the base slug
  whenever it exists, and base slugs are the 408 pages already earning most
  impressions. New URLs would restart that ranking.
- **Slot features keep working.** A 301 would break per-slot reminders and court
  prefill, unless the slot pages stayed reachable anyway.
- **No migration of URLs or foreign keys.** Rows pointing at a meeting
  (`MeetingReminder`, `UserBookmark`, `MeetingAttendance.meeting`) are untouched.

## Changes

### 1. Group key and primary flag (model + sync)

- Add two fields to `Meeting`:
  - `group_key`: CharField, indexed
  - `is_group_primary`: BooleanField, indexed
- `apps/support_services/grouping.py::group_key(meeting_or_dict)`:
  - Source feed: from the slug prefix `mtg-<feed>-` / `online-<feed>-`.
    Community submissions get `community-<pk>`, which is always a singleton.
  - Normalized name: lowercase, punctuation collapsed.
  - Place:
    - In-person and hybrid: normalized `formatted_address`, falling back to
      `address`, then `location`, plus city and state.
    - Online: the conference URL host and path with the query stripped, so a
      Zoom meeting ID stays and `?pwd=` goes. Use `online` when there's no URL.
  - Hashed to a fixed length, so the key never exceeds the column.
  - Online meetings are keyed by URL, not name, so a generic name like
    "Daily Reflections" never merges separate Zoom rooms.
- `assign_primaries(keys)`: for each group, exactly one active row is primary:
  1. The slug with no trailing `-<n>`, if active.
  2. Otherwise the lowest numeric suffix.
  3. Ties go to the lowest pk.

  The rule is deterministic, so the primary only moves when the feed drops that
  slot.
- `meeting_sync.sync_source`: set `group_key` in `_map`, then run
  `assign_primaries` over the touched keys after the upsert and deactivation
  pass.
- Migration with a backfill for all ~23k rows. It's chunked; two `UPDATE`s per
  chunk is fine. Dry run against prod data: 22,415 live slots become 10,839
  groups, computed in 0.3 s.
- `Meeting.save()` sets a key on rows saved outside the sync. Community
  submissions get a `single-` key and are their own primary, so they stay in
  the sitemap.

### 2. Detail page

- Load sibling slots: same `group_key`, active and approved, ordered by day
  and time.
- New **Weekly schedule** block: day, time, format/types, in-person/online,
  with a link to each slot's own page for reminders and court logging.
  - It sits after Join Online and Location, so a 49-slot group doesn't push the
    join link down the page.
  - Rows after the 7th are collapsed in a `<details>` element. They stay in the
    HTML, so every slot page keeps the same content for the canonical.
  - The slot being viewed is highlighted.
  - The 97 true dupes collapse by (day, time) at display time. Deactivating them
    wouldn't stick, because the next sync re-activates them.
- `<link rel="canonical">` points at the primary's URL on every slot page. The
  primary's canonical is itself.
- Primary page title and description move to the group level, for example
  "Perry Street Workshop: AA Meetings Daily, 50 Perry St, New York". Non-primary
  slots keep their slot-specific title; they're canonicalized away anyway.
- No `noindex` on non-primary slots. Canonical plus noindex sends Google
  conflicting signals.

### 3. Sitemap and internal links

- `MeetingSitemap.items()`: `is_group_primary=True` only, about 10.8k URLs
  instead of 22.4k.
- City hubs keep the by-day listing, because "what's on today" is the useful
  view. Each row still links to its slot.
- The detail page's "nearby meetings" excludes siblings of the same group.

### 4. Out of scope

- No changes to reminders, bookmarks, court attendance or the finder's search
  results; they stay slot-level.
- No new URL patterns and no redirects.

## Tests

- `group_key`:
  - Slots of the same group match.
  - Same name at a different address doesn't match.
  - Online rooms are split by meeting ID; `?pwd=` is ignored.
  - Community submissions are always singletons.
- `assign_primaries`:
  - The base slug wins.
  - Without a base slug, the lowest suffix wins.
  - The primary moves only when it's deactivated.
  - Exactly one primary per group.
- Sync: new rows get keys, and the primary is reassigned after deactivation.
- Detail page:
  - The schedule lists every sibling once.
  - Canonical points at the primary from a non-primary slot, and at itself on
    the primary.
- Sitemap only lists primaries.

## Rollout

1. Deploy. The migration backfills keys and primaries.
2. Spot-check in prod:
   - Perry Street (66 slots) has one primary, and its schedule shows every slot.
   - A singleton page is unchanged.
3. In GSC, resubmit `sitemap.xml`. Then use URL Inspection to request indexing
   for about 10 high-impression primaries.
4. Watch for 4–8 weeks:
   - "Discovered – currently not indexed" should fall from 4,293.
   - Non-primary slots should move to "Alternate page with proper canonical
     tag". That's expected and good.
   - Meeting-page clicks and impressions should hold or rise. Today's baseline
     is 291 clicks and 7,926 impressions per quarter on detail pages.

## Risks

- **Google ignores the canonical** when slot pages differ too much from the
  primary. Mitigation: every slot page renders the same full group schedule, so
  the pages are near-duplicates by design.
- **Wrong merges** (two real groups sharing a name and address in one feed, for
  example different fellowships in one church hall). Mitigation:
  - The name is part of the key.
  - The worst case is a schedule listing both groups' times, each linking to its
    correct slot page.
  - Spot-check the largest groups after backfill.
- **The primary moves** when a feed drops the base slug. Rare. The new primary
  carries the same schedule, so Google re-consolidates.

**Effort:** about a day, including tests and the backfill.
