# Facility Self-Serve Onboarding — Design Spec

**Date:** 2026-06-18
**Phase:** Revenue Phase 4 (B2B) — treatment-center aftercare follow-up
**Status:** Design approved, pending spec review

---

## 1. Summary

Replace CLI-only facility provisioning (`manage.py create_facility`) with a
public, self-serve online signup so a treatment center can create its own
aftercare account without any action from the operator. Signup is **free**
(billing handled offline), the facility becomes usable **immediately after work-
email verification**, and the operator is **notified** of each new signup and can
pause any bad actor.

This builds on the existing aftercare module
(`docs/superpowers/specs/2026-06-17-treatment-center-aftercare-design.md`,
shipped to `main`). It does NOT change the alumni/at-risk monitoring — only how a
facility account comes into existence.

### Decisions locked during brainstorming
- **Who:** facility self-serve (the treatment center signs up itself).
- **Access gate:** free now, bill offline later — no card, auto-provisioned.
- **Verification:** auto-active after the signer verifies their work email;
  operator is emailed on each new signup and can pause a facility.
- **`create_facility` command stays** as the operator's manual fallback (creates
  facilities `active` directly — operator is trusted).
- **Existing-email signups are rejected** with a pointer to log in (no
  authenticated "create facility from my account" path in this MVP).
- **Admin notification** goes to `FACILITY_SIGNUP_NOTIFY_EMAIL` if set, else
  `DEFAULT_FROM_EMAIL`.

### Key architectural insight
The existing `status` gate already does the security work. `facility_staff_required`
(dashboard) and `facility_join` (enrollment) both require `status='active'`.
A self-serve signup that starts `status='pending'` is therefore automatically
locked out of the dashboard AND cannot enroll alumni until verification flips it
to `active`. No new gating logic is required — only a new status value and a
verification flow.

---

## 2. Data Model Change

Modify `Facility` in `apps/accounts/facility_models.py` (one migration):

- Add `'pending'` to `STATUS_CHOICES` → `pending` / `active` / `paused`.
  - `pending` = self-serve signup, email not yet verified.
  - `active` = verified self-serve, or operator/admin-created.
  - `paused` = operator disabled it.
- Add `activation_token` (CharField, max_length 64, blank, db_index) — a random
  token for the email-verification link; cleared (set `''`) after verification.
- Add `email_verified_at` (DateTimeField, null=True, blank=True) — stamped at
  verification.
- Reuse `FacilityInvite.generate_code()`-style randomness for the token
  (`secrets.token_urlsafe(32)`).

**Unchanged behaviors that now gate pending facilities for free:**
- `facility_staff_required` requires `facility__status='active'` → pending
  facility's staff are locked out of the dashboard (they see a "verify your
  email" state instead — see §3).
- `facility_join` rejects `facility.status != 'active'` (added in the aftercare
  fix `345d8ee7`) → a pending facility's invite links cannot enroll anyone.
- The `create_facility` command and Django `/admin/` continue to create
  facilities with the default `status='active'` — no change needed.

---

## 3. Flow & Surfaces

New files (keep the signup flow isolated from the existing facility views):
- `apps/accounts/facility_forms.py` — signup form.
- `apps/accounts/facility_signup_views.py` — signup + verify views.

### Public signup — `/accounts/facility/signup/` (no auth)
- GET: renders the signup form. Fields: `facility_name`, `contact_name`,
  `email` (work email), `password`.
- POST (valid):
  1. If a `User` with that email already exists → reject with a form error:
     "An account with this email already exists. Log in and contact us to add a
     facility." (No user/facility created.)
  2. Otherwise create:
     - `User` (username derived from email, collision-safe; password set;
       `is_active=True`),
     - `Facility(name=facility_name, slug=unique-from-name,
       status='pending', activation_token=<random>)`,
     - `FacilityStaff(facility, user, role='admin')`.
  3. Send a **verification email** to `email` with a link to
     `/accounts/facility/verify/<activation_token>/`.
  4. Send an **operator notification** email (to `FACILITY_SIGNUP_NOTIFY_EMAIL`
     or `DEFAULT_FROM_EMAIL`) naming the facility + contact email.
  5. Render a "Check your email to activate your facility" confirmation page.
- POST (invalid): re-render the form with errors. No partial objects created
  (wrap creation in `transaction.atomic`).

### Email verification — `/accounts/facility/verify/<token>/` (no auth required)
- Looks up `Facility` by `activation_token` (non-empty).
  - Found: set `status='active'`, stamp `email_verified_at`, clear
    `activation_token`, log the staff user in, redirect to
    `accounts:facility_dashboard` with a success message.
  - Not found / empty token: render a friendly "link invalid or already used"
    page (if the facility is already `active`, tell them so and link to login).

### Pending state in the dashboard
`facility_staff_required` already redirects non-active facilities' staff away. To
avoid a confusing redirect loop for a freshly-signed-up admin, the decorator's
"no active facility" path stays as-is (redirect to `accounts:progress`), but the
signup confirmation page clearly tells them to verify first. No change to the
decorator. (A logged-in pending admin simply can't reach the dashboard until they
click the verification link — acceptable for MVP.)

### Routes (added to `apps/accounts/urls.py`)
- `/accounts/facility/signup/` → `facility_signup`
- `/accounts/facility/verify/<str:token>/` → `facility_verify_email`

### Settings
- `FACILITY_SIGNUP_NOTIFY_EMAIL = os.environ.get('FACILITY_SIGNUP_NOTIFY_EMAIL', DEFAULT_FROM_EMAIL)`
  in `recovery_hub/settings.py`.

### Templates
- `apps/accounts/templates/accounts/facility/signup.html` — the form.
- `apps/accounts/templates/accounts/facility/signup_done.html` — "check your email".
- `apps/accounts/templates/accounts/facility/verify_invalid.html` — bad/used link.
- `apps/accounts/templates/emails/facility_verify_email.html` — verification email.
- `apps/accounts/templates/emails/facility_signup_notify.html` — operator notify email.

Emails sent via the existing `email_service.send_email(subject, plain_message,
html_message, recipient_email)`.

---

## 4. Data Flow

1. Treatment center visits `/accounts/facility/signup/`, submits the form.
2. System creates User + `pending` Facility + admin FacilityStaff; emails a
   verification link to the signer and a notification to the operator.
3. Signer clicks the verification link → facility becomes `active`, signer is
   logged in and lands on the (now-accessible) dashboard.
4. From the dashboard/roster they generate invite links and onboard alumni
   exactly as before.
5. Operator sees the notification, follows up to arrange billing, and can
   `pause` any facility from `/admin/` if needed.

---

## 5. Out of Scope (this MVP)

- Stripe / any billing (still offline).
- Authenticated "create a facility from my existing account" path.
- A marketing/landing page for the signup (just the functional form).
- Captcha / rate-limiting beyond Django defaults and email verification.
- Re-sending the verification email / token expiry (token is single-use and
  long-lived until used; re-send can be a fast follow if needed).
- Changing the at-risk monitoring, roster, digest, or consent flows.

---

## 6. Testing

- **Signup happy path:** valid POST creates exactly one User, one
  `status='pending'` Facility, one `role='admin'` FacilityStaff; both the
  verification email and the operator-notification email are sent (assert via
  mocked `send_email` call count/recipients).
- **Duplicate email:** POST with an email that already belongs to a User creates
  no objects and returns a form error.
- **Pending gating:** a pending facility's staff get redirected from
  `facility_dashboard`; a pending facility's invite link does not enroll
  (`facility_join` rejects) — confirms reuse of existing gates.
- **Verification:** GET the verify URL with a valid token → facility becomes
  `active`, `email_verified_at` set, `activation_token` cleared, staff logged in,
  redirect to dashboard which now returns 200.
- **Invalid token:** GET verify with an unknown/empty token → invalid page, no
  state change.
- **Atomicity:** a signup that fails partway creates no orphaned User/Facility.

View tests use `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`
(project sets `PREPEND_WWW=True`).

---

## 7. Files

New:
- `apps/accounts/facility_forms.py`
- `apps/accounts/facility_signup_views.py`
- `apps/accounts/templates/accounts/facility/signup.html`
- `apps/accounts/templates/accounts/facility/signup_done.html`
- `apps/accounts/templates/accounts/facility/verify_invalid.html`
- `apps/accounts/templates/emails/facility_verify_email.html`
- `apps/accounts/templates/emails/facility_signup_notify.html`

Modified:
- `apps/accounts/facility_models.py` (status choice + two fields) + migration
- `apps/accounts/urls.py` (two routes)
- `recovery_hub/settings.py` (`FACILITY_SIGNUP_NOTIFY_EMAIL`)
- `apps/accounts/tests_facility.py` (append signup/verify tests)

Unchanged (intentionally): `create_facility` command, `facility_service.py`,
`facility_views.py` dashboard/roster/member-detail, decorator, digest task.
