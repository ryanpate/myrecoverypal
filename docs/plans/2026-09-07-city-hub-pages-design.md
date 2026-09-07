# City Hub Pages — Design

**Date:** 2026-09-07
**Status:** Approved direction; implementation plan in `2026-09-07-city-hub-pages-plan.md`
**Follows:** `2026-09-07-meeting-directory-expansion-design.md` (Phase 2 of that doc)

---

## Goal

Give the 4,844 in-person meetings a page that actually answers the query
people type — "aa meetings in houston" — instead of only 6,451 pages about
individual meetings.

## Why this change

### We have the data and no page that serves the query

Phase 1 imported 4,844 in-person/hybrid meetings across **254 city/state
pairs**. Every one has a detail page. None of them will ever rank for
*"aa meetings in houston"*, because that query wants a **list**, and a page
about the Tuesday 7pm Daily Bread Group is not a list.

Current distribution:

| Cities with ≥N meetings | Count |
|---|---|
| ≥1 | 254 |
| ≥3 | 166 |
| ≥5 | 125 |
| ≥10 | 68 |
| ≥20 | 39 |

Largest: New York 699, Houston 694, Seattle 427, Brooklyn 314, Spring 121,
Bellevue 104.

### 6,451 thin pages is a risk, not just an asset

Individual meeting pages are short and near-identical by nature — a name, a
day, a time, an address. At this volume Google may reasonably decline to
index most of them as doorway-ish content. City hubs are fewer,
substantially richer, and defensible on their own merits; they also give
every detail page an internal-linking parent, which makes the detail pages
*more* likely to index, not less.

### The directory is entirely AA, and our current copy says otherwise

All three feeds are AA intergroups (`nyintergroup.org`, `aahouston.org`,
`seattleaa.org`). There are zero community submissions and zero NA, SMART,
Refuge or LifeRing meetings.

The `/support/meetings/` description shipped on 2026-09-07 reads:

> Search 1,500+ free recovery meetings — AA, NA, SMART Recovery and secular
> groups.

Both halves are wrong: the count is now 6,451, and the directory contains no
NA or SMART meetings. That copy came from conflating "the Court Compliance
tracker is program-neutral" (true, and constitutionally important) with "the
meeting directory carries every program" (false). Fixing it is in scope here
— accurate copy is also better copy, since "aa meetings" is the query that
actually has volume.

## Approved direction

| Topic | Decision |
|---|---|
| City URL | `/support/meetings/<state>/<city-slug>/` e.g. `/support/meetings/tx/houston/` |
| State URL | `/support/meetings/<state>/` e.g. `/support/meetings/tx/` |
| Route ordering | Both registered **before** `meetings/<slug:slug>/`, and the state route regex-constrained to exactly two letters. A bare `<slug:slug>` would otherwise swallow `/meetings/tx/`. |
| Threshold | `MIN_MEETINGS_FOR_HUB = 3`. Yields 166 city pages and 4 state pages. A hub listing one meeting is the thin content we are trying to avoid. |
| Cities below threshold | No page of their own. Still listed on the state page and reachable via the finder and their own detail pages. |
| Program naming | **AA**, because that is what the data is. Not "AA, NA & SMART". |
| New models | None. Derive from the existing `city`/`state` columns; the `(city, state)` index already exists on `Meeting`. |
| Internal linking | detail → city hub; city → state hub; state → its cities; finder → largest cities. Gives the 6,451 detail pages a crawl parent. |
| Sitemap | Both hub types added. ~170 URLs on top of 6,574 — no sitemap-index needed. |

## Implementation shape

No migration. Two new views, two templates, two sitemap classes, plus a
`city_hub_url` helper on `Meeting` for the detail-page backlink.

The list query is a plain aggregate over the existing index:

```python
Meeting.objects.filter(is_approved=True, is_active=True)
    .exclude(city='').exclude(state='')
    .values('city', 'state')
    .annotate(n=Count('id'))
    .filter(n__gte=MIN_MEETINGS_FOR_HUB)
```

City slugs are resolved back to the stored city name by slugifying
candidates within the state, because `city` is free text from the feed and
has no slug column. Verified against production: **no slug collisions
within any state**, and no city names containing characters outside
`[A-Za-z .'-]`.

## Risks

**Only five states, and two are trivial.** NY 1,918, TX 1,704, WA 1,218,
CT 3, NJ 1. The threshold excludes NJ entirely and gives CT a single
one-city page. That is correct behaviour, not a bug — it will resolve itself
when Phase 3 adds feeds.

**City is free text from the feed.** A feed changing "Saint Louis" to
"St. Louis" would silently orphan a hub URL. Acceptable now (the three
feeds are stable and Google re-crawls), but if Phase 3 adds many feeds this
wants a real slug column with history.

**Doorway-content judgement.** 166 city pages that are only a list of
meetings could still read as thin. Each page therefore carries a genuine
schedule grouped by day, the city's meeting count, in-person/online split,
and a link to the state hub — not just a list of names.

## Future work

- Neighbourhood pages for the very large cities (New York 699, Houston 694)
  — only once city pages prove they index.
- A real `city_slug` column with redirect history, when feed count grows.
- `meeting_list`'s `.extra()` sort and the `_resolve_slug` N+1 both want
  fixing before Phase 3 multiplies the feeds.
