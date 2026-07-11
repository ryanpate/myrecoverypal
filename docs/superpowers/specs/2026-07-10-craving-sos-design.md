# Craving SOS Page — "2 AM Toolbox"

**Date:** 2026-07-10
**Status:** Approved design, pending implementation plan

## Problem

Cravings are the moment a user either opens the app or relapses and churns.
The platform has the pieces — crisis page, Anchor coach with an unlimited
crisis mode, a populated online-meeting directory, coping content — but no
single place a person in a craving moment can reach in one tap, and nothing
for the anonymous "how do I stop this craving" searcher.

## Goals

1. One public page at `/craving-sos/` with immediately usable tools:
   breathing, urge surfing, grounding, meetings starting soon, crisis line.
2. Logged-in members additionally get one-tap Anchor (never rate-limited)
   and their own pledge reason/photo.
3. One persistent SOS button in the app nav (web + native).
4. SEO surface for "how to stop alcohol/drug cravings" queries.

Non-goals for v1: pal/sponsor quick messaging, tool-usage analytics beyond
GA page views, a native modal, separate per-tool pages.

## Design

### 1. View + URL

- `CravingSOSView(TemplateView)` in `apps.core`, URL `/craving-sos/`,
  name `core:craving_sos`. Public (no login required).
- Context:
  - `soon_meetings` — from `starting_soon(hours=3, limit=6)` (see §2).
  - For authenticated users: `pledge_reason`, `pledge_photo` (from the
    `User` onboarding fields) and the Anchor SOS link (see §4).
- Sitemap entry priority 0.9; FAQPage schema; `_related_tools.html` card
  (key `craving_sos`) so all landing pages cross-link it; the page itself
  includes the partial `with exclude='craving_sos'`.

### 2. Meetings starting soon

New module `apps/support_services/meeting_queries.py`:

- `starting_soon(hours=3, limit=6)` — returns active, approved online
  meetings whose next occurrence starts within `hours` from now, sorted by
  minutes-until, annotated with `minutes_until` per meeting.
- Meetings store `day` + `time` in their home IANA `timezone`. The helper:
  1. collects distinct timezones among active online meetings (~3 today);
  2. per zone, computes local now; builds a window `[now, now+hours]`;
  3. queries `(day=today_local, time in [now_t, min(now_t+hours, 24:00)))`
     plus, when the window crosses midnight,
     `(day=tomorrow_local, time < spillover)`;
  4. merges across zones, computes `minutes_until`, sorts, trims to `limit`.
- Unit tests cover: a meeting inside the window, outside it, the midnight
  spillover, cross-zone ordering, and inactive/in-person exclusion.

### 3. Interactive tools (inline vanilla JS)

All three tools live in the page template with inline JS (same pattern as
the sobriety calculator — no build step; usable anonymously):

- **Breathing:** 4-7-8 pattern; animated expanding/contracting circle with
  phase label (Breathe in 4 / Hold 7 / Out 8), start/stop, cycle counter.
- **Urge surfing:** guided ~10-minute walkthrough; progress bar plus staged
  copy that changes at intervals ("A craving is a wave — it peaks and
  passes", midpoint encouragement, completion affirmation). Start/stop;
  no persistence.
- **Grounding (5-4-3-2-1):** tap-through steps — 5 things you can see,
  4 hear, 3 touch, 2 smell, 1 taste — with a Next button and completion
  message.

### 4. Crisis line + Anchor

- 988 Suicide & Crisis Lifeline strip pinned at the top of the page,
  always visible, styled unmissable; link to the existing `/crisis/` page.
- Logged-in: "Talk to Anchor now" button opens a Recovery Coach session
  with trigger `sos`, following the existing `coach_start_from_checkin`
  pattern (apps/accounts/views.py ~5034): a new `@login_required` view
  `coach_start_sos` reuses the user's existing active `sos` session from
  today or creates one (deactivating other active sessions), seeds an
  assistant opener appropriate to a craving moment, and redirects to
  `accounts:recovery_coach`. `RecoveryCoachSession.TRIGGER_CHOICES` gains
  `sos`, and the rate-limit exemption in
  `apps/accounts/coach_service.py::can_send_message` treats `sos` exactly
  like `checkin_support` (never limited, messages don't count toward the
  daily total) — a member mid-craving is never paywalled. Choices-only
  model change (trivial migration).
- Anonymous visitors see a "Get free support" register CTA in that slot.

### 5. Nav SOS button

- One small distinct "SOS" pill in the main nav in `templates/base.html`,
  linking to `/craving-sos/`, visible to all users on web.
- Explicitly kept visible in the native app (the native ultra-minimal nav
  CSS hides several nav items; the SOS pill is excluded from those hides).
- No other in-app entry points in v1.

### 6. SEO

- Title targeting "How to Stop Alcohol & Drug Cravings" intent; meta
  description and keywords per the existing landing-page pattern; canonical
  `https://www.myrecoverypal.com/craving-sos/`.
- FAQPage schema (~5 questions: how long do cravings last, what is urge
  surfing, does breathing help, when to call 988, are online meetings
  free) mirrored by visible FAQ content below the tools.

## Testing

- View tests (`apps/core/test_craving_sos.py`, with the repo's standard
  `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`):
  - anonymous GET → 200; contains breathing/urge/grounding markup, FAQPage
    schema, crisis strip; does NOT contain the Anchor button;
  - authenticated GET → contains Anchor button and pledge reason when set;
  - sitemap contains `/craving-sos/`.
- `meeting_queries` tests as listed in §2.
- Coach exemption test: a session with `trigger='sos'` is never limited
  (mirrors the existing `checkin_support` test if one exists; otherwise a
  new focused test on `can_send_message`).
- Manual browser pass on the three JS tools before merge.

## Verification of success

After deploy: SOS pill visible in nav; `/craving-sos/` renders tools for an
anonymous browser; breathing/urge/grounding run in-browser; a logged-in
Anchor SOS session sends more than the free daily limit without being
blocked; meetings-starting-soon shows entries with join links; submit the
URL in Search Console.
