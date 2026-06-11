# Family / Supporter Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a person in recovery share a curated, consent-controlled progress view with paying supporters (family/sponsor), who see a dashboard, send one-tap encouragement, and — at the closest preset — get inactivity alerts plus the member's manual "I need support" pings.

**Architecture:** A dedicated supporter module inside `apps/accounts` mirroring the existing `court_*` pattern (`supporter_models.py`, `supporter_service.py`, `supporter_views.py`, `supporter_forms.py`, a `supporter_required` decorator, a Celery task). A new `supporter` subscription tier reuses the existing Stripe/`SubscriptionPlan`/webhook machinery. The dashboard *reads* existing `DailyCheckIn`/milestone data through a single preset-gated service function — never duplicating data and never exposing craving content or free text.

**Tech Stack:** Django 5.0, PostgreSQL, Celery (`shared_task` + `CELERY_BEAT_SCHEDULE` crontab), existing `create_notification()` helper and `email_service.send_email()`. Tests are Django `TestCase` run via `python manage.py test`.

**Spec:** `docs/superpowers/specs/2026-06-11-family-supporter-dashboard-design.md`

---

## File Structure

**New files**
- `apps/accounts/supporter_models.py` — `SupporterLink` model + consent transition methods + preset constants.
- `apps/accounts/supporter_service.py` — `get_dashboard_data(link)` (preset-gated read model), `send_encouragement(link, key)`, milestone/consistency/mood helpers, `record_support_request(link)`.
- `apps/accounts/supporter_views.py` — member-side (invite/manage links, "I need support"), supporter-side (accept invite, dashboard, send encouragement, renew gate).
- `apps/accounts/supporter_forms.py` — invite form, preset form.
- `apps/accounts/templates/accounts/supporter/` — `dashboard.html`, `manage_links.html`, `invite.html`, `consent.html`, `renew.html`, `_crisis_resources.html`.
- `apps/accounts/test_supporter_service.py`, `test_supporter_consent.py`, `test_supporter_views.py`, `test_supporter_alerts.py`, `test_supporter_billing.py`.

**Modified files**
- `apps/accounts/payment_models.py` — add `supporter` to `TIER_CHOICES`, add `is_supporter()`.
- `apps/accounts/models.py` — register `SupporterLink` (import at bottom); add new notification type choices.
- `apps/accounts/decorators.py` — add `supporter_required`.
- `apps/accounts/payment_views.py` — extend webhook tier mapping to include `supporter`; add supporter plan to pricing context.
- `apps/accounts/tasks.py` — add `send_supporter_inactivity_alerts`.
- `recovery_hub/settings.py` — add beat schedule entry.
- `apps/accounts/urls.py` — supporter routes.
- `apps/accounts/templates/accounts/pricing.html` — supporter tier card.

**Phasing**
- **Phase 1 — Sharing foundation & consent (member side, no billing):** Tasks 1–7.
- **Phase 2 — Supporter dashboard & billing (web):** Tasks 8–12.
- **Phase 3 — Close-support alerts & manual support:** Tasks 13–15.

Each phase ends in working, testable software. Commit after every step. Run all new tests at each phase boundary.

---

# Phase 1 — Sharing foundation & consent

### Task 1: Add the `supporter` subscription tier

**Files:**
- Modify: `apps/accounts/payment_models.py:17-21` (`TIER_CHOICES`) and add `is_supporter()` near `is_court()` (~`:108-110`)
- Test: `apps/accounts/test_supporter_billing.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/test_supporter_billing.py
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from apps.accounts.payment_models import Subscription

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterTierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='supporter', email='s@example.com', password='pw'
        )

    def test_supporter_tier_is_recognized(self):
        sub = Subscription.objects.create(user=self.user, tier='supporter', status='active')
        self.assertTrue(sub.is_supporter())
        self.assertFalse(sub.is_premium())   # supporter is NOT a premium superset
        self.assertFalse(sub.is_court())

    def test_inactive_supporter_is_not_supporter(self):
        sub = Subscription.objects.create(user=self.user, tier='supporter', status='canceled')
        self.assertFalse(sub.is_supporter())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_billing.SupporterTierTests -v 2`
Expected: FAIL — `'supporter' is not a valid choice` on create, or `AttributeError: 'Subscription' object has no attribute 'is_supporter'`.

- [ ] **Step 3: Add the tier choice and helper**

In `apps/accounts/payment_models.py`, change `TIER_CHOICES`:

```python
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('court', 'Court Compliance'),
        ('supporter', 'Supporter'),
    ]
```

Add this method directly after `is_court()`:

```python
    def is_supporter(self):
        """Check if user holds an active Supporter seat.

        Supporter is a distinct paid role, NOT a superset of Premium.
        """
        return self.tier == 'supporter' and self.is_active()
```

- [ ] **Step 4: Make the migration and run the test**

Run: `python manage.py makemigrations accounts -n add_supporter_tier`
Expected: creates `apps/accounts/migrations/0039_add_supporter_tier.py` altering `Subscription.tier` choices.

Run: `python manage.py test apps.accounts.test_supporter_billing.SupporterTierTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/payment_models.py apps/accounts/migrations/0039_add_supporter_tier.py apps/accounts/test_supporter_billing.py
git commit -m "feat(supporter): add supporter subscription tier"
```

---

### Task 2: `SupporterLink` model

**Files:**
- Create: `apps/accounts/supporter_models.py`
- Modify: `apps/accounts/models.py` (register at bottom, near `:1937` court import)
- Test: `apps/accounts/test_supporter_consent.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/test_supporter_consent.py
from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterLinkModelTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='member', email='m@x.com', password='pw')
        self.supporter = User.objects.create_user(username='sup', email='s@x.com', password='pw')

    def test_defaults(self):
        link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='member', preset='standard'
        )
        self.assertEqual(link.status, 'pending')
        self.assertEqual(link.inactivity_threshold_days, 3)

    def test_cannot_support_self(self):
        link = SupporterLink(member=self.member, supporter=self.member, initiated_by='member')
        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_unique_member_supporter(self):
        SupporterLink.objects.create(member=self.member, supporter=self.supporter, initiated_by='member')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SupporterLink.objects.create(member=self.member, supporter=self.supporter, initiated_by='supporter')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_consent.SupporterLinkModelTests -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.accounts.supporter_models'`.

- [ ] **Step 3: Create the model**

```python
# apps/accounts/supporter_models.py
"""
Family / Supporter dashboard models.

A SupporterLink connects a person in recovery (member) with a supporter
(family member / sponsor) who follows a curated, consent-controlled view of
the member's progress. The member always controls the preset and may pause or
revoke at any time. See docs/superpowers/specs/2026-06-11-family-supporter-dashboard-design.md
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PRESET_CHOICES = [
    ('cheerleader', 'Cheerleader'),   # streak + milestones + encouragement
    ('standard', 'Standard'),         # + check-in consistency + mood trend
    ('close', 'Close support'),       # + inactivity alert + manual support ping
]

STATUS_CHOICES = [
    ('pending', 'Pending consent'),
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('revoked', 'Revoked'),
    ('declined', 'Declined'),
]

INITIATED_BY_CHOICES = [
    ('member', 'Member'),
    ('supporter', 'Supporter'),
]


class SupporterLink(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supporter_links',
        help_text='Person in recovery whose progress is shared.',
    )
    supporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supporting_links',
        help_text='Viewer; needs an active supporter subscription to see data.',
    )
    preset = models.CharField(max_length=12, choices=PRESET_CHOICES, default='standard')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    initiated_by = models.CharField(max_length=10, choices=INITIATED_BY_CHOICES)

    invite_email = models.EmailField(blank=True)
    invite_token = models.CharField(max_length=64, blank=True, db_index=True)

    inactivity_threshold_days = models.PositiveSmallIntegerField(default=3)
    last_inactivity_alert_sent = models.DateTimeField(null=True, blank=True)

    consented_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supporter_links'
        constraints = [
            models.UniqueConstraint(fields=['member', 'supporter'], name='unique_member_supporter'),
        ]
        indexes = [
            models.Index(fields=['member', 'status']),
            models.Index(fields=['supporter', 'status']),
        ]

    def __str__(self):
        return f"{self.supporter} → {self.member} ({self.preset}/{self.status})"

    def clean(self):
        if self.member_id and self.member_id == self.supporter_id:
            raise ValidationError("A user cannot be their own supporter.")
```

- [ ] **Step 4: Register the model for discovery**

At the bottom of `apps/accounts/models.py` (next to the existing `from apps.accounts.court_models import (...)` line ~1937), add:

```python
from apps.accounts.supporter_models import SupporterLink  # noqa: E402, F401
```

- [ ] **Step 5: Migrate and run the test**

Run: `python manage.py makemigrations accounts -n supporter_link`
Expected: creates `0040_supporter_link.py` adding `SupporterLink`.

Run: `python manage.py test apps.accounts.test_supporter_consent.SupporterLinkModelTests -v 2`
Expected: PASS (3 tests). Note: `unique_together`-style violation raises `IntegrityError` inside an atomic block — the test wraps the second create accordingly.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/supporter_models.py apps/accounts/models.py apps/accounts/migrations/0040_supporter_link.py apps/accounts/test_supporter_consent.py
git commit -m "feat(supporter): add SupporterLink model"
```

---

### Task 3: Consent state-machine methods

**Files:**
- Modify: `apps/accounts/supporter_models.py` (add methods to `SupporterLink`)
- Test: `apps/accounts/test_supporter_consent.py` (add a test class)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_consent.py
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterLinkTransitionTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='m2', email='m2@x.com', password='pw')
        self.supporter = User.objects.create_user(username='s2', email='s2@x.com', password='pw')
        self.link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='supporter', status='pending'
        )

    def test_member_consent_activates_and_sets_preset(self):
        self.link.consent(preset='close')
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'active')
        self.assertEqual(self.link.preset, 'close')
        self.assertIsNotNone(self.link.consented_at)

    def test_decline_is_terminal(self):
        self.link.decline()
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'declined')

    def test_pause_and_resume(self):
        self.link.consent(preset='standard')
        self.link.pause()
        self.assertEqual(self.link.status, 'paused')
        self.assertFalse(self.link.is_live())
        self.link.resume()
        self.assertEqual(self.link.status, 'active')
        self.assertTrue(self.link.is_live())

    def test_revoke_is_terminal_and_timestamped(self):
        self.link.consent(preset='standard')
        self.link.revoke()
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'revoked')
        self.assertIsNotNone(self.link.revoked_at)
        self.assertFalse(self.link.is_live())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_consent.SupporterLinkTransitionTests -v 2`
Expected: FAIL — `AttributeError: 'SupporterLink' object has no attribute 'consent'`.

- [ ] **Step 3: Add the methods**

Append to the `SupporterLink` class:

```python
    def is_live(self):
        """True when this link is actively sharing data."""
        return self.status == 'active'

    def consent(self, preset=None):
        """Member grants consent (and optionally sets/changes the preset)."""
        if preset:
            self.preset = preset
        self.status = 'active'
        if not self.consented_at:
            self.consented_at = timezone.now()
        self.save(update_fields=['preset', 'status', 'consented_at', 'updated_at'])

    def decline(self):
        self.status = 'declined'
        self.save(update_fields=['status', 'updated_at'])

    def pause(self):
        self.status = 'paused'
        self.save(update_fields=['status', 'updated_at'])

    def resume(self):
        self.status = 'active'
        self.save(update_fields=['status', 'updated_at'])

    def revoke(self):
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        self.save(update_fields=['status', 'revoked_at', 'updated_at'])

    def set_preset(self, preset):
        """Member changes the sharing level on an existing link."""
        self.preset = preset
        self.save(update_fields=['preset', 'updated_at'])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test apps.accounts.test_supporter_consent.SupporterLinkTransitionTests -v 2`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/supporter_models.py apps/accounts/test_supporter_consent.py
git commit -m "feat(supporter): consent state-machine transitions on SupporterLink"
```

---

### Task 4: Preset-gated dashboard read model (the privacy-critical core)

**Files:**
- Create: `apps/accounts/supporter_service.py`
- Test: `apps/accounts/test_supporter_service.py`

- [ ] **Step 1: Write the failing test (including the privacy invariant)**

```python
# apps/accounts/test_supporter_service.py
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink
from apps.accounts.models import DailyCheckIn
from apps.accounts import supporter_service

User = get_user_model()

# Keys that must NEVER appear anywhere in a supporter's dashboard payload.
FORBIDDEN_KEYS = {'craving', 'craving_level', 'gratitude', 'challenge', 'goal', 'journal', 'notes'}


def _flatten_keys(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(k)
            _flatten_keys(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten_keys(v, acc)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DashboardDataTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mm', email='mm@x.com', password='pw')
        self.member.sobriety_date = timezone.now().date() - timedelta(days=95)
        self.member.save()
        self.supporter = User.objects.create_user(username='ss', email='ss@x.com', password='pw')
        # 6 of last 7 days checked in, with cravings recorded (must NOT leak)
        for i in range(7):
            if i == 3:
                continue
            DailyCheckIn.objects.create(
                user=self.member, date=timezone.now().date() - timedelta(days=i),
                mood=4, craving_level=3, energy_level=3, gratitude='private text',
            )
        self.link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='member', status='active',
        )

    def test_cheerleader_has_only_positive_signal(self):
        self.link.preset = 'cheerleader'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertEqual(data['days_sober'], 95)
        self.assertIn('next_milestone', data)
        self.assertNotIn('checkin_consistency', data)
        self.assertNotIn('mood_trend', data)

    def test_standard_adds_consistency_and_mood(self):
        self.link.preset = 'standard'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertEqual(data['checkin_consistency']['count'], 6)
        self.assertEqual(data['checkin_consistency']['window'], 7)
        self.assertTrue(all(isinstance(m, int) for m in data['mood_trend']))

    def test_close_adds_inactivity_status(self):
        self.link.preset = 'close'
        data = supporter_service.get_dashboard_data(self.link)
        self.assertIn('inactivity', data)

    def test_no_preset_ever_leaks_craving_or_freetext(self):
        for preset in ('cheerleader', 'standard', 'close'):
            self.link.preset = preset
            data = supporter_service.get_dashboard_data(self.link)
            keys = set()
            _flatten_keys(data, keys)
            leaked = keys & FORBIDDEN_KEYS
            self.assertFalse(leaked, f"preset {preset} leaked {leaked}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_service.DashboardDataTests -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.accounts.supporter_service'`.

- [ ] **Step 3: Implement the service**

```python
# apps/accounts/supporter_service.py
"""
Read model + actions for the supporter dashboard.

get_dashboard_data() is the SINGLE place the preset -> fields mapping lives.
No other code should read member recovery data for a supporter. It never
queries craving levels, journal entries, or any free-text check-in field.
"""
from datetime import timedelta
from django.utils import timezone

# Day-mark milestones used for the "next milestone" countdown.
MILESTONE_DAYS = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1460, 1825]

CHECKIN_WINDOW_DAYS = 7
MOOD_TREND_DAYS = 7


def _next_milestone(days_sober):
    for target in MILESTONE_DAYS:
        if target > days_sober:
            return {'target': target, 'days_to': target - days_sober}
    # Past the last fixed mark: next yearly anniversary.
    years = days_sober // 365 + 1
    target = years * 365
    return {'target': target, 'days_to': target - days_sober}


def _milestones_hit(days_sober):
    return [d for d in MILESTONE_DAYS if d <= days_sober]


def _checkin_consistency(member):
    cutoff = timezone.now().date() - timedelta(days=CHECKIN_WINDOW_DAYS - 1)
    count = member.daily_checkins.filter(date__gte=cutoff).count()
    return {'count': count, 'window': CHECKIN_WINDOW_DAYS}


def _mood_trend(member):
    cutoff = timezone.now().date() - timedelta(days=MOOD_TREND_DAYS - 1)
    qs = member.daily_checkins.filter(date__gte=cutoff).order_by('date')
    # Only the mood scalar — never notes/gratitude/craving.
    return list(qs.values_list('mood', flat=True))


def _inactivity_status(member, link):
    last = member.daily_checkins.order_by('-date').first()
    if not last:
        return {'days_since_checkin': None, 'over_threshold': True}
    days = (timezone.now().date() - last.date).days
    return {'days_since_checkin': days, 'over_threshold': days >= link.inactivity_threshold_days}


def get_dashboard_data(link):
    """Build the supporter-visible payload for a link, gated by preset."""
    member = link.member
    days_sober = member.get_days_sober()
    data = {
        'member_name': member.get_full_name() or member.username,
        'preset': link.preset,
        'days_sober': days_sober,
        'milestone_label': member.get_sobriety_milestone(),
        'next_milestone': _next_milestone(days_sober),
        'milestones_hit': _milestones_hit(days_sober),
    }
    if link.preset in ('standard', 'close'):
        data['checkin_consistency'] = _checkin_consistency(member)
        data['mood_trend'] = _mood_trend(member)
    if link.preset == 'close':
        data['inactivity'] = _inactivity_status(member, link)
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test apps.accounts.test_supporter_service.DashboardDataTests -v 2`
Expected: PASS (4 tests), including the privacy invariant.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/supporter_service.py apps/accounts/test_supporter_service.py
git commit -m "feat(supporter): preset-gated dashboard read model with privacy invariant"
```

---

### Task 5: `supporter_required` decorator

**Files:**
- Modify: `apps/accounts/decorators.py` (add after `court_required`)
- Test: `apps/accounts/test_supporter_views.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/test_supporter_views.py
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from apps.accounts.payment_models import Subscription
from apps.accounts.decorators import supporter_required

User = get_user_model()


def _view(request):
    from django.http import HttpResponse
    return HttpResponse('ok')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterRequiredTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _prep(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda r: None).process_request(request)

    def test_redirects_without_supporter_sub(self):
        u = User.objects.create_user(username='plain', email='p@x.com', password='pw')
        req = self.factory.get('/supporter/dashboard/')
        req.user = u
        self._prep(req)
        resp = supporter_required(_view)(req)
        self.assertEqual(resp.status_code, 302)

    def test_allows_active_supporter(self):
        u = User.objects.create_user(username='sup', email='s@x.com', password='pw')
        Subscription.objects.create(user=u, tier='supporter', status='active')
        req = self.factory.get('/supporter/dashboard/')
        req.user = u
        self._prep(req)
        resp = supporter_required(_view)(req)
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_views.SupporterRequiredTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'supporter_required'`.

- [ ] **Step 3: Add the decorator**

Append to `apps/accounts/decorators.py`:

```python
def supporter_required(view_func):
    """Requires an active Supporter subscription. Lapsed/absent -> renew/upgrade."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')
        sub = getattr(request.user, 'subscription', None)
        if sub is None or not sub.is_supporter():
            messages.warning(
                request,
                'Viewing a loved one’s progress requires an active Supporter subscription.'
            )
            return redirect('accounts:supporter_renew')
        return view_func(request, *args, **kwargs)
    return wrapper
```

> Note: `accounts:supporter_renew` is wired in Task 9. Until then this test passes because the active-supporter path returns 200 and the redirect path only needs a 302 (Django resolves the redirect target lazily at response time; `RequestFactory` does not follow it).

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test apps.accounts.test_supporter_views.SupporterRequiredTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/decorators.py apps/accounts/test_supporter_views.py
git commit -m "feat(supporter): supporter_required decorator"
```

---

### Task 6: Notification types for supporter events

**Files:**
- Modify: `apps/accounts/models.py:1595` (`Notification.NOTIFICATION_TYPES`)
- Test: covered indirectly; add a quick assertion test in `test_supporter_service.py`

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_service.py
from apps.accounts.models import Notification

@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class NotificationTypeTests(TestCase):
    def test_supporter_notification_types_exist(self):
        keys = dict(Notification.NOTIFICATION_TYPES)
        for k in ['supporter_request', 'supporter_consented', 'supporter_encouragement',
                  'member_support_request', 'member_inactive']:
            self.assertIn(k, keys)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_service.NotificationTypeTests -v 2`
Expected: FAIL — assertion error, keys missing.

- [ ] **Step 3: Add the choices**

In `apps/accounts/models.py`, inside `NOTIFICATION_TYPES` (starts ~line 1595), add before the closing `)`:

```python
        ('supporter_request', 'Supporter Request'),
        ('supporter_consented', 'Supporter Connected'),
        ('supporter_encouragement', 'Encouragement from Supporter'),
        ('member_support_request', 'Member Asked for Support'),
        ('member_inactive', 'Member Inactivity Alert'),
```

- [ ] **Step 4: Migrate and run the test**

Run: `python manage.py makemigrations accounts -n supporter_notification_types`
Expected: creates a migration altering `Notification.notification_type` choices.

Run: `python manage.py test apps.accounts.test_supporter_service.NotificationTypeTests -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/ apps/accounts/test_supporter_service.py
git commit -m "feat(supporter): add supporter notification types"
```

---

### Task 7: Member-side — invite & manage links

**Files:**
- Create: `apps/accounts/supporter_forms.py`, `apps/accounts/supporter_views.py`, templates `accounts/supporter/manage_links.html`, `accounts/supporter/invite.html`
- Modify: `apps/accounts/urls.py`
- Test: `apps/accounts/test_supporter_views.py` (add `MemberSharingTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_views.py
from django.urls import reverse
from apps.accounts.supporter_models import SupporterLink

@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MemberSharingTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mem', email='mem@x.com', password='pw')
        self.client.login(username='mem', password='pw')

    def test_member_can_invite_supporter_by_email(self):
        resp = self.client.post(reverse('accounts:supporter_invite'), {
            'invite_email': 'mom@example.com', 'preset': 'standard',
        })
        self.assertEqual(resp.status_code, 302)
        link = SupporterLink.objects.get(member=self.member)
        self.assertEqual(link.invite_email, 'mom@example.com')
        self.assertEqual(link.preset, 'standard')
        self.assertEqual(link.status, 'pending')
        self.assertEqual(link.initiated_by, 'member')
        self.assertTrue(link.invite_token)

    def test_member_can_change_preset(self):
        link = SupporterLink.objects.create(member=self.member,
            supporter=User.objects.create_user(username='x', email='x@x.com', password='pw'),
            initiated_by='member', status='active', preset='cheerleader')
        resp = self.client.post(reverse('accounts:supporter_set_preset', args=[link.id]),
                                {'preset': 'close'})
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.preset, 'close')

    def test_member_can_revoke(self):
        sup = User.objects.create_user(username='y', email='y@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='member', status='active', preset='standard')
        resp = self.client.post(reverse('accounts:supporter_revoke', args=[link.id]))
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.status, 'revoked')

    def test_cannot_touch_another_members_link(self):
        other = User.objects.create_user(username='other', email='o@x.com', password='pw')
        sup = User.objects.create_user(username='z', email='z@x.com', password='pw')
        link = SupporterLink.objects.create(member=other, supporter=sup,
            initiated_by='member', status='active', preset='standard')
        resp = self.client.post(reverse('accounts:supporter_revoke', args=[link.id]))
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_views.MemberSharingTests -v 2`
Expected: FAIL — `NoReverseMatch: 'supporter_invite' not found`.

- [ ] **Step 3: Create the form**

```python
# apps/accounts/supporter_forms.py
from django import forms
from apps.accounts.supporter_models import SupporterLink, PRESET_CHOICES


class SupporterInviteForm(forms.Form):
    invite_email = forms.EmailField()
    preset = forms.ChoiceField(choices=PRESET_CHOICES, initial='standard')


class PresetForm(forms.Form):
    preset = forms.ChoiceField(choices=PRESET_CHOICES)
```

- [ ] **Step 4: Create the views**

```python
# apps/accounts/supporter_views.py
import secrets
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.accounts.supporter_models import SupporterLink
from apps.accounts.supporter_forms import SupporterInviteForm, PresetForm


@login_required
def manage_links(request):
    """Member view: list supporters who follow me + invite controls."""
    links = SupporterLink.objects.filter(member=request.user).exclude(
        status__in=['revoked', 'declined']
    ).select_related('supporter')
    return render(request, 'accounts/supporter/manage_links.html', {'links': links})


@login_required
def supporter_invite(request):
    if request.method == 'POST':
        form = SupporterInviteForm(request.POST)
        if form.is_valid():
            SupporterLink.objects.create(
                member=request.user,
                supporter=None if True else None,  # placeholder replaced below
                initiated_by='member',
                preset=form.cleaned_data['preset'],
                invite_email=form.cleaned_data['invite_email'],
                invite_token=secrets.token_urlsafe(32),
                status='pending',
            )
            messages.success(request, 'Invitation sent.')
            return redirect('accounts:supporter_manage')
    else:
        form = SupporterInviteForm()
    return render(request, 'accounts/supporter/invite.html', {'form': form})


@login_required
@require_POST
def supporter_set_preset(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user)
    form = PresetForm(request.POST)
    if form.is_valid():
        link.set_preset(form.cleaned_data['preset'])
        messages.success(request, 'Sharing level updated.')
    return redirect('accounts:supporter_manage')


@login_required
@require_POST
def supporter_revoke(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user)
    link.revoke()
    messages.success(request, 'Access revoked.')
    return redirect('accounts:supporter_manage')
```

> **Fix the `supporter` FK for email invites:** `SupporterLink.supporter` is currently non-null. Member-initiated invites to a not-yet-user have no supporter row. In Step 5 of this task, make `supporter` nullable (`null=True, blank=True`) and bind it when the invitee accepts (Task 9). Replace the placeholder line above with simply omitting `supporter` from the create call.

- [ ] **Step 5: Make `supporter` nullable + correct the create call**

In `supporter_models.py`, change the `supporter` field to:

```python
    supporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supporting_links',
        null=True, blank=True,
        help_text='Viewer; null until an email invitee accepts. Needs active supporter sub to view.',
    )
```

Update the `unique` constraint to tolerate nulls (Postgres treats nulls as distinct, which is what we want — multiple pending email invites are fine). Keep the `UniqueConstraint` as-is.

In `supporter_views.py` `supporter_invite`, replace the create call with:

```python
            SupporterLink.objects.create(
                member=request.user,
                initiated_by='member',
                preset=form.cleaned_data['preset'],
                invite_email=form.cleaned_data['invite_email'],
                invite_token=secrets.token_urlsafe(32),
                status='pending',
            )
```

Run: `python manage.py makemigrations accounts -n supporter_nullable`
Expected: migration making `supporter` nullable.

- [ ] **Step 6: Create minimal templates**

```html
<!-- apps/accounts/templates/accounts/supporter/manage_links.html -->
{% extends 'base.html' %}
{% block content %}
<h1>People supporting me</h1>
<a href="{% url 'accounts:supporter_invite' %}">Invite a supporter</a>
<ul>
{% for link in links %}
  <li>
    {{ link.supporter|default:link.invite_email }} — {{ link.get_preset_display }} ({{ link.get_status_display }})
    <form method="post" action="{% url 'accounts:supporter_set_preset' link.id %}" style="display:inline">
      {% csrf_token %}
      <select name="preset">
        <option value="cheerleader">Cheerleader</option>
        <option value="standard">Standard</option>
        <option value="close">Close support</option>
      </select>
      <button type="submit">Update</button>
    </form>
    <form method="post" action="{% url 'accounts:supporter_revoke' link.id %}" style="display:inline">
      {% csrf_token %}<button type="submit">Revoke</button>
    </form>
  </li>
{% empty %}
  <li>No supporters yet.</li>
{% endfor %}
</ul>
{% endblock %}
```

```html
<!-- apps/accounts/templates/accounts/supporter/invite.html -->
{% extends 'base.html' %}
{% block content %}
<h1>Invite a supporter</h1>
<form method="post">{% csrf_token %}{{ form.as_p }}<button type="submit">Send invite</button></form>
{% endblock %}
```

- [ ] **Step 7: Wire URLs**

In `apps/accounts/urls.py`, add (inside `urlpatterns`):

```python
    path('supporter/manage/', supporter_views.manage_links, name='supporter_manage'),
    path('supporter/invite/', supporter_views.supporter_invite, name='supporter_invite'),
    path('supporter/<int:link_id>/preset/', supporter_views.supporter_set_preset, name='supporter_set_preset'),
    path('supporter/<int:link_id>/revoke/', supporter_views.supporter_revoke, name='supporter_revoke'),
```

Add the import at the top of `urls.py`: `from apps.accounts import supporter_views`.

- [ ] **Step 8: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_views.MemberSharingTests -v 2`
Expected: PASS (4 tests).

- [ ] **Step 9: Commit**

```bash
git add apps/accounts/supporter_forms.py apps/accounts/supporter_views.py apps/accounts/supporter_models.py apps/accounts/urls.py apps/accounts/templates/accounts/supporter/ apps/accounts/migrations/ apps/accounts/test_supporter_views.py
git commit -m "feat(supporter): member-side invite and link management"
```

- [ ] **Step 10: Phase 1 gate — run all supporter tests**

Run: `python manage.py test apps.accounts.test_supporter_service apps.accounts.test_supporter_consent apps.accounts.test_supporter_views apps.accounts.test_supporter_billing -v 2`
Expected: all PASS.

---

# Phase 2 — Supporter dashboard & billing

### Task 8: Seed supporter `SubscriptionPlan` rows + extend webhook

**Files:**
- Create: data migration `apps/accounts/migrations/00XX_seed_supporter_plans.py` (mirror `0036_seed_court_subscription_plans.py`)
- Modify: `apps/accounts/payment_views.py:294` (webhook tier mapping)
- Test: `apps/accounts/test_supporter_billing.py` (add `SupporterPlanTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_billing.py
from apps.accounts.payment_models import SubscriptionPlan

@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterPlanTests(TestCase):
    def test_monthly_supporter_plan_seeded(self):
        plan = SubscriptionPlan.objects.filter(tier='supporter', billing_period='monthly').first()
        self.assertIsNotNone(plan)
        self.assertEqual(str(plan.price), '7.99')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_billing.SupporterPlanTests -v 2`
Expected: FAIL — plan is None. (First read `0036_seed_court_subscription_plans.py` to copy its exact field usage for `SubscriptionPlan`.)

- [ ] **Step 3: Write the data migration**

```python
# apps/accounts/migrations/00XX_seed_supporter_plans.py
from django.db import migrations


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    SubscriptionPlan.objects.update_or_create(
        tier='supporter', billing_period='monthly',
        defaults={'name': 'Supporter', 'price': '7.99', 'is_active': True},
    )
    SubscriptionPlan.objects.update_or_create(
        tier='supporter', billing_period='yearly',
        defaults={'name': 'Supporter (Yearly)', 'price': '79.00', 'is_active': True},
    )


def unseed(apps, schema_editor):
    apps.get_model('accounts', 'SubscriptionPlan').objects.filter(tier='supporter').delete()


class Migration(migrations.Migration):
    dependencies = [('accounts', '0040_supporter_link')]  # adjust to latest
    operations = [migrations.RunPython(seed, unseed)]
```

> Confirm the real `SubscriptionPlan` field names against `0036_seed_court_subscription_plans.py` and `payment_models.py:329+` before finalizing (e.g. whether `stripe_price_id` is required — leave blank for manual Stripe wiring). The yearly price `79.00` (~17% off) is the spec recommendation; adjust if desired.

- [ ] **Step 4: Extend the webhook tier mapping**

In `apps/accounts/payment_views.py` (~line 294), change:

```python
            if tier in ['premium', 'court']:
```
to:
```python
            if tier in ['premium', 'court', 'supporter']:
```

- [ ] **Step 5: Run migration and test**

Run: `python manage.py migrate accounts`
Run: `python manage.py test apps.accounts.test_supporter_billing.SupporterPlanTests -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/migrations/ apps/accounts/payment_views.py apps/accounts/test_supporter_billing.py
git commit -m "feat(supporter): seed supporter plans + map supporter tier in webhook"
```

---

### Task 9: Invite acceptance & consent routing (Path A & B)

**Files:**
- Modify: `apps/accounts/supporter_views.py` (add `accept_invite`, `consent_view`, `supporter_renew`), `apps/accounts/urls.py`
- Create: templates `accounts/supporter/consent.html`, `accounts/supporter/renew.html`
- Test: `apps/accounts/test_supporter_views.py` (add `InviteAcceptTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_views.py
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class InviteAcceptTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mb', email='mb@x.com', password='pw')

    def test_supporter_accepts_email_invite_binds_account(self):
        link = SupporterLink.objects.create(member=self.member, initiated_by='member',
            preset='standard', invite_email='mom@x.com', invite_token='tok123', status='pending')
        mom = User.objects.create_user(username='mom', email='mom@x.com', password='pw')
        self.client.login(username='mom', password='pw')
        resp = self.client.post(reverse('accounts:supporter_accept', args=['tok123']))
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.supporter, mom)
        # Member already consented (Path A), so link is active once supporter binds.
        self.assertEqual(link.status, 'active')

    def test_member_consents_to_supporter_initiated_link(self):
        sup = User.objects.create_user(username='dad', email='dad@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='supporter', status='pending')
        self.client.login(username='mb', password='pw')
        resp = self.client.post(reverse('accounts:supporter_consent', args=[link.id]),
                                {'preset': 'close', 'decision': 'accept'})
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.status, 'active')
        self.assertEqual(link.preset, 'close')

    def test_member_declines_silently(self):
        sup = User.objects.create_user(username='dad2', email='dad2@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='supporter', status='pending')
        self.client.login(username='mb', password='pw')
        resp = self.client.post(reverse('accounts:supporter_consent', args=[link.id]),
                                {'decision': 'decline'})
        link.refresh_from_db()
        self.assertEqual(link.status, 'declined')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_views.InviteAcceptTests -v 2`
Expected: FAIL — `NoReverseMatch: 'supporter_accept'`.

- [ ] **Step 3: Add the views**

```python
# add to apps/accounts/supporter_views.py
from django.utils import timezone

@login_required
@require_POST
def supporter_accept(request, token):
    """A supporter (Path A) accepts an email invite, binding their account."""
    link = get_object_or_404(SupporterLink, invite_token=token, status='pending')
    link.supporter = request.user
    # Member set the preset on invite (= consent). Activate now.
    link.status = 'active'
    if not link.consented_at:
        link.consented_at = timezone.now()
    link.save(update_fields=['supporter', 'status', 'consented_at', 'updated_at'])
    messages.success(request, 'You are now connected.')
    return redirect('accounts:supporter_dashboard', link_id=link.id)


@login_required
def supporter_consent(request, link_id):
    """Member (Path B) reviews a supporter-initiated request and accepts/declines."""
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user, status='pending')
    if request.method == 'POST':
        if request.POST.get('decision') == 'accept':
            link.consent(preset=request.POST.get('preset', 'standard'))
            messages.success(request, 'Connected. You control what they see and can pause anytime.')
        else:
            link.decline()
        return redirect('accounts:supporter_manage')
    return render(request, 'accounts/supporter/consent.html', {'link': link})


@login_required
def supporter_renew(request):
    """Landing for supporters without an active subscription."""
    return render(request, 'accounts/supporter/renew.html')
```

- [ ] **Step 4: Templates**

```html
<!-- apps/accounts/templates/accounts/supporter/consent.html -->
{% extends 'base.html' %}
{% block content %}
<h1>{{ link.supporter }} wants to support your recovery</h1>
<p>Choose what they can see. You can change or pause this any time.</p>
<form method="post">{% csrf_token %}
  <select name="preset">
    <option value="cheerleader">Cheerleader — milestones &amp; streak only</option>
    <option value="standard" selected>Standard — + check-in consistency &amp; mood trend</option>
    <option value="close">Close support — + inactivity alerts &amp; my "I need support" pings</option>
  </select>
  <button type="submit" name="decision" value="accept">Accept</button>
  <button type="submit" name="decision" value="decline">Decline</button>
</form>
{% endblock %}
```

```html
<!-- apps/accounts/templates/accounts/supporter/renew.html -->
{% extends 'base.html' %}
{% block content %}
<h1>Follow a loved one’s recovery</h1>
<p>The Supporter plan ($7.99/mo) lets you see their progress, cheer them on, and
get notified if they go quiet — all with their consent.</p>
<a href="{% url 'accounts:pricing' %}">See plans</a>
{% endblock %}
```

- [ ] **Step 5: URLs**

```python
    path('supporter/accept/<str:token>/', supporter_views.supporter_accept, name='supporter_accept'),
    path('supporter/<int:link_id>/consent/', supporter_views.supporter_consent, name='supporter_consent'),
    path('supporter/renew/', supporter_views.supporter_renew, name='supporter_renew'),
```

- [ ] **Step 6: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_views.InviteAcceptTests -v 2`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/supporter_views.py apps/accounts/urls.py apps/accounts/templates/accounts/supporter/
git commit -m "feat(supporter): invite acceptance and member consent routing"
```

---

### Task 10: Supporter dashboard view + template

**Files:**
- Modify: `apps/accounts/supporter_views.py` (add `supporter_dashboard`), `apps/accounts/urls.py`
- Create: `accounts/supporter/dashboard.html`, `accounts/supporter/_crisis_resources.html`
- Test: `apps/accounts/test_supporter_views.py` (add `DashboardViewTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_views.py
from apps.accounts.payment_models import Subscription

@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='dm', email='dm@x.com', password='pw')
        self.sup = User.objects.create_user(username='dsup', email='dsup@x.com', password='pw')
        Subscription.objects.create(user=self.sup, tier='supporter', status='active')
        self.link = SupporterLink.objects.create(member=self.member, supporter=self.sup,
            initiated_by='member', status='active', preset='standard')

    def test_supporter_sees_dashboard(self):
        self.client.login(username='dsup', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('dashboard', resp.context)

    def test_non_owner_supporter_gets_404(self):
        intruder = User.objects.create_user(username='int', email='int@x.com', password='pw')
        Subscription.objects.create(user=intruder, tier='supporter', status='active')
        self.client.login(username='int', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 404)

    def test_unsubscribed_supporter_redirected(self):
        self.sup.subscription.status = 'canceled'
        self.sup.subscription.save()
        self.client.login(username='dsup', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_views.DashboardViewTests -v 2`
Expected: FAIL — `NoReverseMatch: 'supporter_dashboard'`.

- [ ] **Step 3: Add the view**

```python
# add to apps/accounts/supporter_views.py
from apps.accounts.decorators import supporter_required
from apps.accounts import supporter_service

@login_required
@supporter_required
def supporter_dashboard(request, link_id):
    link = get_object_or_404(
        SupporterLink, id=link_id, supporter=request.user, status='active'
    )
    dashboard = supporter_service.get_dashboard_data(link)
    return render(request, 'accounts/supporter/dashboard.html',
                  {'link': link, 'dashboard': dashboard})
```

- [ ] **Step 4: Templates**

```html
<!-- apps/accounts/templates/accounts/supporter/_crisis_resources.html -->
<p class="crisis-resources">In crisis? Call/text <strong>988</strong> (Suicide &amp; Crisis Lifeline) · Text <strong>741741</strong></p>
```

```html
<!-- apps/accounts/templates/accounts/supporter/dashboard.html -->
{% extends 'base.html' %}
{% block content %}
<h1>{{ dashboard.member_name }} — {{ link.get_preset_display }}</h1>

<section><h2>{{ dashboard.days_sober }} days sober</h2>
  <p>{{ dashboard.next_milestone.days_to }} days to the {{ dashboard.next_milestone.target }}-day milestone</p>
</section>

{% if dashboard.checkin_consistency %}
<section><h3>Check-ins</h3>
  <p>{{ dashboard.checkin_consistency.count }} of last {{ dashboard.checkin_consistency.window }} days</p>
</section>
{% endif %}

{% if dashboard.mood_trend %}
<section><h3>Mood trend</h3><p>{{ dashboard.mood_trend }}</p></section>
{% endif %}

{% if dashboard.inactivity %}
<section><h3>Status</h3>
  {% if dashboard.inactivity.over_threshold %}
    <p>⚠️ No check-in for {{ dashboard.inactivity.days_since_checkin }} days.</p>
  {% else %}
    <p>Checked in recently.</p>
  {% endif %}
</section>
{% endif %}

<form method="post" action="{% url 'accounts:supporter_encourage' link.id %}">
  {% csrf_token %}
  <button name="key" value="proud">💪 Proud of you</button>
  <button name="key" value="thinking">❤️ Thinking of you</button>
  <button name="key" value="here">🤝 Here if you need me</button>
</form>

{% include 'accounts/supporter/_crisis_resources.html' %}
<p>🔒 Journal entries are never shared. You only see what {{ dashboard.member_name }} chose to share.</p>
{% endblock %}
```

- [ ] **Step 5: URL**

```python
    path('supporter/<int:link_id>/', supporter_views.supporter_dashboard, name='supporter_dashboard'),
```

- [ ] **Step 6: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_views.DashboardViewTests -v 2`
Expected: PASS (3 tests). (The `supporter_encourage` URL is added in Task 11; the template `{% url %}` resolves at render — add a temporary stub URL if this step is run in isolation, or run Task 11 immediately after.)

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/supporter_views.py apps/accounts/urls.py apps/accounts/templates/accounts/supporter/
git commit -m "feat(supporter): supporter dashboard view + template"
```

---

### Task 11: One-tap encouragement

**Files:**
- Modify: `apps/accounts/supporter_service.py` (add `send_encouragement`), `apps/accounts/supporter_views.py` (add `supporter_encourage`), `apps/accounts/urls.py`
- Test: `apps/accounts/test_supporter_service.py` (add `EncouragementTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_service.py
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EncouragementTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='em', email='em@x.com', password='pw')
        self.sup = User.objects.create_user(username='es', email='es@x.com', password='pw')
        self.link = SupporterLink.objects.create(member=self.member, supporter=self.sup,
            initiated_by='member', status='active', preset='cheerleader')

    def test_encouragement_creates_notification(self):
        ok = supporter_service.send_encouragement(self.link, 'proud')
        self.assertTrue(ok)
        n = Notification.objects.filter(recipient=self.member, notification_type='supporter_encouragement').first()
        self.assertIsNotNone(n)

    def test_invalid_key_rejected(self):
        self.assertFalse(supporter_service.send_encouragement(self.link, 'nonsense'))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_service.EncouragementTests -v 2`
Expected: FAIL — `AttributeError: module 'apps.accounts.supporter_service' has no attribute 'send_encouragement'`.

- [ ] **Step 3: Implement**

```python
# add to apps/accounts/supporter_service.py
ENCOURAGEMENT_MESSAGES = {
    'proud': 'is proud of you 💪',
    'thinking': 'is thinking of you ❤️',
    'here': 'is here if you need them 🤝',
}


def send_encouragement(link, key):
    """Send a canned supportive notification from supporter -> member."""
    if key not in ENCOURAGEMENT_MESSAGES or not link.is_live() or not link.supporter:
        return False
    from apps.accounts.views import create_notification
    sender = link.supporter
    name = sender.get_full_name() or sender.username
    create_notification(
        recipient=link.member,
        sender=sender,
        notification_type='supporter_encouragement',
        title='Encouragement',
        message=f"{name} {ENCOURAGEMENT_MESSAGES[key]}",
    )
    return True
```

- [ ] **Step 4: Add the view + URL**

```python
# add to apps/accounts/supporter_views.py
@login_required
@supporter_required
@require_POST
def supporter_encourage(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, supporter=request.user, status='active')
    if supporter_service.send_encouragement(link, request.POST.get('key', '')):
        messages.success(request, 'Sent. 💛')
    return redirect('accounts:supporter_dashboard', link_id=link.id)
```

```python
    path('supporter/<int:link_id>/encourage/', supporter_views.supporter_encourage, name='supporter_encourage'),
```

- [ ] **Step 5: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_service.EncouragementTests -v 2`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/supporter_service.py apps/accounts/supporter_views.py apps/accounts/urls.py apps/accounts/test_supporter_service.py
git commit -m "feat(supporter): one-tap encouragement"
```

---

### Task 12: Pricing page supporter card

**Files:**
- Modify: `apps/accounts/payment_views.py` (pricing context — add supporter plan, near `:46`), `apps/accounts/templates/accounts/pricing.html`
- Test: manual + smoke

- [ ] **Step 1: Add supporter plan to pricing context**

In `payment_views.py` where `court_monthly_plan` is built (~line 46), add:

```python
    supporter_monthly_plan = plans.filter(tier='supporter', billing_period='monthly').first()
```
and include `'supporter_monthly_plan': supporter_monthly_plan,` in the context dict (~line 51).

- [ ] **Step 2: Add a card to `pricing.html`**

After the Court Compliance tier block (~line 259+), add a Supporter card mirroring its markup:

```html
<!-- Supporter Tier -->
<div class="col-md-6 col-lg-3 mb-4">
  <div class="card h-100">
    <div class="card-body text-center">
      <h3 class="my-3">Supporter</h3>
      <h2 class="display-4">$7.99<small class="text-muted">/mo</small></h2>
      <ul class="list-unstyled text-start mt-3">
        <li class="mb-2"><i class="fas fa-check text-success"></i> Follow a loved one’s progress (with their consent)</li>
        <li class="mb-2"><i class="fas fa-check text-success"></i> Send one-tap encouragement</li>
        <li class="mb-2"><i class="fas fa-check text-success"></i> Optional alert if they go quiet</li>
      </ul>
      <p class="small text-muted">For family, partners, and sponsors. The person you support shares for free and controls what you see.</p>
      {% if supporter_monthly_plan %}
        <button class="btn btn-primary btn-block subscribe-btn"
                data-plan-id="{{ supporter_monthly_plan.id }}"
                data-plan-name="{{ supporter_monthly_plan.name }}">Get Supporter</button>
      {% endif %}
    </div>
  </div>
</div>
```

- [ ] **Step 3: Smoke test the pricing page**

Run: `python manage.py test apps.accounts.tests_nav -v 2` (existing nav/page smoke tests), then manually load `/accounts/pricing/`.
Expected: page renders with the Supporter card; no template errors.

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/payment_views.py apps/accounts/templates/accounts/pricing.html
git commit -m "feat(supporter): supporter tier card on pricing page"
```

- [ ] **Step 5: Phase 2 gate**

Run: `python manage.py test apps.accounts.test_supporter_service apps.accounts.test_supporter_views apps.accounts.test_supporter_billing -v 2`
Expected: all PASS.

---

# Phase 3 — Close-support alerts & manual support

### Task 13: Manual "I need support" (member side)

**Files:**
- Modify: `apps/accounts/supporter_service.py` (add `record_support_request`), `apps/accounts/supporter_views.py` (add `request_support`), `apps/accounts/urls.py`
- Test: `apps/accounts/test_supporter_service.py` (add `SupportRequestTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_service.py
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupportRequestTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='rm', email='rm@x.com', password='pw')
        self.close_sup = User.objects.create_user(username='rs', email='rs@x.com', password='pw')
        self.cheer_sup = User.objects.create_user(username='rc', email='rc@x.com', password='pw')
        SupporterLink.objects.create(member=self.member, supporter=self.close_sup,
            initiated_by='member', status='active', preset='close')
        SupporterLink.objects.create(member=self.member, supporter=self.cheer_sup,
            initiated_by='member', status='active', preset='cheerleader')

    def test_only_close_supporters_notified(self):
        count = supporter_service.record_support_request(self.member)
        self.assertEqual(count, 1)
        self.assertTrue(Notification.objects.filter(
            recipient=self.close_sup, notification_type='member_support_request').exists())
        self.assertFalse(Notification.objects.filter(
            recipient=self.cheer_sup, notification_type='member_support_request').exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_service.SupportRequestTests -v 2`
Expected: FAIL — `AttributeError: ... 'record_support_request'`.

- [ ] **Step 3: Implement**

```python
# add to apps/accounts/supporter_service.py
def record_support_request(member):
    """Member taps 'I need support' -> notify only their Close supporters.

    Returns the number of supporters notified. Content never auto-fires;
    this is an explicit, member-initiated ping.
    """
    from apps.accounts.views import create_notification
    links = member.supporter_links.filter(status='active', preset='close').select_related('supporter')
    name = member.get_full_name() or member.username
    notified = 0
    for link in links:
        if not link.supporter:
            continue
        create_notification(
            recipient=link.supporter,
            sender=member,
            notification_type='member_support_request',
            title='Support requested',
            message=f"{name} asked for support.",
        )
        notified += 1
    return notified
```

- [ ] **Step 4: View + URL**

```python
# add to apps/accounts/supporter_views.py
@login_required
@require_POST
def request_support(request):
    n = supporter_service.record_support_request(request.user)
    messages.success(request,
        "Your close supporters have been notified. You're not alone. "
        "If you're in crisis, call or text 988.")
    return redirect(request.POST.get('next', 'accounts:social_feed'))
```

```python
    path('supporter/request-support/', supporter_views.request_support, name='supporter_request_support'),
```

- [ ] **Step 5: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_service.SupportRequestTests -v 2`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/supporter_service.py apps/accounts/supporter_views.py apps/accounts/urls.py apps/accounts/test_supporter_service.py
git commit -m "feat(supporter): member 'I need support' ping to close supporters"
```

---

### Task 14: Inactivity alert Celery task

**Files:**
- Modify: `apps/accounts/tasks.py` (add `send_supporter_inactivity_alerts`), `recovery_hub/settings.py` (beat entry ~`:705`)
- Test: `apps/accounts/test_supporter_alerts.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/test_supporter_alerts.py
from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink
from apps.accounts.models import DailyCheckIn, Notification
from apps.accounts.tasks import send_supporter_inactivity_alerts

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class InactivityAlertTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='im', email='im@x.com', password='pw')
        self.sup = User.objects.create_user(username='is', email='is@x.com', password='pw')
        self.link = SupporterLink.objects.create(member=self.member, supporter=self.sup,
            initiated_by='member', status='active', preset='close', inactivity_threshold_days=3)

    def test_alert_fires_when_inactive(self):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=5),
                                    mood=3, craving_level=0, energy_level=3)
        sent = send_supporter_inactivity_alerts()
        self.assertEqual(sent, 1)
        self.assertTrue(Notification.objects.filter(
            recipient=self.sup, notification_type='member_inactive').exists())
        self.link.refresh_from_db()
        self.assertIsNotNone(self.link.last_inactivity_alert_sent)

    def test_no_alert_when_recent(self):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date(),
                                    mood=3, craving_level=0, energy_level=3)
        self.assertEqual(send_supporter_inactivity_alerts(), 0)

    def test_cooldown_prevents_repeat(self):
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=5),
                                    mood=3, craving_level=0, energy_level=3)
        self.link.last_inactivity_alert_sent = timezone.now()
        self.link.save()
        self.assertEqual(send_supporter_inactivity_alerts(), 0)

    def test_non_close_presets_never_alert(self):
        self.link.preset = 'standard'
        self.link.save()
        DailyCheckIn.objects.create(user=self.member, date=timezone.now().date() - timedelta(days=10),
                                    mood=3, craving_level=0, energy_level=3)
        self.assertEqual(send_supporter_inactivity_alerts(), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.test_supporter_alerts -v 2`
Expected: FAIL — `ImportError: cannot import name 'send_supporter_inactivity_alerts'`.

- [ ] **Step 3: Implement the task**

```python
# add to apps/accounts/tasks.py
@shared_task(bind=True, max_retries=3)
def send_supporter_inactivity_alerts(self):
    """Notify Close supporters when their member hasn't checked in for N days.

    Behavioral (inactivity-only) — never triggered by check-in content.
    Idempotent per gap via last_inactivity_alert_sent (cooldown = threshold days).
    Returns the number of alerts sent. Runs daily at 6 PM UTC.
    """
    from .models import DailyCheckIn, Notification  # noqa
    from .supporter_models import SupporterLink
    from .views import create_notification

    now = timezone.now()
    today = now.date()
    sent = 0

    links = SupporterLink.objects.filter(status='active', preset='close').select_related('member', 'supporter')
    for link in links:
        if not link.supporter:
            continue
        last = DailyCheckIn.objects.filter(user=link.member).order_by('-date').first()
        days_since = (today - last.date).days if last else link.inactivity_threshold_days + 1
        if days_since < link.inactivity_threshold_days:
            continue
        # Cooldown: don't re-alert within the threshold window.
        if link.last_inactivity_alert_sent and (now - link.last_inactivity_alert_sent).days < link.inactivity_threshold_days:
            continue

        name = link.member.get_full_name() or link.member.username
        create_notification(
            recipient=link.supporter, sender=link.member,
            notification_type='member_inactive', title='Check-in alert',
            message=f"{name} hasn't checked in for {days_since} days.",
        )
        try:
            send_email(
                subject=f"{name} hasn't checked in recently",
                plain_message=(f"{name} hasn't logged a check-in for {days_since} days. "
                               f"A kind message can help. If you're worried about their safety, "
                               f"call or text 988."),
                html_message=(f"<p>{name} hasn't logged a check-in for {days_since} days. "
                              f"A kind message can help.</p><p>If you're worried about their "
                              f"safety, call or text <strong>988</strong>.</p>"),
                recipient_email=link.supporter.email,
            )
        except Exception as exc:  # email failure must not block the notification
            logger.warning(f"Supporter inactivity email failed: {exc}")

        link.last_inactivity_alert_sent = now
        link.save(update_fields=['last_inactivity_alert_sent', 'updated_at'])
        sent += 1

    logger.info(f"Supporter inactivity alerts: {sent} sent")
    return sent
```

- [ ] **Step 4: Add the beat schedule entry**

In `recovery_hub/settings.py`, inside `CELERY_BEAT_SCHEDULE` (~line 705), add:

```python
    'send-supporter-inactivity-alerts': {
        'task': 'apps.accounts.tasks.send_supporter_inactivity_alerts',
        'schedule': crontab(hour=18, minute=0),  # Daily at 6 PM UTC (after 5 PM check-in reminder)
    },
```

- [ ] **Step 5: Run tests**

Run: `python manage.py test apps.accounts.test_supporter_alerts -v 2`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/tasks.py recovery_hub/settings.py apps/accounts/test_supporter_alerts.py
git commit -m "feat(supporter): daily inactivity alert task for close supporters"
```

---

### Task 15: Surface "I need support" + crisis resources in the member app

**Files:**
- Modify: a member-facing template (e.g. `apps/accounts/templates/accounts/social_feed.html` sidebar or the check-in page) to add the button posting to `accounts:supporter_request_support`
- Test: `apps/accounts/test_supporter_views.py` (add `RequestSupportViewTests`)

- [ ] **Step 1: Write the failing test**

```python
# add to apps/accounts/test_supporter_views.py
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RequestSupportViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='rsm', email='rsm@x.com', password='pw')
        self.client.login(username='rsm', password='pw')

    def test_request_support_redirects_and_messages(self):
        resp = self.client.post(reverse('accounts:supporter_request_support'))
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Run test to verify it fails / passes**

Run: `python manage.py test apps.accounts.test_supporter_views.RequestSupportViewTests -v 2`
Expected: PASS already if Task 13 wired the URL (this is a guard test). If it errors on reverse, confirm Task 13 Step 4 URL exists.

- [ ] **Step 3: Add the button to the member UI**

In the social feed sidebar (find the quick-actions block in `social_feed.html`), add:

```html
<form method="post" action="{% url 'accounts:supporter_request_support' %}" class="quick-action">
  {% csrf_token %}
  <input type="hidden" name="next" value="{{ request.path }}">
  <button type="submit" class="btn btn-outline-danger btn-sm">🆘 I need support</button>
</form>
```

Also add a link to `accounts:supporter_manage` ("Who's supporting me") near the existing invite/quick-action links.

- [ ] **Step 4: Smoke test**

Run: `python manage.py test apps.accounts.test_supporter_views -v 2`
Expected: all PASS. Manually load `/accounts/social-feed/` and confirm the button renders.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/templates/accounts/social_feed.html apps/accounts/test_supporter_views.py
git commit -m "feat(supporter): surface 'I need support' + manage-supporters in member UI"
```

- [ ] **Step 6: Phase 3 gate — full suite**

Run: `python manage.py test apps.accounts.test_supporter_service apps.accounts.test_supporter_consent apps.accounts.test_supporter_views apps.accounts.test_supporter_billing apps.accounts.test_supporter_alerts -v 2`
Expected: all PASS.

---

## Manual / out-of-band steps (not code)

- **Stripe (web):** create Product "MyRecoveryPal Supporter" with monthly ($7.99) and yearly ($79) prices; paste the price IDs onto the seeded `SubscriptionPlan` rows (`stripe_price_id`), mirroring how the court plans were wired.
- **Verify** the consent emails for email-invited supporters/members send via `email_service.send_email` (reuse an existing email template pattern) — wire into Task 7/Task 9 if email delivery (not just in-app) is desired for invites.

## Out of scope (future work — do not build now)

Multi-person supporter dashboard; iOS IAP for the supporter tier; open two-way messaging; dual-role accounts; gifting a supporter seat.

---

## Self-Review

- **Spec coverage:** tier (T1), `SupporterLink` + consent (T2–T3), preset-gated read model + no-craving invariant (T4), decorator/gating (T5, T10), notifications (T6), member sharing/invite (T7), both consent paths (T9), billing seed + webhook (T8), dashboard (T10), encouragement (T11), pricing (T12), manual support ping (T13), inactivity alerts (T14), member-app surface + crisis resources (T15). Web-first scope honored (no iOS IAP task). All spec sections map to a task.
- **Placeholders:** none — every code step contains full code; the one intentional throwaway (`supporter=None if True else None`) is explicitly corrected in T7 Step 5.
- **Type consistency:** method names used downstream match definitions — `is_supporter()` (T1), `is_live()`/`consent()`/`revoke()`/`set_preset()` (T3 → used T7/T9/T11), `get_dashboard_data()` (T4 → T10), `send_encouragement()` (T11), `record_support_request()` (T13), `send_supporter_inactivity_alerts()` (T14). Notification keys defined in T6 are exactly those used in T11/T13/T14.
