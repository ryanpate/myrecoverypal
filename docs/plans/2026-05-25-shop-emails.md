# Shop Emails (Weekly Digest + Milestone Celebrations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two new marketing emails (Friday weekly shop digest + milestone celebration emails at 7/30/90/180/365 days then yearly) plus the supporting opt-out infrastructure (User field, unsubscribe view, profile toggle, dedup model).

**Architecture:** One User-level `marketing_emails_enabled` flag (opt-out default), one `MilestoneEmailSent` dedup model on the store app, pure-helper email service in `apps.store.email_service`, two Celery tasks in `apps.store.tasks` calling those helpers, signed-URL unsubscribe via `django.core.signing`, hybrid email template style (personal note + featured product + bulleted others).

**Tech Stack:** Django 5.0, Celery + crontab, Resend HTTP API (via existing `apps.accounts.email_service.send_email`), `django.core.signing` for unsubscribe tokens, inline-CSS email HTML.

**Reference spec:** `docs/plans/2026-05-25-shop-emails-design.md`

---

## Pre-flight

- [ ] **Step 0.1: Verify branch + baseline**

Run:
```bash
git branch --show-current
git log --oneline -3
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.store -v 0 2>&1 | tail -3
```

Expected:
- Branch: `feat/shop-emails`
- Latest commit: `docs: shop emails design spec...`
- Tests pass (count varies but both apps green). Note the baseline number — you'll compare against it after each task.

**Use `python3` (not `python`).** **Use `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` for every test command** (the project transitively imports WeasyPrint via `apps.accounts.court_service`, which needs Pango from Homebrew on macOS).

- [ ] **Step 0.2: Note current migration numbers**

```bash
ls apps/accounts/migrations/ | grep -v __ | tail -1
ls apps/store/migrations/ | grep -v __ | tail -1
```

Expected (as of branch creation):
- `apps/accounts/migrations/`: last is `0036_seed_court_subscription_plans.py` → your new one is **`0037`**
- `apps/store/migrations/`: last is `0002_alter_product_options_product_external_url_and_more.py` → your new one is **`0003`**

If different, use what's actually there + 1.

---

## Task 1: Add `marketing_emails_enabled` field to User + `MilestoneEmailSent` model

Two small migrations bundled into one task because they're both schema-only changes that ship together, neither depends on the other, and the model field tests for both are simple field-existence checks.

**Files:**
- Create: `apps/store/tests_shop_emails.py`
- Modify: `apps/accounts/models.py` (add field to `User`)
- Create: `apps/accounts/migrations/0037_user_marketing_emails_enabled.py`
- Modify: `apps/store/models.py` (add `MilestoneEmailSent` class)
- Create: `apps/store/migrations/0003_milestoneemailsent.py`

### Step 1.1: Write failing tests

Create `apps/store/tests_shop_emails.py`:

```python
# apps/store/tests_shop_emails.py
"""Tests for shop emails (weekly digest + milestone celebrations)."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class MarketingFieldTest(TestCase):
    """User has a marketing_emails_enabled flag, defaults True."""

    def test_field_defaults_to_true(self):
        user = User.objects.create_user(
            username='m1', email='m1@example.com', password='pw'
        )
        self.assertTrue(user.marketing_emails_enabled)

    def test_field_persists_after_save(self):
        user = User.objects.create_user(
            username='m2', email='m2@example.com', password='pw'
        )
        user.marketing_emails_enabled = False
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.marketing_emails_enabled)


class MilestoneEmailSentModelTest(TestCase):
    """MilestoneEmailSent tracks which milestones have been emailed per user."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='mes', email='mes@example.com', password='pw'
        )

    def test_create_milestone_sent_row(self):
        from apps.store.models import MilestoneEmailSent
        row = MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
        self.assertEqual(row.milestone_days, 30)
        self.assertIsNotNone(row.sent_at)

    def test_unique_per_user_and_milestone(self):
        from apps.store.models import MilestoneEmailSent
        MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            MilestoneEmailSent.objects.create(user=self.user, milestone_days=30)
```

### Step 1.2: Run, confirm failures

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2
```

Expected: 4 failures — `AttributeError: 'User' object has no attribute 'marketing_emails_enabled'` and `ModuleNotFoundError`-or-`AttributeError` on `MilestoneEmailSent`.

### Step 1.3: Add field to User model

Edit `apps/accounts/models.py`. Find the `class User(AbstractUser):` block. Find an appropriate spot near other profile/preference fields (e.g., near `is_profile_public`, `show_sobriety_date`, `allow_messages`). Add this field:

```python
    marketing_emails_enabled = models.BooleanField(
        default=True,
        help_text='Receive weekly shop and milestone celebration emails.',
    )
```

### Step 1.4: Create accounts migration

Create `apps/accounts/migrations/0037_user_marketing_emails_enabled.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0036_seed_court_subscription_plans'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='marketing_emails_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Receive weekly shop and milestone celebration emails.',
            ),
        ),
    ]
```

### Step 1.5: Add MilestoneEmailSent model

Edit `apps/store/models.py`. Append at the bottom:

```python
class MilestoneEmailSent(models.Model):
    """Tracks which milestone celebration emails have been sent to each user.
    Prevents double-sends if the Celery task is retried."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='milestone_emails_sent',
    )
    milestone_days = models.IntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'milestone_days']
        indexes = [models.Index(fields=['user', 'milestone_days'])]
        verbose_name = 'Milestone Email Sent'
        verbose_name_plural = 'Milestone Emails Sent'

    def __str__(self):
        return f'{self.user.username} - {self.milestone_days}d ({self.sent_at:%Y-%m-%d})'
```

If the file doesn't already `from django.conf import settings` at the top, add it.

### Step 1.6: Create store migration

Create `apps/store/migrations/0003_milestoneemailsent.py`:

```python
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('store', '0002_alter_product_options_product_external_url_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MilestoneEmailSent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('milestone_days', models.IntegerField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name='milestone_emails_sent',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Milestone Email Sent',
                'verbose_name_plural': 'Milestone Emails Sent',
                'unique_together': {('user', 'milestone_days')},
                'indexes': [models.Index(fields=['user', 'milestone_days'], name='store_miles_user_id_5e6c3a_idx')],
            },
        ),
    ]
```

### Step 1.7: Apply migrations

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py migrate accounts
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py migrate store
```

Expected: both apply cleanly with `OK`.

### Step 1.8: Run tests, confirm pass

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2
```

Expected: 4 tests pass.

Also run the broader suite to confirm no regressions:

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.store -v 0 2>&1 | tail -3
```

Expected: baseline + 4 new tests, all pass.

### Step 1.9: Commit

```bash
git add apps/accounts/models.py apps/accounts/migrations/0037_user_marketing_emails_enabled.py \
        apps/store/models.py apps/store/migrations/0003_milestoneemailsent.py \
        apps/store/tests_shop_emails.py
git commit -m "feat(store): add marketing opt-out field + MilestoneEmailSent model

User.marketing_emails_enabled defaults True (opt-out model, CAN-SPAM
aligned). MilestoneEmailSent tracks which milestone celebration emails
have been delivered per user to prevent double-sends if Celery retries.

Spec: docs/plans/2026-05-25-shop-emails-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Unsubscribe view + URL

The signed-token unsubscribe link is the foundation everything else builds on — every email body will need it. Ships before the email service so we can reference its URL pattern.

**Files:**
- Create: `apps/accounts/email_views.py`
- Create: `apps/accounts/templates/accounts/email_unsubscribed.html`
- Modify: `recovery_hub/urls.py` (mount the URL)
- Modify: `apps/store/tests_shop_emails.py` (append `UnsubscribeViewTest`)

### Step 2.1: Append tests

Append to `apps/store/tests_shop_emails.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class UnsubscribeViewTest(TestCase):
    """One-click unsubscribe from marketing emails via signed-URL token."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='unsub', email='u@example.com', password='pw'
        )
        self.user.marketing_emails_enabled = True
        self.user.save()

    def _signed_token(self, user_id, kind='marketing'):
        from django.core import signing
        return signing.dumps({'user_id': user_id, 'kind': kind})

    def test_valid_token_sets_flag_false(self):
        token = self._signed_token(self.user.id)
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.marketing_emails_enabled)

    def test_invalid_token_returns_404(self):
        resp = self.client.get(reverse('unsubscribe_marketing', args=['garbage-token-not-signed']))
        self.assertEqual(resp.status_code, 404)

    def test_wrong_kind_returns_404(self):
        token = self._signed_token(self.user.id, kind='transactional')
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 404)
        self.user.refresh_from_db()
        self.assertTrue(self.user.marketing_emails_enabled)  # not changed

    def test_unknown_user_returns_404(self):
        token = self._signed_token(999999)
        resp = self.client.get(reverse('unsubscribe_marketing', args=[token]))
        self.assertEqual(resp.status_code, 404)
```

### Step 2.2: Run, confirm failure

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails.UnsubscribeViewTest -v 2
```

Expected: `NoReverseMatch: 'unsubscribe_marketing' is not a registered namespace`.

### Step 2.3: Create the view

Create `apps/accounts/email_views.py`:

```python
# apps/accounts/email_views.py
"""Email-related views (unsubscribe, etc.)."""
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404
from django.shortcuts import render

User = get_user_model()


def unsubscribe_marketing(request, token):
    """One-click unsubscribe from marketing emails.

    Token format: signing.dumps({'user_id': X, 'kind': 'marketing'}).
    No expiry — once unsubscribed, the user can re-enable via their profile.
    """
    try:
        data = signing.loads(token)
    except signing.BadSignature:
        raise Http404('Invalid unsubscribe token')

    if data.get('kind') != 'marketing':
        raise Http404('Unknown unsubscribe kind')

    try:
        user = User.objects.get(pk=data['user_id'])
    except (User.DoesNotExist, KeyError):
        raise Http404('User not found')

    user.marketing_emails_enabled = False
    user.save(update_fields=['marketing_emails_enabled'])

    return render(request, 'accounts/email_unsubscribed.html', {'user': user})
```

### Step 2.4: Create the confirmation template

Create `apps/accounts/templates/accounts/email_unsubscribed.html`:

```html
{% extends 'base.html' %}
{% block title %}Unsubscribed — MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width: 600px; margin: 4rem auto; padding: 0 1rem; text-align: center;">
    <div style="background: white; padding: 2.5rem 2rem; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
        <div style="font-size: 3rem; margin-bottom: 1rem;">✓</div>
        <h1 style="margin: 0 0 0.75rem; color: var(--primary-dark, #1e4d8b);">You're unsubscribed.</h1>
        <p style="color: #555; line-height: 1.6;">
            You'll no longer receive shop emails or milestone celebration
            notifications. Other emails (like check-in reminders and
            account notifications) are unaffected.
        </p>
        <p style="color: #555; line-height: 1.6; margin-top: 1.25rem;">
            Changed your mind? You can re-enable shop emails any time from
            your <a href="{% url 'accounts:edit_profile' %}" style="color: #1e4d8b; font-weight: 600;">profile settings</a>.
        </p>
    </div>
</div>
{% endblock %}
```

### Step 2.5: Mount the URL

Edit `recovery_hub/urls.py`. Near the top of the file (with other imports), add:

```python
from apps.accounts.email_views import unsubscribe_marketing
```

In the `urlpatterns` list, add (place near the existing `verify_court_report` if you have it, or near other utility routes):

```python
    path('email/unsubscribe/<str:token>/', unsubscribe_marketing, name='unsubscribe_marketing'),
```

### Step 2.6: Re-run tests, confirm pass

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails.UnsubscribeViewTest -v 2
```

Expected: 4 tests pass.

### Step 2.7: Commit

```bash
git add apps/accounts/email_views.py apps/accounts/templates/accounts/email_unsubscribed.html \
        recovery_hub/urls.py apps/store/tests_shop_emails.py
git commit -m "feat(accounts): signed-URL marketing-email unsubscribe view

GET /email/unsubscribe/<token>/ where token = signing.dumps({'user_id': X,
'kind': 'marketing'}). Decodes the token, sets marketing_emails_enabled
to False, shows confirmation page with link back to profile settings.

No expiry on the token (industry norm). Wrong-kind, invalid-signature,
and unknown-user tokens all 404.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Email service helpers + email templates

The pure helpers (`select_featured_products`, `select_milestone_product`, `find_users_hitting_milestone_today`) plus the three HTML templates plus the `send_*` orchestrators. Tasks 4+ depend on this being one cohesive unit.

**Files:**
- Create: `apps/store/email_service.py`
- Create: `apps/store/templates/store/emails/_shop_email_base.html`
- Create: `apps/store/templates/store/emails/weekly_digest.html`
- Create: `apps/store/templates/store/emails/milestone_celebration.html`
- Modify: `apps/store/tests_shop_emails.py` (append helper + send tests)

### Step 3.1: Append tests for the helpers

Append to `apps/store/tests_shop_emails.py`:

```python
from unittest.mock import patch
from decimal import Decimal


class FeaturedProductSelectionTest(TestCase):
    """select_featured_products() picks featured first, falls back to newest."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='Test', slug='test')

    def _product(self, name, **kwargs):
        from apps.store.models import Product
        defaults = dict(
            name=name,
            category=self.cat,
            description='x',
            price=Decimal('10.00'),
            external_url='https://example.com/p',
            is_active=True,
            is_featured=False,
        )
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def test_returns_featured_first(self):
        from apps.store.email_service import select_featured_products
        self._product('Plain A')
        f1 = self._product('Featured A', is_featured=True)
        f2 = self._product('Featured B', is_featured=True)
        result = list(select_featured_products(limit=3))
        self.assertEqual(result[0], f2)  # newest featured first
        self.assertEqual(result[1], f1)
        # Third slot filled by the plain product as fallback
        self.assertEqual(len(result), 3)

    def test_falls_back_to_newest_when_no_featured(self):
        from apps.store.email_service import select_featured_products
        p1 = self._product('Plain A')
        p2 = self._product('Plain B')
        result = list(select_featured_products(limit=3))
        self.assertIn(p1, result)
        self.assertIn(p2, result)

    def test_excludes_inactive_products(self):
        from apps.store.email_service import select_featured_products
        active = self._product('Active', is_featured=True)
        self._product('Inactive', is_featured=True, is_active=False)
        result = list(select_featured_products(limit=3))
        self.assertIn(active, result)
        self.assertEqual(len(result), 1)

    def test_respects_limit(self):
        from apps.store.email_service import select_featured_products
        for i in range(5):
            self._product(f'P{i}', is_featured=True)
        result = list(select_featured_products(limit=3))
        self.assertEqual(len(result), 3)


class MilestoneEligibilityTest(TestCase):
    """find_users_hitting_milestone_today() returns the right user set."""

    def _user_sober_for(self, days, **overrides):
        kwargs = dict(
            username=f'u{days}',
            email=f'u{days}@example.com',
            password='pw',
        )
        kwargs.update(overrides)
        user = User.objects.create_user(**kwargs)
        user.sobriety_date = date.today() - timedelta(days=days)
        user.marketing_emails_enabled = True
        user.save()
        return user

    def test_finds_user_at_exact_milestone(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(30)
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 1)
        user, milestone = results[0]
        self.assertEqual(milestone, 30)

    def test_skips_user_not_at_milestone(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(45)  # not a milestone
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_skips_user_with_marketing_disabled(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        user = self._user_sober_for(30)
        user.marketing_emails_enabled = False
        user.save()
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_skips_user_already_emailed(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        from apps.store.models import MilestoneEmailSent
        user = self._user_sober_for(30)
        MilestoneEmailSent.objects.create(user=user, milestone_days=30)
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)

    def test_finds_year_anniversaries(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        self._user_sober_for(730)  # 2 years
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 1)
        _, milestone = results[0]
        self.assertEqual(milestone, 730)

    def test_skips_user_without_sobriety_date(self):
        from apps.store.email_service import find_users_hitting_milestone_today
        u = User.objects.create_user(username='nodate', email='nd@x.com', password='pw')
        u.sobriety_date = None
        u.save()
        results = find_users_hitting_milestone_today()
        self.assertEqual(len(results), 0)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WeeklyDigestSendTest(TestCase):
    """send_weekly_shop_digest() sends to opted-in users only."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='X', slug='x')
        Product.objects.create(
            name='Featured', category=self.cat, description='x',
            price=Decimal('10.00'), external_url='https://example.com/f',
            is_active=True, is_featured=True,
        )
        # Three users: two opted-in, one opted-out
        self.opted_in_1 = User.objects.create_user(
            username='oi1', email='oi1@example.com', password='pw'
        )
        self.opted_in_2 = User.objects.create_user(
            username='oi2', email='oi2@example.com', password='pw'
        )
        self.opted_out = User.objects.create_user(
            username='oo', email='oo@example.com', password='pw'
        )
        self.opted_out.marketing_emails_enabled = False
        self.opted_out.save()

    @patch('apps.store.email_service.send_email')
    def test_sends_to_opted_in_users_only(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_weekly_shop_digest
        sent_count = send_weekly_shop_digest()
        self.assertEqual(sent_count, 2)  # opted_in_1 + opted_in_2
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertIn('oi1@example.com', recipients)
        self.assertIn('oi2@example.com', recipients)
        self.assertNotIn('oo@example.com', recipients)

    @patch('apps.store.email_service.send_email')
    def test_email_contains_unsubscribe_url(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_weekly_shop_digest
        send_weekly_shop_digest()
        first_call = mock_send.call_args_list[0]
        html = first_call.kwargs['html_message']
        self.assertIn('/email/unsubscribe/', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MilestoneCelebrationSendTest(TestCase):
    """send_milestone_celebration_email() sends one email + creates dedup row."""

    def setUp(self):
        from apps.store.models import Category, Product
        self.cat = Category.objects.create(name='Stickers', slug='stickers')
        Product.objects.create(
            name='30d Sticker', category=self.cat, description='x',
            price=Decimal('5.00'), external_url='https://example.com/s',
            is_active=True, is_featured=True,
        )
        self.user = User.objects.create_user(
            username='mile', email='mile@example.com', password='pw'
        )
        self.user.sobriety_date = date.today() - timedelta(days=30)
        self.user.save()

    @patch('apps.store.email_service.send_email')
    def test_creates_milestone_sent_row(self, mock_send):
        mock_send.return_value = (True, None)
        from apps.store.email_service import send_milestone_celebration_email
        from apps.store.models import MilestoneEmailSent
        send_milestone_celebration_email(self.user, 30)
        self.assertTrue(
            MilestoneEmailSent.objects.filter(user=self.user, milestone_days=30).exists()
        )
        mock_send.assert_called_once()

    @patch('apps.store.email_service.send_email')
    def test_does_not_send_when_send_email_fails(self, mock_send):
        mock_send.return_value = (False, 'SMTP fail')
        from apps.store.email_service import send_milestone_celebration_email
        from apps.store.models import MilestoneEmailSent
        send_milestone_celebration_email(self.user, 30)
        # No dedup row created on failure — so a retry can succeed
        self.assertFalse(
            MilestoneEmailSent.objects.filter(user=self.user, milestone_days=30).exists()
        )
```

### Step 3.2: Run, confirm failures

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2 2>&1 | tail -25
```

Expected: previous tests still pass; new ones fail with `ModuleNotFoundError: No module named 'apps.store.email_service'`.

### Step 3.3: Create the email service

Create `apps/store/email_service.py`:

```python
# apps/store/email_service.py
"""Shop email service — featured product selection, milestone matching,
and orchestration of send-to-many for weekly digests and per-user
milestone celebration emails.

All `send_*` functions use apps.accounts.email_service.send_email under
the hood, which handles Resend HTTP API + SMTP fallback.
"""
import logging
from datetime import date
from typing import Iterable, List, Optional, Tuple

from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from apps.accounts.email_service import send_email
from apps.store.models import Category, MilestoneEmailSent, Product

User = get_user_model()
logger = logging.getLogger(__name__)

# Milestones (in days) that trigger a celebration email.
FIXED_MILESTONES = [7, 30, 90, 180, 365]

# Map each milestone bucket to a product category slug. Year anniversaries
# (730, 1095, ...) always fall through to 'apparel'.
MILESTONE_PRODUCT_CATEGORIES = {
    7:   'stickers',
    30:  'journals',
    90:  'journals',
    180: 'apparel',
    365: 'apparel',
}


def select_featured_products(limit: int = 3) -> List[Product]:
    """Top featured products, falling back to newest active if not enough."""
    featured = list(
        Product.objects.filter(is_active=True, is_featured=True).order_by('-updated_at')[:limit]
    )
    if len(featured) >= limit:
        return featured
    # Fallback: top up with newest non-featured active products
    remaining = limit - len(featured)
    fallback = list(
        Product.objects
        .filter(is_active=True, is_featured=False)
        .exclude(pk__in=[p.pk for p in featured])
        .order_by('-created_at')[:remaining]
    )
    return featured + fallback


def select_milestone_product(milestone_days: int) -> Optional[Product]:
    """Pick one Product for a milestone email. Falls back to any featured."""
    if milestone_days >= 365 and milestone_days % 365 == 0:
        category_slug = 'apparel'
    else:
        category_slug = MILESTONE_PRODUCT_CATEGORIES.get(milestone_days, 'apparel')

    product = (
        Product.objects
        .filter(is_active=True, category__slug=category_slug)
        .order_by('-is_featured', '-updated_at')
        .first()
    )
    if product:
        return product
    return Product.objects.filter(is_active=True).order_by('-is_featured', '-updated_at').first()


def find_users_hitting_milestone_today() -> List[Tuple]:
    """Returns [(user, milestone_days), ...] for users hitting a milestone today.

    Excludes users with marketing_emails_enabled=False, inactive users,
    users without a sobriety_date, and users who have already been emailed
    for that specific milestone."""
    today = date.today()
    results = []

    qs = User.objects.filter(
        sobriety_date__isnull=False,
        marketing_emails_enabled=True,
        is_active=True,
    )

    for user in qs:
        days_sober = (today - user.sobriety_date).days
        is_fixed = days_sober in FIXED_MILESTONES
        is_yearly = days_sober > 365 and days_sober % 365 == 0
        if not (is_fixed or is_yearly):
            continue
        if MilestoneEmailSent.objects.filter(user=user, milestone_days=days_sober).exists():
            continue
        results.append((user, days_sober))

    return results


def _build_unsubscribe_url(user) -> str:
    token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}{reverse('unsubscribe_marketing', args=[token])}"


def _profile_settings_url() -> str:
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}{reverse('accounts:edit_profile')}"


def _shop_url() -> str:
    site_url = getattr(dj_settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    return f"{site_url}/store/"


def _milestone_message(milestone_days: int) -> Tuple[str, str]:
    """Return (subject, body_intro) for a milestone email."""
    if milestone_days == 7:
        return (
            'You hit 7 days. We see you.',
            "First week sober. The hardest stretch — and you did it."
        )
    if milestone_days == 30:
        return (
            'You hit 30 days. We see you.',
            "A full month. The brain chemistry shifts started about 5 days ago."
        )
    if milestone_days == 90:
        return (
            'You hit 90 days. We see you.',
            "90 days. Strong evidence the change is sticking."
        )
    if milestone_days == 180:
        return (
            'You hit 180 days. We see you.',
            "Half a year. Most people who relapse never get this far."
        )
    if milestone_days == 365:
        return (
            'One year sober. Today is the anniversary.',
            "One year. Today is the anniversary."
        )
    # Yearly anniversaries
    years = milestone_days // 365
    return (
        f'{years} years sober. That\'s a life.',
        f'{years} years sober. That\'s a life.'
    )


def send_weekly_shop_digest() -> int:
    """Send the Friday weekly shop digest. Returns count of emails sent."""
    products = select_featured_products(limit=3)
    if not products:
        logger.info('Weekly shop digest skipped — no active products to feature')
        return 0

    recipients = User.objects.filter(
        is_active=True,
        marketing_emails_enabled=True,
    ).exclude(email='').exclude(email__isnull=True)

    sent = 0
    for user in recipients:
        ctx = {
            'user': user,
            'first_name': user.first_name or 'Friend',
            'featured': products[0],
            'others': list(products[1:]),
            'unsubscribe_url': _build_unsubscribe_url(user),
            'profile_settings_url': _profile_settings_url(),
            'shop_url': _shop_url(),
        }
        html = render_to_string('store/emails/weekly_digest.html', ctx)
        plain = strip_tags(html)
        success, err = send_email(
            subject='New in the Recovery Shop this week',
            plain_message=plain,
            html_message=html,
            recipient_email=user.email,
        )
        if success:
            sent += 1
        else:
            logger.warning('Weekly digest send failed for %s: %s', user.email, err)

    return sent


def send_milestone_celebration_email(user, milestone_days: int) -> bool:
    """Send a single milestone celebration email. Returns True on success.

    Only creates the MilestoneEmailSent dedup row if send_email succeeds —
    so a transient failure can be retried by the next daily run."""
    if not user.email:
        return False

    product = select_milestone_product(milestone_days)
    subject, intro = _milestone_message(milestone_days)

    ctx = {
        'user': user,
        'first_name': user.first_name or 'Friend',
        'milestone_days': milestone_days,
        'milestone_intro': intro,
        'product': product,
        'unsubscribe_url': _build_unsubscribe_url(user),
        'profile_settings_url': _profile_settings_url(),
        'shop_url': _shop_url(),
    }
    html = render_to_string('store/emails/milestone_celebration.html', ctx)
    plain = strip_tags(html)
    success, err = send_email(
        subject=subject,
        plain_message=plain,
        html_message=html,
        recipient_email=user.email,
    )
    if success:
        MilestoneEmailSent.objects.get_or_create(user=user, milestone_days=milestone_days)
        return True
    logger.warning('Milestone email send failed for %s @ %dd: %s', user.email, milestone_days, err)
    return False
```

### Step 3.4: Create the base email template

Create `apps/store/templates/store/emails/_shop_email_base.html`:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{% block title %}MyRecoveryPal{% endblock %}</title>
</head>
<body style="margin:0;padding:0;background:#f4f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#222;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f4f7fa;padding:24px 0;">
  <tr><td align="center">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560" style="max-width:560px;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.06);">
      <tr><td style="padding:24px 28px 0;text-align:left;">
        <a href="{{ shop_url }}" style="color:#1e4d8b;text-decoration:none;font-weight:700;font-size:18px;">MyRecoveryPal</a>
      </td></tr>
      <tr><td style="padding:16px 28px 24px;">
        {% block content %}{% endblock %}
      </td></tr>
      <tr><td style="padding:16px 28px 24px;border-top:1px solid #eee;font-size:12px;color:#888;line-height:1.6;">
        You're receiving this because you have a MyRecoveryPal account.<br>
        <a href="{{ unsubscribe_url }}" style="color:#888;">Unsubscribe from shop emails</a>
        &nbsp;·&nbsp;
        <a href="{{ profile_settings_url }}" style="color:#888;">Manage email preferences</a>
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
```

### Step 3.5: Create the weekly digest template

Create `apps/store/templates/store/emails/weekly_digest.html`:

```html
{% extends 'store/emails/_shop_email_base.html' %}
{% block title %}New in the Recovery Shop this week{% endblock %}

{% block content %}
<p style="margin:0 0 12px;font-size:16px;">Hey {{ first_name }},</p>
<p style="margin:0 0 20px;font-size:15px;line-height:1.6;">
  A few new things in the Recovery Shop this week. Quick note on the one I'm most excited about, then the rest.
</p>

<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#fafbfd;border:1px solid #e8edf3;border-radius:10px;margin-bottom:20px;">
  <tr>
    {% if featured.image %}
    <td style="padding:18px;text-align:center;" width="40%">
      <img src="{{ featured.image.url }}" alt="{{ featured.name }}" style="max-width:160px;height:auto;border-radius:8px;display:block;margin:0 auto;">
    </td>
    {% endif %}
    <td style="padding:18px 18px 18px 0;vertical-align:top;">
      <div style="font-weight:700;font-size:16px;color:#1e4d8b;margin-bottom:6px;">{{ featured.name }}</div>
      <div style="font-size:14px;color:#555;line-height:1.5;margin-bottom:12px;">{{ featured.description|truncatewords:25 }}</div>
      <div style="font-weight:700;color:#222;margin-bottom:12px;">${{ featured.price }}</div>
      <a href="{{ featured.external_url }}" style="display:inline-block;background:#52b788;color:white;text-decoration:none;padding:9px 18px;border-radius:6px;font-weight:600;font-size:14px;">{{ featured.cta_label }} &rarr;</a>
    </td>
  </tr>
</table>

{% if others %}
<p style="margin:0 0 8px;font-weight:600;font-size:14px;color:#555;">Also new:</p>
<ul style="margin:0 0 20px;padding-left:20px;font-size:14px;line-height:1.7;">
  {% for p in others %}
  <li><a href="{{ p.external_url }}" style="color:#1e4d8b;text-decoration:none;">{{ p.name }}</a> &mdash; ${{ p.price }}</li>
  {% endfor %}
</ul>
{% endif %}

<p style="margin:20px 0 0;font-size:14px;">
  <a href="{{ shop_url }}" style="color:#1e4d8b;font-weight:600;text-decoration:none;">Shop everything &rarr;</a>
</p>
{% endblock %}
```

### Step 3.6: Create the milestone celebration template

Create `apps/store/templates/store/emails/milestone_celebration.html`:

```html
{% extends 'store/emails/_shop_email_base.html' %}
{% block title %}{{ milestone_days }} days sober &mdash; MyRecoveryPal{% endblock %}

{% block content %}
<p style="margin:0 0 12px;font-size:16px;">Hey {{ first_name }},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.6;font-weight:600;color:#1e4d8b;">
  {{ milestone_intro }}
</p>
<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#555;">
  That's worth marking. Here's something from the Recovery Shop that fits the moment &mdash; not because you need to buy anything to make today real, but because some people find a small physical reminder helps the next morning.
</p>

{% if product %}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#fafbfd;border:1px solid #e8edf3;border-radius:10px;margin-bottom:20px;">
  <tr>
    {% if product.image %}
    <td style="padding:18px;text-align:center;" width="40%">
      <img src="{{ product.image.url }}" alt="{{ product.name }}" style="max-width:160px;height:auto;border-radius:8px;display:block;margin:0 auto;">
    </td>
    {% endif %}
    <td style="padding:18px 18px 18px 0;vertical-align:top;">
      <div style="font-weight:700;font-size:16px;color:#1e4d8b;margin-bottom:6px;">{{ product.name }}</div>
      <div style="font-size:14px;color:#555;line-height:1.5;margin-bottom:12px;">{{ product.description|truncatewords:20 }}</div>
      <div style="font-weight:700;color:#222;margin-bottom:12px;">${{ product.price }}</div>
      <a href="{{ product.external_url }}" style="display:inline-block;background:#52b788;color:white;text-decoration:none;padding:9px 18px;border-radius:6px;font-weight:600;font-size:14px;">{{ product.cta_label }} &rarr;</a>
    </td>
  </tr>
</table>
{% endif %}

<p style="margin:24px 0 0;font-size:14px;color:#555;">
  Whatever's next, we're here.
</p>
<p style="margin:6px 0 0;font-size:14px;color:#555;">
  &mdash; The MyRecoveryPal team
</p>
{% endblock %}
```

### Step 3.7: Run tests, confirm pass

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2 2>&1 | tail -25
```

Expected: all previous tests still pass, all new tests pass. Total new tests in `tests_shop_emails.py` so far: ~16 (4 model + 4 unsubscribe + 4 featured + 6 milestone-eligibility + 2 weekly-send + 2 milestone-send).

### Step 3.8: Commit

```bash
git add apps/store/email_service.py \
        apps/store/templates/store/emails/ \
        apps/store/tests_shop_emails.py
git commit -m "feat(store): shop email service + templates (weekly digest + milestone)

Pure helpers: select_featured_products (featured first, newest fallback),
select_milestone_product (category-mapped, falls back to any featured),
find_users_hitting_milestone_today (filters opt-out, dedups via
MilestoneEmailSent). Orchestrators: send_weekly_shop_digest and
send_milestone_celebration_email — both use the existing
apps.accounts.email_service.send_email (Resend HTTP + SMTP fallback).

Hybrid email template style: personal greeting + featured product card
with image + bulleted 'Also new' list. Inline-CSS table layout for
Outlook compatibility. Plain-text version auto-generated via
django.utils.html.strip_tags.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Celery tasks + Beat schedule

Wrap the service functions in Celery `@shared_task` decorators and add the schedule entries.

**Files:**
- Create: `apps/store/tasks.py`
- Modify: `recovery_hub/settings.py` (add two entries to `CELERY_BEAT_SCHEDULE`)
- Modify: `apps/store/tests_shop_emails.py` (append task tests)

### Step 4.1: Append tests for the tasks

Append to `apps/store/tests_shop_emails.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WeeklyDigestTaskTest(TestCase):
    """The weekly_shop_digest_task wraps the service and is idempotent on retry."""

    def setUp(self):
        from apps.store.models import Category, Product
        cat = Category.objects.create(name='X', slug='x')
        Product.objects.create(
            name='F', category=cat, description='x',
            price=Decimal('10.00'), external_url='https://example.com/f',
            is_active=True, is_featured=True,
        )
        User.objects.create_user(username='wt1', email='wt1@example.com', password='pw')

    @patch('apps.store.tasks.send_weekly_shop_digest')
    def test_task_calls_service(self, mock_send):
        mock_send.return_value = 1
        from apps.store.tasks import weekly_shop_digest_task
        weekly_shop_digest_task()
        mock_send.assert_called_once()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MilestoneCelebrationTaskTest(TestCase):
    """The daily milestone task finds eligible users and sends to each."""

    def setUp(self):
        from apps.store.models import Category, Product
        cat = Category.objects.create(name='Stickers', slug='stickers')
        Product.objects.create(
            name='S', category=cat, description='x',
            price=Decimal('5.00'), external_url='https://example.com/s',
            is_active=True, is_featured=True,
        )

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_sends_to_users_at_milestones(self, mock_send):
        mock_send.return_value = True
        # User at 30 days
        u = User.objects.create_user(username='mu', email='mu@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=30)
        u.save()
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_called_once_with(u, 30)

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_no_op_when_no_users_at_milestone(self, mock_send):
        mock_send.return_value = True
        # User at 45 days — not a milestone
        u = User.objects.create_user(username='mu2', email='mu2@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=45)
        u.save()
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_not_called()

    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_task_idempotent_when_already_sent(self, mock_send):
        from apps.store.models import MilestoneEmailSent
        mock_send.return_value = True
        u = User.objects.create_user(username='mu3', email='mu3@example.com', password='pw')
        u.sobriety_date = date.today() - timedelta(days=30)
        u.save()
        MilestoneEmailSent.objects.create(user=u, milestone_days=30)
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task()
        mock_send.assert_not_called()
```

### Step 4.2: Run, confirm failures

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2 2>&1 | tail -20
```

Expected: new tests fail with `ModuleNotFoundError: No module named 'apps.store.tasks'`.

### Step 4.3: Create the tasks module

Create `apps/store/tasks.py`:

```python
# apps/store/tasks.py
"""Celery tasks for the shop emails.

Friday weekly digest: weekly_shop_digest_task (Fridays 10am UTC)
Daily milestone scan: daily_milestone_celebration_task (Daily 9am UTC)
"""
import logging

from celery import shared_task

from apps.store.email_service import (
    find_users_hitting_milestone_today,
    send_milestone_celebration_email,
    send_weekly_shop_digest,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,  # 30s, 60s, 120s, ...
    retry_kwargs={'max_retries': 3},
)
def weekly_shop_digest_task(self):
    """Send the Friday weekly shop digest to all opted-in users."""
    sent = send_weekly_shop_digest()
    logger.info('Weekly shop digest task: %d emails sent', sent)
    return sent


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={'max_retries': 3},
)
def daily_milestone_celebration_task(self):
    """Daily scan for users hitting a milestone today and send each a celebration email."""
    pairs = find_users_hitting_milestone_today()
    sent = 0
    for user, milestone_days in pairs:
        if send_milestone_celebration_email(user, milestone_days):
            sent += 1
    logger.info(
        'Milestone celebration task: %d/%d emails sent',
        sent, len(pairs),
    )
    return sent
```

### Step 4.4: Add Beat schedule entries

Edit `recovery_hub/settings.py`. Find the `CELERY_BEAT_SCHEDULE = {` block. Add these two entries (anywhere within the dict, but cluster them with related entries for readability):

```python
    # Shop emails (Audit Priority #3)
    'send-weekly-shop-digest': {
        'task': 'apps.store.tasks.weekly_shop_digest_task',
        'schedule': crontab(hour=10, minute=0, day_of_week=5),  # Friday 10am UTC
    },
    'send-milestone-celebrations': {
        'task': 'apps.store.tasks.daily_milestone_celebration_task',
        'schedule': crontab(hour=9, minute=0),  # Daily 9am UTC
    },
```

If `crontab` isn't already imported at the top of the file (it probably is — search for `from celery.schedules import crontab`), make sure it is.

### Step 4.5: Run all tests

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.store.tests_shop_emails -v 2 2>&1 | tail -10
```

Expected: all task tests pass.

### Step 4.6: Run Django system check

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check 2>&1 | tail -3
```

Expected: `System check identified no issues (0 silenced).`

### Step 4.7: Commit

```bash
git add apps/store/tasks.py recovery_hub/settings.py apps/store/tests_shop_emails.py
git commit -m "feat(store): Celery tasks + Beat schedule for shop emails

weekly_shop_digest_task — Fridays 10am UTC (~5am EST, lands in inbox at
US work-start). daily_milestone_celebration_task — daily 9am UTC, scans
for users hitting 7/30/90/180/365 days or yearly anniversary, dedups
via MilestoneEmailSent. Both tasks have autoretry with 30s exponential
backoff and max 3 retries.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Profile UI toggle

Surface the opt-out as a checkbox on the existing edit-profile page.

**Files:**
- Modify: `apps/accounts/forms.py` (add field to `UserProfileForm`)
- Modify: `apps/accounts/templates/accounts/edit_profile.html` (add the checkbox)

### Step 5.1: Look up the existing UserProfileForm

```bash
grep -n "class UserProfileForm\|class.*UserProfile.*Form" apps/accounts/forms.py | head -3
grep -nE "is_profile_public|show_sobriety_date|allow_messages" apps/accounts/forms.py | head -10
```

Note the line where `UserProfileForm.Meta.fields` is defined and the existing privacy/preference fields it includes.

### Step 5.2: Add the field to the form

Edit `apps/accounts/forms.py`. Find `class UserProfileForm` and its `Meta.fields` tuple. Add `'marketing_emails_enabled'` to the tuple, near other preference fields like `is_profile_public`. For example, if the existing tuple looks like:

```python
        fields = (
            'first_name', 'last_name', 'bio', 'location', 'avatar',
            'is_profile_public', 'show_sobriety_date', 'allow_messages',
            'interests', 'recovery_stage',
        )
```

Change it to:

```python
        fields = (
            'first_name', 'last_name', 'bio', 'location', 'avatar',
            'is_profile_public', 'show_sobriety_date', 'allow_messages',
            'marketing_emails_enabled',
            'interests', 'recovery_stage',
        )
```

If `UserProfileForm` has a `widgets` or `labels` dict, also add an entry there for the new field:

```python
        labels = {
            ...
            'marketing_emails_enabled': 'Send me shop & milestone celebration emails',
        }
```

### Step 5.3: Render the field in the template

```bash
grep -n "is_profile_public\|show_sobriety_date\|allow_messages\|Privacy" apps/accounts/templates/accounts/edit_profile.html | head -10
```

Find where the existing privacy checkboxes are rendered. Add a new block immediately after the `allow_messages` checkbox (or wherever the privacy section ends), following the same HTML pattern as the surrounding checkboxes. The exact markup depends on the template's existing style. As a pattern reference:

```django
<div class="form-check" style="margin-bottom: 0.75rem;">
    {{ form.marketing_emails_enabled }}
    <label for="{{ form.marketing_emails_enabled.id_for_label }}" class="form-check-label" style="margin-left: 0.5rem;">
        Send me shop &amp; milestone celebration emails
    </label>
    <small style="display: block; color: #888; margin-top: 0.25rem; margin-left: 1.75rem;">
        Includes the Friday "New in the Shop" digest and celebration emails
        when you hit a sobriety milestone. You can also unsubscribe from any
        email's footer.
    </small>
</div>
```

Match the existing template's class names and inline styles — don't introduce a new visual treatment.

### Step 5.4: Smoke-test the form renders + saves

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.accounts.forms import UserProfileForm
User = get_user_model()
u = User.objects.first()  # use any existing user
f = UserProfileForm(instance=u)
print('marketing_emails_enabled in fields:', 'marketing_emails_enabled' in f.fields)
"
```

Expected: `marketing_emails_enabled in fields: True`.

If you have a logged-in test client handy, also load `/accounts/edit-profile/` in a browser and verify the checkbox shows up in the Privacy section.

### Step 5.5: Run the full test suite

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.store -v 0 2>&1 | tail -3
```

Expected: all tests pass.

### Step 5.6: Commit

```bash
git add apps/accounts/forms.py apps/accounts/templates/accounts/edit_profile.html
git commit -m "feat(accounts): profile toggle for marketing emails

UserProfileForm now exposes marketing_emails_enabled in the Privacy
section of the edit-profile page. Users can re-enable shop & milestone
celebration emails after unsubscribing from an email footer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Final regression + push + PR

- [ ] **Step 6.1: Run all tests one more time**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts apps.store -v 0 2>&1 | tail -3
```

Expected: all green. Count should be `baseline + ~20` (4 model + 4 unsubscribe + 4 featured + 6 milestone-eligibility + 2 weekly-send + 2 milestone-send + 4 task tests).

- [ ] **Step 6.2: Run Django system check**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check --deploy 2>&1 | tail -5
```

Expected: no new warnings introduced. Pre-existing W009 (SECRET_KEY) is fine.

- [ ] **Step 6.3: Confirm migrations apply on a clean database**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py migrate --run-syncdb --no-input 2>&1 | tail -5
```

Expected: all migrations report `OK`.

- [ ] **Step 6.4: Commit the implementation plan doc (currently untracked)**

```bash
git status --short | grep "docs/plans/2026-05-25-shop-emails.md"
```

If the plan file appears as untracked, commit it:

```bash
git add docs/plans/2026-05-25-shop-emails.md
git commit -m "docs: shop emails implementation plan

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6.5: Push branch**

```bash
git push -u origin feat/shop-emails 2>&1 | tail -3
```

- [ ] **Step 6.6: Open the PR**

```bash
gh pr create --base main --head feat/shop-emails \
  --title "feat(store): weekly shop email + milestone celebration emails (Audit #3)" \
  --body "$(cat <<'EOF'
## Summary

Audit Priority #3 — two new marketing emails to activate the 218 existing users.

1. **Weekly Shop Digest** — Fridays 10am UTC, featured products from the Recovery Shop
2. **Milestone Celebration Email** — at 7/30/90/180/365 days then yearly anniversaries, featuring one curated product per milestone

Both emails are personal/hybrid-style (greeting + featured product with image + bulleted 'Also new' list) and include a one-click unsubscribe link.

## What changed

**Backend (model + migrations):**
- New `User.marketing_emails_enabled` field (opt-out default, CAN-SPAM aligned)
- New `MilestoneEmailSent` dedup model (prevents double-sends on Celery retries)

**Email infrastructure:**
- New `apps.store.email_service` — pure helpers (`select_featured_products`, `select_milestone_product`, `find_users_hitting_milestone_today`) + send orchestrators
- Three new templates: `_shop_email_base.html` (header/footer/unsubscribe), `weekly_digest.html`, `milestone_celebration.html` — all inline-CSS, table-based, Outlook-safe

**Celery tasks:**
- `weekly_shop_digest_task` — Friday 10am UTC
- `daily_milestone_celebration_task` — Daily 9am UTC, scans for milestone-hitters, dedups via `MilestoneEmailSent`
- Both tasks have autoretry with 30s exponential backoff, max 3 retries

**Unsubscribe:**
- Signed-URL view at `/email/unsubscribe/<token>/` (token = `signing.dumps({'user_id': X, 'kind': 'marketing'})`)
- No expiry on the token — once unsubscribed, user can re-enable via profile

**Profile UI:**
- `UserProfileForm` gains the `marketing_emails_enabled` field, surfaced as a checkbox in the Privacy section of edit-profile

## What deliberately wasn't built (per spec)

- ❌ Coupon codes (shop is off-site Printify/Amazon — coupons can't be auto-generated)
- ❌ Per-email-type preference granularity (one toggle covers both shop emails)
- ❌ Newsletter Subscriber model integration (separate audience, intentionally untouched)
- ❌ Email open/click tracking (Resend dashboard handles this)

## Test plan

- [x] ~20 new tests pass across `MarketingFieldTest`, `MilestoneEmailSentModelTest`, `UnsubscribeViewTest`, `FeaturedProductSelectionTest`, `MilestoneEligibilityTest`, `WeeklyDigestSendTest`, `MilestoneCelebrationSendTest`, `WeeklyDigestTaskTest`, `MilestoneCelebrationTaskTest`
- [x] Full `apps.accounts` + `apps.store` suites green
- [x] `manage.py check` clean
- [x] Migrations apply on a clean database
- [ ] **Post-merge manual smoke (you):**
  - Visit `/accounts/edit-profile/` and confirm the new toggle appears under Privacy
  - In Django shell, build a test unsubscribe URL: `from apps.store.email_service import _build_unsubscribe_url; from django.contrib.auth import get_user_model; print(_build_unsubscribe_url(get_user_model().objects.first()))`
  - Hit that URL in your browser and verify the confirmation page shows
  - Verify the user's flag flipped via `python manage.py shell -c "from django.contrib.auth import get_user_model; print(get_user_model().objects.first().marketing_emails_enabled)"`
  - Manually fire the weekly digest task: `python manage.py shell -c "from apps.store.tasks import weekly_shop_digest_task; weekly_shop_digest_task()"`
  - Check your inbox

## Operational notes

- Celery Beat is already running on Railway (celery-worker service). The new schedule entries take effect on the next deploy.
- The next Friday after deploy, the weekly digest fires automatically. To send it earlier, manually invoke `weekly_shop_digest_task()` via Django shell.
- The milestone task runs daily at 9am UTC starting tomorrow. If you have users who already passed milestones (e.g., a user at day 31 won't trigger day 30 retroactively), backfill is intentional — we don't want to spam users with months-old anniversaries.

Spec: \`docs/plans/2026-05-25-shop-emails-design.md\`
Implementation plan: \`docs/plans/2026-05-25-shop-emails.md\`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" 2>&1 | tail -3
```

Expected: PR URL printed.

---

## Self-Review

**Spec coverage** — walking the spec section by section:

| Spec requirement | Plan task |
|---|---|
| `User.marketing_emails_enabled` field | Task 1 |
| `MilestoneEmailSent` model | Task 1 |
| `apps/store/email_service.py` | Task 3 |
| `apps/store/tasks.py` | Task 4 |
| Three email templates | Task 3 |
| Unsubscribe view + URL | Task 2 |
| Profile UI toggle | Task 5 |
| Celery schedule entries | Task 4 |
| Test coverage (~12 tests minimum) | Tasks 1, 2, 3, 4 — actual count is ~20 |
| Friday 10am UTC weekly digest | Task 4 (Beat schedule) |
| Daily 9am UTC milestone scan | Task 4 (Beat schedule) |
| Milestones at 7/30/90/180/365 + yearly | Task 3 (`FIXED_MILESTONES` constant + yearly mod-365 check) |
| Hybrid email style | Task 3 (templates) |
| Idempotent milestone sends | Task 3 (`MilestoneEmailSent.get_or_create` only on success) |
| Signed-URL unsubscribe | Task 2 |
| Inline-CSS table-based email layout | Task 3 (templates) |
| Plain-text version | Task 3 (`strip_tags(html)` in service) |

**Placeholder scan:** No "TBD", no "implement later", every step has actual code or actual commands. Estimates are ranges (~20 tests, ~4–5 days) which is acceptable for estimates.

**Type consistency:**
- `MilestoneEmailSent` (Task 1) — referenced from `email_service.py` (Task 3) and `tests` — name consistent
- `FIXED_MILESTONES` constant (Task 3) — used in `find_users_hitting_milestone_today` — consistent
- `marketing_emails_enabled` — same field name in model (Task 1), form (Task 5), view (Task 2), service queries (Task 3), tests (all) — consistent
- `unsubscribe_marketing` URL name (Task 2) — referenced from `_build_unsubscribe_url` (Task 3) and tests — consistent
- Function signatures (`send_weekly_shop_digest`, `send_milestone_celebration_email(user, milestone_days)`, `find_users_hitting_milestone_today()`) — match between definition (Task 3), tests (Tasks 3 + 4), and task wrappers (Task 4)

No gaps identified.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-25-shop-emails.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
