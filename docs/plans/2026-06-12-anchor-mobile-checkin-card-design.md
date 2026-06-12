# Phase 1a.1: Anchor card on the AJAX/mobile check-in — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Depends on:** Phase 1a (shipped). Reuses its `coach_start_from_checkin` endpoint and exempt-session behavior unchanged.
**Related:** `docs/plans/2026-06-12-anchor-conversion-engine-design.md`

## Problem

Phase 1a wired the contextual Anchor card into the **web** check-in flow
(`daily_checkin_view` → confirmation screen → card). But the **AJAX** check-in
path (`quick_checkin`) returns JSON and never hits the confirmation screen. That
path is POSTed from `hybrid_landing.html`, which is the page the **mobile app**
loads — so mobile users (and hybrid-landing web users) who log a struggling /
high-craving check-in are never offered Anchor. This is the conversion+safety
net's biggest blind spot.

## Goal / success criteria

After a hard quick-checkin (`mood ≤ 2` or `craving_level ≥ 3`), the "checked in"
state reveals an inline Anchor prompt with a button to
`coach_start_from_checkin` for that check-in. Calm check-ins show nothing extra.

**Verifiable:** (a) `quick_checkin`'s success JSON includes `needs_support`
(true for a hard check-in, false for a calm one) and a valid `coach_url`; (b) the
hybrid-landing success handler reveals the prompt only when `needs_support` is
true and points it at `coach_url`.

## Non-goals

- No change to the web `daily_checkin` flow (already covered in 1a).
- No new endpoint or coach-session logic (reuse `coach_start_from_checkin`).
- No new card design (reuse 1a's card styling/copy).
- No change to the `already_checked_in` response.

## Design

### Backend — `quick_checkin` (`apps/accounts/views.py`)

The success `JsonResponse` (currently `{'success': True, 'mood', 'mood_display',
'message', 'shared_to_feed'}`) gains two keys:

```python
        'needs_support': checkin.needs_support(),
        'coach_url': reverse('accounts:coach_start_from_checkin', args=[checkin.id]),
```

`reverse` is already imported in `views.py`. `needs_support()` already exists on
`DailyCheckIn` (1a). No other backend change.

### Frontend — `hybrid_landing.html`

1. Add a hidden Anchor prompt inside the existing `#checkin-done` block (after
   the "Add more details →" link), reusing the brand styling:
   ```html
   <div id="checkin-anchor-prompt" style="display:none; border:1px solid #1e4d8b; background:#f4f8fc; border-radius:12px; padding:14px; margin-top:14px; text-align:center;">
       <div style="color:#1e4d8b; font-weight:600; margin-bottom:6px;">Today sounds heavy.</div>
       <a id="checkin-anchor-link" href="#" style="background:#1e4d8b; color:#fff; padding:9px 18px; border-radius:8px; text-decoration:none; font-weight:600; display:inline-block;">
           Talk it through with Anchor
       </a>
   </div>
   ```
2. In the quick-checkin success handler, after `showCheckedInState(selectedMood)`,
   add:
   ```javascript
   if (data.needs_support && data.coach_url) {
       const link = document.getElementById('checkin-anchor-link');
       const prompt = document.getElementById('checkin-anchor-prompt');
       if (link && prompt) {
           link.href = data.coach_url;
           prompt.style.display = 'block';
       }
   }
   ```

## Testing

- Backend (ephemeral DB, Django test Client): a hard quick-checkin (`mood=1,
  craving=4`) → response JSON `needs_support` is `True` and `coach_url` reverses
  to the `coach_start_from_checkin` path for that check-in id; a calm quick-checkin
  (`mood=5, craving=0`) → `needs_support` is `False`.
- Frontend: render-check the template compiles; manual verification of the reveal
  (consistent with how the rest of this template's inline JS is handled — it has
  no JS unit tests).

## Edge cases

- `already_checked_in` and error responses are untouched → no prompt.
- The prompt starts hidden and is only revealed via JS, so non-JS/SSR renders
  show nothing extra.
- Re-tapping the Anchor link reuses the existing exempt session (1a behavior).

## Rollout

Single release, no migration. Additive JSON keys + a hidden DOM block + a few JS
lines — safe.

## Open questions

None.
