# Phase 0: Trial Expiration — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Author:** brainstormed with Claude
**Related:** Revenue/conversion thesis (Anchor-as-conversion-engine). This is the
prerequisite unlock; Phase 1 (contextual Anchor, free-allowance rework,
habit-centered home) is a separate follow-up spec.

## Problem

238 registered users, **0 paying**. The conversion rate is not low — it is
structurally zero, because **the 14-day Premium trial never expires**, so the
paywall has never fired for anyone.

### Root cause (verified)

- On signup, `signals.py::create_user_subscription` creates a subscription with
  `tier='premium'`, `status='trialing'`, `trial_end = now + 14 days`.
- `Subscription.is_premium()` = `tier in ['premium','court'] AND is_active()`.
- `Subscription.is_active()` = `status in ['active','trialing']` — **it never
  checks `trial_end`.**
- **Nothing ever flips `status` from `'trialing'` once `trial_end` passes.** The
  only task touching trialing rows (`send_trial_ending_notifications`) just sends
  a reminder email; it does not downgrade. Status changes only via a real
  Stripe/Apple paid webhook.

Net: every user passes `is_premium()` **permanently**. No gate ever closes, so no
upgrade prompt ever shows. You cannot convert users who are never gated.

## Goals / success criteria

1. A `trialing` subscription whose `trial_end` has passed no longer grants
   premium access (gate is correct at read time).
2. All 238 existing users get a **fresh 14-day trial from launch** (soft
   landing), with no mid-deploy window where they are abruptly downgraded.
3. When a trial genuinely ends, the user is downgraded to free and receives a
   "trial ended" email that drives to the upgrade path.
4. A downgraded free user who hits a gate sees a **working** upgrade CTA that
   reaches Stripe checkout (no dead-ends).
5. Real paying users (Stripe/Apple `status='active'`) are never affected.

**Verifiable:** after this ships, (a) a subscription with `trial_end` in the past
reports `is_premium() == False`; (b) the nightly task downgrades ended trials and
skips future/paid ones; (c) clicking "upgrade" from the Anchor wall opens Stripe
checkout.

## Non-goals (explicitly deferred to Phase 1)

- No homepage/feed redesign, no Anchor repositioning.
- No change to the free-tier Anchor allowance (the 10-lifetime → daily rework is
  Phase 1).
- No new subscription tiers or pricing changes.
- No proactive/contextual Anchor triggering.

This spec only turns the **existing, already-built** paywall on, safely.

## Design

Four components, all shipped in one release.

### A. Fix the gate (`payment_models.py`)

Make an expired trial count as inactive:

```python
def is_active(self):
    """Active = paid-active, or a trial whose window hasn't passed."""
    if self.status == 'trialing':
        return bool(self.trial_end and self.trial_end > timezone.now())
    return self.status == 'active'
```

This is the core correctness fix. `is_premium()`, `is_court()`, `is_supporter()`
all already delegate to `is_active()`, so they inherit the fix with no further
change. It also closes the gap between nightly task runs — an expired trial stops
granting access immediately, not "by tomorrow's job."

Also add a status value for the downgrade outcome (current `STATUS_CHOICES` has no
"expired"): add `('expired', 'Expired')`. This is the correct semantic for "trial
ended without converting" (distinct from a user-initiated `canceled`) and makes
that cohort queryable when we measure the conversion funnel. Changing `choices`
on a `CharField` produces a state-only migration (no SQL).

### B. Fresh-trial reset (data migration)

A Django data migration that sets `trial_end = now + 14 days` for **every**
`status='trialing'` subscription (all existing users; none have a real paid sub
because paid → `status='active'`).

Why a migration and not a management command: migrations run **before** the new
gate (A) serves traffic during deploy, so there is no window where existing users
are downgraded mid-deploy. The reset and the gate fix land atomically. Resetting
users whose trial already had future time left (recent signups) is intentional —
everyone gets a uniform 14 days "from launch."

```python
# migration operation (RunPython)
def reset_trials(apps, schema_editor):
    from django.utils import timezone
    from datetime import timedelta
    Subscription = apps.get_model('accounts', 'Subscription')
    Subscription.objects.filter(status='trialing').update(
        trial_end=timezone.now() + timedelta(days=14)
    )
```

Reverse migration: no-op (trial_end values can't be meaningfully restored).

### C. Nightly expiration task (`tasks.py` + beat schedule)

```python
@shared_task(bind=True, max_retries=3)
def expire_ended_trials(self):
    """Downgrade trials whose window has passed to free, and email the user."""
    from django.db.models import Q
    now = timezone.now()
    ended = Subscription.objects.filter(
        status='trialing',
        trial_end__lt=now,
    ).filter(
        # defensive: never touch a real payer (field is null=True, blank=True)
        Q(stripe_subscription_id__isnull=True) | Q(stripe_subscription_id='')
    ).select_related('user')
    for sub in ended:
        sub.tier = 'free'
        sub.status = 'expired'
        sub.save(update_fields=['tier', 'status'])
        # send "trial ended" email (see below) + in-app notification
```

- Register in `CELERY_BEAT_SCHEDULE` (settings.py:708) to run daily, early
  (e.g. `crontab(hour=9, minute=0)`), before the existing 10:00 email tasks.
- `send_trial_ending_notifications` already emails the day *before* expiry, so
  the "heads-up" is covered for fresh trials automatically — no separate launch
  email needed.
- **New email template** `emails/trial_ended.html`: "Your Premium trial ended —
  here's what changed, upgrade to keep [Anchor / unlimited groups / analytics]."
  CTA → `/accounts/pricing/`. This is the conversion moment.

### D. Make the upgrade path work on downgrade

`coach_send_message` already returns `{'error': 'upgrade_required',
'upgrade_required': True}` with HTTP 429 when a free user is gated. **The coach
frontend (`recovery_coach.html`) does not currently handle this** — it would show
the literal string "upgrade_required" as an error.

Work:
- In `recovery_coach.html`, when a send response has `upgrade_required`, show a
  small upgrade prompt (modal or inline card): short value line + "Upgrade to
  keep talking to Anchor" button → `/accounts/pricing/`.
- Confirm the pricing page → `create_checkout_session` → Stripe flow works for
  the **premium** plan (court already verified live). Fix if it dead-ends.

Scope guard: this is the *minimum* working upgrade surface, not a redesigned
paywall (that's Phase 1). One clean, functional CTA.

## Edge cases & risks

- **Mid-deploy race:** avoided by doing the reset as a migration (runs before new
  gate serves traffic). Confirmed ordering is the whole reason B is a migration.
- **Real payers:** `status='active'` users are never matched by A's trialing
  branch or C's filter. C additionally guards on empty `stripe_subscription_id`.
- **Existing-user churn/backlash:** softened by the fresh 14-day window + the
  existing day-before reminder email + the new trial-ended email. Expected and
  accepted: some dormant users will lapse to free — that is the point.
- **Court/supporter trials:** same mechanism; court users who actually paid are
  `status='active'`. No special handling needed.
- **Clock/timezone:** all comparisons use `timezone.now()` (project is TZ-aware).

## Testing (ephemeral test DB, per project pattern)

1. `is_active()` / `is_premium()`:
   - trialing + `trial_end` future → premium True
   - trialing + `trial_end` past → premium False
   - active → True; expired/free → False
2. `expire_ended_trials`:
   - flips trialing+past → `tier='free', status='expired'`
   - skips trialing+future
   - skips `status='active'` and trialing-with-stripe_subscription_id
   - sends one email per downgraded user
3. Migration B: a trialing sub with past `trial_end` ends up `now+14d`.
4. Item D: a gated `coach_send_message` returns `upgrade_required`; (frontend
   behavior verified manually / via the webapp-testing tooling).

## Rollout / deploy sequence

1. Single release contains A + B + C + D.
2. Deploy → migration B runs first (everyone gets fresh 14 days) → new gate A
   serves traffic (no one expired yet) → beat picks up task C.
3. Over the next ~14 days, fresh trials approach end: day-before reminder fires
   (existing task), then C downgrades + sends trial-ended email.
4. Watch: subscriptions with `status='expired'` should start appearing ~14 days
   post-launch; first real Stripe conversions become possible immediately for any
   user who upgrades during/after their window.

## Open questions

None. Phase 1 (the conversion experience itself) is a separate spec to be
brainstormed after Phase 0 ships.
