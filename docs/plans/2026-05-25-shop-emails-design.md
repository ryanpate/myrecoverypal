# Weekly Shop Email + Milestone Celebration Email — Design

**Date:** 2026-05-25
**Status:** Approved direction; implementation plan to follow
**Audit reference:** Conversion audit Priority #3 — "Weekly Shop email + milestone-coupon trigger." The audit's stated goal is to activate the dormant 218 users with regular shop touchpoints and high-intent milestone moments. Currently the shop gets ~0 internal traffic outside the in-app store page.

---

## Goal

Ship two new marketing emails:

1. **Weekly Shop Digest** — every Friday 10am UTC, send all opted-in users a summary of featured products in the Recovery Shop.
2. **Milestone Celebration Email** — when a user hits 7, 30, 90, 180, 365 days sober (then yearly), send a celebratory email featuring one curated product.

Both share infrastructure: a User-level opt-out preference, a base email template, an unsubscribe view, and the `apps.accounts.email_service.send_email()` delivery layer.

## Why this change

- The 218 existing users get zero shop-related touch points outside the in-app `/store/` page (verified: shop has 0 organic discovery, $0 sales)
- Milestones are the highest-emotion moments in the user lifecycle — perfect for low-friction product surfacing (e.g., "You hit 90 days. Mark it with a milestone journal.")
- Email infrastructure is already operational (Resend HTTP API + SMTP fallback, Celery Beat schedule, existing welcome series proves deliverability is healthy)

## Decisions locked from brainstorm

| Topic | Decision |
|---|---|
| Coupon mechanism | **No coupons.** The Recovery Shop is off-site (Printify Pop-Up + Amazon KDP). Coupons would require manual Printify dashboard setup per code. Drop entirely — emails feature products, no discount codes. |
| Recipients | **All Users, opt-out by default.** `User.marketing_emails_enabled = True` field, every email has unsubscribe link. Aligns with CAN-SPAM. |
| Scope | **One PR** with both emails together. Shared infra (model field, base template, unsubscribe view) justifies bundling. |
| Email style | **Hybrid (Option C).** Personal note + one featured product with image + bulleted list of others. Same template works for slow weeks (1 product) and busy weeks (3+). |
| Milestones triggered | **7, 30, 90, 180, 365 days, then yearly** (730, 1095, ...). Skip 1/14/60 — too frequent, would feel patronizing. Five emails year 1, one per year after. |
| Featured product selection (weekly) | **Top 3 by `is_featured=True`** ordered by `-updated_at`. Falls back to newest `is_active=True` products if fewer than 3 featured. Managed via existing Django admin `is_featured` toggle — no new admin UI. |
| Product mapping (milestone) | **One product per milestone-bucket.** Mapping is a small dict in code (e.g., 30/90 days → Milestone Journals; 365+ → Apparel). Easy to tune. |
| Unsubscribe token | **Signed URL, no expiry.** `django.core.signing.dumps({'user_id': X, 'kind': 'marketing'})`. Industry standard. |

## Architecture

### Model changes (one migration)

`apps/accounts/models.py` — add field to `User`:
```python
marketing_emails_enabled = models.BooleanField(
    default=True,
    help_text='Receive weekly shop and milestone celebration emails.'
)
```

`apps/store/models.py` — new model:
```python
class MilestoneEmailSent(models.Model):
    """Tracks which milestone celebration emails have been sent to each user.
    Prevents double-sends if the Celery task is retried."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='milestone_emails_sent')
    milestone_days = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'milestone_days']
        indexes = [models.Index(fields=['user', 'milestone_days'])]
```

### New files

| Path | Responsibility |
|---|---|
| `apps/store/email_service.py` | Pure helper functions: `select_featured_products()`, `select_milestone_product(milestone_days)`, `find_users_hitting_milestone_today()`, `send_weekly_shop_digest()`, `send_milestone_celebration_email(user, milestone_days)` |
| `apps/store/tasks.py` | Two Celery tasks: `weekly_shop_digest_task()` and `daily_milestone_celebration_task()` |
| `apps/store/templates/store/emails/_shop_email_base.html` | Shared layout (header, footer, unsubscribe link, hybrid-style two-column structure) |
| `apps/store/templates/store/emails/weekly_digest.html` | Extends base — featured product + "Also new" list |
| `apps/store/templates/store/emails/milestone_celebration.html` | Extends base — milestone-specific copy + one product highlight |
| `apps/accounts/email_views.py` | `unsubscribe_marketing(request, token)` view |
| `apps/accounts/templates/accounts/email_unsubscribed.html` | Confirmation page after unsubscribe |
| `apps/store/tests_shop_emails.py` | Test suite (~12 tests) |
| `apps/accounts/migrations/0037_user_marketing_emails_enabled.py` | Migration for the new User field |
| `apps/store/migrations/0XXX_milestone_email_sent.py` | Migration for the new model (number depends on last store migration) |

### Modified files

| Path | Change |
|---|---|
| `recovery_hub/settings.py` | Add two entries to `CELERY_BEAT_SCHEDULE` |
| `recovery_hub/urls.py` | Mount `/email/unsubscribe/<str:token>/` route |
| `apps/accounts/templates/accounts/edit_profile.html` | Add `marketing_emails_enabled` checkbox under existing Privacy section |
| `apps/accounts/forms.py` | Add `marketing_emails_enabled` to `UserProfileForm` (or wherever profile editing lives) |

## Email template (hybrid style)

### Base template (`_shop_email_base.html`)

```
┌──────────────────────────────────────────────────┐
│ [MyRecoveryPal logo, link to /]                  │
│                                                   │
│ {% block content %}{% endblock %}                │
│                                                   │
│ ─────────────────────────────────────             │
│ You're receiving this because you have an        │
│ account at MyRecoveryPal.                         │
│ {{ unsubscribe_url }} · {{ profile_settings_url }}│
└──────────────────────────────────────────────────┘
```

### Weekly digest (`weekly_digest.html`)

- Subject: `New in the Recovery Shop this week`
- Personal opening: `Hey {{ first_name|default:"Friend" }},`
- One-sentence intro
- Featured product: image (300×300), name, one-sentence "why I picked this" copy, price, big "[Get one →]" CTA button → product's `external_url`
- "Also new:" — bulleted list of remaining products (`• Name — $price [link]`)
- Closing line + "Shop all →" link to `/store/`

### Milestone celebration (`milestone_celebration.html`)

- Subject: `You hit {{ milestone_days }} days. We see you.`
- Opening: `Hey {{ first_name|default:"Friend" }},`
- Milestone-specific message (varies by `milestone_days`):
  - 7: "First week sober. The hardest stretch — and you did it."
  - 30: "A full month. The brain chemistry shifts started about 5 days ago."
  - 90: "90 days. Strong evidence the change is sticking."
  - 180: "Half a year. Most people who relapse never get this far."
  - 365: "One year. Today is the anniversary."
  - 730+: "{{ years }} years sober. That's a life."
- One featured product (from milestone → product mapping)
- Closing: "Whatever's next, we're here."

### Hybrid layout HTML (per email)

Each email template is ~120 lines of inline-CSS HTML (email-client safe), no JavaScript, no external CSS files (most clients strip them). Uses table-based layout for Outlook compatibility (industry standard for HTML email).

## Celery schedule additions

```python
# settings.py — add to CELERY_BEAT_SCHEDULE
'send-weekly-shop-digest': {
    'task': 'apps.store.tasks.weekly_shop_digest_task',
    'schedule': crontab(hour=10, minute=0, day_of_week=5),  # Friday 10am UTC
},
'send-milestone-celebrations': {
    'task': 'apps.store.tasks.daily_milestone_celebration_task',
    'schedule': crontab(hour=9, minute=0),  # Daily 9am UTC
},
```

Friday 10am UTC = 5am EST / 6am EDT / 2am PST. Send before US users wake up; lands at top of their inbox at work-start. The 9am UTC milestone task hits users at 5am EDT — same logic.

## Milestone trigger logic

`find_users_hitting_milestone_today()` returns a queryset of `User` objects whose `sobriety_date` makes today exactly N days into recovery, where N is one of `[7, 30, 90, 180, 365]` OR a multiple of 365 (so 730, 1095, etc.).

```python
def find_users_hitting_milestone_today():
    """Return [(user, milestone_days), ...] for users hitting a milestone today."""
    from datetime import date
    from django.contrib.auth import get_user_model
    User = get_user_model()

    today = date.today()
    fixed_milestones = [7, 30, 90, 180, 365]
    results = []

    for user in User.objects.filter(sobriety_date__isnull=False,
                                     marketing_emails_enabled=True,
                                     is_active=True):
        days_sober = (today - user.sobriety_date).days
        is_fixed = days_sober in fixed_milestones
        is_yearly = days_sober > 365 and days_sober % 365 == 0
        if is_fixed or is_yearly:
            # Skip if we already sent this one
            from apps.store.models import MilestoneEmailSent
            if not MilestoneEmailSent.objects.filter(
                user=user, milestone_days=days_sober
            ).exists():
                results.append((user, days_sober))
    return results
```

The 365-multiple check correctly handles leap years per the existing `User.get_milestone_to_celebrate()` precedent.

## Product → milestone mapping

```python
# apps/store/email_service.py
MILESTONE_PRODUCT_CATEGORIES = {
    7:   'stickers',       # small, low-commitment first-week marker
    30:  'journals',       # journal for the first month of reflection
    90:  'journals',
    180: 'apparel',
    365: 'apparel',
    # Yearly anniversaries (730+) → apparel by default
}

def select_milestone_product(milestone_days: int):
    """Returns a single Product for a milestone email, or None if no
    suitable product exists. Falls back to any featured product."""
    from apps.store.models import Product, Category
    if milestone_days >= 365 and milestone_days % 365 == 0:
        category_slug = 'apparel'  # year anniversaries
    else:
        category_slug = MILESTONE_PRODUCT_CATEGORIES.get(milestone_days, 'apparel')

    product = (
        Product.objects.filter(is_active=True, category__slug=category_slug)
        .order_by('-is_featured', '-updated_at')
        .first()
    )
    if product:
        return product
    # Fallback — any featured/active product
    return Product.objects.filter(is_active=True).order_by('-is_featured', '-updated_at').first()
```

## Unsubscribe view

```python
# apps/accounts/email_views.py
from django.core import signing
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model

def unsubscribe_marketing(request, token):
    """One-click unsubscribe from marketing emails.
    Token format: signing.dumps({'user_id': X, 'kind': 'marketing'})"""
    try:
        data = signing.loads(token)
    except signing.BadSignature:
        return render(request, '404.html', status=404)

    if data.get('kind') != 'marketing':
        return render(request, '404.html', status=404)

    User = get_user_model()
    user = get_object_or_404(User, pk=data['user_id'])
    user.marketing_emails_enabled = False
    user.save(update_fields=['marketing_emails_enabled'])
    return render(request, 'accounts/email_unsubscribed.html', {'user': user})
```

URL mount in `recovery_hub/urls.py`:
```python
path('email/unsubscribe/<str:token>/', unsubscribe_marketing, name='unsubscribe_marketing'),
```

Token generation in email service:
```python
def _build_unsubscribe_url(user):
    from django.conf import settings as dj_settings
    from django.core import signing
    from django.urls import reverse
    token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
    return f"{dj_settings.SITE_URL.rstrip('/')}{reverse('unsubscribe_marketing', args=[token])}"
```

`SITE_URL` already exists in settings as `https://www.myrecoverypal.com`.

## Profile UI

Edit `apps/accounts/templates/accounts/edit_profile.html` — under existing Privacy section, add one checkbox:

```django
<div class="form-group">
    <label>
        {{ form.marketing_emails_enabled }}
        Send me shop & milestone celebration emails
    </label>
    <small>
        Includes the Friday "New in the Shop" digest and celebration emails
        when you hit a sobriety milestone. You can also unsubscribe from any
        email's footer.
    </small>
</div>
```

`UserProfileForm` (`apps/accounts/forms.py`) — add `'marketing_emails_enabled'` to its `Meta.fields` tuple.

## Test coverage (~12 tests in `apps/store/tests_shop_emails.py`)

| Test class | Test | Asserts |
|---|---|---|
| `MarketingFieldTest` | `test_field_defaults_to_true` | New users default to opted-in |
| | `test_field_persists_after_save` | Roundtrip save/load |
| `FeaturedProductSelectionTest` | `test_returns_featured_products_first` | `is_featured=True` ordered correctly |
| | `test_falls_back_to_newest_when_no_featured` | Returns newest active when no featured |
| | `test_excludes_inactive_products` | `is_active=False` never returned |
| `MilestoneEligibilityTest` | `test_finds_user_at_exact_milestone` | User with `today - sobriety_date == 30` is returned |
| | `test_skips_user_with_marketing_disabled` | User who opted out is excluded |
| | `test_skips_user_already_emailed` | Existing `MilestoneEmailSent` row prevents re-send |
| | `test_finds_year_anniversaries` | 730/1095/... days work |
| `WeeklyDigestTaskTest` | `test_sends_to_opted_in_users_only` | Mock send_email, assert call count = opted-in users |
| | `test_email_contains_unsubscribe_url` | Body includes signed token URL |
| `MilestoneCelebrationTaskTest` | `test_idempotent_on_rerun` | Second invocation in same day sends 0 emails |
| | `test_creates_milestone_sent_row` | `MilestoneEmailSent` row is created on success |
| `UnsubscribeViewTest` | `test_valid_token_sets_flag_false` | Hitting URL flips `marketing_emails_enabled` to False |
| | `test_invalid_token_returns_404` | Tampered token returns 404 |

## Success criteria

1. Friday 10am UTC, all 218 (or n active) opted-in users receive the weekly digest with 1–3 product cards
2. When a user hits day 7, 30, 90, 180, or 365 (or yearly anniversary), they receive exactly one celebration email that day
3. Clicking the unsubscribe link in any email flips their flag to False and they receive no further marketing emails
4. Profile page lets them re-enable from the toggle
5. Re-running the Celery task does not double-send emails (idempotent)
6. All ~12 tests pass, full `apps.store` suite remains green
7. No regressions in `apps.accounts` test suite

## Out of scope (explicit non-goals)

- ❌ Coupon codes (per Q1 decision — shop is off-site)
- ❌ Email open/click tracking (Resend dashboard handles this; we don't need our own)
- ❌ A/B testing infrastructure
- ❌ Newsletter Subscriber model integration (separate audience, intentionally untouched)
- ❌ Changes to existing welcome series, check-in reminders, weekly social digest, premium trial nudge — those are transactional/lifecycle emails, separate from marketing
- ❌ Per-email-type preference granularity (one toggle controls both shop emails; finer-grained controls are a future improvement)
- ❌ Re-subscribe flow from email link (user can re-enable via profile; that's enough for v1)
- ❌ HTML preview view for admins (Resend dashboard shows sent emails)

## Implementation hand-off notes

For the writing-plans skill:

- TDD strictly: every test in the table above gets written first, run-fail-confirmed, implemented, run-pass-confirmed
- Two migrations: 0037 on accounts (User field) + new one on store (MilestoneEmailSent model)
- Both migrations are pure schema changes — no data backfill needed
- Estimated effort: 4–5 days solo dev (~1 day per major component: model + email service + tasks + templates + tests)
- No env vars, no Stripe touched, no Printify integration, no new Python dependencies
- Resend API key already in Railway env vars

## Open questions

None. All decisions locked.
