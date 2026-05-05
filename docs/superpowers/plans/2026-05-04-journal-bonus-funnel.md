# Journal Bonus Funnel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public landing page at `/journal-bonus` that captures emails from journal QR-code scanners, routes them through the existing register/login flow, and grants a 60-day Premium trial via a new `Promo` model.

**Architecture:** A two-page flow. `/journal-bonus` is a public marketing page with email capture. Submitting routes new emails to `/accounts/register/` (with email pre-filled) and existing emails to `/accounts/login/?next=/journal-bonus/claim/`. The `journal_bonus_claim` view (login-required) and the existing `register_view` both call a single `apply_promo_to_user(user, code)` helper that holds the policy. Promo state lives in the session between marketing page and authentication.

**Tech Stack:** Django 5.0.10, PostgreSQL, vanilla server-rendered templates extending `base.html`. Existing `Subscription` model already supports `tier='premium'`/`status='trialing'`/`trial_end`. No new JS, no frameworks.

**Spec:** `docs/superpowers/specs/2026-05-04-journal-bonus-funnel-design.md`

---

## File Structure

**Created:**
- `apps/accounts/promo_service.py` — `apply_promo_to_user()` helper
- `apps/accounts/migrations/0030_promo_models.py` — schema for `Promo` + `PromoRedemption`
- `apps/accounts/migrations/0031_seed_pal90.py` — data migration seeding PAL90
- `apps/accounts/test_promo_service.py` — unit tests for the helper
- `apps/core/test_journal_bonus.py` — integration tests for views
- `apps/core/templates/core/journal_bonus.html` — landing page template

**Modified:**
- `apps/accounts/payment_models.py` — add `Promo` and `PromoRedemption` classes
- `apps/core/urls.py` — add two paths for `/journal-bonus/` and `/journal-bonus/claim/`
- `apps/core/views.py` — add `JournalBonusView` (GET + POST) and `journal_bonus_claim` (login-required)
- `apps/accounts/views.py` — surgical patch to `register_view` (apply session promo after subscription is created, both branches)
- `recovery_hub/sitemaps.py` — add `journal-bonus/` entry

---

## Task 1: Add Promo and PromoRedemption models

**Files:**
- Modify: `apps/accounts/payment_models.py` (append at end)
- Create: `apps/accounts/migrations/0030_promo_models.py`

- [ ] **Step 1: Add models to `apps/accounts/payment_models.py`**

Append to the end of the file (after the existing `Invoice` class or last model):

```python
class Promo(models.Model):
    """
    Promotional code that grants a Premium trial extension.
    Used by external funnels (e.g., book QR codes) to seed signups.
    """
    code = models.CharField(max_length=32, unique=True, db_index=True)
    trial_days = models.IntegerField(help_text="Days of Premium trial to grant")
    description = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promos'
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'

    def __str__(self):
        return f"{self.code} ({self.trial_days}d)"


class PromoRedemption(models.Model):
    """
    Records that a user has redeemed a given promo. unique_together
    enforces one redemption per (user, promo) at the database level.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='promo_redemptions'
    )
    promo = models.ForeignKey(
        Promo,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_redemptions'
        unique_together = ('user', 'promo')

    def __str__(self):
        return f"{self.user.username} redeemed {self.promo.code}"
```

- [ ] **Step 2: Generate the migration**

```bash
cd /Users/ryanpate/myrecoverypal && python manage.py makemigrations accounts --name promo_models
```

Expected: creates `apps/accounts/migrations/0030_promo_models.py`. Verify the file exists and contains `CreateModel` operations for both `Promo` and `PromoRedemption`.

- [ ] **Step 3: Apply the migration locally**

```bash
python manage.py migrate accounts
```

Expected output: `Applying accounts.0030_promo_models... OK`

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/payment_models.py apps/accounts/migrations/0030_promo_models.py
git commit -m "feat: add Promo and PromoRedemption models"
```

---

## Task 2: Seed PAL90 via data migration

**Files:**
- Create: `apps/accounts/migrations/0031_seed_pal90.py`

- [ ] **Step 1: Create the data migration**

```bash
python manage.py makemigrations accounts --empty --name seed_pal90
```

This creates an empty migration file. Replace its contents with:

```python
from django.db import migrations


def seed_pal90(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.update_or_create(
        code='PAL90',
        defaults={
            'trial_days': 60,
            'description': '90 Day Recovery Journal back cover',
            'active': True,
        },
    )


def remove_pal90(apps, schema_editor):
    Promo = apps.get_model('accounts', 'Promo')
    Promo.objects.filter(code='PAL90').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0030_promo_models'),
    ]
    operations = [
        migrations.RunPython(seed_pal90, remove_pal90),
    ]
```

- [ ] **Step 2: Apply the migration**

```bash
python manage.py migrate accounts
```

Expected: `Applying accounts.0031_seed_pal90... OK`

- [ ] **Step 3: Verify the row exists**

```bash
python manage.py shell -c "from apps.accounts.payment_models import Promo; p = Promo.objects.get(code='PAL90'); print(p.code, p.trial_days, p.active)"
```

Expected output: `PAL90 60 True`

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/migrations/0031_seed_pal90.py
git commit -m "feat: seed PAL90 promo (60-day Premium trial)"
```

---

## Task 3: Write `apply_promo_to_user` helper (TDD)

**Files:**
- Create: `apps/accounts/test_promo_service.py`
- Create: `apps/accounts/promo_service.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_promo_service.py`:

```python
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Subscription, Promo, PromoRedemption
from apps.accounts.promo_service import apply_promo_to_user

User = get_user_model()


class ApplyPromoTests(TestCase):
    def setUp(self):
        self.promo = Promo.objects.create(
            code='PAL90', trial_days=60, active=True
        )
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='x'
        )
        # The User post_save signal creates a default trialing Subscription.
        # Grab it so tests start from a known state.
        self.sub = self.user.subscription
        self.sub.tier = 'free'
        self.sub.status = 'active'
        self.sub.trial_end = None
        self.sub.subscription_source = 'stripe'
        self.sub.save()

    def test_applies_60_day_trial_to_free_user(self):
        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.assertEqual(msg, 'applied')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tier, 'premium')
        self.assertEqual(self.sub.status, 'trialing')
        self.assertEqual(self.sub.subscription_source, 'manual')
        # trial_end should be ~60 days from now (within 1 minute tolerance)
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((self.sub.trial_end - expected).total_seconds()), 60)
        # PromoRedemption row created
        self.assertTrue(
            PromoRedemption.objects.filter(user=self.user, promo=self.promo).exists()
        )

    def test_extends_existing_trial_only_if_longer(self):
        far_future = timezone.now() + timedelta(days=120)
        self.sub.tier = 'premium'
        self.sub.status = 'trialing'
        self.sub.trial_end = far_future
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.sub.refresh_from_db()
        # Should NOT shorten the existing 120-day trial
        self.assertEqual(
            self.sub.trial_end.replace(microsecond=0),
            far_future.replace(microsecond=0),
        )

    def test_extends_short_trial_to_60_days(self):
        soon = timezone.now() + timedelta(days=5)
        self.sub.tier = 'premium'
        self.sub.status = 'trialing'
        self.sub.trial_end = soon
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertTrue(applied)
        self.sub.refresh_from_db()
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((self.sub.trial_end - expected).total_seconds()), 60)

    def test_skips_active_paid_premium(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.subscription_source = 'stripe'
        self.sub.stripe_subscription_id = 'sub_123'
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already premium')
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.tier, 'premium')
        self.assertEqual(self.sub.subscription_source, 'stripe')
        self.assertFalse(
            PromoRedemption.objects.filter(user=self.user, promo=self.promo).exists()
        )

    def test_skips_active_paid_apple_premium(self):
        self.sub.tier = 'premium'
        self.sub.status = 'active'
        self.sub.subscription_source = 'apple'
        self.sub.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already premium')

    def test_rejects_already_redeemed(self):
        PromoRedemption.objects.create(user=self.user, promo=self.promo)

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'already redeemed')

    def test_rejects_unknown_code(self):
        applied, msg = apply_promo_to_user(self.user, 'BOGUS')
        self.assertFalse(applied)
        self.assertEqual(msg, 'invalid code')

    def test_rejects_inactive_code(self):
        self.promo.active = False
        self.promo.save()

        applied, msg = apply_promo_to_user(self.user, 'PAL90')
        self.assertFalse(applied)
        self.assertEqual(msg, 'invalid code')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.accounts.test_promo_service -v 2
```

Expected: ImportError for `apps.accounts.promo_service` because the file doesn't exist yet.

- [ ] **Step 3: Create `apps/accounts/promo_service.py`**

```python
"""
Promo code application service.

Single source of truth for the policy:
  - new / free users: grant trial_days of Premium
  - users currently trialing: extend trial_end if longer
  - active paid Premium/Pro users: no-op
  - already-redeemed: no-op (DB-enforced via unique_together)
  - unknown / inactive code: no-op
"""
from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone

from .payment_models import Promo, PromoRedemption, Subscription


def apply_promo_to_user(user, code):
    """
    Apply a promo code to a user's subscription.

    Returns:
        (applied: bool, message: str)
        applied=True only when the subscription was actually modified.
    """
    if not code:
        return False, 'invalid code'

    try:
        promo = Promo.objects.get(code=code, active=True)
    except Promo.DoesNotExist:
        return False, 'invalid code'

    if PromoRedemption.objects.filter(user=user, promo=promo).exists():
        return False, 'already redeemed'

    sub, _ = Subscription.objects.get_or_create(
        user=user,
        defaults={'tier': 'free', 'status': 'active'},
    )

    # Don't override an active paid subscription.
    if (
        sub.tier in ('premium', 'pro')
        and sub.status == 'active'
        and sub.subscription_source in ('stripe', 'apple')
    ):
        return False, 'already premium'

    new_trial_end = timezone.now() + timedelta(days=promo.trial_days)
    if sub.trial_end and sub.trial_end > new_trial_end:
        new_trial_end = sub.trial_end

    try:
        with transaction.atomic():
            sub.tier = 'premium'
            sub.status = 'trialing'
            sub.trial_end = new_trial_end
            sub.subscription_source = 'manual'
            sub.save()
            PromoRedemption.objects.create(user=user, promo=promo)
    except IntegrityError:
        # Race: another request redeemed the same code first.
        return False, 'already redeemed'

    return True, 'applied'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.accounts.test_promo_service -v 2
```

Expected: 8 tests pass, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/promo_service.py apps/accounts/test_promo_service.py
git commit -m "feat: add apply_promo_to_user helper with policy tests"
```

---

## Task 4: Build the marketing page (GET only, skeleton)

**Files:**
- Modify: `apps/core/urls.py`
- Modify: `apps/core/views.py`
- Create: `apps/core/templates/core/journal_bonus.html`

- [ ] **Step 1: Add URL routes**

In `apps/core/urls.py`, add two new paths to the `urlpatterns` list (after `sobriety_medallion_maker`):

```python
    path('journal-bonus/', views.JournalBonusView.as_view(), name='journal_bonus'),
    path('journal-bonus/claim/', views.journal_bonus_claim, name='journal_bonus_claim'),
```

- [ ] **Step 2: Add the GET view**

In `apps/core/views.py`, append at the end (and add the imports at the top of the file alongside existing imports):

```python
# At top of file, alongside existing imports:
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views.generic import View
from django.views.decorators.http import require_http_methods

DEFAULT_PROMO_CODE = 'PAL90'


class JournalBonusView(View):
    """
    Public landing page for the journal QR funnel.
    GET: render the page.
    POST: capture email, store promo + email in session, redirect to
          register or login depending on whether email is registered.
    """
    template_name = 'core/journal_bonus.html'

    def get(self, request):
        code = request.GET.get('code') or DEFAULT_PROMO_CODE
        return render(request, self.template_name, {
            'promo_code': code,
        })


@login_required
def journal_bonus_claim(request):
    """
    Login-required handler that consumes the session promo and
    applies it to the now-authenticated user. Placeholder for now.
    """
    # Filled in during Task 7
    return redirect('accounts:social_feed')
```

- [ ] **Step 3: Create the template (skeleton — full content in Task 5)**

Create `apps/core/templates/core/journal_bonus.html`:

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Welcome — Your 60-day Premium Trial | MyRecoveryPal{% endblock %}
{% block meta_description %}Thanks for picking up the 90 Day Recovery Journal. Start your 60-day MyRecoveryPal Premium trial — community feed, AI coach, daily check-ins.{% endblock %}

{% block content %}
<div style="max-width: 720px; margin: 2rem auto; padding: 0 1rem;">
  <div style="background: white; border-radius: 16px; padding: 2rem 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
    <h1 style="font-size: 1.9rem; line-height: 1.2; margin: 0 0 0.75rem;">
      Welcome — your 60-day Premium trial starts here.
    </h1>
    <p style="font-size: 1.05rem; color: #555; margin: 0 0 1.5rem;">
      Thanks for picking up the 90 Day Recovery Journal. This is the community it points to.
    </p>

    {% if form_error %}
    <div style="background: #fef2f2; color: #b91c1c; padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem;">
      {{ form_error }}
    </div>
    {% endif %}

    <form method="post" action="{% url 'core:journal_bonus' %}" novalidate
          style="display: flex; flex-direction: column; gap: 0.75rem;">
      {% csrf_token %}
      <input type="hidden" name="code" value="{{ promo_code }}">
      <input type="email" name="email" required
             autocomplete="email" inputmode="email"
             placeholder="your@email.com"
             value="{{ submitted_email|default_if_none:'' }}"
             style="padding: 0.85rem 1rem; font-size: 1rem; border: 1px solid #d1d5db; border-radius: 10px; width: 100%;">
      <button type="submit"
              style="padding: 0.95rem 1.25rem; font-size: 1.05rem; font-weight: 600; color: white; background: linear-gradient(135deg, #4db8e8 0%, #6dd5a8 100%); border: none; border-radius: 10px; cursor: pointer;">
        Start free trial
      </button>
    </form>

    <p style="margin: 1rem 0 0; font-size: 0.9rem; color: #6b7280; text-align: center;">
      Already have an account?
      <a href="{% url 'accounts:login' %}?next={% url 'core:journal_bonus_claim' %}?code={{ promo_code }}">Log in</a>
    </p>

    <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: #9ca3af; text-align: center;">
      60-day Premium trial. No credit card required. Cancel anytime.
    </p>
  </div>

  <div style="margin-top: 2rem; padding: 1.5rem; background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
    <p style="margin: 0 0 0.5rem; font-size: 1rem; color: #1f2937;">
      MyRecoveryPal is a private community feed, daily check-ins, and milestone tracking — built for people in recovery.
    </p>
    <p style="margin: 0 0 0.5rem; font-size: 1rem; color: #1f2937;">
      Anchor, our 24/7 AI recovery coach, is included with Premium.
    </p>
    <p style="margin: 0; font-size: 1rem; color: #1f2937;">
      No ads. No selling your data. Just support that meets you where you are.
    </p>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-top: 1.5rem;">
      <picture>
        <source srcset="{% static 'images/demo/feed.webp' %}" type="image/webp">
        <img src="{% static 'images/demo/feed.png' %}" alt="MyRecoveryPal social feed"
             loading="lazy" width="600" height="450"
             style="width: 100%; height: auto; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      </picture>
      <img src="{% static 'images/anchor-ai-coach.png' %}" alt="Anchor AI Recovery Coach"
           loading="lazy"
           style="width: 100%; height: auto; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Verify the page renders**

```bash
python manage.py runserver 8000 &
sleep 3
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/journal-bonus/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/journal-bonus/?code=PAL90
kill %1
```

Expected: both return `200`.

- [ ] **Step 5: Commit**

```bash
git add apps/core/urls.py apps/core/views.py apps/core/templates/core/journal_bonus.html
git commit -m "feat: add /journal-bonus landing page (GET only)"
```

---

## Task 5: Implement POST handler with email-routing logic (TDD)

**Files:**
- Create: `apps/core/test_journal_bonus.py`
- Modify: `apps/core/views.py`

- [ ] **Step 1: Write failing integration tests**

Create `apps/core/test_journal_bonus.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Promo

User = get_user_model()


class JournalBonusGetTests(TestCase):
    def test_get_renders_page(self):
        resp = self.client.get(reverse('core:journal_bonus'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Welcome')
        self.assertContains(resp, 'Start free trial')

    def test_default_promo_code_is_pal90(self):
        resp = self.client.get(reverse('core:journal_bonus'))
        self.assertContains(resp, 'value="PAL90"')

    def test_query_param_overrides_default_code(self):
        resp = self.client.get(reverse('core:journal_bonus') + '?code=OTHER')
        self.assertContains(resp, 'value="OTHER"')


class JournalBonusPostTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='PAL90',
            defaults={'trial_days': 60, 'active': True},
        )

    def test_post_with_new_email_redirects_to_register(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'newperson@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/register/', resp.url)
        self.assertIn('email=newperson%40example.com', resp.url)
        # Promo stashed in session
        self.assertEqual(self.client.session.get('journal_promo'), 'PAL90')

    def test_post_with_existing_email_redirects_to_login(self):
        User.objects.create_user(
            username='returning', email='returning@example.com', password='x'
        )
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'returning@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
        self.assertIn('next=', resp.url)
        self.assertEqual(self.client.session.get('journal_promo'), 'PAL90')

    def test_post_with_invalid_email_rerenders_with_error(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'not-an-email',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'valid email')

    def test_post_with_empty_email_rerenders_with_error(self):
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': '',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'valid email')

    def test_email_lookup_is_case_insensitive(self):
        User.objects.create_user(
            username='returning', email='returning@example.com', password='x'
        )
        resp = self.client.post(reverse('core:journal_bonus'), {
            'email': 'RETURNING@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.core.test_journal_bonus -v 2
```

Expected: GET tests pass, POST tests fail (the POST handler doesn't exist yet).

- [ ] **Step 3: Add the POST handler**

In `apps/core/views.py`, replace the existing `JournalBonusView` class with:

```python
class JournalBonusView(View):
    """
    Public landing page for the journal QR funnel.
    GET: render the page.
    POST: capture email, store promo + email in session, redirect to
          register or login depending on whether email is registered.
    """
    template_name = 'core/journal_bonus.html'

    def get(self, request):
        code = request.GET.get('code') or DEFAULT_PROMO_CODE
        return render(request, self.template_name, {
            'promo_code': code,
        })

    def post(self, request):
        from django.contrib.auth import get_user_model
        from urllib.parse import urlencode
        User = get_user_model()

        code = (request.POST.get('code') or DEFAULT_PROMO_CODE).strip()
        email = (request.POST.get('email') or '').strip().lower()

        # Validate email
        validator = EmailValidator()
        try:
            validator(email)
        except ValidationError:
            return render(request, self.template_name, {
                'promo_code': code,
                'submitted_email': email,
                'form_error': 'Please enter a valid email address.',
            })

        # Stash promo in session for the downstream auth flow
        request.session['journal_promo'] = code

        # Branch on whether the email is already registered
        existing = User.objects.filter(email__iexact=email).first()
        if existing is None:
            register_url = reverse('accounts:register')
            qs = urlencode({'email': email})
            return redirect(f'{register_url}?{qs}')

        # Existing user — send them through login then to claim
        claim_url = reverse('core:journal_bonus_claim')
        login_url = reverse('accounts:login')
        next_qs = urlencode({'code': code})
        next_url = f'{claim_url}?{next_qs}'
        login_qs = urlencode({'next': next_url})
        return redirect(f'{login_url}?{login_qs}')
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test apps.core.test_journal_bonus -v 2
```

Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/core/views.py apps/core/test_journal_bonus.py
git commit -m "feat: route /journal-bonus POST to register or login"
```

---

## Task 6: Wire promo into `register_view`

**Files:**
- Modify: `apps/accounts/views.py` (`register_view` function only)
- Modify: `apps/core/test_journal_bonus.py` (add end-to-end test)

- [ ] **Step 1: Add an end-to-end integration test**

Append to `apps/core/test_journal_bonus.py`:

```python
from django.utils import timezone
from datetime import timedelta
from apps.accounts.payment_models import Subscription, PromoRedemption


class JournalBonusEndToEndTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='PAL90',
            defaults={'trial_days': 60, 'active': True},
        )

    def test_full_signup_flow_grants_60_day_trial(self):
        # Step 1: hit the funnel
        self.client.post(reverse('core:journal_bonus'), {
            'email': 'newuser@example.com',
            'code': 'PAL90',
        })
        self.assertEqual(self.client.session.get('journal_promo'), 'PAL90')

        # Step 2: complete registration via the standard form
        register_resp = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!@',
            'password2': 'StrongPass123!@',
        })
        self.assertEqual(register_resp.status_code, 302)

        # Step 3: verify the new user has a 60-day Premium trial
        user = User.objects.get(username='newuser')
        sub = Subscription.objects.get(user=user)
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.status, 'trialing')
        self.assertEqual(sub.subscription_source, 'manual')
        expected = timezone.now() + timedelta(days=60)
        self.assertLess(abs((sub.trial_end - expected).total_seconds()), 120)

        # Step 4: PromoRedemption row created
        self.assertTrue(
            PromoRedemption.objects.filter(user=user, promo__code='PAL90').exists()
        )

        # Step 5: session promo cleared so it doesn't fire again
        self.assertNotIn('journal_promo', self.client.session)

    def test_register_without_promo_in_session_unchanged(self):
        # No funnel POST first — promo not in session.
        register_resp = self.client.post(reverse('accounts:register'), {
            'username': 'plainuser',
            'email': 'plain@example.com',
            'password1': 'StrongPass123!@',
            'password2': 'StrongPass123!@',
        })
        self.assertEqual(register_resp.status_code, 302)

        user = User.objects.get(username='plainuser')
        sub = Subscription.objects.get(user=user)
        # No promo applied → subscription_source stays at default ('stripe')
        self.assertNotEqual(sub.subscription_source, 'manual')
        self.assertFalse(
            PromoRedemption.objects.filter(user=user).exists()
        )
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
python manage.py test apps.core.test_journal_bonus.JournalBonusEndToEndTests -v 2
```

Expected: `test_full_signup_flow_grants_60_day_trial` fails (subscription_source is not `manual`).

- [ ] **Step 3: Patch `register_view`**

In `apps/accounts/views.py`, locate the `register_view` function (starts around line 41).

Find both places where this block appears (in the non-invite branch around line 67 and in the invite branch around line 145):

```python
                # Create subscription for user
                Subscription.objects.get_or_create(
                    user=user,
                    defaults={
                        'tier': 'free',
                        'status': 'active',
                    }
                )
```

After each `Subscription.objects.get_or_create(...)` call, insert:

```python
                # Apply funnel promo if user came from /journal-bonus
                journal_promo = request.session.pop('journal_promo', None)
                if journal_promo:
                    from .promo_service import apply_promo_to_user
                    apply_promo_to_user(user, journal_promo)
```

Both instances must be patched. Read the surrounding code first to be sure you're editing the right lines.

- [ ] **Step 4: Run all journal-bonus tests**

```bash
python manage.py test apps.core.test_journal_bonus apps.accounts.test_promo_service -v 2
```

Expected: all tests pass (10 + 8 = 18 tests).

- [ ] **Step 5: Manual smoke check**

```bash
python manage.py runserver 8000 &
sleep 3
# Submit funnel
curl -s -c /tmp/jb_cookies.txt -L -o /dev/null \
  -X POST http://localhost:8000/journal-bonus/ \
  -d "email=manual@example.com&code=PAL90&csrfmiddlewaretoken=$(curl -s -c /tmp/jb_cookies.txt http://localhost:8000/journal-bonus/ | grep -oP 'csrfmiddlewaretoken[\"'\''=]+\K[a-zA-Z0-9]+' | head -1)"
echo "Funnel POST done"
kill %1
```

(If CSRF makes manual curl fiddly, this step is optional — the integration tests cover the same path.)

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/views.py apps/core/test_journal_bonus.py
git commit -m "feat: apply journal-bonus promo on register"
```

---

## Task 7: Implement `journal_bonus_claim` for existing users

**Files:**
- Modify: `apps/core/views.py` (replace placeholder `journal_bonus_claim`)
- Modify: `apps/core/test_journal_bonus.py` (add tests)

- [ ] **Step 1: Add tests for the claim view**

Append to `apps/core/test_journal_bonus.py`:

```python
class JournalBonusClaimTests(TestCase):
    def setUp(self):
        Promo.objects.update_or_create(
            code='PAL90',
            defaults={'trial_days': 60, 'active': True},
        )
        self.user = User.objects.create_user(
            username='returning', email='returning@example.com', password='pw'
        )
        # Reset their auto-created trialing sub to free state
        sub = self.user.subscription
        sub.tier = 'free'
        sub.status = 'active'
        sub.trial_end = None
        sub.subscription_source = 'stripe'
        sub.save()

    def test_claim_requires_login(self):
        resp = self.client.get(reverse('core:journal_bonus_claim'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_claim_applies_promo_from_session(self):
        self.client.login(username='returning', password='pw')
        session = self.client.session
        session['journal_promo'] = 'PAL90'
        session.save()

        resp = self.client.get(reverse('core:journal_bonus_claim'))
        self.assertEqual(resp.status_code, 302)

        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.status, 'trialing')
        self.assertEqual(sub.subscription_source, 'manual')
        self.assertTrue(
            PromoRedemption.objects.filter(user=self.user, promo__code='PAL90').exists()
        )

    def test_claim_falls_back_to_query_param(self):
        self.client.login(username='returning', password='pw')
        # Session is empty — claim should still work via ?code=
        resp = self.client.get(reverse('core:journal_bonus_claim') + '?code=PAL90')
        self.assertEqual(resp.status_code, 302)

        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.tier, 'premium')

    def test_claim_with_no_code_redirects_to_feed(self):
        self.client.login(username='returning', password='pw')
        resp = self.client.get(reverse('core:journal_bonus_claim'))
        self.assertEqual(resp.status_code, 302)

        sub = Subscription.objects.get(user=self.user)
        # No promo applied — still free
        self.assertEqual(sub.tier, 'free')
```

- [ ] **Step 2: Run tests to verify the failing ones**

```bash
python manage.py test apps.core.test_journal_bonus.JournalBonusClaimTests -v 2
```

Expected: `test_claim_applies_promo_from_session` and `test_claim_falls_back_to_query_param` fail (placeholder view doesn't apply promo).

- [ ] **Step 3: Replace the `journal_bonus_claim` placeholder**

In `apps/core/views.py`, replace the existing placeholder `journal_bonus_claim` function with:

```python
@login_required
def journal_bonus_claim(request):
    """
    Login-required handler that consumes the session promo (or ?code=
    fallback) and applies it to the now-authenticated user. Used when
    an existing user comes back through the journal funnel.
    """
    from apps.accounts.promo_service import apply_promo_to_user

    code = request.session.pop('journal_promo', None) or request.GET.get('code')
    if code:
        applied, msg = apply_promo_to_user(request.user, code)
        if applied:
            messages.success(
                request,
                "Welcome back! 60 days of Premium has been added to your account."
            )
        elif msg == 'already premium':
            messages.info(
                request,
                "You already have Premium — thanks for picking up the journal!"
            )
        elif msg == 'already redeemed':
            messages.info(request, "You've already used this code.")
        # 'invalid code' → silent, no toast

    return redirect('accounts:social_feed')
```

- [ ] **Step 4: Run all tests**

```bash
python manage.py test apps.core.test_journal_bonus apps.accounts.test_promo_service -v 2
```

Expected: all tests pass (~22 tests total).

- [ ] **Step 5: Commit**

```bash
git add apps/core/views.py apps/core/test_journal_bonus.py
git commit -m "feat: handle existing-user claim path for journal funnel"
```

---

## Task 8: Add to sitemap

**Files:**
- Modify: `recovery_hub/sitemaps.py`

- [ ] **Step 1: Add the URL to the static sitemap**

In `recovery_hub/sitemaps.py`, find the `items()` method on `StaticViewSitemap` and add this entry near the other landing-page entries (e.g., right after `('core:sobriety_calculator', 0.95)`):

```python
            ('core:journal_bonus', 0.5),  # Journal QR funnel — internal use, low priority
```

- [ ] **Step 2: Verify the sitemap loads**

```bash
python manage.py runserver 8000 &
sleep 3
curl -s http://localhost:8000/sitemap.xml | grep journal-bonus
kill %1
```

Expected: output shows `<loc>https://www.myrecoverypal.com/journal-bonus/</loc>` (or similar with the configured domain).

- [ ] **Step 3: Commit**

```bash
git add recovery_hub/sitemaps.py
git commit -m "chore: add journal-bonus to sitemap"
```

---

## Task 9: Smoke test and verify

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite for the changed apps**

```bash
python manage.py test apps.accounts apps.core -v 2
```

Expected: all tests pass. If any pre-existing tests fail, investigate before claiming success — but only fix things our changes broke.

- [ ] **Step 2: Manual mobile-viewport check**

```bash
python manage.py runserver 8000 &
sleep 3
```

Then in a browser (or via Playwright if available), open `http://localhost:8000/journal-bonus/` with viewport 375×667 (iPhone SE). Verify:
- No horizontal scroll
- Email field is full-width
- "Start free trial" button is full-width
- Two screenshots stack properly in the 2-column grid (acceptable to be small at 375px wide)
- "Already have an account? Log in" link is visible

```bash
kill %1
```

- [ ] **Step 3: Smoke-test existing pages**

```bash
python manage.py runserver 8000 &
sleep 3
for path in / /accounts/register/ /accounts/login/ /accounts/dashboard/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$path)
  echo "$path -> $code"
done
kill %1
```

Expected: all return either `200` (public pages) or `302` (login-redirect for `/accounts/dashboard/`). No `500`s.

- [ ] **Step 4: Production verification (after deploy)**

After Railway auto-deploys from `main`:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://myrecoverypal.com/journal-bonus
curl -s -o /dev/null -w "%{http_code}\n" https://myrecoverypal.com/journal-bonus/
```

Expected: trailing-slash version returns `200`. Non-trailing-slash returns `301` (Django's `APPEND_SLASH=True` default) — that's fine for a QR-code URL since browsers follow it.

If non-trailing-slash returns `404`, check the QR code's encoded URL — make sure it includes the trailing slash, or add an explicit redirect.

- [ ] **Step 5: Final commit (if any cleanup)**

If no changes are needed, skip. Otherwise:

```bash
git add -A
git commit -m "chore: misc cleanup for journal-bonus funnel"
```

---

## Self-Review Notes

**Spec coverage check:**
- Hero / form / CTA → Task 4 (template) ✓
- 3-line description + 2 screenshots → Task 4 ✓
- Promo model + migration + seed → Tasks 1, 2 ✓
- `apply_promo_to_user` policy (4 cases) → Task 3 (8 unit tests) ✓
- `register_view` integration → Task 6 ✓
- Existing-user claim path → Task 7 ✓
- Sitemap entry → Task 8 ✓
- Mobile rendering check → Task 9 ✓
- Smoke tests on existing pages → Task 9 ✓
- "Logs them in if email exists" → Task 5 (redirect to login w/ next=claim) ✓
- Auto-applied promo code → Task 4 (hidden input from query string or default) ✓
- "60-day Premium trial" copy → Task 4 ✓

**Placeholder scan:** No TBDs, TODOs, or "implement later" markers. Every code step has the actual code.

**Type consistency:** Verified the function signature `apply_promo_to_user(user, code) -> (bool, str)` is consistent across Tasks 3, 6, and 7. Field names (`tier`, `status`, `trial_end`, `subscription_source`) match the existing `Subscription` model.

**Migration numbering:** Latest existing migration is `0029_add_saved_badge.py`, so `0030_promo_models.py` and `0031_seed_pal90.py` are correct. If another migration lands on `main` before this work merges, renumber both files accordingly.
