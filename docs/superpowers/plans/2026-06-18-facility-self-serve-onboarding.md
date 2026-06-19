# Facility Self-Serve Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a treatment center create its own aftercare account online (free, offline-billed) via a public signup that verifies a work email before activating — replacing CLI-only provisioning.

**Architecture:** A public signup creates the facility in a new `status='pending'` state; an emailed verification link flips it to `active`. The existing `status='active'` gate (`facility_staff_required` + `facility_join`) already locks pending facilities out of the dashboard and enrollment, so no new gating code is needed — only a status value, two fields, and a signup/verify flow.

**Tech Stack:** Django 5.0, PostgreSQL, existing `email_service.send_email`, Django `TestCase`.

## Global Constraints

- Self-serve signup is **free** (no card, no Stripe); billing stays offline. `Facility.monthly_rate` remains record-keeping only.
- New self-serve facilities start `status='pending'`; they become `active` ONLY after the work-email verification link is used. `create_facility` command and Django `/admin/` still create `active` (unchanged).
- Existing-email signups are **rejected** with a form error pointing to login — no User/Facility created.
- Operator notification email goes to `FACILITY_SIGNUP_NOTIFY_EMAIL` env var, defaulting to `DEFAULT_FROM_EMAIL`.
- Privacy/consent invariants from the aftercare module are unchanged — this plan does NOT touch monitoring, roster, digest, or consent.
- Environment: work from `/Users/ryanpate/myrecoverypal`; use `python3` (NOT `python`). Run tests: `python3 manage.py test apps.accounts.tests_facility -v 2` (sqlite test DB, boots locally). View tests use `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)` (project sets `PREPEND_WWW=True`).
- `send_email(subject, plain_message, html_message, recipient_email)` returns a `(success_bool, error)` tuple.
- Active settings module is `recovery_hub/settings.py`. Auth uses Django's default `ModelBackend`; auto-login must pass `backend='django.contrib.auth.backends.ModelBackend'` explicitly.

---

### Task 1: Add `pending` status + verification fields to `Facility`

**Files:**
- Modify: `apps/accounts/facility_models.py` (Facility STATUS_CHOICES + two fields)
- Test: `apps/accounts/tests_facility.py` (append)
- Migration: `apps/accounts/migrations/` (generated)

**Interfaces:**
- Produces: `Facility.STATUS_CHOICES` now includes `('pending', 'Pending')`; `Facility.activation_token` (CharField, blank, default `''`, db_index); `Facility.email_verified_at` (DateTimeField, null). Default `status` stays `'active'`.

- [ ] **Step 1: Write the failing tests** (append to `apps/accounts/tests_facility.py`)

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PendingFacilityGatingTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name='Pend', slug='pend', status='pending')
        self.staff_user = User.objects.create_user(
            username='ps', email='ps@example.com', password='pw')
        FacilityStaff.objects.create(facility=self.facility, user=self.staff_user)

    def test_pending_is_valid_status(self):
        self.assertIn('pending', [c[0] for c in Facility.STATUS_CHOICES])

    def test_pending_facility_has_token_fields(self):
        self.facility.activation_token = 'abc'
        self.facility.email_verified_at = timezone.now()
        self.facility.save()
        self.facility.refresh_from_db()
        self.assertEqual(self.facility.activation_token, 'abc')
        self.assertIsNotNone(self.facility.email_verified_at)

    def test_pending_facility_dashboard_blocked(self):
        self.client.force_login(self.staff_user)
        resp = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(resp.status_code, 302)  # decorator: facility not active

    def test_pending_facility_invite_rejected(self):
        invite = FacilityInvite.objects.create(
            facility=self.facility, code=FacilityInvite.generate_code())
        member = User.objects.create_user(
            username='m', email='m@example.com', password='pw')
        self.client.force_login(member)
        self.client.post(
            reverse('accounts:facility_join', args=[invite.code]),
            {'consent': 'on'})
        self.assertFalse(FacilityMembership.objects.filter(
            facility=self.facility, user=member, status='active').exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.tests_facility.PendingFacilityGatingTest -v 2`
Expected: FAIL — `test_pending_facility_has_token_fields` errors (no `activation_token` field); the gating tests may error on save too.

- [ ] **Step 3: Edit the model**

In `apps/accounts/facility_models.py`, in `class Facility`, replace the `STATUS_CHOICES` line and add two fields after `created_at`:

```python
    STATUS_CHOICES = [('pending', 'Pending'), ('active', 'Active'), ('paused', 'Paused')]
```

```python
    # Self-serve signup: random token for the email-verification link, cleared
    # once used. Default status stays 'active' so create_facility/admin are
    # unaffected; only self-serve signups set status='pending'.
    activation_token = models.CharField(
        max_length=64, blank=True, default='', db_index=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
```

(Place the two fields immediately before the `class Meta:` block. Leave `status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')` unchanged — `'pending'` fits in 10 chars.)

- [ ] **Step 4: Make the migration**

Run: `python3 manage.py makemigrations accounts`
Expected: a new migration altering `Facility.status` choices and adding `activation_token`, `email_verified_at`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (all facility tests, including the 4 new ones).

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/facility_models.py apps/accounts/migrations/ apps/accounts/tests_facility.py
git commit -m "feat(b2b): add pending status + verification fields to Facility"
```

---

### Task 2: Facility signup form

**Files:**
- Create: `apps/accounts/facility_forms.py`
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Produces: `FacilitySignupForm(forms.Form)` with fields `facility_name` (CharField max 200), `contact_name` (CharField max 150, required=False), `email` (EmailField), `password` (CharField min_length 8, PasswordInput). `clean_email` lowercases and rejects an email already belonging to a `User`.

- [ ] **Step 1: Write the failing test** (append to `apps/accounts/tests_facility.py`)

```python
from apps.accounts.facility_forms import FacilitySignupForm


class FacilitySignupFormTest(TestCase):
    def test_valid_form(self):
        form = FacilitySignupForm(data={
            'facility_name': 'New Hope', 'contact_name': 'Dana',
            'email': 'Dana@NewHope.org', 'password': 'sekret123'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'dana@newhope.org')  # lowercased

    def test_duplicate_email_invalid(self):
        User.objects.create_user(
            username='x', email='dup@example.com', password='pw')
        form = FacilitySignupForm(data={
            'facility_name': 'Dup', 'email': 'dup@example.com',
            'password': 'sekret123'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_short_password_invalid(self):
        form = FacilitySignupForm(data={
            'facility_name': 'X', 'email': 'a@b.com', 'password': 'short'})
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilitySignupFormTest -v 2`
Expected: FAIL — `No module named 'apps.accounts.facility_forms'`

- [ ] **Step 3: Write the form**

```python
# apps/accounts/facility_forms.py
"""Forms for self-serve facility onboarding."""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class FacilitySignupForm(forms.Form):
    facility_name = forms.CharField(max_length=200)
    contact_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Log in and contact us to add a facility.')
        return email
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilitySignupFormTest -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/facility_forms.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): facility signup form with duplicate-email guard"
```

---

### Task 3: Signup view + templates + settings + URL

**Files:**
- Create: `apps/accounts/facility_signup_views.py`
- Create: `apps/accounts/templates/accounts/facility/signup.html`
- Create: `apps/accounts/templates/accounts/facility/signup_done.html`
- Create: `apps/accounts/templates/emails/facility_verify_email.html`
- Create: `apps/accounts/templates/emails/facility_signup_notify.html`
- Modify: `recovery_hub/settings.py` (add `FACILITY_SIGNUP_NOTIFY_EMAIL`)
- Modify: `apps/accounts/urls.py` (add signup route)
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `FacilitySignupForm` (Task 2); `Facility`/`FacilityStaff` (Task 1); `email_service.send_email`.
- Produces: URL name `accounts:facility_signup` (`facility/signup/`). `facility_signup(request)`: GET renders form; valid POST creates `User` + `Facility(status='pending', activation_token=<secrets.token_urlsafe(32)>)` + `FacilityStaff(role='admin')` atomically, sends a verification email (to the signer) and a notification email (to `FACILITY_SIGNUP_NOTIFY_EMAIL`), then renders `signup_done.html`. Module-level helpers `_unique_facility_slug(name)` and `_unique_username(email)`. The verification link points at URL name `accounts:facility_verify_email` (defined in Task 4) — the route is added in Task 4, so test the email send via a mock in this task and the live verify flow in Task 4.

- [ ] **Step 1: Write the failing tests** (append to `apps/accounts/tests_facility.py`)

```python
from unittest.mock import patch


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FacilitySignupViewTest(TestCase):
    @patch('apps.accounts.facility_signup_views.send_email', return_value=(True, None))
    def test_signup_creates_pending_facility_and_sends_two_emails(self, mock_send):
        resp = self.client.post(reverse('accounts:facility_signup'), {
            'facility_name': 'New Hope', 'contact_name': 'Dana',
            'email': 'dana@newhope.org', 'password': 'sekret123'})
        self.assertEqual(resp.status_code, 200)
        facility = Facility.objects.get(name='New Hope')
        self.assertEqual(facility.status, 'pending')
        self.assertTrue(facility.activation_token)
        user = User.objects.get(email='dana@newhope.org')
        self.assertTrue(FacilityStaff.objects.filter(
            facility=facility, user=user, role='admin').exists())
        self.assertEqual(mock_send.call_count, 2)  # verify + operator notify

    @patch('apps.accounts.facility_signup_views.send_email', return_value=(True, None))
    def test_duplicate_email_creates_nothing(self, mock_send):
        User.objects.create_user(
            username='x', email='dup@example.com', password='pw')
        resp = self.client.post(reverse('accounts:facility_signup'), {
            'facility_name': 'Dup', 'email': 'dup@example.com',
            'password': 'sekret123'})
        self.assertEqual(resp.status_code, 200)  # form re-rendered with error
        self.assertFalse(Facility.objects.filter(name='Dup').exists())
        mock_send.assert_not_called()

    def test_get_renders_form(self):
        resp = self.client.get(reverse('accounts:facility_signup'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'facility_name')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilitySignupViewTest -v 2`
Expected: FAIL — `Reverse for 'facility_signup' not found`.

- [ ] **Step 3: Add the setting**

In `recovery_hub/settings.py`, immediately after the `DEFAULT_FROM_EMAIL = ...` assignment (around line 596), add:

```python
# Where new self-serve facility-signup notifications are sent.
FACILITY_SIGNUP_NOTIFY_EMAIL = os.environ.get(
    'FACILITY_SIGNUP_NOTIFY_EMAIL', DEFAULT_FROM_EMAIL)
```

- [ ] **Step 4: Write the signup view**

```python
# apps/accounts/facility_signup_views.py
"""Self-serve facility onboarding: public signup + email verification."""
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.email_service import send_email
from apps.accounts.facility_forms import FacilitySignupForm
from apps.accounts.facility_models import Facility, FacilityStaff

User = get_user_model()


def _unique_facility_slug(name):
    base = slugify(name) or 'facility'
    slug, i = base, 2
    while Facility.objects.filter(slug=slug).exists():
        slug = f'{base}-{i}'
        i += 1
    return slug


def _unique_username(email):
    base = email.split('@')[0] or 'staff'
    username, i = base, 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{i}'
        i += 1
    return username


def facility_signup(request):
    if request.method != 'POST':
        return render(request, 'accounts/facility/signup.html',
                      {'form': FacilitySignupForm()})

    form = FacilitySignupForm(request.POST)
    if not form.is_valid():
        return render(request, 'accounts/facility/signup.html', {'form': form})

    data = form.cleaned_data
    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        user = User.objects.create_user(
            username=_unique_username(data['email']),
            email=data['email'], password=data['password'])
        if data.get('contact_name'):
            user.first_name = data['contact_name'][:150]
            user.save(update_fields=['first_name'])
        facility = Facility.objects.create(
            name=data['facility_name'],
            slug=_unique_facility_slug(data['facility_name']),
            status='pending', activation_token=token)
        FacilityStaff.objects.create(
            facility=facility, user=user, role='admin')

    verify_url = request.build_absolute_uri(
        reverse('accounts:facility_verify_email', args=[token]))
    send_email(
        subject=f'Verify your facility — {facility.name}',
        plain_message=f'Verify your MyRecoveryPal facility account: {verify_url}',
        html_message=render_to_string('emails/facility_verify_email.html',
                                      {'facility': facility, 'verify_url': verify_url}),
        recipient_email=user.email)
    send_email(
        subject=f'New facility signup: {facility.name}',
        plain_message=f'New facility "{facility.name}" signed up ({user.email}).',
        html_message=render_to_string('emails/facility_signup_notify.html',
                                      {'facility': facility, 'contact_email': user.email}),
        recipient_email=getattr(settings, 'FACILITY_SIGNUP_NOTIFY_EMAIL',
                                settings.DEFAULT_FROM_EMAIL))

    return render(request, 'accounts/facility/signup_done.html',
                  {'email': user.email})
```

- [ ] **Step 5: Write the templates**

```html
<!-- apps/accounts/templates/accounts/facility/signup.html -->
{% extends "base.html" %}
{% block content %}
<div class="container" style="max-width:560px;margin:2rem auto;">
  <h1>Create your facility's aftercare account</h1>
  <p>Monitor your alumni's recovery engagement and spot at-risk clients early.
     Free while in beta — we'll reach out about billing.</p>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Create account</button>
  </form>
</div>
{% endblock %}
```

```html
<!-- apps/accounts/templates/accounts/facility/signup_done.html -->
{% extends "base.html" %}
{% block content %}
<div class="container" style="max-width:560px;margin:2rem auto;">
  <h1>Check your email</h1>
  <p>We sent a verification link to <strong>{{ email }}</strong>. Click it to
     activate your facility and open your dashboard.</p>
</div>
{% endblock %}
```

```html
<!-- apps/accounts/templates/emails/facility_verify_email.html -->
<div style="font-family:sans-serif;max-width:600px;">
  <h2>Verify your facility</h2>
  <p>Confirm your email to activate <strong>{{ facility.name }}</strong> on
     MyRecoveryPal and open your aftercare dashboard.</p>
  <p><a href="{{ verify_url }}">Verify &amp; activate</a></p>
  <p style="color:#888;font-size:12px;">If you didn't request this, ignore this email.</p>
</div>
```

```html
<!-- apps/accounts/templates/emails/facility_signup_notify.html -->
<div style="font-family:sans-serif;max-width:600px;">
  <h2>New facility signup</h2>
  <p><strong>{{ facility.name }}</strong> just signed up ({{ contact_email }}).</p>
  <p>It is pending email verification. Follow up to arrange billing once active.</p>
</div>
```

- [ ] **Step 6: Add the URL**

```python
# apps/accounts/urls.py
# add to imports:
from .facility_signup_views import facility_signup
# add inside urlpatterns:
    path('facility/signup/', facility_signup, name='facility_signup'),
```

- [ ] **Step 7: Run tests**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilitySignupViewTest -v 2`
Expected: PASS (3 tests). (The verify URL is referenced via `reverse` inside the view; it is added in Task 4. To keep this task runnable, ALSO add the Task-4 verify route now if `reverse` fails — but the route IS added in Task 4 Step 6; if running tasks in order, add the verify path in Task 4 before running the full suite. For this task's tests, `send_email` is mocked but `reverse('accounts:facility_verify_email', ...)` still executes — so add the verify URL route now as part of Step 6 as well.)

Add BOTH routes in Step 6 to avoid a `NoReverseMatch`:

```python
# apps/accounts/urls.py — import and routes (signup now, verify wired in Task 4 view)
from .facility_signup_views import facility_signup, facility_verify_email
    path('facility/signup/', facility_signup, name='facility_signup'),
    path('facility/verify/<str:token>/', facility_verify_email, name='facility_verify_email'),
```

Since `facility_verify_email` doesn't exist until Task 4, this task cannot import it. Resolution: **define a minimal `facility_verify_email` stub in `facility_signup_views.py` in this task** so the import and `reverse` work, then flesh it out in Task 4:

```python
def facility_verify_email(request, token):
    # Implemented in Task 4.
    return render(request, 'accounts/facility/verify_invalid.html')
```

And create the `verify_invalid.html` template now (it's needed by Task 4 anyway):

```html
<!-- apps/accounts/templates/accounts/facility/verify_invalid.html -->
{% extends "base.html" %}
{% block content %}
<div class="container" style="max-width:560px;margin:2rem auto;">
  <h1>Link invalid or already used</h1>
  <p>This verification link is invalid or has already been used.
     If your facility is already active, please <a href="{% url 'accounts:login' %}">log in</a>.</p>
</div>
{% endblock %}
```

- [ ] **Step 8: Run full facility suite**

Run: `python3 manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (all prior + new signup tests).

- [ ] **Step 9: Commit**

```bash
git add apps/accounts/facility_signup_views.py apps/accounts/templates/accounts/facility/ apps/accounts/templates/emails/ recovery_hub/settings.py apps/accounts/urls.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): self-serve facility signup view, emails, settings, routes"
```

---

### Task 4: Email-verification view (activate + auto-login)

**Files:**
- Modify: `apps/accounts/facility_signup_views.py` (replace the `facility_verify_email` stub with the real implementation)
- Test: `apps/accounts/tests_facility.py` (append)

**Interfaces:**
- Consumes: `Facility`, `FacilityStaff` (Task 1); the `facility/verify/<token>/` route + `verify_invalid.html` (added in Task 3).
- Produces: `facility_verify_email(request, token)`: looks up a `Facility` by non-empty `activation_token`; if found, sets `status='active'`, stamps `email_verified_at`, clears `activation_token`, logs in the facility's admin `FacilityStaff.user` (backend `'django.contrib.auth.backends.ModelBackend'`), redirects to `accounts:facility_dashboard`; if not found, renders `verify_invalid.html` with no state change.

- [ ] **Step 1: Write the failing tests** (append to `apps/accounts/tests_facility.py`)

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FacilityVerifyEmailTest(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(
            name='Verify Me', slug='verify-me',
            status='pending', activation_token='tok123')
        self.user = User.objects.create_user(
            username='v', email='v@example.com', password='pw')
        FacilityStaff.objects.create(
            facility=self.facility, user=self.user, role='admin')

    def test_valid_token_activates_and_logs_in(self):
        resp = self.client.get(
            reverse('accounts:facility_verify_email', args=['tok123']))
        self.assertRedirects(
            resp, reverse('accounts:facility_dashboard'),
            fetch_redirect_response=False)
        self.facility.refresh_from_db()
        self.assertEqual(self.facility.status, 'active')
        self.assertIsNotNone(self.facility.email_verified_at)
        self.assertEqual(self.facility.activation_token, '')
        # auto-logged-in: the now-active dashboard returns 200
        dash = self.client.get(reverse('accounts:facility_dashboard'))
        self.assertEqual(dash.status_code, 200)

    def test_invalid_token_no_state_change(self):
        resp = self.client.get(
            reverse('accounts:facility_verify_email', args=['nope']))
        self.assertEqual(resp.status_code, 200)  # verify_invalid page
        self.facility.refresh_from_db()
        self.assertEqual(self.facility.status, 'pending')

    def test_reused_token_is_invalid(self):
        self.client.get(reverse('accounts:facility_verify_email', args=['tok123']))
        # token now cleared; a second hit with the same token finds nothing
        self.client.logout()
        resp = self.client.get(
            reverse('accounts:facility_verify_email', args=['tok123']))
        self.assertEqual(resp.status_code, 200)  # verify_invalid page
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilityVerifyEmailTest -v 2`
Expected: FAIL — the stub returns `verify_invalid.html` for the valid token, so `test_valid_token_activates_and_logs_in` fails (no redirect, status not activated).

- [ ] **Step 3: Replace the stub with the real view**

In `apps/accounts/facility_signup_views.py`, replace the `facility_verify_email` stub with:

```python
def facility_verify_email(request, token):
    facility = (Facility.objects
                .filter(activation_token=token)
                .exclude(activation_token='')
                .first())
    if not facility:
        return render(request, 'accounts/facility/verify_invalid.html')

    facility.status = 'active'
    facility.email_verified_at = timezone.now()
    facility.activation_token = ''
    facility.save(update_fields=['status', 'email_verified_at', 'activation_token'])

    staff = (FacilityStaff.objects
             .filter(facility=facility, role='admin')
             .select_related('user').first())
    if staff:
        login(request, staff.user,
              backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f'{facility.name} is verified and active.')
    return redirect('accounts:facility_dashboard')
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.tests_facility.FacilityVerifyEmailTest -v 2`
Expected: PASS (3 tests).

- [ ] **Step 5: Run full facility suite**

Run: `python3 manage.py test apps.accounts.tests_facility -v 2`
Expected: PASS (entire facility suite).

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/facility_signup_views.py apps/accounts/tests_facility.py
git commit -m "feat(b2b): facility email-verification view (activate + auto-login)"
```

---

## Self-Review

**Spec coverage:**
- §2 model change (pending status, activation_token, email_verified_at, migration) → Task 1 ✓
- §3 signup form + duplicate-email rejection → Task 2 ✓
- §3 signup view (atomic create, two emails, confirmation page), settings notify var, routes, templates → Task 3 ✓
- §3 verify view (activate, stamp, clear, auto-login, redirect; invalid page) → Task 4 ✓
- §2 reuse insight (pending facility blocked from dashboard + enrollment) → Task 1 gating tests ✓
- §6 testing (signup happy path, duplicate email, pending gating, verification, invalid token, atomicity) → covered across Tasks 1/3/4 ✓ (atomicity is implicit via `transaction.atomic` in Task 3 view; duplicate-email test proves no objects created)
- §5 out-of-scope items → none implemented ✓
- `create_facility` unchanged (still creates `active` via model default) ✓

**Placeholder scan:** none — all steps contain complete code. (Task 3 Step 7 deliberately introduces a `facility_verify_email` stub + the verify route so the signup view's `reverse()` resolves; Task 4 replaces the stub. This is an explicit, ordered handoff, not a placeholder.)

**Type consistency:** `activation_token` (CharField default `''`), `email_verified_at`, `status='pending'/'active'` used identically across Tasks 1/3/4. URL names `accounts:facility_signup` and `accounts:facility_verify_email` consistent between views, urls.py, templates, and tests. `send_email` patched at `apps.accounts.facility_signup_views.send_email` (the namespace it's imported into) in Task 3 tests. Auto-login backend string matches the Global Constraints note.
