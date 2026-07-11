# Daily Reflection + Reading on the Progress Home

**Date:** 2026-07-10
**Status:** Approved design, pending implementation plan

## Problem

The daily-thought pipeline already exists (`DailyRecoveryThought` model, 90+
seeded entries, a 6 AM Celery task that guarantees today has one, and the
`_daily_thought.html` partial on the social feed) — but it is decoration on
the feed, not part of the daily ritual on the progress home where pledge and
check-in live. It also recycles after ~90 entries, and nothing connects it
to action.

## Goals

1. Surface the daily thought on the progress home (`accounts:progress`).
2. Turn it into a ritual: a "Reflect in your journal" action that opens a
   pre-filled private journal entry.
3. Add a "Today's reading" suggestion rotating through the site's own blog
   content.
4. Expand the corpus to 365 unique entries so a full year never repeats.

Non-goals: morning push notification (phase-2 candidate), AI-generated
dynamic quotes, external literature links.

## Design

### 1. Progress home card

- `progress_view` (apps/accounts/views.py) adds `daily_thought` to context —
  the same `DailyRecoveryThought.objects.filter(date=today)` lookup the
  social feed uses (extract a tiny shared helper if the feed's lookup is
  inline).
- `accounts/partials/_daily_thought.html` is included on
  `accounts/progress.html` near the pledge card.
- The partial gains two elements (rendered on BOTH surfaces, feed and
  progress home): a "Reflect in your journal" button and a "Today's
  reading" link. Both render only when their context is present, so the
  partial stays safe anywhere it's included.

### 2. Reflect flow (journal app)

- New view `journal:reflect_today` (`/journal/reflect/`), login required.
- GET: renders the existing create-entry form pre-filled:
  - title: `Daily Reflection — July 10, 2026` (user-local date),
  - content seeded with the day's quote, attribution, and reflection
    prompt as an opening block the user writes beneath.
- Saving goes through the existing journal entry flow — entries are
  private, like all journal entries (privacy non-negotiable holds).
- All "today" math uses `timezone.localdate()` (per-user timezone via
  `UserTimezoneMiddleware`) — the repo's convention for pledge/check-in.
- Duplicate guard: if the user already saved a reflection today (matched by
  an entry created today user-local whose title starts with "Daily
  Reflection"), the
  partial's button links to that entry's detail page instead, labeled
  "View today's reflection". The reflect view itself also redirects to the
  existing entry in that case.

### 3. Today's reading

- Deterministic daily rotation over published blog posts:
  `posts[date.toordinal() % count]` on a stable ordering (by id). Same pick
  for every user all day; cycles the full archive; no new model or task.
- Computed where `daily_thought` context is built, exposed as
  `daily_reading` (post object). When no published posts exist, the link
  simply doesn't render.

### 4. Corpus expansion to 365

- Extend `apps/accounts/management/commands/seed_recovery_quotes.py` to 365
  entries (~275 new).
- **Hard constraints:** every entry is ORIGINAL, program-neutral (no
  12-step-only framing), and contains no copyrighted recovery literature —
  AA's "Daily Reflections" and similar works are copyrighted; nothing may
  be lifted or paraphrased from them. Attribution only for genuinely
  public-domain or widely-attributed general quotes; otherwise no
  attribution.
- Each entry: quote, optional attribution, reflection prompt.
- The 6 AM recycling task remains unchanged as the backstop.
- Run the extended seed command in production after deploy (idempotent
  get_or_create keyed as the command already does).

## Testing

- Progress view: response contains the daily thought and (when posts exist)
  the reading link; anonymous users aren't affected (progress is
  login-required already).
- Partial safety: social feed still renders (no missing-context crash when
  `daily_reading` absent).
- Reflect view: GET pre-fills title + quoted content; POST saves a private
  entry owned by the user; second GET the same day redirects to the
  existing entry; button label switches to "View today's reflection".
- Reading rotation: deterministic for a fixed date; changes across dates;
  empty-blog case renders no link.
- Seed command: idempotent; yields 365 distinct entries; no entry text
  duplicated.

## Verification of success

After deploy: progress home shows the quote card with working Reflect and
reading links; completing a reflection saves a private journal entry and
flips the button label; run the extended seed command in a Railway shell and
confirm 365 entries exist.
