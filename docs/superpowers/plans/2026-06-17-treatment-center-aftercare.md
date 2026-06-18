# Treatment-Center Aftercare Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a treatment center monitor its alumni's post-discharge engagement and spot at-risk clients early, via a consent-gated staff dashboard and weekly digest.

**Architecture:** Dedicated `Facility*` models in a new isolated module (mirrors `court_models.py`/`court_service.py`). At-risk status is computed live from existing `DailyCheckIn` data — no new metric tables. Facilities are provisioned manually; alumni use the free consumer app and opt in via an invite link.

**Tech Stack:** Django 5.0, PostgreSQL, Celery (weekly beat task), existing `email_service.send_email`, Django `TestCase`.

## Global Constraints

- **Privacy invariants (never violate):** journal entries never exposed; raw `gratitude`/`challenge`/`goal` check-in text never exposed; only derived signals surface to staff; no data for a membership unless `status == 'active'` AND `consent_granted_at is not None`; staff of facility A can never see facility B.
- **Clients are free users** — no Premium gating on alumni; the facility pays (offline, no billing code).
- **No self-serve org billing, no real-time alerts, no in-app staff↔client messaging, no risk snapshots** (compute-on-read) — all out of scope.
- **Follow existing patterns:** decorators in `apps/accounts/decorators.py`; function-based views imported into `apps/accounts/urls.py`; tests as `apps/accounts/tests_*.py` using `django.test.TestCase`.
- **Run tests with:** `python manage.py test apps.accounts.tests_facility -v 2` (Django test runner, sqlite test DB — boots fine locally without prod env).
- **Risk thresholds (verbatim):** disengaged ≥ 5 days since last check-in; high craving = `craving_level >= 4` (Intense) within 7 days; low mood = `mood <= 1` (Struggling) within 7 days; `watch` = 3–4 days quiet with no flag; else `ok`.

---

### Task 1: Facility data models + migration

**Files:**
- Create: `apps/accounts/facility_models.py`
- Modify: `apps/accounts/admin.py` (register models for manual inspection)
- Test: `apps/accounts/tests_facility.py`

**Interfaces:**
- Produces:
  - `Facility(name, slug, status, monthly_rate, notes, created_at)`; `STATUS_CHOICES` = `active`/`paused`.
  - `FacilityStaff(facility, user, role, created_at)`; `ROLE_CHOICES` = `admin`/`coordinator`; related_names `facility.staff`, `user.facility_staff_roles`.
  - `FacilityMembership(facility, user, status, consent_granted_at, enrolled_at, left_at, risk_notified_at, created_at)`; `STATUS_CHOICES` = `invited`/`active`/`revoked`/`left`; related_names `facility.memberships`, `user.facility_memberships`; property `is_visible_to_staff` → `status == 'active' and consent_granted_at is not None`.
  - `FacilityInvite(facility, code, created_by, uses, max_uses, expires_at, created_at)`; method `is_valid()` → not expired and under max_uses; classmethod `generate_code()`.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py
"""Tests for the treatment-center aftercare (Facility) feature."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.accounts.facility_models import (
    Facility, FacilityStaff, FacilityMembership, FacilityInvite,
)

User = get_user_model()


class FacilityModelTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope Center', slug='hope-center')
        self.client_user = User.objects.create_user(
            username='alum1', email='alum1@example.com', password='pw')

    def test_membership_not_visible_without_consent(self):
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.client_user, status='invited')
        self.assertFalse(m.is_visible_to_staff)

    def test_membership_visible_when_active_and_consented(self):
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.client_user,
            status='active', consent_granted_at=timezone.now())
        self.assertTrue(m.is_visible_to_staff)

    def test_invite_validity(self):
        valid = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code())
        self.assertTrue(valid.is_valid())

        expired = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code(),
            expires_at=timezone.now() - timedelta(days=1))
        self.assertFalse(expired.is_valid())

        maxed = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code(),
            uses=3, max_uses=3)
        self.assertFalse(maxed.is_valid())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.accounts.facility_models'`

- [ ] **Step 3: Write the models**

```python
# apps/accounts/facility_models.py
"""
Treatment-center aftercare models. A Facility (org) monitors its alumni's
post-discharge engagement. Alumni opt in via FacilityInvite; FacilityMembership
is the consent record. See docs/superpowers/specs/2026-06-17-treatment-center-aftercare-design.md
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class Facility(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('paused', 'Paused')]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    monthly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Record-keeping only; billing is handled offline.')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facilities'
        verbose_name_plural = 'facilities'

    def __str__(self):
        return self.name


class FacilityStaff(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('coordinator', 'Coordinator')]

    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='facility_staff_roles')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='coordinator')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_staff'
        unique_together = ('facility', 'user')

    def __str__(self):
        return f'{self.user} @ {self.facility} ({self.role})'


class FacilityMembership(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'), ('active', 'Active'),
        ('revoked', 'Revoked'), ('left', 'Left'),
    ]

    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='facility_memberships')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='invited')
    consent_granted_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    # Drives the "newly at-risk" weekly digest: stamped when included as at-risk,
    # cleared when the member returns to ok.
    risk_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_memberships'
        unique_together = ('facility', 'user')

    def __str__(self):
        return f'{self.user} @ {self.facility} ({self.status})'

    @property
    def is_visible_to_staff(self):
        return self.status == 'active' and self.consent_granted_at is not None


class FacilityInvite(models.Model):
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='invites')
    code = models.CharField(max_length=40, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_facility_invites')
    uses = models.IntegerField(default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_invites'

    def __str__(self):
        return f'{self.code} ({self.facility})'

    @staticmethod
    def generate_code():
        return secrets.token_urlsafe(12)

    def is_valid(self):
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        return True
```

- [ ] **Step 4: Register in admin**

```python
# apps/accounts/admin.py — add at end of file
from apps.accounts.facility_models import (
    Facility, FacilityStaff, FacilityMembership, FacilityInvite,
)

admin.site.register(Facility)
admin.site.register(FacilityStaff)
admin.site.register(FacilityMembership)
admin.site.register(FacilityInvite)
```

- [ ] **Step 5: Make migration**

Run: `python manage.py makemigrations accounts`
Expected: new migration creating Facility, FacilityStaff, FacilityMembership, FacilityInvite.

- [ ] **Step 6: Run tests**

Run: `python manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/facility_models.py apps/accounts/admin.py apps/accounts/migrations/ apps/accounts/tests_facility.py
git commit -m "feat(b2b): facility aftercare models + consent record"
```

---

### Task 2: At-risk computation service

**Files:**
- Create: `apps/accounts/facility_service.py`
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `FacilityMembership` (Task 1); `User.daily_checkins`, `User.get_checkin_streak()`, `User.get_days_sober()`; `DailyCheckIn(date, mood, craving_level)`.
- Produces:
  - Constants: `RISK_OK='ok'`, `RISK_WATCH='watch'`, `RISK_AT_RISK='at_risk'`.
  - `compute_member_risk(membership)` → dict: `{risk_level, flags, last_checkin_date, checkin_streak, days_sober, craving_trend, mood_trend}` where `flags` ⊆ `{'disengaged','high_craving','low_mood'}` and trends ∈ `{'up','down','flat',None}`.
  - `cohort_summary(facility)` → dict: `{total, ok, watch, at_risk}` over visible (active + consented) members.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py — append
from apps.accounts.models import DailyCheckIn
from apps.accounts import facility_service as fs


class RiskComputationTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.user = User.objects.create_user(
            username='u', email='u@example.com', password='pw')
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.user,
            status='active', consent_granted_at=timezone.now())

    def _checkin(self, days_ago, mood=4, craving=0):
        return DailyCheckIn.objects.create(
            user=self.user, date=timezone.now().date() - timedelta(days=days_ago),
            mood=mood, craving_level=craving, energy_level=3)

    def test_no_checkins_is_at_risk_disengaged(self):
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_AT_RISK)
        self.assertIn('disengaged', r['flags'])

    def test_recent_engaged_is_ok(self):
        self._checkin(0, mood=5, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_OK)
        self.assertEqual(r['flags'], [])

    def test_high_craving_is_at_risk(self):
        self._checkin(0, mood=4, craving=4)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_AT_RISK)
        self.assertIn('high_craving', r['flags'])

    def test_struggling_mood_is_at_risk(self):
        self._checkin(1, mood=1, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertIn('low_mood', r['flags'])

    def test_quiet_three_days_is_watch(self):
        self._checkin(3, mood=4, craving=0)
        r = fs.compute_member_risk(self.m)
        self.assertEqual(r['risk_level'], fs.RISK_WATCH)

    def test_cohort_summary_counts_only_visible(self):
        # an invited (non-consented) member must not count
        other = User.objects.create_user(username='o', email='o@x.com', password='pw')
        FacilityMembership.objects.create(
            facility=self.facility, user=other, status='invited')
        summary = fs.cohort_summary(self.facility)
        self.assertEqual(summary['total'], 1)
        self.assertEqual(summary['at_risk'], 1)  # self.user has no check-ins
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility.RiskComputationTest -v 2`
Expected: FAIL — `No module named 'apps.accounts.facility_service'`

- [ ] **Step 3: Write the service**

```python
# apps/accounts/facility_service.py
"""
At-risk computation for treatment-center aftercare. Derives engagement signals
from DailyCheckIn — never exposes raw note text. Computed on read.
"""
from datetime import timedelta

from django.utils import timezone

DISENGAGED_DAYS = 5
WATCH_DAYS = 3
RISK_WINDOW_DAYS = 7
HIGH_CRAVING_LEVEL = 4   # Intense
LOW_MOOD_LEVEL = 1       # Struggling

RISK_OK = 'ok'
RISK_WATCH = 'watch'
RISK_AT_RISK = 'at_risk'


def _trend(values):
    """values chronological (oldest first). Returns up/down/flat/None."""
    if len(values) < 4:
        return None
    mid = len(values) // 2
    prior, recent = values[:mid], values[mid:]
    diff = (sum(recent) / len(recent)) - (sum(prior) / len(prior))
    if diff > 0.5:
        return 'up'
    if diff < -0.5:
        return 'down'
    return 'flat'


def compute_member_risk(membership):
    user = membership.user
    today = timezone.now().date()
    # Most recent 14 check-ins, newest first.
    checkins = list(user.daily_checkins.order_by('-date')[:14])
    last_date = checkins[0].date if checkins else None
    days_since = (today - last_date).days if last_date else None

    window_start = today - timedelta(days=RISK_WINDOW_DAYS)
    recent = [c for c in checkins if c.date >= window_start]

    flags = []
    if days_since is None or days_since >= DISENGAGED_DAYS:
        flags.append('disengaged')
    if any(c.craving_level >= HIGH_CRAVING_LEVEL for c in recent):
        flags.append('high_craving')
    if any(c.mood <= LOW_MOOD_LEVEL for c in recent):
        flags.append('low_mood')

    if flags:
        risk = RISK_AT_RISK
    elif days_since is not None and days_since >= WATCH_DAYS:
        risk = RISK_WATCH
    else:
        risk = RISK_OK

    chrono = list(reversed(checkins))  # oldest first
    return {
        'risk_level': risk,
        'flags': flags,
        'last_checkin_date': last_date,
        'checkin_streak': user.get_checkin_streak(),
        'days_sober': user.get_days_sober(),
        'craving_trend': _trend([c.craving_level for c in chrono]),
        'mood_trend': _trend([c.mood for c in chrono]),
    }


def visible_memberships(facility):
    """Active, consented members only — the privacy boundary."""
    return facility.memberships.filter(
        status='active', consent_granted_at__isnull=False
    ).select_related('user')


def cohort_summary(facility):
    counts = {'total': 0, RISK_OK: 0, RISK_WATCH: 0, RISK_AT_RISK: 0}
    for m in visible_memberships(facility):
        counts['total'] += 1
        counts[compute_member_risk(m)['risk_level']] += 1
    return counts
```

- [ ] **Step 4: Run tests**

Run: `python manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/facility_service.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): at-risk computation service (compute-on-read)"
```

---

### Task 3: Enrollment, consent, and revoke

**Files:**
- Create: `apps/accounts/facility_views.py`
- Create: `apps/accounts/templates/accounts/facility/join_consent.html`
- Modify: `apps/accounts/urls.py` (add join + revoke routes)
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `Facility`, `FacilityMembership`, `FacilityInvite` (Task 1).
- Produces (URL names): `accounts:facility_join` (`facility/join/<code>/`), `accounts:facility_leave` (`facility/leave/<int:membership_id>/`).
  - `facility_join(request, code)`: GET renders consent screen (login-required, redirects to login with `?next=`); POST with `consent=on` activates membership (`status='active'`, `consent_granted_at`/`enrolled_at` set), increments invite `uses`. Idempotent for an existing active membership.
  - `facility_leave(request, membership_id)`: POST only; the **member** revoking their own consent → `status='revoked'`, `left_at` set.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py — append
from django.urls import reverse


class EnrollmentConsentTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.invite = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code())
        self.user = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')

    def test_join_requires_login(self):
        resp = self.client.get(
            reverse('accounts:facility_join', args=[self.invite.code]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.url)

    def test_consent_activates_membership(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]),
            {'consent': 'on'})
        self.assertEqual(resp.status_code, 302)
        m = FacilityMembership.objects.get(facility=self.facility, user=self.user)
        self.assertEqual(m.status, 'active')
        self.assertIsNotNone(m.consent_granted_at)
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.uses, 1)

    def test_join_without_consent_does_not_activate(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]), {})
        self.assertFalse(FacilityMembership.objects.filter(
            facility=self.facility, user=self.user, status='active').exists())

    def test_expired_invite_rejected(self):
        self.invite.expires_at = timezone.now() - timedelta(days=1)
        self.invite.save()
        self.client.force_login(self.user)
        self.client.post(
            reverse('accounts:facility_join', args=[self.invite.code]),
            {'consent': 'on'})
        self.assertFalse(FacilityMembership.objects.filter(
            facility=self.facility, user=self.user, status='active').exists())

    def test_member_can_revoke(self):
        self.client.force_login(self.user)
        m = FacilityMembership.objects.create(
            facility=self.facility, user=self.user,
            status='active', consent_granted_at=timezone.now())
        self.client.post(reverse('accounts:facility_leave', args=[m.id]))
        m.refresh_from_db()
        self.assertEqual(m.status, 'revoked')
        self.assertFalse(m.is_visible_to_staff)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility.EnrollmentConsentTest -v 2`
Expected: FAIL — `Reverse for 'facility_join' not found`.

- [ ] **Step 3: Write the views**

```python
# apps/accounts/facility_views.py
"""Treatment-center aftercare views: enrollment/consent (client) + dashboard (staff)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.facility_models import (
    Facility, FacilityInvite, FacilityMembership,
)


@login_required
def facility_join(request, code):
    invite = get_object_or_404(FacilityInvite, code=code)
    facility = invite.facility

    membership = FacilityMembership.objects.filter(
        facility=facility, user=request.user).first()
    if membership and membership.status == 'active':
        messages.info(request, f'You are already sharing with {facility.name}.')
        return redirect('accounts:progress')

    if request.method == 'POST':
        if request.POST.get('consent') != 'on':
            messages.warning(request, 'You must consent in order to join.')
            return render(request, 'accounts/facility/join_consent.html',
                          {'facility': facility, 'code': code})
        if not invite.is_valid():
            messages.error(request, 'This invite link is no longer valid.')
            return redirect('accounts:progress')

        now = timezone.now()
        if membership is None:
            membership = FacilityMembership(facility=facility, user=request.user)
        membership.status = 'active'
        membership.consent_granted_at = now
        membership.enrolled_at = now
        membership.left_at = None
        membership.save()

        invite.uses += 1
        invite.save(update_fields=['uses'])

        messages.success(request, f'You are now connected with {facility.name}.')
        return redirect('accounts:progress')

    return render(request, 'accounts/facility/join_consent.html',
                  {'facility': facility, 'code': code})


@login_required
@require_POST
def facility_leave(request, membership_id):
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, user=request.user)
    membership.status = 'revoked'
    membership.left_at = timezone.now()
    membership.save(update_fields=['status', 'left_at'])
    messages.success(request, 'You have stopped sharing with your facility.')
    return redirect('accounts:progress')
```

- [ ] **Step 4: Write the consent template**

```html
<!-- apps/accounts/templates/accounts/facility/join_consent.html -->
{% extends "base.html" %}
{% block content %}
<div class="container" style="max-width:600px;margin:2rem auto;">
  <h1>Connect with {{ facility }}</h1>
  <p>{{ facility }} would like to support your recovery after discharge.</p>
  <p>If you consent, your care team will be able to see your
     <strong>check-in engagement and risk signals</strong> (such as whether
     you've been checking in, your sobriety streak, and craving/mood trends)
     so they can reach out if you're struggling.</p>
  <p><strong>Your journal is never shared.</strong> The exact words you write in
     check-ins are never shared. You can stop sharing at any time.</p>
  <form method="post">
    {% csrf_token %}
    <label>
      <input type="checkbox" name="consent">
      I consent to share my engagement and risk signals with {{ facility }}.
    </label>
    <button type="submit" class="btn btn-primary">Connect</button>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 5: Add URL routes**

```python
# apps/accounts/urls.py
# add to the imports from .facility_views:
from .facility_views import facility_join, facility_leave
# add inside urlpatterns:
    path('facility/join/<str:code>/', facility_join, name='facility_join'),
    path('facility/leave/<int:membership_id>/', facility_leave, name='facility_leave'),
```

- [ ] **Step 6: Run tests**

Run: `python manage.py test apps.accounts.tests_facility.EnrollmentConsentTest -v 2`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/facility_views.py apps/accounts/templates/accounts/facility/join_consent.html apps/accounts/urls.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): invite-link enrollment with consent gate + member revoke"
```

---

### Task 4: Staff dashboard, roster, member detail (+ decorator)

**Files:**
- Modify: `apps/accounts/decorators.py` (add `facility_staff_required`)
- Modify: `apps/accounts/facility_views.py` (add staff views)
- Create: `apps/accounts/templates/accounts/facility/dashboard.html`
- Create: `apps/accounts/templates/accounts/facility/roster.html`
- Create: `apps/accounts/templates/accounts/facility/member_detail.html`
- Modify: `apps/accounts/urls.py`
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `facility_service.cohort_summary`, `compute_member_risk`, `visible_memberships`; `FacilityStaff`, `FacilityMembership`, `FacilityInvite`.
- Produces:
  - `facility_staff_required(view_func)` — sets `request.facility_staff` and `request.facility`; redirects non-staff to `accounts:progress`.
  - URL names: `accounts:facility_dashboard` (`facility/`), `accounts:facility_roster` (`facility/roster/`), `accounts:facility_member` (`facility/member/<int:membership_id>/`), `accounts:facility_generate_invite` (`facility/invite/new/`, POST), `accounts:facility_revoke_member` (`facility/member/<int:membership_id>/revoke/`, POST).

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py — append
class StaffDashboardTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.other = Facility.objects.create(name='Rival', slug='rival')
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='pw')
        FacilityStaff.objects.create(facility=self.facility, user=self.staff_user)
        self.alum = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.alum,
            status='active', consent_granted_at=timezone.now())

    def test_non_staff_blocked(self):
        self.client.force_login(self.alum)
        resp = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_staff_sees_dashboard(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'alum')

    def test_tenant_isolation_on_member_detail(self):
        # a membership in the rival facility must 404 for this staff
        rival_member = FacilityMembership.objects.create(
            facility=self.other, user=self.alum,
            status='active', consent_granted_at=timezone.now())
        self.client.force_login(self.staff_user)
        resp = self.client.get(
            reverse('accounts:facility_member', args=[rival_member.id]))
        self.assertEqual(resp.status_code, 404)

    def test_member_detail_hidden_without_consent(self):
        self.m.consent_granted_at = None
        self.m.status = 'invited'
        self.m.save()
        self.client.force_login(self.staff_user)
        resp = self.client.get(
            reverse('accounts:facility_member', args=[self.m.id]))
        self.assertEqual(resp.status_code, 404)

    def test_generate_invite(self):
        self.client.force_login(self.staff_user)
        resp = self.client.post(reverse('accounts:facility_generate_invite'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FacilityInvite.objects.filter(facility=self.facility).exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility.StaffDashboardTest -v 2`
Expected: FAIL — `Reverse for 'facility_dashboard' not found`.

- [ ] **Step 3: Add the decorator**

```python
# apps/accounts/decorators.py — add (mirrors court_required)
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def facility_staff_required(view_func):
    """Requires the user to be staff of an active facility.
    Attaches request.facility_staff and request.facility."""
    from apps.accounts.facility_models import FacilityStaff

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')
        staff = (FacilityStaff.objects
                 .select_related('facility')
                 .filter(user=request.user, facility__status='active')
                 .first())
        if not staff:
            messages.warning(request, 'You do not have a facility dashboard.')
            return redirect('accounts:progress')
        request.facility_staff = staff
        request.facility = staff.facility
        return view_func(request, *args, **kwargs)
    return wrapper
```

- [ ] **Step 4: Add staff views**

```python
# apps/accounts/facility_views.py — append
from apps.accounts.decorators import facility_staff_required
from apps.accounts.facility_models import FacilityInvite as _Invite  # for clarity
from apps.accounts import facility_service as fs

RISK_ORDER = {fs.RISK_AT_RISK: 0, fs.RISK_WATCH: 1, fs.RISK_OK: 2}


@facility_staff_required
def facility_dashboard(request):
    facility = request.facility
    rows = []
    for m in fs.visible_memberships(facility):
        risk = fs.compute_member_risk(m)
        rows.append({'membership': m, 'risk': risk})
    rows.sort(key=lambda r: RISK_ORDER[r['risk']['risk_level']])
    return render(request, 'accounts/facility/dashboard.html', {
        'facility': facility,
        'summary': fs.cohort_summary(facility),
        'rows': rows,
    })


@facility_staff_required
def facility_roster(request):
    facility = request.facility
    members = facility.memberships.select_related('user').order_by('-created_at')
    invites = facility.invites.order_by('-created_at')
    return render(request, 'accounts/facility/roster.html', {
        'facility': facility, 'members': members, 'invites': invites,
    })


@facility_staff_required
def facility_member_detail(request, membership_id):
    # tenant isolation + consent gate enforced in the queryset
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, facility=request.facility,
        status='active', consent_granted_at__isnull=False)
    return render(request, 'accounts/facility/member_detail.html', {
        'facility': request.facility,
        'membership': membership,
        'risk': fs.compute_member_risk(membership),
    })


@facility_staff_required
@require_POST
def facility_generate_invite(request):
    FacilityInvite.objects.create(
        facility=request.facility, code=FacilityInvite.generate_code(),
        created_by=request.user)
    messages.success(request, 'New invite link created.')
    return redirect('accounts:facility_roster')


@facility_staff_required
@require_POST
def facility_revoke_member(request, membership_id):
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, facility=request.facility)
    membership.status = 'revoked'
    membership.left_at = timezone.now()
    membership.save(update_fields=['status', 'left_at'])
    messages.success(request, 'Member removed from your cohort.')
    return redirect('accounts:facility_roster')
```

- [ ] **Step 5: Write the templates**

```html
<!-- apps/accounts/templates/accounts/facility/dashboard.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <h1>{{ facility }} — Aftercare</h1>
  <p><a href="{% url 'accounts:facility_roster' %}">Manage roster &amp; invites</a></p>
  <p>{{ summary.total }} members ·
     <strong>{{ summary.at_risk }} at-risk</strong> ·
     {{ summary.watch }} watch · {{ summary.ok }} ok</p>
  <table>
    <thead><tr><th>Member</th><th>Risk</th><th>Flags</th><th>Last check-in</th><th>Streak</th><th>Days sober</th></tr></thead>
    <tbody>
    {% for row in rows %}
      <tr>
        <td><a href="{% url 'accounts:facility_member' row.membership.id %}">{{ row.membership.user.username }}</a></td>
        <td>{{ row.risk.risk_level }}</td>
        <td>{{ row.risk.flags|join:", " }}</td>
        <td>{{ row.risk.last_checkin_date|default:"never" }}</td>
        <td>{{ row.risk.checkin_streak }}</td>
        <td>{{ row.risk.days_sober }}</td>
      </tr>
    {% empty %}
      <tr><td colspan="6">No consented members yet. Share an invite link from the roster.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

```html
<!-- apps/accounts/templates/accounts/facility/roster.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <h1>{{ facility }} — Roster</h1>
  <form method="post" action="{% url 'accounts:facility_generate_invite' %}">
    {% csrf_token %}
    <button type="submit" class="btn btn-primary">Create invite link</button>
  </form>
  <h2>Invite links</h2>
  <ul>
  {% for inv in invites %}
    <li>{{ request.scheme }}://{{ request.get_host }}{% url 'accounts:facility_join' inv.code %}
        — uses: {{ inv.uses }}</li>
  {% empty %}<li>No invite links yet.</li>{% endfor %}
  </ul>
  <h2>Members</h2>
  <table>
    <thead><tr><th>Member</th><th>Status</th><th></th></tr></thead>
    <tbody>
    {% for m in members %}
      <tr>
        <td>{{ m.user.username }}</td>
        <td>{{ m.status }}</td>
        <td>
          {% if m.status == 'active' %}
          <form method="post" action="{% url 'accounts:facility_revoke_member' m.id %}">
            {% csrf_token %}<button type="submit">Remove</button>
          </form>
          {% endif %}
        </td>
      </tr>
    {% empty %}<tr><td colspan="3">No members yet.</td></tr>{% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

```html
<!-- apps/accounts/templates/accounts/facility/member_detail.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
  <h1>{{ membership.user.username }}</h1>
  <p>Risk: <strong>{{ risk.risk_level }}</strong></p>
  <ul>
    <li>Flags: {{ risk.flags|join:", "|default:"none" }}</li>
    <li>Last check-in: {{ risk.last_checkin_date|default:"never" }}</li>
    <li>Check-in streak: {{ risk.checkin_streak }}</li>
    <li>Days sober: {{ risk.days_sober }}</li>
    <li>Craving trend: {{ risk.craving_trend|default:"n/a" }}</li>
    <li>Mood trend: {{ risk.mood_trend|default:"n/a" }}</li>
  </ul>
  <p><em>Journal entries and check-in notes are never shown.</em></p>
</div>
{% endblock %}
```

- [ ] **Step 6: Add URL routes**

```python
# apps/accounts/urls.py
# extend the .facility_views import:
from .facility_views import (
    facility_join, facility_leave, facility_dashboard, facility_roster,
    facility_member_detail, facility_generate_invite, facility_revoke_member,
)
# add inside urlpatterns:
    path('facility/', facility_dashboard, name='facility_dashboard'),
    path('facility/roster/', facility_roster, name='facility_roster'),
    path('facility/invite/new/', facility_generate_invite, name='facility_generate_invite'),
    path('facility/member/<int:membership_id>/', facility_member_detail, name='facility_member'),
    path('facility/member/<int:membership_id>/revoke/', facility_revoke_member, name='facility_revoke_member'),
```

- [ ] **Step 7: Run tests**

Run: `python manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (all facility tests).

- [ ] **Step 8: Commit**

```bash
git add apps/accounts/decorators.py apps/accounts/facility_views.py apps/accounts/templates/accounts/facility/ apps/accounts/urls.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): staff aftercare dashboard, roster, member detail (consent + tenant gated)"
```

---

### Task 5: Weekly at-risk digest (Celery)

**Files:**
- Modify: `apps/accounts/tasks.py` (add `send_facility_risk_digest`)
- Create: `apps/accounts/templates/emails/facility_risk_digest.html`
- Modify: `recovery_hub/settings.py` (`CELERY_BEAT_SCHEDULE`)
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `facility_service.compute_member_risk`, `visible_memberships`; `FacilityStaff`; `email_service.send_email(subject, plain_message, html_message, recipient_email)`.
- Produces: `send_facility_risk_digest()` Celery task. Emails each staff member of each active facility the members who are **newly** at-risk (`risk_level == at_risk` and `risk_notified_at is None`); stamps `risk_notified_at` on inclusion; clears it when a member is no longer at-risk. Returns an int count of emails sent.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py — append
from unittest.mock import patch
from apps.accounts.tasks import send_facility_risk_digest


class DigestTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(name='Hope', slug='hope')
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='pw')
        FacilityStaff.objects.create(facility=self.facility, user=self.staff_user)
        self.alum = User.objects.create_user(
            username='alum', email='alum@example.com', password='pw')
        # active + consented, no check-ins => at-risk (disengaged)
        self.m = FacilityMembership.objects.create(
            facility=self.facility, user=self.alum,
            status='active', consent_granted_at=timezone.now())

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_digest_emails_staff_about_newly_at_risk(self, mock_send):
        sent = send_facility_risk_digest()
        self.assertEqual(sent, 1)
        mock_send.assert_called_once()
        self.m.refresh_from_db()
        self.assertIsNotNone(self.m.risk_notified_at)

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_digest_does_not_repeat_already_notified(self, mock_send):
        self.m.risk_notified_at = timezone.now()
        self.m.save()
        sent = send_facility_risk_digest()
        self.assertEqual(sent, 0)
        mock_send.assert_not_called()

    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_recovered_member_clears_notified_flag(self, mock_send):
        from apps.accounts.models import DailyCheckIn
        self.m.risk_notified_at = timezone.now()
        self.m.save()
        DailyCheckIn.objects.create(
            user=self.alum, date=timezone.now().date(),
            mood=5, craving_level=0, energy_level=4)  # now ok
        send_facility_risk_digest()
        self.m.refresh_from_db()
        self.assertIsNone(self.m.risk_notified_at)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility.DigestTest -v 2`
Expected: FAIL — `cannot import name 'send_facility_risk_digest'`.

- [ ] **Step 3: Write the task**

```python
# apps/accounts/tasks.py — append (ensure these imports exist at top of file:
#   from celery import shared_task
#   from apps.accounts.email_service import send_email)
from django.template.loader import render_to_string
from django.utils import timezone as _tz


@shared_task
def send_facility_risk_digest():
    """Weekly: email facility staff the members newly at-risk since last digest."""
    from apps.accounts.facility_models import Facility, FacilityStaff
    from apps.accounts import facility_service as fs

    emails_sent = 0
    for facility in Facility.objects.filter(status='active'):
        newly_at_risk = []
        for m in fs.visible_memberships(facility):
            level = fs.compute_member_risk(m)['risk_level']
            if level == fs.RISK_AT_RISK:
                if m.risk_notified_at is None:
                    newly_at_risk.append(m)
                    m.risk_notified_at = _tz.now()
                    m.save(update_fields=['risk_notified_at'])
            else:
                if m.risk_notified_at is not None:
                    m.risk_notified_at = None
                    m.save(update_fields=['risk_notified_at'])

        if not newly_at_risk:
            continue

        names = [m.user.username for m in newly_at_risk]
        html = render_to_string('emails/facility_risk_digest.html', {
            'facility': facility, 'members': newly_at_risk,
        })
        plain = (f'{len(names)} alumni need attention at {facility.name}: '
                 + ', '.join(names))
        for staff in FacilityStaff.objects.filter(facility=facility).select_related('user'):
            if not staff.user.email:
                continue
            send_email(
                subject=f'{len(names)} alumni need attention — {facility.name}',
                plain_message=plain, html_message=html,
                recipient_email=staff.user.email)
            emails_sent += 1
    return emails_sent
```

- [ ] **Step 4: Write the email template**

```html
<!-- apps/accounts/templates/emails/facility_risk_digest.html -->
<div style="font-family:sans-serif;max-width:600px;">
  <h2>{{ members|length }} alumni need attention</h2>
  <p>The following {{ facility }} alumni have shown at-risk signals this week:</p>
  <ul>
    {% for m in members %}<li>{{ m.user.username }}</li>{% endfor %}
  </ul>
  <p>Log in to your aftercare dashboard to review and reach out.</p>
  <p style="color:#888;font-size:12px;">Engagement signals only — journal and
     check-in notes are never shared.</p>
</div>
```

- [ ] **Step 5: Register in beat schedule**

```python
# recovery_hub/settings.py — add an entry inside CELERY_BEAT_SCHEDULE
    'send_facility_risk_digest': {
        'task': 'apps.accounts.tasks.send_facility_risk_digest',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Mondays 9 AM
    },
```

- [ ] **Step 6: Run tests**

Run: `python manage.py test apps.accounts.tests_facility.DigestTest -v 2`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/tasks.py apps/accounts/templates/emails/facility_risk_digest.html recovery_hub/settings.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): weekly at-risk digest email to facility staff"
```

---

### Task 6: `create_facility` management command

**Files:**
- Create: `apps/accounts/management/commands/create_facility.py`
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `Facility`, `FacilityStaff`.
- Produces: `python manage.py create_facility --name "X" --staff-email a@b.com [--slug x] [--role admin]`. Creates the Facility (idempotent on slug) and a `FacilityStaff` row, creating the staff user if no account has that email.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_facility.py — append
from django.core.management import call_command


class CreateFacilityCommandTest(TestCase):
    def test_creates_facility_and_staff(self):
        call_command('create_facility', name='Hope Center',
                     staff_email='dir@hope.org')
        facility = Facility.objects.get(slug='hope-center')
        staff_user = User.objects.get(email='dir@hope.org')
        self.assertTrue(FacilityStaff.objects.filter(
            facility=facility, user=staff_user).exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test apps.accounts.tests_facility.CreateFacilityCommandTest -v 2`
Expected: FAIL — `Unknown command: 'create_facility'`.

- [ ] **Step 3: Write the command**

```python
# apps/accounts/management/commands/create_facility.py
"""Provision a treatment-center facility + a staff login (manual B2B onboarding)."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.accounts.facility_models import Facility, FacilityStaff

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a Facility and attach a staff user (creating the user if needed).'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True)
        parser.add_argument('--staff-email', required=True, dest='staff_email')
        parser.add_argument('--slug', default=None)
        parser.add_argument('--role', default='admin', choices=['admin', 'coordinator'])

    def handle(self, *args, **opts):
        slug = opts['slug'] or slugify(opts['name'])
        facility, created = Facility.objects.get_or_create(
            slug=slug, defaults={'name': opts['name']})
        verb = 'Created' if created else 'Found'
        self.stdout.write(f'{verb} facility: {facility.name} ({facility.slug})')

        email = opts['staff_email']
        user = User.objects.filter(email=email).first()
        if not user:
            username = email.split('@')[0]
            base, i = username, 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'
                i += 1
            user = User.objects.create_user(username=username, email=email)
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.WARNING(
                f'Created staff user {username} ({email}) — send a password reset.'))

        staff, s_created = FacilityStaff.objects.get_or_create(
            facility=facility, user=user, defaults={'role': opts['role']})
        if not s_created:
            raise CommandError('That user is already staff of this facility.')
        self.stdout.write(self.style.SUCCESS(
            f'Attached {user.email} as {staff.role} of {facility.name}.'))
```

- [ ] **Step 4: Run tests**

Run: `python manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (entire facility suite).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/management/commands/create_facility.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): create_facility provisioning command"
```

---

## Self-Review

**Spec coverage:**
- §3 models → Task 1 ✓ (all four models + consent invariant + `risk_notified_at`)
- §4 at-risk logic → Task 2 ✓ (thresholds verbatim, compute-on-read, cohort summary)
- §5 enrollment/consent/revoke → Task 3 ✓; staff dashboard/roster/member-detail + decorator → Task 4 ✓; weekly digest + `risk_notified_at` mechanism → Task 5 ✓; provisioning command → Task 6 ✓; client transparency/revoke → Task 3 (`facility_leave`) ✓
- §8 testing → consent gating (Task 4 `test_member_detail_hidden_without_consent`), tenant isolation (Task 4 `test_tenant_isolation_on_member_detail`), non-staff blocked (Task 4), digest newly-at-risk (Task 5), enrollment valid/expired (Task 3), revoke (Task 3) ✓
- §7 out-of-scope items → none implemented ✓

**Deferred from spec (acceptable, low-value polish):** the client-settings *display* of "which facility you share with" is not its own task — the `facility_leave` revoke endpoint exists (Task 3) and can be linked from the existing account settings template during Task 3 if desired; not adding a separate task avoids touching the large settings template speculatively.

**Placeholder scan:** none — every code step is complete.

**Type consistency:** `compute_member_risk` return keys (`risk_level`, `flags`, `last_checkin_date`, `checkin_streak`, `days_sober`, `craving_trend`, `mood_trend`) used consistently in Tasks 4–5; `visible_memberships`/`cohort_summary`/`RISK_*` constants consistent; URL names consistent between view definitions and `urls.py` and templates; `is_visible_to_staff` used in Tasks 1, 3.
