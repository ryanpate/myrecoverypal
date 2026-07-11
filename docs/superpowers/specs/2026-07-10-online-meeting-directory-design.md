# Online AA Meeting Directory — Sync + SEO Landing Page

**Date:** 2026-07-10
**Status:** Approved design, pending implementation plan

## Problem

The searchable meeting finder already exists (`apps/support_services`: `Meeting`
model on the Meeting Guide API spec, searchable/filterable list at
`/support/meetings/`, TSML UI finder, geo API, bookmarks, submission flow,
meeting reminders) but has almost no data in production, so the page reads as
broken rather than useful. Separately, organic search remains the platform's
weakest acquisition channel, and "online AA meetings" queries are high-volume.

## Goals

1. A populated, self-maintaining directory of online AA meetings that every
   user can join regardless of location.
2. A public SEO landing page at `/online-aa-meetings/` that renders the live
   directory and targets online-meeting search queries.

Non-goals for this pass: in-person metro imports, NA (BMLT) or SMART sources,
per-user timezone conversion of meeting times.

## Design

### 1. Import pipeline (refactor, no model changes)

- Extract the import/upsert logic from the existing
  `seed_online_meetings` management command into a shared service module:
  `apps/support_services/meeting_sync.py`.
- The management command and the new Celery task both call this service.
- Feed sources are a constant list in the service module. Each source has a
  short `key` and a feed URL. Imported slugs are namespaced
  `online-<sourcekey>-<slug>`, so:
  - each feed owns its slug namespace (no cross-feed collisions);
  - a row's source is derivable from its slug prefix (no migration needed);
  - community-submitted meetings (no `online-` prefix) are structurally
    distinguishable and never touched by sync.
- Source selection is verified at implementation time. Criteria: TSML/Meeting
  Guide JSON feed, online meetings present with non-empty `conference_url`.
  Seattle AA is confirmed working; candidates to test include NYC Intergroup,
  Houston AA, and OIAA. Target: 150+ online meetings covering all 7 days and
  a spread of time slots.
- Imported rows keep the existing command's mapping: `attendance_option='online'`,
  `location='Online Meeting'`, blank address fields, join instructions in
  `notes`, auto-approved.

### 2. Weekly sync task

- New Celery task `sync_online_meetings` in `apps/support_services/tasks.py`,
  scheduled weekly via Celery beat at an off-peak time.
- Per source: fetch feed → upsert meetings → record seen slugs → set
  `is_active=False` on any meeting under that source's slug prefix that no
  longer appears in the feed.
- **Failure isolation:** if a source's fetch or parse fails, skip that
  source's deactivation step entirely — a down feed must never wipe out its
  meetings. Log the failure (Sentry picks it up).
- **Deactivation guard:** targets rows matching the source's slug prefix
  (`online-<sourcekey>-`) **and** `submitted_by IS NULL`. Imported rows never
  have a submitter; community submissions always do. This prevents a
  community meeting whose name slugifies to a matching prefix (e.g. "Online
  Seattle Serenity") from ever being deactivated by sync.
- **Legacy rows:** the previous single-source seed used the bare `online-`
  prefix (no source key). On first run, the sync re-imports Seattle under
  `online-seattle-` and deactivates legacy `online-` rows with
  `submitted_by IS NULL` that lack a source key, so stale duplicates don't
  linger. One-time behavior, covered by a test.

### 3. SEO landing page

- Public view + template in `apps.core`, following the existing SEO
  landing-page pattern (e.g. sobriety calculator page).
- URL: `/online-aa-meetings/`.
- Content: intro copy targeting "online AA meetings" queries, live meeting
  count, "meetings today" list pulled from the directory, CTA link to the
  full searchable finder, FAQ section with FAQPage schema, `_related_tools`
  partial cross-links.
- Added to the sitemap; indexable (no noindex).
- Renders live data so it stays fresh without manual maintenance.

### 4. Display fix: timezone label

- The meeting list currently shows times with no timezone context, which is
  meaningless for online meetings. Show the meeting's stored timezone
  (abbreviated) next to the time in the list and detail templates.
- Per-user timezone conversion is explicitly out of scope for this pass.

## Testing

- Sync service tests against fixture feed JSON:
  - creates new meetings;
  - updates changed meetings (same slug);
  - deactivates meetings missing from the feed;
  - a failed feed fetch skips deactivation for that source;
  - never modifies community-submitted (non-`online-` prefixed) meetings.
- Celery task test with mocked fetch covering multi-source iteration.
- Landing page tests: renders with live counts, contains FAQPage schema,
  present in sitemap.

## Verification of success

After deploy: run the sync once in a Railway shell; confirm
`/support/meetings/` shows a populated, searchable list and
`/online-aa-meetings/` renders live counts; submit the new URL in Google
Search Console.
