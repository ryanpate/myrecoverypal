# Phase 1a: Anchor Conversion Engine — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Depends on:** Phase 0 trial-expiration (shipped — the paywall now actually fires).
**Related:** `docs/plans/2026-06-12-trial-expiration-design.md`. Phase 1b (habit-centered home) and 1c (positioning) are separate, later specs.

## Problem

Phase 0 turned the paywall on, but Anchor still won't convert free users well:
1. The free limit is **10 messages lifetime** — users hit a terminal wall before forming any habit, so the wall feels arbitrary and there's no recurring upgrade moment.
2. Anchor is passive — the user must navigate to it. Its highest-value moment (someone struggling / craving) is exactly when they won't think to open a chat.

The thesis (approved): **convert habits, not first impressions.** Make Anchor show up at the emotional-peak moment (a low-mood/high-craving check-in), let a daily habit form, and convert on felt value — while never gating someone mid-struggle.

## Goals / success criteria

1. A struggling/high-craving check-in offers Anchor via an inline card that opens a session **pre-seeded** with a proactive, context-aware opener.
2. Free routine use is **3 messages/day** (resets daily), replacing the 10-lifetime cap. Premium stays 20/day.
3. **Crisis-triggered conversations are exempt** from the limit and never hard-cut — a struggling user is never paywalled away from support.
4. The existing upgrade CTA (Phase 0) fires when a free user exceeds 3 *routine* messages in a day.

**Verifiable:** (a) a `mood≤2 or craving≥3` check-in renders the card; a calmer one does not. (b) messages in a `checkin_support` session don't count toward the daily limit and are never blocked. (c) a free user is blocked after 3 manual messages in a day and unblocked the next day. (d) premium 20/day unchanged.

## Non-goals (deferred)

- Habit-centered home/feed redesign (Phase 1b).
- Any pricing/tier change.
- Proactive Anchor outside the check-in flow (e.g., scheduled nudges).
- Changing the AI model, system prompt structure, or crisis-detection/988 safety logic.

## Design

### A. Data model (`apps/accounts/models.py`)

Add to `RecoveryCoachSession`:
```python
    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('checkin_support', 'Check-in support'),
    ]
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual')
    triggering_checkin = models.ForeignKey(
        'DailyCheckIn', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='coach_sessions')
```
Add to `DailyCheckIn` a small, testable predicate used by the view and template:
```python
    def needs_support(self):
        """True when this check-in indicates a struggling/high-craving moment."""
        return self.mood <= 2 or self.craving_level >= 3
```
(`mood` 1–6 where 1=Struggling, 2=Down; `craving_level` 0–4 where 3=Strong, 4=Intense.)

Migration: one auto-generated migration adding the two nullable fields (safe, additive).

### B. Gating rework (`apps/accounts/coach_service.py`)

- `get_message_count_today(user)` — scope to **non-exempt** sessions:
  ```python
  return CoachMessage.objects.filter(
      session__user=user, role='user', created_at__gte=today_start,
  ).exclude(session__trigger='checkin_support').count()
  ```
- `can_send_message(user, session=None)` — becomes session-aware and daily for free:
  ```python
  def can_send_message(user, session=None):
      # Crisis-triggered conversations are never limited.
      if session is not None and session.trigger == 'checkin_support':
          return True, None
      is_premium = hasattr(user, 'subscription') and user.subscription.is_premium()
      today_count = get_message_count_today(user)
      if is_premium:
          if today_count >= 20:
              return False, "You've reached your daily limit of 20 messages. Your limit resets at midnight."
          return True, None
      if today_count >= 3:
          return False, "upgrade_required"
      return True, None
  ```
- `get_total_free_messages` (lifetime) is no longer used for gating. Remove its use; delete the function if nothing else references it (verify during implementation).
- New `generate_checkin_opener(user, checkin) -> str`: builds the system prompt via the existing `build_user_context(user)`, then makes one Anthropic call (same client/model `claude-haiku-4-5-20251001`) with a single synthetic user turn instructing Anchor to open warmly and reference the check-in (mood, craving level, and the check-in's `challenge` text if present). Returns the assistant text. On any error, return a **static fallback**: *"I saw your check-in — sounds like today's been heavy. I'm here. What's going on right now?"* Caller saves the result as the session's first `CoachMessage(role='assistant')`.

### C. Views (`apps/accounts/views.py`) + URLs

- **`checkin_confirmation(request)`** (new): renders a brief "Checked in ✓" template. It reads the just-created check-in (id passed via redirect, e.g. `?checkin=<id>`, validated to belong to `request.user`) and, if `checkin.needs_support()`, renders the Anchor card linking to `coach_start_from_checkin`. Non-supportive check-ins show the confirmation without the card.
- **`daily_checkin_view`**: on successful create, redirect to `accounts:checkin_confirmation?checkin=<id>` instead of straight to the dashboard. (The second check-in creation path at views.py:915, if it's a distinct quick-checkin entry, is out of scope for this slice — note it but don't wire the card there.)
- **`coach_start_from_checkin(request, checkin_id)`** (new): fetch the check-in (404 if not the user's). If a `checkin_support` session already exists for it, reuse it; else deactivate other active sessions, create `RecoveryCoachSession(user, trigger='checkin_support', triggering_checkin=checkin, is_active=True)`, and save the proactive opener from `generate_checkin_opener`. Redirect to `accounts:recovery_coach`.
- **`coach_send_message`**: load the session *before* the limit check, then call `can_send_message(request.user, session)` so `checkin_support` sessions are correctly exempt. (Currently it calls `can_send_message(request.user)` and loads the session after — reorder.)
- **`recovery_coach`** view + template: the "messages remaining" display currently uses the lifetime count. Update it to reflect the daily model — show remaining of the daily allowance (`max(0, limit - get_message_count_today(user))` where limit is 20 for premium / 3 for free). Copy changes from "X free messages left" to "X messages left today".

URLs (`apps/accounts/urls.py`):
```python
path('checkin/done/', views.checkin_confirmation, name='checkin_confirmation'),
path('recovery-coach/from-checkin/<int:checkin_id>/', views.coach_start_from_checkin, name='coach_start_from_checkin'),
```

### D. Templates

- `accounts/checkin_confirmation.html` (new): minimal confirmation + the conditional Anchor card (warm copy, brand `#1e4d8b`, button → `coach_start_from_checkin checkin.id`). Reuse the existing card styling approach from the coach upgrade prompt for visual consistency.
- `accounts/recovery_coach.html`: update the remaining-count copy only (no structural change).

## Edge cases & risks

- **Never gate mid-struggle:** guaranteed by the `checkin_support` exemption short-circuit at the top of `can_send_message`, plus `get_message_count_today` excluding those sessions so they don't even count toward routine use.
- **Re-tapping the card** reuses the existing `checkin_support` session for that check-in (no duplicate sessions, no duplicate opener).
- **Opener API failure** falls back to a static warm message — the user always lands in a populated, supportive chat.
- **Day boundary:** "today" uses the existing `today_start` (local midnight) logic; the daily reset is consistent with the premium path already in place.
- **Premium users** are unaffected except the count is now scoped to non-exempt sessions (a premium user's crisis sessions also don't burn their 20/day — a reasonable, generous behavior).
- **Existing free users mid-day:** anyone who already sent ≥3 routine messages today is gated immediately on deploy — acceptable and intended (that's the paywall working); they can still get crisis sessions.

## Testing (ephemeral test DB)

1. `DailyCheckIn.needs_support()`: mood 2→True, mood 3→False (craving 0); craving 3→True, craving 2→False (mood 5); both high→True.
2. `get_message_count_today` excludes `checkin_support` messages.
3. `can_send_message`:
   - free, 0 routine today → allowed; after 3 routine → `upgrade_required`; next day → allowed again.
   - `checkin_support` session → always allowed even past 3.
   - premium → allowed until 20 non-exempt/day.
4. `coach_start_from_checkin`: creates one `checkin_support` session linked to the check-in, saves an opener (mock the Anthropic call); re-tap reuses the same session; another user's check-in → 404.
5. `generate_checkin_opener`: returns the static fallback when the API call raises (patched).
6. `checkin_confirmation`: renders the card when `needs_support()`, omits it otherwise; rejects a check-in not owned by the user.

## Rollout

Single release. Additive migration (two nullable fields) runs first. The free limit flips from 10-lifetime to 3-daily on deploy. No data backfill needed (`trigger` defaults to `'manual'`, so all existing sessions/messages count as routine — correct).

## Open questions

None. Habit-centered home (1b) and positioning (1c) are separate specs.
