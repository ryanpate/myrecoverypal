# Revenue Plan — Phase 1 & 2: Fix the Funnel + Reprice

**Date:** 2026-06-15
**Goal:** Convert the first-ever paying users and lift price to market. Target: first paid users within 2 weeks; repriced and live within 4 weeks.
**Context:** 244 users, $0 revenue, 0 paid. Four tiers exist in code (Free / Premium $4.99–29.99 / Court $19.99–179 / Supporter $7.99). The entire trial→nudge→pricing→checkout funnel is built and scheduled. $0 means the leak is at the **payment step or trial config**, not missing features.

---

## Root-Cause Diagnosis (from code audit)

1. **No-card auto-trial.** Every signup gets `tier='premium', status='trialing'` for 14 days with **no card on file** (`signals.py:34`). It silently expires to free (`expire_ended_trials`). No payment method is ever captured → conversion depends entirely on the user re-entering the funnel and typing a card, which almost no one does. Card-required trials are why health/fitness apps hit 35% trial-to-paid.
2. **Premium Stripe price IDs are hardcoded in a migration** (`0023_seed_subscription_plans.py`: `price_1T7NmL...`, `price_1T7NmM...`). These must be confirmed **live-mode** prices matching the prod `STRIPE_SECRET_KEY`. A test/live mismatch throws "No such price" → silent JSON error → $0. **Prime suspect.**
3. **iOS IAP path unverified.** Most traffic is mobile/social. If RevenueCat products aren't approved/configured, mobile users literally cannot pay. **Second suspect.**
4. **Underpriced.** $29.99/yr vs Reframe $99.99, I Am Sober $39.99, Sunnyside $99. Caps revenue and signals low value.

---

## Phase 1 — Fix the Leak (Week 1–2)

### 1.1 Prove the web payment path end-to-end *(do this first — it may be the whole problem)*
- In prod, confirm `SubscriptionPlan` rows for `tier='premium'` are `is_active=True` and their `stripe_price_id` resolves against the **live** Stripe key:
  `railway run -- python3 manage.py shell` → `stripe.Price.retrieve('price_1T7NmL6oOlORkbTyymje0SAM')`.
- If it throws "No such price": the seeded IDs are test-mode. Create live prices, update the `SubscriptionPlan` rows (build a `setup_premium_stripe` command mirroring `setup_court_stripe` so it's idempotent and repeatable).
- Buy Premium on the live site with a real card. **Verify:** `Subscription.status='active'`, `tier='premium'`, a `Transaction` row exists, webhook `checkout.session.completed` fired.

### 1.2 Prove the iOS IAP path end-to-end
- Confirm RevenueCat products + entitlements are approved in App Store Connect and mapped in RevenueCat.
- Buy Premium inside the iOS app (sandbox tester). **Verify:** `MRPIAP.isPremium` flips true and the backend subscription record updates.
- If broken, this is likely the larger leak given mobile-heavy traffic.

### 1.3 Confirm the Celery Beat tasks actually run in prod
- Check Railway `celery-worker` logs for `send_trial_ending_notifications`, `send_premium_trial_nudge`, `expire_ended_trials` daily runs. **Verify:** non-zero `sent` counts in logs.

### 1.4 Switch to a card-required trial (biggest conversion lever in Phase 1)
- Change signup so the 14-day trial is started **through Stripe Checkout with a card captured** (Stripe `trial_period_days=14`, which `create_checkout_session` already supports), OR keep the no-card trial but add a prominent "Add payment to keep Premium" step in the trial-ending email that goes straight to a one-click checkout.
- Decision needed: card-at-signup (higher conversion, slightly lower signup rate) vs card-at-trial-end (current, near-zero conversion). **Recommend card-at-signup** given $0 baseline.
- **Verify:** new signups create a Stripe customer with a payment method; trial auto-converts unless cancelled.

### 1.5 Win-back flow
- Add a task: on cancellation/expiry, send a 50%-off coupon within 24h (Stripe coupon + email). Recovers 10–15% of churned users.
- **Verify:** cancelling triggers the coupon email; redeeming it reactivates at the discount.

---

## Phase 2 — Reprice to Market (Week 2–4)

### 2.1 New Stripe prices
- Create live prices: **Premium $9.99/mo, $59.99/yr.** Keep old prices archived (grandfather = moot, zero current payers).
- Update `SubscriptionPlan` rows via the new `setup_premium_stripe --commit`.

### 2.2 Update every hardcoded price string
- `pricing.html`: line ~139 ($4.99), ~421 ($4.99/$29.99 footer), ~212 ("Save $22/year"), AI-coach value line ~143.
- `tasks.py` trial-ending email: line ~821 and ~842 ($4.99 → $9.99, add annual CTA).
- Welcome emails (`welcome_day_*.html`) and any blog/landing CTA referencing $4.99/$29.99.
- iOS: update RevenueCat / App Store Connect product prices to match.
- **Verify:** grep for `4.99` and `29.99` across `apps/`, `templates/`, `static/` returns only changelog/archive hits.

### 2.3 Lead with annual, framed against therapy
- Make the **annual** plan the default-highlighted card: "$59.99/yr — less than one therapy copay." Reuse the existing therapy-cost comparison as the hero.
- Annual plans are 60% of health-app revenue and lock in LTV.

### 2.4 Harden a second paywall as an upgrade trigger
- Today only the AI Coach gates (3 free msgs). Add one more high-value gate with an inline upgrade prompt: 90-day analytics/charts is the strongest candidate (already premium-gated in `views.py` — make the upgrade CTA prominent, not a silent block).

---

## Success Criteria
- [ ] A real card completes Premium checkout on web → active subscription. (1.1)
- [ ] A real purchase completes Premium on iOS → isPremium true. (1.2)
- [ ] Trial-conversion tasks confirmed running in prod logs. (1.3)
- [ ] Card captured at trial start (or one-click checkout at trial end). (1.4)
- [ ] Win-back coupon flow live. (1.5)
- [ ] Premium repriced to $9.99/$59.99 everywhere, web + iOS. (2.1–2.2)
- [ ] Annual is the highlighted default with therapy framing. (2.3)
- [ ] **First paying customer recorded.** ← the real metric

## Out of scope (later phases)
- Phase 3: activate Court Compliance + Supporter tiers (Stripe `--commit` + surfacing + court marketing).
- Phase 4: B2B treatment-center aftercare ($200–500/mo/facility) and court/probation bulk sales — the path to "significant" revenue.

## Sources (competitor economics)
- Reframe $99.99/yr, ~$400k/mo, $14M raised — PitchBook / ChoosingTherapy
- I Am Sober $9.99/mo, $39.99/yr — ChoosingTherapy
- Sunnyside $12/mo, $99/yr + naltrexone $99/mo — ChoosingTherapy
- Health/fitness 35% trial-to-paid, annual = 60% revenue; win-back 10–15% — RevenueCat State of Subscription Apps 2026, Adapty 2026
- Sober-living B2B software $65–199/mo/facility — Sober Living App / SobrietyHub
