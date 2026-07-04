# Revenue Roadmap — Master Phased Plan

**Date:** 2026-07-03
**Owner:** Ryan (solo dev)
**Status of business:** ~260 users, $0 revenue, 0 paying customers.
**Goal:** Get to first paying customers, then to durable monthly recurring revenue, in ordered phases where each phase is shippable on its own and unblocks the next.

> **How to use this doc:** This is the master roadmap. Each phase lists an objective, why it's sequenced where it is, concrete tasks (checkbox-tracked), effort, and the single success metric that says "phase done." Code-heavy phases point to a detailed sub-plan to spin up before building. Do phases in order — later phases assume earlier ones shipped.

---

## The core thesis (why this order)

Three facts from the code audit + competitive research drive the sequence:

1. **$0 is probably plumbing, not strategy.** The June 15 audit found the whole trial→nudge→pricing→checkout funnel is *built*, but signups get a **no-card auto-trial** and the Premium Stripe price IDs may be **test-mode** (→ silent "No such price" → $0). **You cannot earn a dollar until a real card can complete a real checkout.** That's Phase 0 and nothing else matters until it's green.
2. **You can't monetize users who leave in week 1.** Retention is ~6% week-1. Freemium converts ~2.1% of *retained* users. At 260 users that's ~5 theoretical payers — the base is too small and too leaky. The single-player daily loop (counter + pledge) is what fixes retention and grows the denominator. That's why the retention engine sits early, before chasing conversion tricks.
3. **One segment pays regardless of the recovery-is-free ethos: court-ordered users.** Legal mandate overrides poverty and stigma. Soberlink charges $150–290/mo for court-admissible monitoring; you're priced at $19.99. Court is your realest near-term revenue and your sharpest differentiator — so it gets its own phase and a price increase.

**Sequencing in one line:** Make payment work → reprice → stop the leak (retention) → own the court niche → turn on zero-marginal-cost revenue → widen the market → B2B.

---

## Existing sub-plans this roadmap absorbs

- `docs/plans/2026-06-15-revenue-phase1-fix-funnel-reprice.md` — detailed Phase 0 + Phase 1 tasks (payment-path verification, card-required trial, reprice). **This roadmap's Phase 0 and Phase 1 are that plan; do not rewrite it, execute it.**
- `docs/plans/2026-02-19-revenue-implementation-plan.md` — original funnel build (mostly shipped; historical reference).
- `docs/plans/2026-06-12-anchor-conversion-engine-plan.md` — AI-coach upgrade prompts (shipped; reference for paywall placement).

---

## Phase 0 — Make payment physically possible *(Week 1 — BLOCKER)*

**Objective:** A real card completes a real Premium purchase on web AND iOS. Until this is proven, every other revenue task is worthless.

**Why first:** If checkout is broken, you've been selling to a locked door. This is the single highest-probability explanation for $0.

**Tasks** (detail in `2026-06-15-revenue-phase1-fix-funnel-reprice.md` §1.1–1.3):
- [ ] Confirm prod `SubscriptionPlan` rows for `tier='premium'` are `is_active=True` and their `stripe_price_id` resolves against the **live** Stripe key (`stripe.Price.retrieve(...)` in `railway run` shell).
- [ ] If IDs are test-mode: create live prices, build an idempotent `setup_premium_stripe` mgmt command (mirror `setup_court_stripe`), update the rows.
- [ ] Buy Premium on the live site with a real card. Verify `Subscription.status='active'`, a `Transaction` row exists, `checkout.session.completed` webhook fired.
- [ ] Verify iOS IAP: RevenueCat products + entitlements approved in App Store Connect and mapped; buy Premium in-app (sandbox); `MRPIAP.isPremium` flips true and backend record updates.
- [ ] Confirm Celery Beat tasks run in prod (`send_trial_ending_notifications`, `send_premium_trial_nudge`, `expire_ended_trials`) — non-zero `sent` counts in `celery-worker` logs.

**Effort:** 2–4 days (mostly verification; fix only if broken).
**Success metric:** ✅ One real card = one active subscription, web + iOS. (Test purchases you can refund yourself count.)

### Phase 0 RESULTS — verified 2026-07-03 (prod)

**The original "test-mode price IDs" hypothesis is FALSE. The payment path is correctly configured and functional. $0 is a funnel/trial-design problem, not a broken door.**

Diagnostics run against `web`/production via `railway ssh`:
- Stripe is in **LIVE** mode. All paid tiers resolve to valid live prices:
  - Premium `$9.99/mo` (`price_1TiiVi…QUwO`) + `$59.99/yr` (`…eTF7`) — VALID
  - Court `$19.99/mo` (`price_1ThUb9…bx9o`) + `$179/yr` (`…cF8v`) — VALID (the CLAUDE.md "`mailto:` placeholder / Stripe TODO" note is **stale**; court billing is fully wired)
  - Supporter `$7.99/mo` + `$69/yr` — VALID
  - All `SubscriptionPlan` rows in sync (`changes=none`).
- Prod data: 262 users → 219 free/active, 29 free/expired, **8 premium in no-card trial**, 1 premium + 1 court "active" **but flipped manually** (no Stripe sub id, no transaction — comp/testing).
- **Stripe subscriptions ever created: 0. Transactions: 0. Revenue collected ever: $0.**
- **13 live Checkout Sessions created over ~8 months — 100% `expired`/`unpaid` (0 completed). 1 PaymentIntent, `canceled`.** Sessions are user-abandonment, not system errors → the path works; nobody finishes it.
- Only 3 users ever reached the "Stripe customer created" stage (2 are Ryan, 1 real user `LiviJane`); none has a subscription id.

**Root cause (confirmed in code):** the 14-day Premium trial is granted at signup with **no card** (`signals.py:34`). Users get full Premium during their most-engaged days for free, so there's no reason to enter payment; the trial then silently expires. Combined with ~6% week-1 retention, almost nobody is still around at trial-end to convert, so the checkout page is barely visited (13 attempts in 8 months) and converts 0%.

**Redirect:** Phase 0's fix is not "repair the config" (it's fine) — it's the **card-required-trial decision (Phase 1 §1.4)** plus **retention (Phase 2)**, because a card trial only converts users who stick around. Remaining manual step: complete one real-card purchase to prove end-to-end (needs a human + card; sessions expiring-unpaid already strongly imply the path is sound).

---

## Phase 1 — Reprice to market + card-required trial *(Week 1–3)*

**Objective:** Stop underpricing and stop leaking trials. Move to annual-first pricing framed against therapy cost, and capture a card at trial start.

**Why here:** Cheap to do, directly multiplies revenue-per-payer, and the card-required trial is the biggest single conversion lever (health/fitness card-trials hit 35–40% trial-to-paid vs near-zero for no-card).

**Tasks** (detail in `2026-06-15...` §1.4–1.5, §2):
- [ ] Switch signup to a **card-required 14-day trial** via Stripe Checkout `trial_period_days=14` (already supported by `create_checkout_session`). Recommend card-at-signup given the $0 baseline.
- [ ] Create live prices **Premium $9.99/mo, $59.99/yr**; archive old $4.99/$29.99. Update rows via `setup_premium_stripe --commit`.
- [ ] Replace every hardcoded price string: `pricing.html`, `tasks.py` trial-ending email, `welcome_day_*.html`, blog/landing CTAs, iOS RevenueCat/ASC. Verify `grep -r '4.99\|29.99'` returns only archive/changelog hits.
- [ ] Make the **annual** card the highlighted default: "$59.99/yr — less than one therapy copay." Reuse existing therapy-cost hero.
- [ ] Win-back flow: on cancel/expiry, auto-send a 50%-off Stripe coupon within 24h (recovers 10–15%).
- [ ] Add one more prominent upgrade gate: 90-day analytics/charts already premium-gated in `views.py` — make the CTA loud, not a silent block.

**Effort:** 3–5 days.
**Success metric:** ✅ First paying customer recorded, at the new price, with card captured at trial start.

---

## Phase 2 — Retention engine: the single-player daily loop *(Week 2–5)*

> **DECISION 2026-07-03:** Do Phase 2 **before** Phase 1's card-required-trial change. Phase 0 proved the payment path works and that the binding constraint is retention (~6% week-1) — a card trial only converts users who are still around at trial-end, and today almost none are. Grow the denominator first, then monetize it. Phase 1 pricing/reprice work is already largely shipped (Premium is live at $9.99/$59.99); the remaining Phase 1 item (card-at-signup) waits until retention lifts.

**Objective:** Fix the ~6% week-1 retention by making the app valuable on day one for a user with *nobody else online*. This grows the paying denominator — the real reason revenue is stuck.

**Why here:** Conversion tricks are pointless if users leave. The category winners (I Am Sober 12M downloads, Nomo 4.93★) retain on single-player mechanics: a live-ticking streak the user emotionally *owns* + a daily re-commitment ritual. You already have a counter and check-in — this phase adds the ritual and makes the solo experience the front door.

**Spin up detailed sub-plan first:** `docs/plans/2026-07-XX-daily-pledge-and-solo-home.md`

**Tasks:**
- [ ] **Daily pledge** (highest-ROI feature in the whole roadmap). On the progress home, a morning re-commitment tied to the user's own photo + their reason-for-quitting, re-affirmed each day, feeding the streak. Build on the existing `DailyCheckIn`. This is the mechanic users say they "look forward to."
- [ ] Make the **counter + streak + pledge** the unmistakable hero of the post-login home and the marketing landing page — demote the social feed to one-tap-away (nav already does this post-login; fix the *marketing* + first-run framing).
- [ ] Reframe the landing headline away from community-you-can't-yet-deliver toward the solo tools (counter, streak, pledge, Anchor). (See `2026-05-24-hero-rewrite.md` for the rewrite pattern.)
- [ ] Tangible-progress rendering on home: money saved, hours reclaimed, next-milestone token (you already compute money-saved in the sobriety calculator — reuse it).

**Effort:** 1–2 weeks.
**Success metric:** ✅ Week-1 retention measurably up (target ≥15% from ~6%) in analytics over the following 30 days.

---

## Phase 3 — Own "court-ordered recovery" *(Week 4–8)*

**Objective:** Turn the Court Compliance tier into your primary near-term revenue line and your defensible differentiator. Raise the price, finish the billing, and market to the *concentrated referral sources* (probation officers, DUI classes, drug courts).

**Why here:** This is the one audience whose willingness-to-pay survives the "recovery is free" ethos and early-recovery poverty, because the alternative is a failed compliance check or jail. Comparable services (Soberlink) charge $150–290/mo. You're at $19.99 with the product mostly built.

**Tasks:**
- [ ] **Finish Court Stripe wiring** (CLAUDE.md flags it as a `mailto:` placeholder — the one tier people will pay for currently can't take money). Seed `SubscriptionPlan` rows for `tier='court'`, wire `accounts:checkout`, map court price IDs in the webhook handler. (Detail: extend `setup_court_stripe --commit`.)
- [ ] **Raise Court to $29.99/mo** (annual ~$269/yr). You are priced ~10x below comparables for a legally-mandated need — test the increase on new signups.
- [ ] Verify the full court flow end-to-end with a real card: subscribe → log attendance → generate tamper-evident PDF → email-to-PO → public verify URL.
- [ ] **Court-ordered SEO landing page** hardened around high-intent, low-competition queries: "court-ordered AA/NA attendance tracker," "proof of meeting attendance for probation," "DUI class attendance report." (You already have `/court-ordered-meeting-tracker/` — expand + internal-link it.)
- [ ] **Referral-source outreach kit** (manual, no code): one-page PDF for probation officers / public defenders / drug-court coordinators explaining the verify URL. Target a handful of POs, not millions of consumers — this is the distribution wedge.

**Effort:** 3–5 days code + ongoing outreach.
**Success metric:** ✅ First court-tier paying customer, and a repeatable outreach message that a PO has responded to.

---

## Phase 4 — Zero-marginal-cost revenue that scales with traffic *(Week 6–10)*

**Objective:** Turn on revenue that doesn't depend on growing headcount — ~100%-margin digital goods and affiliate — gated mainly by the organic-search gap.

**Why here:** These scale with *traffic*, not user count, so they compound as SEO improves. Low effort, high margin.

**Tasks:**
- [ ] **Digital milestone badges as IAP** (~100% margin) leveraging the existing badge creator. Sell premium/animated milestone badges and shareable milestone cards. (Physical engraved coins sell $20–25 on ~$1–2 COGS but require fulfillment — defer; digital first.)
- [ ] **Reactivate the BetterHelp affiliate** by fixing the organic-search gap (0% of traffic is organic search per the analytics). Realistic payout is $10–40/referral (correct the inflated $100–200 figure in CLAUDE.md), but one referral ≈ 20–40 months of a subscription. This is gated by SEO, which the roadmap in CLAUDE.md's SEO section already advances.
- [ ] Ensure affiliate + badge revenue is instrumented in the admin analytics dashboard so you can see it working.

**Effort:** 3–5 days for badges IAP; SEO is ongoing per existing plan.
**Success metric:** ✅ First badge IAP sale AND first tracked affiliate referral.

---

## Phase 5 — Widen the funnel: the "cut back / sober-curious" on-ramp *(Week 8–12)*

**Objective:** Stop repelling the largest, highest-paying segment — people who want to *drink less* but won't call themselves "in recovery." This is the entire business of Reframe (5M downloads, $99/yr) and Sunnyside (600K members, $99/yr).

**Why here:** After the solo core (Phase 2) and payment (Phases 0–1) are solid, opening a moderation on-ramp multiplies the addressable *paying* market without new infrastructure — it's mostly goal-type + copy changes.

**Tasks:**
- [ ] Add a **"cut back" goal type** alongside "quit" at onboarding; let the counter track "days within my limit," not only "days abstinent."
- [ ] Soften identity language on the moderation path ("your journey" vs "your recovery"); keep the abstinence path unchanged for existing users.
- [ ] A/B test a moderation-flavored landing variant targeting "how to cut back on drinking" / "mindful drinking" keywords.
- [ ] (Stretch) A lightweight structured "path" — a short daily-lesson series — since the funded competitors monetize a *program*, not a counter. Start small: a 14-day email/in-app mini-course.

**Effort:** 1–2 weeks.
**Success metric:** ✅ Moderation-path signups convert to trial at a rate comparable to the abstinence path.

---

## Phase 6 — B2B: the path to "significant" revenue *(Month 3+)*

**Objective:** Land recurring contracts an order of magnitude larger than consumer subs. This is where real revenue lives, but it needs a deliberate sales motion, so it's last.

**Why last:** B2B needs a working, retained product to demo (Phases 0–3) and a founder-led sales push. Don't start until the consumer core proves it retains.

**Tasks (mostly sales, some white-label code later):**
- [ ] **Sober-living / treatment-center aftercare licensing** — $65–250/mo per facility (verified comps: Sober Living App, SobrietyHub $65–199/mo). Pitch: "give discharged residents a retention tool." Court + attendance features are the hook.
- [ ] **EAP / employer** — price **per-employee-per-month ($1–5)**, NOT flat (correct CLAUDE.md's "$1,000–5,000/mo flat" framing).
- [ ] **Court/probation bulk** — county drug-court or probation-department seat licenses, building on the Phase 3 court product and PO relationships.
- [ ] Build white-label / org-admin features only *after* a signed pilot — don't spec-build.

**Effort:** Ongoing; sales-led.
**Success metric:** ✅ First signed B2B pilot (one facility or one employer).

---

## Guardrails (apply in every phase)

- **Never paywall the emotional core.** The counter, streak, pledge, and crisis-coach access stay free forever. Winners gate *protection of the asset* (backup, biometric lock, full history, widgets), not the asset. (The iOS WidgetKit widget you already built is a good premium gate — Nomo proves widgets drive upgrades.)
- **Trust is the category's currency.** Tempest died partly from a data-sharing scandal. Your always-private-journal stance is a competitive asset — never dilute it, and never share health data with advertisers.
- **A/B test price changes on new signups only**, optimizing for revenue + 3-month retention, not raw conversion %.
- **Instrument everything** in the admin analytics dashboard so each phase's success metric is observable.

---

## At-a-glance sequence

| Phase | Objective | Effort | Done when |
|------|-----------|--------|-----------|
| 0 | Payment works (web + iOS) | 2–4 d | Real card → active sub |
| 1 | Reprice + card-required trial | 3–5 d | First paying customer |
| 2 | Retention engine (pledge + solo home) | 1–2 wk | Week-1 retention up |
| 3 | Own court-ordered niche (+ reprice, marketing) | 3–5 d + outreach | First court payer |
| 4 | Digital badges IAP + affiliate | 3–5 d | First IAP + referral |
| 5 | "Cut back" moderation on-ramp | 1–2 wk | Moderation path converts |
| 6 | B2B licensing | ongoing | First signed pilot |

**North-star ordering:** Phases 0→1 get you your *first dollar*. Phase 2 makes revenue *durable*. Phase 3 is your *biggest near-term line*. Phases 4–6 are *scale*.
