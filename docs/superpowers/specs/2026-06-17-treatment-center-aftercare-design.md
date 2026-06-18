# Treatment-Center Aftercare — Design Spec

**Date:** 2026-06-17
**Phase:** Revenue Phase 4 (B2B) — first slice
**Status:** Design approved, pending spec review

---

## 1. Summary

A B2B product that lets a treatment center monitor the post-discharge engagement
of its alumni and **spot at-risk clients early** so staff can reach out before a
relapse. The facility is the paying customer ($200–500/mo in the revenue plan);
its alumni use the existing consumer app for free.

This is the first of three independent B2B products (the others —
court/probation bulk, and EAP/employer — are **out of scope**, each its own
future spec → plan → build cycle).

### MVP job-to-be-done
Spot at-risk alumni early (relapse prevention). Other facility jobs (prove
program engagement, run an alumni community, comp Premium) are deliberately
deferred.

### Decisions locked during brainstorming
- **Core job:** at-risk detection.
- **Client visibility:** engagement signals + risk trend (craving/mood
  direction, "struggling" flags). **No** raw journal, **no** raw check-in note
  text. Client consent required.
- **Enrollment:** facility invite code/link with an explicit consent gate;
  works for new signups and existing users.
- **Alerting:** staff dashboard at-risk list **plus** a scheduled email digest.
- **Account/billing:** manual provisioning; offline billing. No self-serve org
  billing UI.
- **Clients are free users** (facility pays, alumni do not). Check-ins are a
  free feature, so no Premium comp is needed.
- **Digest cadence:** weekly.

---

## 2. Architecture

### Chosen approach — dedicated Facility models, risk computed on read
A new isolated module (mirrors the existing `court_models.py` /
`supporter_models.py` / `court_service.py` patterns). At-risk status is derived
**live** from existing `DailyCheckIn` data plus existing `get_days_sober()` /
streak helpers — no new metric tables for the MVP.

### Rejected — reuse `RecoveryGroup` as the cohort
Tempting (free join/invite/membership), but the semantics clash and create a
privacy hazard: group members see each other and post to a shared feed. An
aftercare cohort must be **private** — alumni must not be exposed to one another
through the facility, and staff need a metrics dashboard, not a group wall.
Forcing clinical aftercare into the social model would leak privacy and fight
the abstraction. A private alumni-community group can be added later as a
separate job.

### Deferred — self-serve / Stripe org billing
Manual provisioning was chosen, so org subscriptions, seat management, and
self-serve signup are not built.

---

## 3. Data Model

New file: `apps/accounts/facility_models.py`.

### `Facility`
The organization (one treatment center).
- `name` (CharField)
- `slug` (SlugField, unique)
- `status` — `active` / `paused`
- `monthly_rate` (DecimalField, null=True) — record-keeping only; no billing logic
- `notes` (TextField, blank) — internal sales/account notes
- `created_at`

### `FacilityStaff`
A staff user who can view the facility dashboard.
- `facility` (FK → Facility)
- `user` (FK → User)
- `role` — `admin` / `coordinator`
- `created_at`
- Unique on (facility, user).
- Access is gated by a new `@facility_staff_required` decorator
  (`apps/accounts/decorators.py`, mirroring `court_required`).

### `FacilityMembership`
The link between an alumni/client and a facility. **This row is the consent
record.**
- `facility` (FK → Facility)
- `user` (FK → User) — the alumni/client
- `status` — `invited` / `active` / `revoked` / `left`
- `consent_granted_at` (DateTimeField, null=True) — null until the client opts in
- `enrolled_at` (DateTimeField, null=True)
- `left_at` (DateTimeField, null=True)
- `risk_notified_at` (DateTimeField, null=True) — set when this member was last
  included in a digest as at-risk; cleared when they return to `ok`. Drives the
  "newly at-risk" digest logic (see §5).
- Unique on (facility, user).
- **Invariant:** staff see no engagement data for a membership unless
  `status == 'active'` AND `consent_granted_at is not None`.

### `FacilityInvite`
A shareable enrollment link. Dedicated (not reusing `InviteCode`) so consent
semantics stay clean.
- `facility` (FK → Facility)
- `code` (CharField, unique, random)
- `created_by` (FK → User, the staff member)
- `uses` (IntegerField, default 0)
- `max_uses` (IntegerField, null=True — null = unlimited)
- `expires_at` (DateTimeField, null=True)
- `created_at`

### Hard privacy invariants (enforced in service layer, covered by tests)
1. Journal entries are never exposed (consistent with global non-negotiable).
2. Raw `gratitude` / `challenge` / `goal` check-in text is never exposed.
3. Only **derived signals** surface to staff (dates, counts, levels, trend
   direction, boolean flags).
4. No consent ⇒ no data.
5. Tenant isolation: staff of facility A can never see facility B's members.

---

## 4. At-Risk Logic

New file: `apps/accounts/facility_service.py`.

Thresholds are module-level constants for the MVP (per-facility configuration is
a future enhancement). Signals are computed from `DailyCheckIn`
(`date`, `mood` where `1 == Struggling`, `craving_level`) over a trailing window.

### Flags
- **Disengaged** — no check-in in ≥ 5 days.
- **High craving** — `craving_level` at the top tier in the last 7 days.
- **Low mood** — any `mood == 1` (Struggling) in the last 7 days.

### Risk level
- `at_risk` — any flag fires.
- `watch` — no flag, but 3–4 days since last check-in.
- `ok` — otherwise.

### Functions
- `compute_member_risk(membership)` →
  `{risk_level, flags, last_checkin_date, checkin_streak, days_sober,
  craving_trend, mood_trend}`. Output is signals only — never raw text.
- `cohort_summary(facility)` → counts of members by risk level (consented active
  members only).

Computed on read. If cohorts grow large enough that dashboard/digest queries
become slow, add a daily `AftercareRiskSnapshot` precompute — explicitly **not**
in MVP scope.

---

## 5. Surfaces & Flows

New file: `apps/accounts/facility_views.py`. New decorator in
`apps/accounts/decorators.py`.

### Staff-facing (gated by `@facility_staff_required`)
- **Dashboard** — `cohort_summary` + at-risk list sorted worst-first.
- **Member detail** — engagement + risk-trend for one consented client; mood /
  craving trend charts reuse the existing progress-visualization code.
- **Roster** — list members with status; generate/copy an invite link; revoke a
  member.

### Client-facing
- **Join + consent** — `facility/join/<code>`:
  - Logged-out → route through signup/login, then return to the consent screen.
  - Consent screen: "Share your check-in engagement and risk signals with
    [Facility] so your care team can support you. Your journal is never shared.
    You can revoke anytime."
  - On accept: membership `status = active`, `consent_granted_at` set,
    `enrolled_at` set, invite `uses` incremented.
- **Transparency / revoke** — in the client's own account settings: shows which
  facility they share with and a **Revoke** button (sets `status = revoked`;
  staff visibility stops immediately).

### Background
- **Weekly digest** — Celery task `send_facility_risk_digest`:
  - Runs weekly (added to the existing celery-beat schedule).
  - For each active facility, emails each staff member the alumni who are
    **newly** at-risk since the last digest (avoid repeating the same names every
    week). "Newly" is tracked via `FacilityMembership.risk_notified_at`: a member
    is included when `risk_level == at_risk` and `risk_notified_at is None`; on
    inclusion, `risk_notified_at` is stamped; when a member returns to `ok`,
    `risk_notified_at` is cleared so a future relapse re-notifies.
  - New template `apps/accounts/templates/emails/facility_risk_digest.html`,
    sent via the existing `send_email()` service.

### Provisioning (manual)
- `manage.py create_facility --name "X" --staff-email a@b.com` creates the
  `Facility` and a `FacilityStaff` row (creating/linking the staff user). Mirrors
  existing management-command patterns.

### Routes (under `apps/accounts/urls.py`)
- `/accounts/facility/` — dashboard
- `/accounts/facility/roster/` — roster + invite management
- `/accounts/facility/member/<id>/` — member detail
- `/accounts/facility/join/<code>/` — join + consent (client)
- Client revoke lives in existing account settings.

---

## 6. Data Flow

1. You run `create_facility` → Facility + staff login exist.
2. Staff logs in → dashboard (empty) → roster → generates an invite link → sends
   it to alumni (off-platform).
3. Alumni opens link → signs up or logs in → consents → `FacilityMembership`
   active.
4. Alumni uses the app normally (free daily check-ins).
5. `facility_service` computes risk on dashboard load; the weekly digest emails
   staff the newly at-risk.
6. Staff reach out to at-risk alumni off-platform (in-app messaging is a future
   enhancement).

---

## 7. Out of Scope (MVP)

- Self-serve facility signup / Stripe org subscriptions / seat management.
- Alumni community group (the "run a community" job).
- Real-time alerts (weekly digest only).
- In-app staff ↔ client messaging.
- Raw check-in note text or journal exposure (never, not just MVP).
- Precomputed risk snapshots (compute-on-read; revisit if cohorts grow).
- Comping Premium to clients.
- Court/probation bulk and EAP B2B products (separate future specs).

---

## 8. Testing

- **Risk computation** across scenarios: no check-ins, recent struggling mood,
  high craving, healthy/engaged.
- **Consent gating:** staff cannot retrieve any engagement data for a membership
  without `consent_granted_at` (and `status == active`).
- **Tenant isolation:** facility A staff cannot access facility B members or
  dashboard.
- **Access control:** non-staff users are blocked from all facility staff views.
- **Digest:** includes only members newly at-risk since the last run; emails go
  to all staff of the facility.
- **Enrollment:** valid code activates membership + records consent + increments
  uses; expired/maxed code is rejected.
- **Revoke:** revoking immediately removes staff visibility.

---

## 9. Files (new unless noted)

- `apps/accounts/facility_models.py` — Facility, FacilityStaff, FacilityMembership, FacilityInvite
- `apps/accounts/facility_service.py` — risk computation + cohort summary
- `apps/accounts/facility_views.py` — dashboard, member detail, roster, join/consent
- `apps/accounts/decorators.py` — add `facility_staff_required` (existing file)
- `apps/accounts/urls.py` — add facility routes (existing file)
- `apps/accounts/templates/accounts/facility/` — dashboard, roster, member_detail, join_consent templates
- `apps/accounts/templates/emails/facility_risk_digest.html`
- `apps/accounts/management/commands/create_facility.py`
- `apps/accounts/tasks.py` — add `send_facility_risk_digest` (existing file)
- migration for the new models
- account settings template — add facility sharing/revoke section (existing)
- tests
