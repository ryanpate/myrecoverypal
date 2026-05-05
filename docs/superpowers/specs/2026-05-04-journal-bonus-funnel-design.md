# Journal Bonus Funnel — Design

**Date:** 2026-05-04
**URL:** `https://myrecoverypal.com/journal-bonus`
**Promo code:** `PAL90` → 60-day Premium trial
**Source:** QR code on back cover of *90 Day Recovery Journal* (Amazon ASIN B0FR4MPHSW)

---

## Problem

The journal sells 2–5 copies/month with no path back to MyRecoveryPal. Updated covers will ship with a QR pointing to `/journal-bonus`, which currently 404s. Each unscanned QR is a lost trial signup.

## Goal

Give every reader who scans the QR a frictionless path to a 60-day Premium trial that lands them in the social feed.

## Non-goals

- New auth flow (magic links, passwordless, etc.)
- Analytics/tracking changes beyond what the rest of the site already does
- Email automation beyond the existing welcome sequence
- Cover/journal interior changes (handled in Canva)
- Admin UI for managing promos
- Promo expiry windows or usage caps

---

## User flow

```
QR scan → /journal-bonus[?code=PAL90]
  ↓ render landing page (hero, screenshots, FAQ, trust strip)
  ↓ user enters email, clicks "Start free trial"
  ↓ server stashes promo + email in session
  ↓
  ├─ email NOT registered → 302 /accounts/register/?email=<prefilled>
  │     existing register flow runs; on success, register_view
  │     consumes session promo via apply_promo_to_user(); user lands
  │     on social feed with 60-day Premium trial active.
  │
  └─ email IS registered → 302 /accounts/login/?next=/journal-bonus/claim/
        existing login flow runs; on success, /journal-bonus/claim
        view consumes session promo via apply_promo_to_user();
        toast confirms "60 days of Premium added"; redirects to feed.
```

The two URLs (marketing page, claim handler) keep public marketing separate from the login-required action.

## Promo policy

Implemented once in `apply_promo_to_user(user, code) -> (bool, str)`:

| User state | Outcome |
|---|---|
| New user | `tier=premium`, `status=trialing`, `trial_end = now + 60d`, `subscription_source='manual'` |
| Existing free user (no active sub or expired trial) | Same as new user |
| Existing user currently trialing | `trial_end = max(current trial_end, now + 60d)` (don't shorten) |
| Existing user with active paid Stripe/Apple Premium | No-op, returns `(False, "already premium")` |
| User already redeemed this code | No-op, returns `(False, "already redeemed")` |
| Unknown / inactive code | No-op, returns `(False, "invalid code")` |

`subscription_source='manual'` keeps Stripe webhooks from disturbing this row (no `stripe_subscription_id` is set).

---

## Data model

`apps/accounts/payment_models.py`:

```python
class Promo(models.Model):
    code = models.CharField(max_length=32, unique=True, db_index=True)
    trial_days = models.IntegerField()
    description = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promos'

class PromoRedemption(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='promo_redemptions')
    promo = models.ForeignKey(Promo, on_delete=models.CASCADE, related_name='redemptions')
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_redemptions'
        unique_together = ('user', 'promo')
```

`unique_together` is the abuse guard — one redemption per (user, code).

A data migration seeds: `Promo(code='PAL90', trial_days=60, description='90 Day Recovery Journal back cover')`.

---

## Files

**Created**
- `apps/core/templates/core/journal_bonus.html`
- `apps/accounts/migrations/00XX_promo_models.py`
- `apps/accounts/migrations/00XX_seed_pal90.py`
- `apps/accounts/promo_service.py`
- `docs/plans/2026-05-04-journal-bonus-funnel.md` (implementation plan)

**Modified**
- `apps/core/urls.py` — two new paths: `journal-bonus/` and `journal-bonus/claim/`
- `apps/core/views.py` — `JournalBonusView` (GET render + POST email capture) and `journal_bonus_claim` (login-required action)
- `apps/accounts/payment_models.py` — `Promo` and `PromoRedemption` classes
- `apps/accounts/views.py:register_view` — surgical: after `Subscription.objects.get_or_create`, if `request.session.get('journal_promo')` is set, call `apply_promo_to_user` and clear the session key. Both invite-only and standard branches.
- `recovery_hub/sitemaps.py` — add `journal-bonus/` (priority 0.5)

**Not touched**
- `templates/base.html`, navigation, footer
- Existing trial/Stripe/IAP flow
- `signals.py`'s `create_user_subscription` (it's clobbered by `register_view` today; not our problem)
- Pricing page, blog, any iOS code

---

## Page content

**Hero**
- H1: "Welcome — your 60-day Premium trial starts here."
- Subhead: "Thanks for picking up the 90 Day Recovery Journal. This is the community it points to."
- Email input (`type="email"`, `required`, `autocomplete="email"`, `inputmode="email"`)
- Hidden input: `code` (defaults to `PAL90` if no query param present)
- CTA: "Start free trial"
- Small print: "Already have an account? Log in"

**Below fold**
- 3-line product description (community, AI coach, no-ads/no-tracking)
- Two screenshots from repo root: `Home - MyRecoveryPal.png` and `AnchorAICoach.png` (copied or referenced from existing static path used by `index.html`)
- Trust strip: "60-day Premium trial. No credit card required. Cancel anytime."

No testimonial (none stored). No FAQ accordion (the page is intentionally short).

---

## Edge cases

| Case | Behavior |
|---|---|
| Empty / malformed email | HTML5 `required` + `type="email"` block at form layer; server-side re-validates and re-renders with error |
| `?code=BOGUS` query param | `apply_promo_to_user` returns `(False, "invalid code")`; falls back to default registration with no extra trial |
| No promo in session at register time | `register_view` no-op, behaves exactly as today |
| User already logged in on /journal-bonus | Form submission short-circuits to `/journal-bonus/claim/` directly |
| Promo cleared from session between login redirect and claim | `journal_bonus_claim` falls back to `request.GET.get('code')` or default `PAL90` |
| iOS WKWebView / Capacitor | No special handling — page is plain server-rendered HTML, doesn't touch IAP toggles |
| Double-submit (concurrent) | `unique_together` raises `IntegrityError`; wrapped in `try/except` returning `(False, "already redeemed")` |

Out of scope: rate limiting, captcha, analytics events beyond default GA4 pageview.

---

## Testing

**Unit (Django `TestCase`)**
- `test_apply_promo_to_new_free_user_grants_60d_trial`
- `test_apply_promo_extends_existing_trial_only_if_longer`
- `test_apply_promo_skips_active_paid_premium`
- `test_apply_promo_rejects_already_redeemed`
- `test_apply_promo_rejects_inactive_code`

**Integration**
- GET `/journal-bonus/` → 200, page contains form
- POST `/journal-bonus/` with new email → 302 to `/accounts/register/?email=...`
- After register → user has `tier=premium`, `status=trialing`, `trial_end` ≈ `now + 60d`, `PromoRedemption` row exists

**Manual smoke**
- `curl -I https://myrecoverypal.com/journal-bonus` → 200
- Mobile viewport at 375×667 (Chrome devtools or Playwright)
- Existing pages unaffected: `/`, `/accounts/register/`, `/accounts/login/`, `/accounts/dashboard/`

---

## Success criteria

1. `curl -I /journal-bonus` returns 200 in production after deploy.
2. Submitting the form with a new email creates a user, subscription has `tier=premium`/`status=trialing`/`trial_end` ≈ `now + 60d`, and `PromoRedemption` row exists.
3. Submitting with an existing free user's email logs them in and applies the same trial.
4. Submitting with an active paid user's email logs them in but doesn't change their subscription (and shows a "you're already Premium" toast).
5. No regressions on homepage, register, login, dashboard.
6. Page renders without horizontal scroll at 375×667.
