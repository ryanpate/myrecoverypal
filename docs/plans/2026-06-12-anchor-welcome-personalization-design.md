# Phase 1c: Personalize the Anchor welcome state — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Depends on:** nothing new (uses existing User methods + the coach page).
**Related:** Phase 1a/1b conversion work; the marketing pages already *claim* personalization.

## Problem

Anchor's differentiation vs a generic chatbot is that it knows the user's
recovery (name, days sober, recovery stage, recent moods, check-in streak — all
already in the coach's system prompt). The marketing pages claim this
("remembers your history", "tailored to your stage"). But the **in-product**
first impression — the coach's welcome state — is fully generic ("Hi, I'm
Anchor. I'm your AI recovery companion…") and never demonstrates that knowledge.
So the claim is marketed but not *proven* at the moment a (often free, deciding)
user actually opens Anchor.

## Goal / success criteria

The coach welcome state greets the user by name and surfaces **days sober +
check-in streak**, proving Anchor knows them — with a graceful fallback to the
current generic greeting when that data is absent (brand-new users), never
fabricating numbers.

**Verifiable:** a user with a sobriety date sees their day count in the welcome
state; a user with a multi-day streak sees it; a brand-new user (no sobriety
date, no streak) sees the unchanged generic greeting.

## Non-goals

- No system-prompt change (Anchor already *uses* this data in replies; 1c makes
  it *visible*).
- No dynamic suggestion chips (deferred).
- No marketing-copy changes (the stale "10 free messages" → "3/day" copy on
  `pricing.html`/`ai_recovery_coach.html` is a separate fix).
- No change to anything outside the welcome state.

## Design

### A. Backend — `recovery_coach` view (`apps/accounts/views.py`)

Add three keys to the context dict (all from existing methods; `get_days_sober()`
returns an int or `None`, `get_checkin_streak()` returns an int):

```python
        'coach_first_name': request.user.first_name or request.user.username,
        'coach_days_sober': request.user.get_days_sober(),
        'coach_streak': request.user.get_checkin_streak(),
```

### B. Frontend — welcome state (`apps/accounts/templates/accounts/recovery_coach.html`)

Replace the static heading + description inside `#welcomeState`.

Heading:
```html
<div class="welcome-heading">Hi {{ coach_first_name }}, I'm Anchor</div>
```

Description (server-rendered conditionals — `coach_days_sober` of `None`/`0` is
falsy, so day-0 and no-date users fall through):
```html
<div class="welcome-desc">
    {% if coach_days_sober %}
        I can see you're <strong>{{ coach_days_sober }} days sober</strong>{% if coach_streak > 1 %} with a <strong>{{ coach_streak }}-day check-in streak</strong>{% endif %}. I'm here whenever you need to talk through cravings, celebrate a win, or just process your day.
    {% elif coach_streak > 1 %}
        That's a <strong>{{ coach_streak }}-day check-in streak</strong> you're building. I'm here whenever you need to talk through cravings, celebrate a win, or just process your day.
    {% else %}
        I'm your AI recovery companion. I'm here to listen, support, and encourage you on your journey. Whether you need to talk through cravings, celebrate a milestone, or just process your day &mdash; I'm here for you.
    {% endif %}
</div>
```

The suggestion chips below are unchanged.

## Edge cases

- **New user, no sobriety date, no streak:** both conditions falsy → the `{% else %}`
  generic greeting (identical to today). No fabricated numbers.
- **Day 0 (sobriety date = today):** `get_days_sober()` returns `0` → falsy →
  falls through (we don't print "0 days sober").
- **Has a streak but no sobriety date:** the `{% elif %}` leads with the streak.
- **`first_name` blank:** falls back to `username` (always present).
- The welcome state only renders for a session with no messages (existing
  behavior), so this is the cold-entry first impression — exactly the target.

## Testing (ephemeral DB, Client)

- View passes `coach_first_name`/`coach_days_sober`/`coach_streak`.
- Template via GET `accounts:recovery_coach`:
  - user with `sobriety_date` 47 days ago → response contains "47 days sober".
  - user with a 2-day check-in streak (check-ins today + yesterday) → response
    contains "check-in streak".
  - brand-new user (no sobriety date, no check-ins) → response contains the
    generic "AI recovery companion" line and does NOT contain "days sober".

## Rollout

Single release, no migration. Template + 3 context keys on the existing
server-rendered coach page. Safe, additive.

## Open questions

None.
