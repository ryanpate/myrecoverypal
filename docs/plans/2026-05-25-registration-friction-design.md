# Registration Friction Reduction — Design

**Date:** 2026-05-25
**Status:** Approved direction; implementation plan to follow
**Audit reference:** Conversion audit Priority #2 — registration is the conversion bottleneck downstream of the (now-shipped) tool-first hero. Cuts visible form fields from 4–5 to 2.

---

## Goal

Reduce the public-mode signup form from 4 visible fields (username, email, password, confirm-password) plus 1 optional (sobriety date) — down to **2 fields: email + password (with show-password toggle)**. Auto-generate a friendly anonymous username. Preserve every server-side behavior (subscription creation, invite-code handling, welcome emails, sponsor/pal linkage, promo application).

## Why this change

GSC data shows your traffic ranks 30–80 on real tool-seeker queries — when discovery does work, the next-largest funnel leak is the signup form itself. Five fields plus a confirm-password and a sobriety-date picker is a heavy ask for a user who just clicked "Count My Days" on the hero. Modern signup UX (Notion, Linear, Stripe, GitHub) is 2 fields with show-password. This change brings registration in line with that standard.

The full audit's "+ Apple/Google SSO" item is **explicitly out of scope** for this change — that's a follow-up (Tier 2/3 in the brainstorm) requiring OAuth credentials, App Store re-submission, and Capacitor native plugin work. Field reduction alone delivers ~80% of the friction win at ~10% of the implementation cost.

## Approved direction

Brainstorm session locked these decisions:

1. **Scope:** Tier 1 — field reduction only. No SSO in this PR.
2. **Username strategy:** Friendly anonymous default ("Friend1234"-style). Auto-generated server-side from a small wordlist + 4-digit random suffix, collision-checked.
3. **Confirm-password field:** Dropped. Replaced with a show-password (eye icon) toggle on the single password field.
4. **Sobriety date:** Removed from signup. Users can set it later from their profile or progress page (progressive disclosure pattern already established by the 2026-02 onboarding simplification).
5. **Page layout:** Approach C from brainstorm — `<h2>` + tagline + small value pill + form. Drops the heavy green value-card and the blue 2x2 feature grid (visual noise reduction).
6. **Value-prop messaging:** Compressed from 3 visual elements down to one tagline (`Includes Anchor AI Coach + 14-day Premium trial`) + one pill (`✓ Free forever · No credit card`).
7. **Invite-only mode path:** Existing `CustomUserCreationFormWithInvite` form/template path stays unchanged. The simplification applies only to the default (public) signup form. If/when invite mode is re-enabled, that variant continues to render its full form.

## Final UI

```
┌──────────────────────────────────────┐
│         Create your account         │
│   Includes Anchor AI Coach +        │
│       14-day Premium trial          │
│                                      │
│  [ ✓ Free forever · No credit card ]│
│                                      │
│  Email                              │
│  [ you@example.com              ]   │
│                                      │
│  Password                           │
│  [ ••••••••                  👁 ]   │
│  At least 8 characters.             │
│                                      │
│  [      Create Account         ]    │
│                                      │
│  By creating an account you agree    │
│  to the Terms and Privacy Policy.   │
│                                      │
│  Already have an account? Sign in   │
└──────────────────────────────────────┘
```

### Email field

- `<input type="email" name="email" required autocomplete="email" inputmode="email" autocapitalize="off" spellcheck="false">`
- `inputmode="email"` triggers the @-bearing mobile keyboard
- `autocapitalize="off"` prevents iOS Safari from capitalizing the first letter
- `autocomplete="email"` enables password-manager pre-fill

### Password field with toggle

- `<input type="password" name="password" required minlength="8" autocomplete="new-password">`
- Eye icon overlaid on the right side; click toggles `type` between `password` and `text`
- Pure JavaScript (no library), inline event handler in the template
- `autocomplete="new-password"` signals to password managers this is a signup, not a login

## Backend changes

### `apps/accounts/forms.py`

Slim `CustomUserCreationForm` to email + password only:

```python
class CustomUserCreationForm(forms.ModelForm):
    """Minimal-friction signup: email + password only.

    Username is auto-generated server-side; users can change it later
    in their profile. Sobriety date is captured progressively, not at signup.
    """
    email = forms.EmailField(required=True)
    password = forms.CharField(
        widget=forms.PasswordInput(),
        min_length=8,
        help_text='At least 8 characters.',
    )

    class Meta:
        model = User
        fields = ('email',)  # username is generated, password set manually

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. '
                'Try signing in instead.'
            )
        return email

    def save(self, commit=True):
        user = User(
            email=self.cleaned_data['email'],
            username=generate_unique_username(),
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
```

The existing `CustomUserCreationFormWithInvite` form is **left unchanged** — it still has username/sobriety_date/password1/password2 since the invite-only flow has a different audience (existing users sharing invite codes) and isn't the conversion target this change addresses.

### `apps/accounts/username_generator.py` (new file)

```python
"""Generate friendly anonymous usernames for new signups."""
import random
from django.contrib.auth import get_user_model

User = get_user_model()

WORDLIST = [
    'Friend', 'NewMember', 'Recovering', 'Hopeful', 'Brave',
    'Strong', 'Anchored', 'Steady', 'Rising', 'OneDay',
]

MAX_ATTEMPTS = 10


def generate_unique_username() -> str:
    """Return a unique username like 'Friend1234'.

    Tries wordlist + 4-digit suffix up to MAX_ATTEMPTS times. Falls back to
    longer numeric suffix on persistent collision (vanishingly unlikely).
    """
    for _ in range(MAX_ATTEMPTS):
        word = random.choice(WORDLIST)
        suffix = random.randint(1000, 9999)
        candidate = f'{word}{suffix}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
    # Pathological collision case — extend suffix to 8 digits
    while True:
        candidate = f'Friend{random.randint(10_000_000, 99_999_999)}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
```

### `apps/accounts/views.py` — `register_view`

Existing view reads `form.cleaned_data.get('username')` to log the user in. That keeps working with the new form because the form's `save()` sets `user.username` to the generated value, which is then on the user object. But the line `username = form.cleaned_data.get('username')` would return `None` (no such form field anymore). Fix: read `username` from the saved `user` object instead.

```python
# Before:
user = form.save()
username = form.cleaned_data.get('username')
password = form.cleaned_data.get('password1')
...
user = authenticate(username=username, password=password)

# After:
user = form.save()
password = form.cleaned_data['password']
user = authenticate(username=user.username, password=password)
```

The `if user.sobriety_date:` Milestone-creation block stays as-is — it just becomes a no-op for signups (sobriety_date is null until the user sets it later). No change needed there.

### Template `apps/accounts/templates/registration/register.html`

Replace the public-mode form block (the `{% if invite_only %}` branch's else block) with the new layout. The invite-only branch stays untouched.

## What's removed (visible)

- The green "Join Free — Includes AI Recovery Coach" card
- The blue "What you get" 2x2 feature grid
- The username form field
- The sobriety_date form field
- The "Confirm Password" field
- The "✨ Join MyRecoveryPal" page header (it duplicates the form's own H2)

## What stays (server-side, preserved exactly)

- Subscription row creation with `tier='free', status='active'` (no change)
- Journal-bonus promo application (`apply_promo_to_user`) — unchanged, still reads `journal_promo` from session
- Invite-code role-based relationship creation (sponsor/pal) — unchanged, still reads invite from POST/GET on the public form when a `?invite=` query param is present
- Initial Milestone creation IF `user.sobriety_date` is set — unchanged (just becomes a no-op for default signups)
- Post-signup redirect to `accounts:progress`
- Welcome email sequence (Day 1/3/5/7) — unchanged
- `SystemSettings.max_users` enforcement
- Invite-only mode (`CustomUserCreationFormWithInvite` form + its template branch)

## Files affected

| File | Change type |
|---|---|
| `apps/accounts/forms.py` | Modify — slim down `CustomUserCreationForm`; leave `CustomUserCreationFormWithInvite` untouched |
| `apps/accounts/username_generator.py` | Create — new module with `generate_unique_username()` |
| `apps/accounts/views.py` | Modify — `register_view` line that reads `username` from form data → read from saved user; password field name changes from `password1` to `password` |
| `apps/accounts/templates/registration/register.html` | Modify — replace public-mode form block |
| `apps/accounts/tests_signup.py` | Create — test suite for the new form + username generator |

No model changes. No migration. No new URL routes. No new dependencies. No new static assets. No JavaScript file changes (eye-toggle JS is inline in the template).

## Test coverage

| Test class | Test | Asserts |
|---|---|---|
| `UsernameGeneratorTest` | `test_returns_string_matching_pattern` | Result is `<wordlist-entry><4 digits>` |
| | `test_returns_unique_value_on_collision` | Pre-creating users with all expected names forces the fallback path and still returns unique |
| | `test_uses_wordlist_words_only` | Multiple calls only produce wordlist prefixes |
| `SignupFormTest` | `test_minimal_fields_required` | Form has exactly `email` and `password` fields |
| | `test_email_required` | Form invalid without email |
| | `test_password_minimum_length` | Form invalid with 7-char password, valid with 8+ |
| | `test_duplicate_email_rejected` | Pre-existing email returns ValidationError with friendly message |
| | `test_save_generates_username_and_sets_password` | Saved user has generated username + working password |
| `RegisterViewTest` | `test_get_renders_form` | GET / register / returns 200 with new H2 |
| | `test_post_creates_user_and_logs_in` | Valid POST creates User, logs in, redirects to `accounts:progress` |
| | `test_post_creates_subscription` | Same as above + Subscription exists with `tier='free'` |
| | `test_post_invalid_email_returns_form_errors` | Invalid POST stays on register page with error visible |

## Success criteria

1. New register page renders with 2 visible fields + show-password toggle works
2. Successful signup with email + 8-char password creates a User, Subscription, and logs them in
3. Username on the new account follows `<word><4-digit>` pattern
4. All test classes above pass
5. Invite-only mode (when toggled on in `SystemSettings`) still renders its existing form unchanged
6. No regressions in `apps.accounts` test suite

## Out of scope (explicit non-goals)

- Apple SSO or Google SSO (separate brainstorm; requires OAuth credentials + iOS Capacitor plugin work)
- Email verification before login (currently not enforced; adding it would *increase* friction)
- Username editing UI changes (existing profile-edit flow already supports it)
- Post-signup sobriety-date prompt modal (progressive disclosure stays)
- A/B testing infrastructure (no measurement of conversion lift in this PR — directional bet)
- iOS Capacitor app changes (the iOS app already works via the same `/accounts/register/` endpoint; the new form serves both web and native browsers equally)

## Implementation hand-off notes

For the writing-plans skill:

- Use TDD strictly: each test in the table above gets written first, run-fail-confirmed, implemented, run-pass-confirmed
- Run baseline test count before starting (currently 48 in `apps.accounts`); should land at 60–63 (12–15 new tests)
- One PR. Single file structure change (new `username_generator.py`); rest is in-place edits
- Estimated effort: 4–6 hours including manual smoke at desktop + mobile viewports + invite-only mode regression check
- No env vars, no migration, no Stripe/external service touched
