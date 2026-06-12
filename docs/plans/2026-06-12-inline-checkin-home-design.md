# Phase 1b: Low-friction inline check-in on the home — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Depends on:** Phase 1a / 1a.1 (shipped). Reuses `quick_checkin` (already returns
`needs_support` + `coach_url`) and `coach_start_from_checkin`.
**Related:** `docs/plans/2026-06-12-anchor-conversion-engine-design.md`

## Problem

The post-login home is `progress.html` (via `LOGIN_REDIRECT_URL`, the `/accounts/`
redirect, and the core index — **not** the social feed; CLAUDE.md is stale). Its
daily check-in prompt links **out to the full `daily_checkin` form** (mood +
craving + energy + gratitude + goal on a separate page). For a *daily* ritual
that friction suppresses completion, and check-in completion is the core
retention loop.

A low-friction inline check-in widget already exists — but it's stranded on
`hybrid_landing.html`, an **orphaned, unrouted page** (no URL serves it; its view
`hybrid_landing_view` is dead). So `quick_checkin` currently has no live caller,
and 1a.1's Anchor card on that page never reaches users.

## Goals / success criteria

1. On the home, a user who hasn't checked in today can log **mood + craving in
   place** (AJAX, no page navigation) instead of being sent to the full form.
2. On submit, the home shows the checked-in state inline (mood + updated streak)
   and reveals the contextual **Anchor card** on a struggling/high-craving
   check-in — finally delivering 1a.1's backend on a live page.
3. The full `daily_checkin` form remains one tap away ("Add more details →") for
   gratitude/goal/energy.
4. Dead `hybrid_landing` code is removed; CLAUDE.md routing note corrected.

**Verifiable:** (a) the home renders the inline mood widget when not checked in,
and the done bar when checked in; (b) `quick_checkin` returns `current_streak`;
(c) a hard inline check-in reveals the Anchor card pointing at
`coach_start_from_checkin`.

## Non-goals (deferred)

- Streak-mechanics overhaul / loss-aversion framing (separate slice).
- Above-the-fold reorg of the rest of the progress page.
- Any change to the full `daily_checkin` form or the charts.
- Auto-sharing the check-in to the social feed (inline check-in stays private —
  no `share_to_feed`).

## Design

### A. Backend — `quick_checkin` returns the updated streak (`apps/accounts/views.py`)

The widget shows the streak inline after submit; the page-load streak predates
today's check-in. Add `current_streak` to the success JSON so the JS can update
the badge:

```python
        'needs_support': checkin.needs_support(),
        'coach_url': reverse('accounts:coach_start_from_checkin', args=[checkin.id]),
        'current_streak': request.user.get_checkin_streak(),
```

(`needs_support`/`coach_url` already added in 1a.1; `get_checkin_streak()` is the
same method `progress_view` uses.) No other backend change.

### B. Frontend — inline widget on `progress.html`

**Replace the contents of `#checkinFormCard`** (currently a prompt + a link-out
button) with an inline widget:
- prompt text "How are you feeling today?"
- a row of the 6 mood buttons (`data-mood="1..6"` with the model's emoji)
- a compact craving selector (None/Mild/Moderate/Strong/Intense → `data-craving="0..4"`, None preselected)
- a "Check In" button (disabled until a mood is chosen)
- the existing "Add more details →" link to `daily_checkin` (kept, secondary)

**Make `#checkinDoneBar`'s dynamic parts always present in the DOM** so the AJAX
path can fill them (today they're rendered only when `todays_checkin` exists):
- the mood text node (server fills it on page load when checked in; JS fills it
  from `data.mood_display` after AJAX)
- the streak badge element always present but hidden when streak ≤ 1; server sets
  it on load, JS updates its text + visibility from `data.current_streak`

**Add a hidden inline Anchor prompt** after the done bar (reusing 1a's card copy
and brand styling), revealed by JS when `data.needs_support`.

**JS (in the page's existing `<script>`, reusing the `getCookie('csrftoken')`
helper):**
- mood button click → mark selected, enable "Check In"
- craving click → mark selected
- "Check In" click → `fetch('{% url "accounts:quick_checkin" %}', {method:'POST', headers:{'X-CSRFToken': csrftoken}, body: form data with mood + craving_level})`
- on `data.success`: hide `#checkinFormCard`; fill + show `#checkinDoneBar`
  (mood text, streak badge from `data.current_streak`); if `data.needs_support &&
  data.coach_url`, set the Anchor link href and reveal the prompt
- on error / `data.already_checked_in`: re-enable the button and show the
  existing checked-in/error handling

The existing page-load toggle JS (`#checkinFormCard` vs `#checkinDoneBar` by
`data-has-checkin`/date, progress.html ~1952-1965) is unchanged — it still picks
the right initial state; the widget only changes what the form card *contains*
and what happens on submit.

### C. Dead-code cleanup

- Delete `apps/accounts/templates/accounts/hybrid_landing.html` and the
  `hybrid_landing_view` function in `views.py` (orphaned; verify no remaining
  references first).
- The `path('', lambda request: redirect('accounts:progress'), name='hybrid_landing')`
  (urls.py:48) does **not** reference the dead view, but replace the lambda with a
  `RedirectView.as_view(pattern_name='accounts:progress')` for clarity, keeping
  the `name='hybrid_landing'` (verify nothing reverses a different behavior).
- Update CLAUDE.md: correct "Users land on the Social Feed" → land on the
  `progress` home.

## Edge cases

- **Streak element missing for new users:** resolved by always rendering the
  streak badge element (hidden when ≤1), so JS can reveal/update it.
- **Already checked in (race / double tab):** `quick_checkin` returns
  `already_checked_in`; JS shows the done state, no duplicate.
- **AJAX failure:** button re-enables with a message; the "Add more details →"
  full-form path remains as a fallback.
- **No JS:** `#checkinFormCard` stays visible with the "Add more details →" link
  to the working full form (graceful degradation).

## Testing

- Backend (ephemeral DB, Client): `quick_checkin` success JSON includes
  `current_streak` (an int); a hard inline check-in still returns
  `needs_support=True` + a valid `coach_url` (already covered in 1a.1 — extend
  with the streak assertion).
- View/template: GET the progress home as a user with no check-in today → the
  inline mood widget markup (e.g. `data-mood="1"`) is present and the done bar is
  hidden; as a user who checked in today → done bar shown.
- Cleanup: a test/Bash grep confirming `hybrid_landing_view` / `hybrid_landing.html`
  are gone and nothing references them.
- The AJAX submit + inline reveal is vanilla JS — manual verification (consistent
  with the rest of this template), plus a template render check.

## Rollout

Single release, no migration. Additive JSON key + template/JS changes on the live
home + dead-code deletion. The full-form path stays intact as a fallback.

## Open questions

None.
