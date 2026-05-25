# Registration Friction Reduction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the public signup form from 4–5 visible fields to 2 (email + password with show-password toggle). Auto-generate friendly anonymous usernames server-side. Preserve every server-side side effect (subscription creation, invite-code linking, promo application, welcome emails).

**Architecture:** One new pure-Python module (`username_generator.py`) with a single helper, slimmed `CustomUserCreationForm` in the existing `forms.py`, two-line fix in the existing `register_view`, and a rewritten `register.html` template. Invite-only mode path is left untouched.

**Tech Stack:** Django 5.0, plain HTML/CSS, inline JS for the password eye toggle. No new dependencies, no migrations, no model changes.

**Reference spec:** `docs/plans/2026-05-25-registration-friction-design.md`

---

## Pre-flight

- [ ] **Step 0.1: Verify branch and clean baseline**

Run:
```bash
git branch --show-current
git log --oneline -3
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -3
```

Expected:
- Branch: `feat/registration-friction`
- Most recent commit: `docs: registration friction reduction design spec`
- 48 tests pass (baseline)

If `apps.accounts` baseline is anything other than 48, investigate before proceeding. **Note about `python3`:** use this everywhere, not `python` (the project's Python 3.10 install isn't aliased). The `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` prefix is required on macOS because the test suite transitively imports WeasyPrint via `apps.accounts.court_service`, which dlopens Pango from Homebrew.

- [ ] **Step 0.2: Confirm User model + form patterns are what we expect**

```bash
grep -n "USERNAME_FIELD\|email = models.EmailField\|class CustomUserCreationForm\|class CustomUserCreationFormWithInvite" apps/accounts/models.py apps/accounts/forms.py | head -10
```

Expected output should include:
- `apps/accounts/models.py: email = models.EmailField(unique=True)` — confirms email is enforced unique at the DB level
- `apps/accounts/models.py: USERNAME_FIELD = 'username'` — username still drives Django auth
- `apps/accounts/forms.py: class CustomUserCreationForm(UserCreationForm):` — this is what we're slimming
- `apps/accounts/forms.py: class CustomUserCreationFormWithInvite(UserCreationForm):` — leave this alone

---

## Task 1: Username generator module

A pure function that returns a unique `<word><4-digit>`-style username. Pure means no external state beyond the User table — easy to test, easy to reason about.

**Files:**
- Create: `apps/accounts/username_generator.py`
- Modify: `apps/accounts/tests_signup.py` (create new file in this task)

- [ ] **Step 1.1: Write the failing test**

Create `apps/accounts/tests_signup.py` with this content:

```python
# apps/accounts/tests_signup.py
"""Tests for the friction-reduced signup flow (Audit Priority #2)."""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class UsernameGeneratorTest(TestCase):
    """generate_unique_username() returns a friendly anonymous identifier."""

    def test_returns_string_matching_pattern(self):
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        u = generate_unique_username()
        self.assertIsInstance(u, str)
        # Pattern: one wordlist entry followed by exactly 4 digits
        pattern = re.compile(rf'^({"|".join(WORDLIST)})\d{{4}}$')
        self.assertRegex(u, pattern)

    def test_returns_unique_value_when_collision(self):
        """If all preferred candidates are taken, the generator still returns
        a unique value (extended-suffix fallback)."""
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        # Saturate every possible 4-digit Friend* candidate
        # (10 words × 9000 slots = too many to enumerate; instead pre-populate
        # the username table with all 10 wordlist words at one specific suffix
        # so collisions happen, then assert we still get a unique result back)
        for word in WORDLIST:
            User.objects.create_user(
                username=f'{word}1234',
                email=f'{word.lower()}1234@example.com',
                password='pw'
            )
        # Burn random by patching with a deterministic seed scenario:
        # we just verify the generator returns SOME unique username, and the
        # returned value is not any of the pre-existing ones.
        existing = set(User.objects.values_list('username', flat=True))
        u = generate_unique_username()
        self.assertNotIn(u, existing)
        self.assertFalse(User.objects.filter(username=u).exists())

    def test_uses_wordlist_words_only(self):
        """Across 25 calls, every generated username's prefix is in WORDLIST."""
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        for _ in range(25):
            u = generate_unique_username()
            # Strip trailing digits; what's left should be a wordlist entry
            prefix = re.sub(r'\d+$', '', u)
            self.assertIn(prefix, WORDLIST, f'{prefix!r} (from {u!r}) not in WORDLIST')
```

- [ ] **Step 1.2: Run the test, confirm it fails**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.UsernameGeneratorTest -v 2
```

Expected: `ModuleNotFoundError: No module named 'apps.accounts.username_generator'` — three errors, one per test.

- [ ] **Step 1.3: Create the module**

Create `apps/accounts/username_generator.py`:

```python
# apps/accounts/username_generator.py
"""Generate friendly anonymous usernames for new signups.

The default username is intentionally not derived from the user's email
(privacy) and is intentionally human-readable rather than UUID-based
(less intimidating in the social feed).
"""
import random

from django.contrib.auth import get_user_model

User = get_user_model()

WORDLIST = [
    'Friend',
    'NewMember',
    'Recovering',
    'Hopeful',
    'Brave',
    'Strong',
    'Anchored',
    'Steady',
    'Rising',
    'OneDay',
]

MAX_ATTEMPTS = 10


def generate_unique_username() -> str:
    """Return a unique username like 'Friend1234'.

    Tries a wordlist + 4-digit suffix up to MAX_ATTEMPTS times. Falls back to
    an extended 8-digit numeric suffix on persistent collision (vanishingly
    unlikely under normal load; this branch exists for test determinism and
    pathological collision scenarios).
    """
    for _ in range(MAX_ATTEMPTS):
        word = random.choice(WORDLIST)
        suffix = random.randint(1000, 9999)
        candidate = f'{word}{suffix}'
        if not User.objects.filter(username=candidate).exists():
            return candidate

    # Pathological collision case — extend suffix
    while True:
        candidate = f'Friend{random.randint(10_000_000, 99_999_999)}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
```

- [ ] **Step 1.4: Re-run tests, confirm pass**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.UsernameGeneratorTest -v 2
```

Expected: 3 tests pass.

- [ ] **Step 1.5: Run the full apps.accounts suite to confirm no collateral damage**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -3
```

Expected: 51 tests pass (48 baseline + 3 new).

- [ ] **Step 1.6: Commit**

```bash
git add apps/accounts/username_generator.py apps/accounts/tests_signup.py
git commit -m "feat(accounts): username generator for friction-reduced signup

generate_unique_username() returns 'Friend1234'-style names from a
small wordlist + 4-digit suffix. Collision-checks against the User
table; falls back to 8-digit suffix on pathological collisions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Slim down CustomUserCreationForm

Replace the existing 5-field form (username, email, password1, password2, sobriety_date) with a 2-field form (email, password). The form's `save()` method auto-generates the username and hashes the password.

**Files:**
- Modify: `apps/accounts/forms.py` (lines ~106–125 — the `CustomUserCreationForm` class)
- Modify: `apps/accounts/tests_signup.py` (append tests)

**IMPORTANT:** Do NOT touch `CustomUserCreationFormWithInvite` (lines ~126+) — that's the invite-only-mode form and stays as-is.

- [ ] **Step 2.1: Write failing tests**

Append to `apps/accounts/tests_signup.py`:

```python
class SignupFormTest(TestCase):
    """The slimmed CustomUserCreationForm: email + password only."""

    def test_form_has_only_email_and_password(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm()
        # The visible fields must be exactly email + password
        self.assertEqual(set(form.fields.keys()), {'email', 'password'})

    def test_email_required(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={'password': 'abcdefgh'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_minimum_length_enforced(self):
        from apps.accounts.forms import CustomUserCreationForm
        # 7 chars — should fail
        form = CustomUserCreationForm(data={
            'email': 'a@b.com', 'password': '1234567'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        # 8 chars — should pass
        form = CustomUserCreationForm(data={
            'email': 'a@b.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_rejected_with_friendly_message(self):
        User.objects.create_user(
            username='existing', email='taken@example.com', password='pw'
        )
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'taken@example.com', 'password': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        # Must contain a hint that "sign in" is the right next action
        self.assertTrue(
            any('sign in' in str(e).lower() or 'already exists' in str(e).lower()
                for e in form.errors['email']),
            f'Expected friendly duplicate-email message, got: {form.errors["email"]}'
        )

    def test_email_is_lowercased_on_save(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'Mixed.Case@EXAMPLE.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, 'mixed.case@example.com')

    def test_save_generates_username_matching_pattern(self):
        import re
        from apps.accounts.forms import CustomUserCreationForm
        from apps.accounts.username_generator import WORDLIST
        form = CustomUserCreationForm(data={
            'email': 'new@example.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertRegex(
            user.username,
            re.compile(rf'^({"|".join(WORDLIST)})\d{{4}}$')
        )

    def test_save_hashes_password(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'hash@example.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertNotEqual(user.password, '12345678')  # hashed
        self.assertTrue(user.check_password('12345678'))
```

- [ ] **Step 2.2: Run, confirm failure**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.SignupFormTest -v 2
```

Expected: All 7 tests fail. The current form has different fields, so the first test will fail with `AssertionError`, others with `KeyError` on `password` field, etc.

- [ ] **Step 2.3: Slim the form**

In `apps/accounts/forms.py`, find the existing `class CustomUserCreationForm` block (search for `class CustomUserCreationForm(UserCreationForm):` — around line 106). Replace the entire `CustomUserCreationForm` class (NOT `CustomUserCreationFormWithInvite` below it) with:

```python
class CustomUserCreationForm(forms.ModelForm):
    """Minimal-friction signup form: email + password only.

    Username is auto-generated server-side (see username_generator.py).
    Sobriety date is captured progressively in the profile/onboarding flow,
    not at signup. Confirm-password is replaced by a show-password toggle
    on the template side.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'inputmode': 'email',
            'autocapitalize': 'off',
            'spellcheck': 'false',
            'placeholder': 'you@example.com',
        }),
    )
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'minlength': '8',
        }),
        help_text='At least 8 characters.',
    )

    class Meta:
        model = User
        fields = ('email',)  # username and password are handled in save()

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. Try signing in instead.'
            )
        return email

    def save(self, commit=True):
        from apps.accounts.username_generator import generate_unique_username
        user = User(
            email=self.cleaned_data['email'],
            username=generate_unique_username(),
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
```

Note: the class now extends `forms.ModelForm` (not `UserCreationForm`) because we no longer need Django's built-in username/password1/password2 machinery — the form is fully custom now.

- [ ] **Step 2.4: Re-run form tests, confirm pass**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.SignupFormTest -v 2
```

Expected: All 7 tests pass.

- [ ] **Step 2.5: Run the full apps.accounts suite — expect some pre-existing tests to break**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -10
```

Expected: A handful of failures or errors related to `register_view` because that view still references `form.cleaned_data.get('password1')` and `form.cleaned_data.get('username')` (lines ~64–65 of `views.py`). These get fixed in Task 3. **Do not commit yet** if there are failures — proceed to Task 3.

If the new tests show passing and only existing tests fail, that's the expected state. Move to Task 3.

If new tests fail, debug them first before continuing.

- [ ] **Step 2.6: Do NOT commit yet — Task 3 fixes the view that depends on this form**

The form change and view change must land together to keep the codebase compilable. Don't commit until Task 3 is done.

---

## Task 3: Update register_view

Fix the two lines that read field names that no longer exist on the form.

**Files:**
- Modify: `apps/accounts/views.py` (lines ~63–65, ~82–86)
- Modify: `apps/accounts/tests_signup.py` (append view tests)

- [ ] **Step 3.1: Write failing tests for the view**

Append to `apps/accounts/tests_signup.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RegisterViewTest(TestCase):
    """The /accounts/register/ endpoint integrates the slimmed form."""

    def test_get_renders_form(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(resp.status_code, 200)
        # Form fields are present in HTML
        self.assertContains(resp, 'name="email"')
        self.assertContains(resp, 'name="password"')
        # Old fields are absent
        self.assertNotContains(resp, 'name="password1"')
        self.assertNotContains(resp, 'name="password2"')
        self.assertNotContains(resp, 'name="sobriety_date"')

    def test_post_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'new@example.com',
            'password': 'mysecurepw123',
        })
        # Should redirect (302) somewhere authenticated, not stay on the form
        self.assertEqual(resp.status_code, 302)
        # User exists
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
        # User is logged in (session has _auth_user_id)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_creates_subscription(self):
        from apps.accounts.payment_models import Subscription
        self.client.post(reverse('accounts:register'), {
            'email': 'sub@example.com',
            'password': 'mysecurepw123',
        })
        user = User.objects.get(email='sub@example.com')
        sub = Subscription.objects.get(user=user)
        self.assertEqual(sub.tier, 'free')
        self.assertEqual(sub.status, 'active')

    def test_post_invalid_email_returns_form_with_errors(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'not-an-email',
            'password': 'mysecurepw123',
        })
        # Form re-renders (200, not 302), no user created
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='not-an-email').exists())

    def test_post_short_password_returns_form_with_errors(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'short@example.com',
            'password': '1234567',  # 7 chars
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='short@example.com').exists())
```

- [ ] **Step 3.2: Run, confirm failures**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.RegisterViewTest -v 2
```

Expected: Failures. The view tries to read `password1`/`username` from form, which raises `KeyError` or returns `None`, breaking the `authenticate()` call → likely 500 or test assertion failures.

- [ ] **Step 3.3: Read the current register_view to confirm exact line numbers**

```bash
grep -n "form.cleaned_data\|username = \|password = \|form = CustomUserCreationForm" apps/accounts/views.py | head -10
```

Note the lines around `username = form.cleaned_data.get('username')` and `password = form.cleaned_data.get('password1')`. Line numbers may have drifted; what matters is the file structure: there are TWO instances (one in the public-mode branch ~line 65, one in the invite-only branch ~line 165). **Only touch the public-mode branch.** The invite-only branch is unchanged.

- [ ] **Step 3.4: Edit `register_view` — public-mode branch only**

In `apps/accounts/views.py`, find the public-mode form-handling block. It contains code like this:

```python
form = CustomUserCreationForm(request.POST)
if form.is_valid():
    user = form.save()
    username = form.cleaned_data.get('username')
    password = form.cleaned_data.get('password1')

    # Create subscription for user
    Subscription.objects.get_or_create(
        user=user,
        defaults={
            'tier': 'free',
            'status': 'active',
        }
    )
    ...
    messages.success(
        request, f'Welcome to the community, {username}!')

    user = authenticate(username=username, password=password)
    login(request, user)
```

Replace those exact lines (the `username = ...` and `password = ...` and downstream uses) with:

```python
form = CustomUserCreationForm(request.POST)
if form.is_valid():
    user = form.save()
    username = user.username  # auto-generated by the form
    password = form.cleaned_data['password']

    # Create subscription for user
    Subscription.objects.get_or_create(
        user=user,
        defaults={
            'tier': 'free',
            'status': 'active',
        }
    )
    ...
    messages.success(
        request, f'Welcome to the community, {username}!')

    user = authenticate(username=username, password=password)
    login(request, user)
```

The only changes are:
- `username = form.cleaned_data.get('username')` → `username = user.username`
- `password = form.cleaned_data.get('password1')` → `password = form.cleaned_data['password']`

Leave everything else in the block untouched (Subscription creation, journal-bonus promo, Milestone creation if sobriety_date is set, invite_code relationship handling, redirect).

- [ ] **Step 3.5: Re-run view tests**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.RegisterViewTest -v 2
```

Expected: All 5 view tests pass.

Note: `test_get_renders_form` checks that `name="email"` and `name="password"` are present and `name="password1"` is absent. The template (Task 4) renders these. If the template hasn't been updated yet, this test may fail on the `assertContains/assertNotContains` checks. If so, mark this test as `@expectedFailure` temporarily and clear it in Task 4. Or — and this is cleaner — **proceed to Task 4 before declaring Task 3 done.**

Actually: the existing template uses Django's form-rendering shortcut (`{{ form.username }}` etc.) which generates the field name from the form's field declarations. With the new form having `email` + `password` fields, Django will generate `name="email"` and `name="password"` automatically when the existing template renders it via `{{ form.email }}` / `{{ form.password }}`. But the existing template references `{{ form.username }}` and `{{ form.password1 }}` etc., which become empty strings when those fields don't exist.

**So `test_get_renders_form` may currently render with old field labels but blank input fields.** This will still likely pass the `name="email"` and `name="password"` assertions only after Task 4 rewrites the template. Best path: skip Step 3.5's full-pass expectation and continue to Task 4. Run all signup tests after Task 4.

- [ ] **Step 3.6: Do NOT commit yet — Task 4 finishes the template**

Same reasoning as Task 2: the view and template must land together for a coherent commit.

---

## Task 4: Rewrite the register.html template

Replace the public-mode form block (the `{% else %}` branch of the `{% if invite_only %}` conditional) with the new minimal layout from Approach C of the brainstorm. The `{% if invite_only %}` branch stays untouched.

**Files:**
- Modify: `apps/accounts/templates/registration/register.html`
- Modify: `apps/accounts/tests_signup.py` (append template-rendering tests)

- [ ] **Step 4.1: Append failing test for the new template content**

Append to `apps/accounts/tests_signup.py`:

```python
@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RegisterTemplateTest(TestCase):
    """The rendered register page matches Approach C from the brainstorm."""

    def test_renders_simplified_layout(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(resp.status_code, 200)
        # New layout markers
        self.assertContains(resp, 'Create your account')
        self.assertContains(resp, 'Anchor AI Coach')
        self.assertContains(resp, 'Free forever')
        # Eye toggle present
        self.assertContains(resp, 'password-eye-toggle')
        # Sign-in link present
        self.assertContains(resp, 'Already have an account?')
        # Old layout markers gone
        self.assertNotContains(resp, '✨ Join MyRecoveryPal')
        self.assertNotContains(resp, 'What you get')
        self.assertNotContains(resp, 'name="username"')
        self.assertNotContains(resp, 'name="password1"')
        self.assertNotContains(resp, 'name="password2"')
        self.assertNotContains(resp, 'name="sobriety_date"')

    def test_email_input_has_mobile_keyboard_attributes(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertContains(resp, 'inputmode="email"')
        self.assertContains(resp, 'autocapitalize="off"')
        self.assertContains(resp, 'autocomplete="email"')

    def test_password_input_has_signup_autocomplete(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertContains(resp, 'autocomplete="new-password"')
```

- [ ] **Step 4.2: Run, confirm failure**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup.RegisterTemplateTest -v 2
```

Expected: Failures — current template doesn't have any of the new markers.

- [ ] **Step 4.3: Replace the public-mode template block**

Read the current file to confirm structure:

```bash
wc -l apps/accounts/templates/registration/register.html
grep -n "{% if invite_only %}\|{% else %}\|{% endif %}\|page-header\|invite_code" apps/accounts/templates/registration/register.html | head -15
```

The file has roughly this top-level structure (from the original Read at session start):

```django
{% extends 'base.html' %}
{% load static %}
{% block title %}...{% endblock %}
{% block content %}
<div class="page-header">...</div>
<div class="container" ...>
    {% if invite_only and settings.waitlist_enabled %}
        <!-- waitlist banner -->
    {% endif %}
    <div style="background: white; padding: 2rem; ...">
        <div style="background: linear-gradient(135deg, #52b788...">  <!-- green value card -->
            ...
        </div>
        <div style="background: #f0f9ff; ...">  <!-- blue "What you get" grid -->
            ...
        </div>
        {% if invite_only %}
            <div ...>Invite-Only Beta banner</div>
        {% endif %}
        <h2 ...>Create Your Account</h2>
        <form method="post">
            {% csrf_token %}
            ...
            {% if invite_only %}
                <div ...>invite_code field</div>
            {% endif %}
            <div ...>username field</div>
            <div ...>email field</div>
            <div ...>password1 field</div>
            <div ...>password2 field</div>
            <div ...>sobriety_date field</div>
            <button>Create Account</button>
        </form>
        <div ...>Already have an account? <a>Log in</a></div>
    </div>
</div>
{% endblock %}
```

**The full rewrite** — replace the entire content of `apps/accounts/templates/registration/register.html` with:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Create your account &mdash; MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width: 500px; margin: 3rem auto; padding: 0 1rem;">

    {% if invite_only and settings.waitlist_enabled %}
    <div style="background: linear-gradient(135deg, #4db8e8 0%, #6dd5a8 100%); padding: 1.25rem; border-radius: 12px; margin-bottom: 1.5rem; text-align: center;">
        <h3 style="color: white; margin: 0 0 0.5rem 0; font-size: 1.15rem;">Don't have an invite code?</h3>
        <p style="color: white; margin: 0 0 0.85rem 0; font-size: 0.9rem;">
            Join our waitlist to get early access.
        </p>
        <a href="{% url 'accounts:request_access' %}"
            style="display: inline-block; background: white; color: #4db8e8; padding: 0.6rem 1.5rem; border-radius: 8px; font-weight: 600; text-decoration: none;">
            Request Access &rarr;
        </a>
    </div>
    {% endif %}

    <div style="background: white; padding: 2rem 1.75rem; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">

        {% if invite_only %}
            {# INVITE-ONLY MODE: keep the full form path unchanged. #}
            <h2 style="text-align: center; margin: 0 0 0.5rem; color: var(--primary-dark, #1e4d8b);">Create your account</h2>
            <p style="text-align: center; color: #666; margin: 0 0 1.25rem; font-size: 0.9rem;">Invite-only beta &mdash; enter your code below.</p>
            <form method="post">
                {% csrf_token %}
                {% if form.non_field_errors %}
                <div class="alert alert-danger" style="margin-bottom: 1rem;">{{ form.non_field_errors }}</div>
                {% endif %}
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.invite_code.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Invite Code *</label>
                    {{ form.invite_code }}
                    <small style="color: #666; display: block; margin-top: 0.25rem;">{{ form.invite_code.help_text }}</small>
                    {% if form.invite_code.errors %}<div style="color: #dc3545; font-size: 0.85rem; margin-top: 0.25rem;">{{ form.invite_code.errors }}</div>{% endif %}
                </div>
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.username.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Username *</label>
                    {{ form.username }}
                    {% if form.username.errors %}<div style="color: #dc3545; font-size: 0.85rem;">{{ form.username.errors }}</div>{% endif %}
                </div>
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.email.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Email Address *</label>
                    {{ form.email }}
                    {% if form.email.errors %}<div style="color: #dc3545; font-size: 0.85rem;">{{ form.email.errors }}</div>{% endif %}
                </div>
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.password1.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Password *</label>
                    {{ form.password1 }}
                    <small style="color: #666; display: block; margin-top: 0.25rem;">At least 8 characters.</small>
                    {% if form.password1.errors %}<div style="color: #dc3545; font-size: 0.85rem;">{{ form.password1.errors }}</div>{% endif %}
                </div>
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.password2.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Confirm Password *</label>
                    {{ form.password2 }}
                    {% if form.password2.errors %}<div style="color: #dc3545; font-size: 0.85rem;">{{ form.password2.errors }}</div>{% endif %}
                </div>
                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.sobriety_date.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Sobriety Date (Optional)</label>
                    {{ form.sobriety_date }}
                    <small style="color: #666; display: block; margin-top: 0.25rem;">{{ form.sobriety_date.help_text }}</small>
                </div>
                <button type="submit" class="btn btn-success" style="width: 100%; padding: 0.85rem; font-size: 1rem; margin-top: 0.5rem;">Create Account</button>
            </form>
        {% else %}
            {# PUBLIC MODE: friction-reduced 2-field form. #}
            <h2 style="text-align: center; margin: 0 0 0.4rem; color: var(--primary-dark, #1e4d8b); font-size: 1.5rem;">Create your account</h2>
            <p style="text-align: center; color: #666; margin: 0 0 0.85rem; font-size: 0.9rem;">Includes Anchor AI Coach + 14-day Premium trial</p>
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <span style="display: inline-block; background: #e3f4ec; color: #45a374; padding: 0.3rem 0.85rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600;">
                    &#x2713; Free forever &middot; No credit card
                </span>
            </div>

            <form method="post">
                {% csrf_token %}
                {% if form.non_field_errors %}
                <div class="alert alert-danger" style="margin-bottom: 1rem;">{{ form.non_field_errors }}</div>
                {% endif %}

                <div class="form-group" style="margin-bottom: 1rem;">
                    <label for="{{ form.email.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Email</label>
                    {{ form.email }}
                    {% if form.email.errors %}<div style="color: #dc3545; font-size: 0.85rem; margin-top: 0.25rem;">{{ form.email.errors }}</div>{% endif %}
                </div>

                <div class="form-group" style="margin-bottom: 1.25rem; position: relative;">
                    <label for="{{ form.password.id_for_label }}" style="display: block; margin-bottom: 0.35rem; font-weight: 600; font-size: 0.85rem;">Password</label>
                    {{ form.password }}
                    <button type="button" id="password-eye-toggle" aria-label="Show or hide password"
                        style="position: absolute; right: 12px; top: 32px; background: none; border: none; cursor: pointer; padding: 0.25rem; color: #888; font-size: 1.1rem;">
                        <i class="fas fa-eye" id="password-eye-icon" aria-hidden="true"></i>
                    </button>
                    <small style="color: #666; display: block; margin-top: 0.25rem;">At least 8 characters.</small>
                    {% if form.password.errors %}<div style="color: #dc3545; font-size: 0.85rem; margin-top: 0.25rem;">{{ form.password.errors }}</div>{% endif %}
                </div>

                <button type="submit" class="btn btn-success" style="width: 100%; padding: 0.85rem; font-size: 1rem; font-weight: 700; border-radius: 8px;">Create Account</button>

                <p style="text-align: center; color: #888; font-size: 0.75rem; margin-top: 1rem; line-height: 1.5;">
                    By creating an account you agree to the
                    <a href="{% url 'core:terms' %}" style="color: #1e4d8b;">Terms</a> and
                    <a href="{% url 'core:privacy' %}" style="color: #1e4d8b;">Privacy Policy</a>.
                </p>
            </form>
        {% endif %}

        <div style="margin-top: 1.5rem; padding-top: 1.25rem; border-top: 1px solid #eee; text-align: center;">
            <p style="color: #666; margin: 0; font-size: 0.9rem;">
                Already have an account?
                <a href="{% url 'accounts:login' %}" style="color: var(--primary-light, #4db8e8); font-weight: 600;">Sign in</a>
            </p>
        </div>
    </div>
</div>

<style>
    .form-control,
    form input[type="text"],
    form input[type="email"],
    form input[type="password"],
    form input[type="date"] {
        width: 100%;
        padding: 0.65rem 0.85rem;
        border: 1.5px solid #ddd;
        border-radius: 8px;
        font-size: 0.95rem;
        background: #fafafa;
        box-sizing: border-box;
        font-family: inherit;
    }
    form input:focus {
        outline: none;
        border-color: #52b788;
        background: white;
        box-shadow: 0 0 0 3px rgba(82, 183, 136, 0.15);
    }
</style>

<script>
(function () {
    var toggle = document.getElementById('password-eye-toggle');
    if (!toggle) return;
    var passwordInput = document.querySelector('input[name="password"]');
    var icon = document.getElementById('password-eye-icon');
    if (!passwordInput || !icon) return;
    toggle.addEventListener('click', function () {
        var showing = passwordInput.type === 'text';
        passwordInput.type = showing ? 'password' : 'text';
        icon.classList.toggle('fa-eye', showing);
        icon.classList.toggle('fa-eye-slash', !showing);
    });
})();
</script>
{% endblock %}
```

**Notes for the implementer:**
- Two distinct branches in the template: invite-only (preserves the full 6-field flow) vs public (the new 2-field flow). The `{% if invite_only %}` conditional gates which one renders.
- The invite-only branch preserves the original look — username, password1, password2, sobriety_date all still render — because that form (`CustomUserCreationFormWithInvite`) still has those fields.
- The public branch uses `{{ form.email }}` and `{{ form.password }}` which Django will render with the widget attributes (`autocomplete`, `inputmode`, etc.) from the form class.
- The `<style>` block applies to BOTH branches but its rules are field-name-agnostic.
- The eye-toggle JS only attaches if `#password-eye-toggle` exists in the DOM — invite-mode renders nothing with that id, so the JS is a no-op there.
- The Font Awesome `fa-eye` / `fa-eye-slash` icons are already loaded site-wide via `base.html` (used elsewhere in the site).

- [ ] **Step 4.4: Run all signup tests**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts.tests_signup -v 2 2>&1 | tail -20
```

Expected: All signup tests pass — 3 (generator) + 7 (form) + 5 (view) + 3 (template) = 18.

- [ ] **Step 4.5: Run full apps.accounts suite — should be clean now**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -3
```

Expected: 66 tests pass (48 baseline + 18 new). Zero failures, zero errors.

If any pre-existing test fails, it's almost certainly something that was hitting `password1`/`username` in the old form. Read the failure and fix it.

- [ ] **Step 4.6: Smoke-test the public-mode template via Django render-bytes check**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py shell -c "
from django.test import Client
from django.test.utils import override_settings
with override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
    c = Client()
    r = c.get('/accounts/register/')
    print('Status:', r.status_code)
    print('Has new H2:           ', b'Create your account' in r.content)
    print('Has value pill:       ', b'Free forever' in r.content)
    print('Has email input:      ', b'name=\"email\"' in r.content)
    print('Has password input:   ', b'name=\"password\"' in r.content)
    print('Has eye toggle:       ', b'password-eye-toggle' in r.content)
    print('Old H1 gone:          ', b'\xe2\x9c\xa8 Join MyRecoveryPal' not in r.content)
    print('username field gone:  ', b'name=\"username\"' not in r.content)
    print('password1 field gone: ', b'name=\"password1\"' not in r.content)
    print('sobriety_date gone:   ', b'name=\"sobriety_date\"' not in r.content)
"
```

Expected: Every line `True` (status 200).

- [ ] **Step 4.7: Commit everything from Tasks 2, 3, 4 in one cohesive commit**

```bash
git add apps/accounts/forms.py apps/accounts/views.py apps/accounts/templates/registration/register.html apps/accounts/tests_signup.py
git commit -m "feat(accounts): friction-reduced signup form (5 visible fields → 2)

Public-mode register page now shows only email + password (with
show-password eye toggle). Username is auto-generated server-side
('Friend1234'-style). Sobriety date is deferred to progressive
disclosure. Confirm-password field is replaced by the eye toggle.

- CustomUserCreationForm slimmed to email + password
- register_view reads username from saved user (not form data)
- Template rewritten for invite-only path unchanged; public path
  matches brainstorm Approach C (tagline + value pill, no heavy cards)
- 18 new tests in apps/accounts/tests_signup.py

Spec: docs/plans/2026-05-25-registration-friction-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Final regression + push + PR

- [ ] **Step 5.1: Re-run the full test suite**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py test apps.accounts -v 0 2>&1 | tail -3
```

Expected: 66 tests pass.

- [ ] **Step 5.2: Run Django system check**

```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib python3 manage.py check 2>&1 | tail -3
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 5.3: Push branch**

```bash
git push -u origin feat/registration-friction 2>&1 | tail -3
```

- [ ] **Step 5.4: Open the PR**

```bash
gh pr create --base main --head feat/registration-friction \
  --title "feat(accounts): friction-reduced signup form (5 fields → 2)" \
  --body "$(cat <<'EOF'
## Summary

Audit Priority #2 — collapse the public signup form from 4–5 visible fields down to 2 (email + password with show-password eye toggle). Auto-generates a friendly anonymous username server-side. Preserves every existing server-side behavior (subscription creation, invite-code linking, promo application, welcome emails).

**Before:** 4 required fields (username, email, password1, password2) + 1 optional (sobriety_date) + heavy green value card + blue 2x2 'What you get' grid

**After:** 2 fields (email, password with eye toggle) + single tagline + one value pill

## Why

GSC data shows your traffic ranks 30–80 on real tool-seeker queries — when discovery works, the next biggest funnel leak is the form itself. Modern signup UX (Notion, Linear, Stripe, GitHub) is 2 fields with show-password. This brings registration in line with that standard.

**Apple/Google SSO is explicitly out of scope** — that's a follow-up (Tier 2/3 in the brainstorm) requiring OAuth credentials, App Store re-submission, and Capacitor native plugin work. Field reduction alone delivers ~80% of the friction win at ~10% of the implementation cost.

## What changed

- New `apps/accounts/username_generator.py` — `generate_unique_username()` returns 'Friend1234'-style names from a 10-word list + 4-digit suffix, with collision fallback
- Slimmed `CustomUserCreationForm` to email + password (now a `ModelForm` instead of `UserCreationForm`)
- `register_view` reads `username` from the saved user object instead of form data; reads `password` (not `password1`)
- Template rewritten — invite-only branch preserved unchanged; public branch matches brainstorm Approach C
- `CustomUserCreationFormWithInvite` left untouched (invite-only flow has a different audience)

## Test plan

- [x] 66/66 tests pass (48 baseline + 18 new across `UsernameGeneratorTest`, `SignupFormTest`, `RegisterViewTest`, `RegisterTemplateTest`)
- [x] `manage.py check` clean
- [x] Render-bytes assertion confirms new H2, value pill, eye toggle, all old field names absent
- [ ] **Post-merge manual smoke:** open www.myrecoverypal.com/accounts/register/ on production at desktop and mobile. Verify:
  - 2 visible fields (email, password) + eye toggle works
  - Submit creates a user with auto-generated username (check via Django admin or shell)
  - Welcome flow + Subscription creation still happen (check Subscription table)
  - Invite-only mode (if you flip `SystemSettings.invite_only_mode=True`) renders the unchanged 5-field form

## Out of scope (separate audit follow-ups)

- Apple/Google SSO (separate brainstorm + spec)
- Email verification before login (would *add* friction)
- A/B test infrastructure (this is a directional bet based on GSC + audit data)
- Post-signup sobriety-date prompt modal (progressive disclosure stays)

Design spec: \`docs/plans/2026-05-25-registration-friction-design.md\`
Implementation plan: \`docs/plans/2026-05-25-registration-friction.md\`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" 2>&1 | tail -3
```

Expected: PR URL printed. GitGuardian (the only configured CI check) should pass since this branch only touches code and templates.

---

## Self-Review

**Spec coverage check** — walking the spec section-by-section:

- ✓ "2 fields: email + password" → Task 2 form + Task 4 template
- ✓ "auto-generated username server-side" → Task 1 (module) + Task 2 (form.save uses it) + Task 3 (view reads from saved user)
- ✓ "sobriety_date dropped from signup" → Task 2 removes field; Task 4 template no longer renders it
- ✓ "confirm-password dropped + eye toggle" → Task 2 single password field; Task 4 inline JS toggle
- ✓ "Approach C layout (tagline + pill, no heavy cards)" → Task 4 template
- ✓ "invite-only mode untouched" → Task 2 explicitly preserves `CustomUserCreationFormWithInvite`; Task 4 preserves the `{% if invite_only %}` template branch
- ✓ "preserve subscription creation, journal-bonus promo, sponsor/pal invite linking, milestone creation, welcome emails" → Task 3 only touches the two specific lines that read form fields by their old names; the rest of `register_view` is preserved verbatim
- ✓ All test classes from spec's test table are written in Tasks 1–4

**Placeholder scan:** No "TBD", no "implement later", no "add error handling" — every step has actual code or actual commands. ✓

**Type consistency:** 
- `WORDLIST` (Task 1) is imported and used in Tasks 1, 2 tests ✓
- `generate_unique_username` (Task 1) is called from `CustomUserCreationForm.save()` (Task 2) ✓
- `user.username` (Task 3 view) gets the value from `form.save()` (Task 2) ✓
- Field names: `email`, `password` — consistent across form (Task 2), view (Task 3), template (Task 4), tests (all tasks) ✓
- Old field names (`password1`, `password2`, `username`, `sobriety_date`) explicitly NOT referenced anywhere in public-mode path; explicitly ARE preserved in invite-only path. ✓

One thing worth noting: the `min_length=8` validation lives in two places in the new form code (the `min_length` kwarg on the field AND the `minlength="8"` attr on the input widget). The kwarg enforces server-side; the attr is for HTML5 client-side hinting. Both are intentional — server-side is the source of truth, client-side is UX polish. Same pattern as Django defaults elsewhere.

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-25-registration-friction.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
