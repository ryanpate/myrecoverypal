# Family / Supporter Dashboard — Design Spec

**Date:** 2026-06-11
**Status:** Approved design — ready for implementation plan
**Author:** Ryan Pate (with Claude)

## Summary

A premium tool that lets a family member, spouse, or sponsor follow a person's
recovery progress **with that person's consent**. The supporter sees a curated,
positive-leaning dashboard (sobriety streak, milestones, check-in consistency,
mood trend), can send one-tap encouragement, and — at the most intimate preset —
receives a behavioral inactivity alert plus the person's own deliberate "I need
support" pings.

The **supporter** is the paying customer ($7.99/mo). The person in recovery
shares for free. This targets a net-new buyer segment surfaced by Google Search
Console (`track loved ones recovery`, `recovery companion`, etc.) — a non-user
who pays — rather than monetizing the existing small user base.

## Problem & evidence

GSC (last 3 months) shows organic demand is entirely tool/intent-driven, and one
recurring intent is a *family member wanting to follow a loved one's recovery*
(`track loved ones recovery`, pos 49). That buyer is a non-addict with real
willingness to pay (peace of mind), distinct from the recovery-community Premium
audience. No social-network search demand exists. This feature converts that
searched-for intent into a subscription.

## Goals

- Let a person in recovery share a **curated** progress view with one or more supporters, under explicit consent they control.
- Give supporters a warm, useful dashboard + a one-tap way to encourage.
- Provide a genuine safety net (inactivity alert + manual support ping) **without** degrading the honesty of the person's check-in data.
- Open a new revenue line by selling the **supporter** seat.

## Non-goals (MVP)

- Multi-person supporter dashboards (one seat follows one person; schema allows many — UI is a fast-follow).
- Open two-way messaging between supporter and member (encouragement is one-tap canned only).
- Exposing any craving content to supporters (ever — see Privacy invariants).
- iOS in-app purchase for the supporter tier (web-first; see Billing).
- Dual-role accounts (a Premium recovery user who also pays to support someone) — deferred.

## Decisions log

| # | Decision |
|---|----------|
| Relationship model | Either side may initiate; the **supporter seat is the paid piece** regardless of who pays. |
| Sharing model | **Three presets** chosen *by the member*, per supporter: Cheerleader / Standard / Close support. |
| Interaction | View **+ one-tap canned encouragement**. No open chat (avoids moderation/abuse surface). |
| Alerts & honesty | **Inactivity-only** auto-alerts (can't be gamed by lying) **+ a manual "I need support" button**. Content (craving/mood) never auto-fires. Crisis resources always attached. |
| Who pays | **Supporter subscribes directly** ($7.99/mo). Member shares for free. |
| Cardinality | A member may have **many supporters**; each supporter seat follows **one** member. Schema is many-to-many for a later multi-person UI. |
| Architecture | **Dedicated supporter module** mirroring the existing court-compliance pattern + a new `supporter` subscription tier. |
| Craving content | **No preset ever surfaces craving content** to a supporter (overrides the initial Q2 sketch; protects check-in honesty). |
| Path B onboarding | An invited brand-new member hits the **consent screen first**, completes recovery onboarding after. |
| Decline UX | **Silent** — supporter sees a neutral "pending," never a hard rejection. Pending invites quietly expire. |
| Price | **$7.99/mo (~$59/yr).** |
| Platform scope | **Web-first** for the supporter subscription + dashboard. Member-side controls live in the existing app (free, no IAP issue). |

## Personas

- **Member** — person in recovery, already (or newly) a MyRecoveryPal user. Free. Controls all sharing.
- **Supporter** — parent / spouse / sponsor. Often not a recovery user. Pays $7.99/mo. Sees only what the member's chosen preset reveals.

## Data model

### New subscription tier

Add `'supporter'` to `Subscription.TIER_CHOICES` (alongside `free`, `premium`,
`court`) and an `is_supporter()` helper. Supporter is **not** a superset of
Premium — it is a distinct role with its own price. Because `Subscription` is
`OneToOne` per user, an account is either a recovery user or a paying supporter,
not both (dual-role deferred).

### `SupporterLink` (new model in `supporter_models.py`)

The many-to-many "through" between two `User`s — the spine of the feature.

| field | type | purpose |
|-------|------|---------|
| `member` | FK(User, related_name='supporter_links') | person in recovery whose signals are shared |
| `supporter` | FK(User, related_name='supporting_links') | the viewer; needs active `supporter` sub to view |
| `preset` | char: `cheerleader` / `standard` / `close` | **member-controlled** sharing level |
| `status` | char: `pending` / `active` / `paused` / `revoked` / `declined` | consent state machine |
| `initiated_by` | char: `member` / `supporter` | who started the link |
| `invite_email` | email, nullable | invite target when not yet a user |
| `invite_token` | char, unique, nullable | signup/accept link token |
| `inactivity_threshold_days` | small int, default 3 | only used by `close` |
| `last_inactivity_alert_sent` | datetime, nullable | alert cooldown bookkeeping |
| `consented_at` | datetime, nullable | audit: when member consented |
| `revoked_at` | datetime, nullable | audit |
| `created_at` / `updated_at` | datetime | standard |

Constraints: `unique_together = (member, supporter)`; validation `member != supporter`.

No recovery data is duplicated. The dashboard **reads** existing `DailyCheckIn`
and milestone data; it never copies it.

## Consent & invite flow

A link cannot become `active` until the **member explicitly consents and the
member sets the preset** — never the supporter.

**Path A — Member initiates:**
1. Member: "Invite a supporter" → enters email / picks existing user **and chooses the preset**.
2. Link created `pending`, `initiated_by=member`; the preset choice records member consent.
3. Supporter receives invite; to view past a teaser they start the $7.99/mo subscription.
4. Supporter accepts + pays → link `active`.

**Path B — Supporter initiates (the searched-for "worried parent"):**
1. Supporter signs up, subscribes, → "Invite the person you support" → enters email/username.
2. Link created `pending`, `initiated_by=supporter`; **no preset yet**.
3. Member notified: who wants to support them + exactly what each preset reveals.
4. Member **explicitly consents and picks the preset** (or declines) → link `active`. New members hit this consent screen first, onboard after.

**Lifecycle:** `pending → active → paused ⇄ active`; `active → revoked`; `pending → declined`.
Pause/revoke/decline are one-tap, member-controlled, no supporter approval. Decline is silent.

**Edge cases:**
- Invited person isn't a user yet → `invite_token` email link → signup → consent step.
- Supporter subscription lapses → dashboard gated to "renew to view," member data hidden, link **preserved** (resumes on renewal).
- Cannot support self; duplicate links blocked by `unique_together`.

## Presets & dashboard

The member picks one preset per supporter. Each tier is additive.

| Preset | What the supporter sees |
|--------|-------------------------|
| **Cheerleader** | Days sober + milestone progress, milestone celebrations, encouragement. Pure positive signal. |
| **Standard** | + check-in consistency ("6 of last 7 days") and an **aggregate mood-scalar trend**. No alerts. |
| **Close support** | + inactivity auto-alert + the member's manual "I need support" pings. The paid safety net. |

**No preset surfaces craving content.** Mood trend is an aggregate scalar (not a
raw entry), so its chilling effect is minimal; craving levels and all free-text
(journal, gratitude, check-in notes) are never exposed.

**Dashboard layout (single member, MVP):** header (member + preset badge) →
sobriety hero + next-milestone ring → milestones hit → check-in consistency
(Standard+) → mood-trend sparkline (Standard+) → Close-only alert area →
one-tap encouragement bar → always-on crisis resources (988 / 741741) → a
"journal is never shared" reassurance line.

## Signal aggregation service & alert task (`supporter_service.py`)

- **`get_dashboard_data(link)`** — the single source of the preset→fields mapping
  (one code path to test; no view can over-expose). Gated by `link.preset`. Reads
  `member.get_days_sober()`, existing calendar-based milestone logic, `DailyCheckIn`
  counts (Standard+) and the mood scalar (Standard+), and Close-only pings. Never
  queries journal, craving, or free-text columns.
- **`send_encouragement(link, key)`** — creates a `Notification` (`supporter_encouragement`)
  for the member; rate-limited per link.
- **Manual "I need support"** — member action records a ping on the link, notifies
  Close supporters (`member_support_request`), and surfaces crisis resources to the member.
- **Inactivity alert** — Celery Beat daily task (~6 PM, after the 5 PM check-in
  reminder), mirroring the existing pal-nudge task. For each `active` + `close` link:
  if days since last check-in ≥ `inactivity_threshold_days` and not already alerted
  this gap (`last_inactivity_alert_sent` cooldown), send `Notification` + email via
  the existing `send_email()` / `create_notification()`, and stamp the timestamp.
  Clears when the member checks in so a new gap re-triggers.

## Billing wiring

- Add `'supporter'` tier + `is_supporter()`. Seed `SubscriptionPlan` rows for
  `tier='supporter'` (monthly $7.99, yearly ~$59).
- Stripe: create Product "MyRecoveryPal Supporter" with monthly + yearly prices;
  store `stripe_price_id` on the plans (manual config step, like court).
- Webhook (`payment_views.py`): extend the existing `tier in ['premium','court']`
  mapping to include `'supporter'`.
- Checkout reuses the existing flow; the supporter invite/accept path links to it.
- `supporter_required` decorator gates dashboard views (`request.user.subscription.is_supporter()`
  and active). Lapsed → "renew to view." Pre-subscribe → value-prop + subscribe CTA, no data.
- **Web-first:** supporter subscription + dashboard are web-only for MVP. iOS IAP
  for the supporter tier is future work. The member-side controls ship in the
  existing app (web + iOS) since they are free.

## Notifications (new types)

`supporter_request` (invite/consent prompt), `supporter_joined` /
`supporter_consented` (confirmation), `supporter_encouragement` (to member),
`member_support_request` (to Close supporters), `member_inactive` (inactivity alert).

## Privacy & safety invariants

- Journal entries are never shared (existing platform rule, unchanged).
- Craving content and all check-in free-text/gratitude are never exposed to any supporter at any preset.
- A link only transmits data while `status='active'`; consent is explicit and member-revocable at any time.
- Every alert, dashboard, and support ping shows crisis resources (988 Lifeline, text 741741).
- No medical advice; alerts use supportive, non-clinical framing.

## Error handling & edge cases

- Invite to an email that later registers → token binds the new account to the pending link.
- Member revokes → supporter dashboard goes dark immediately; supporter keeps their subscription (may support someone else later).
- Supporter cancels/lapses → links preserved and dormant; resume on renewal.
- Rate-limit encouragement and manual support pings to prevent spam.
- Inactivity task is idempotent per gap via `last_inactivity_alert_sent`.

## Testing strategy

- **Unit:** `get_dashboard_data` returns exactly the allowed fields for each preset; asserts craving/journal/free-text never present at any preset (the critical privacy test).
- **Unit:** consent state machine transitions (both initiation paths, decline, pause, revoke, lapse).
- **Unit:** inactivity task fires at threshold, respects cooldown, resets on check-in.
- **Integration:** Path A and Path B end-to-end to `active`; supporter sub gating; lapse → renew gate.
- **Integration:** Stripe webhook maps the supporter price to `tier='supporter'`.

## Files

**New (mirroring the court pattern):** `apps/accounts/supporter_models.py`,
`supporter_views.py`, `supporter_service.py`, `supporter_forms.py`,
`apps/accounts/decorators.py::supporter_required`, supporter templates, a Celery
task for inactivity alerts, and a migration for `SupporterLink` + the new tier.

**Changed:** `payment_models.py` (`TIER_CHOICES` + `is_supporter()`),
`payment_views.py` (webhook tier mapping + checkout context), URLs, notification
type choices, member-side share/"I need support" UI, pricing page.

## Out of scope / future work

- Multi-person supporter dashboard (sponsor with several sponsees).
- iOS IAP for the supporter tier (RevenueCat product).
- Open two-way messaging.
- Dual-role accounts (recovery user who also supports).
- Gifting a supporter seat (the recovery user covering the cost).
