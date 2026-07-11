# Relapse Prevention Plan Builder

**Date:** 2026-07-11
**Status:** Approved design, pending implementation plan

## Problem

A written relapse prevention plan is a standard, high-value recovery tool
(therapists assign it as homework), but the platform has nowhere to build
one. It is also the last of the three ranked retention features from the
2026-07-10 brainstorm, and pairs naturally with the Craving SOS page — the
plan is exactly what the 2 AM moment needs.

## Goals

1. A guided, private, editable relapse prevention plan per member.
2. Premium-gated PDF export (the plan itself is always free — consistent
   with the never-paywall-safety principle).
3. Entry points: Craving SOS page, Resources nav, and a public SEO landing
   page at `/relapse-prevention-plan/`.

Non-goals for v1: sharing with pal/sponsor, auto-embedding personal tools
(pledge photo, sobriety date) in the PDF, plan-update reminders, a
multi-step wizard.

## Design

### 1. Model

`apps/accounts/plan_models.py` (separate file re-exported through
`models.py`, matching the `court_models.py` pattern):

- `RelapsePreventionPlan`
  - `user` OneToOne → User (CASCADE), related_name `relapse_plan`
  - Section TextFields, all `blank=True`: `triggers`, `warning_signs`,
    `coping_strategies`, `reasons`, `emergency_steps`, `halt_notes`
  - `support_contacts` JSONField, default list — list of dicts
    `{"name": str, "phone": str, "relationship": str}`
  - `created_at` / `updated_at`
  - Property `filled_section_count` → int 0..7 (six text sections plus
    contacts counted when non-empty) for a "5 of 7 sections" progress hint.
- Privacy: plan content is private like the journal — never rendered in
  feeds, activity, or any other member's view.
- One migration.

### 2. Builder page

- URL `/accounts/plan/`, name `accounts:relapse_plan`, `@login_required`.
- `apps/accounts/plan_views.py::relapse_plan_view`: GET renders the form
  bound to `RelapsePreventionPlan.objects.get_or_create(user=...)`; POST
  validates and saves, then redirects back with a success message.
- `apps/accounts/plan_forms.py::RelapsePreventionPlanForm`: the six text
  sections as textareas, plus a hidden `support_contacts` field carrying
  JSON. Server-side clean: parse JSON, require list of dicts, keep only
  the three known keys, strip whitespace, drop fully-empty rows, cap at
  10 contacts and 100 chars per value; invalid JSON → form error.
- Template `accounts/relapse_prevention_plan.html`: one scrolling page;
  each section a card with a one-line "why this matters" and placeholder
  examples; support contacts as add/remove rows managed by small inline
  vanilla JS that syncs rows into the hidden JSON field on submit; a
  "{{ filled }} of 7 sections" progress hint; Save button; a PDF-export
  button (see §3).

### 3. PDF export (premium)

- URL `/accounts/plan/pdf/`, name `accounts:relapse_plan_pdf`, decorated
  `@login_required` + `@premium_required` (existing decorator).
- `apps/accounts/plan_service.py::render_plan_pdf(user) -> bytes` follows
  the court_service WeasyPrint pattern: render
  `accounts/relapse_plan_pdf.html` (print-styled: member display name,
  generation date, all seven sections, 988 crisis-line footer) →
  `HTML(string=...).write_pdf(buf)`.
- The view returns the bytes as an `application/pdf` attachment
  (`relapse-prevention-plan.pdf`).
- On the builder page, free users see the Export button rendered with a
  lock and an upgrade hint linking to pricing (progressive-upgrade
  pattern); premium users get the working download button.

### 4. Entry points

- **Craving SOS page** (`apps/core/templates/core/craving_sos.html`):
  in the members' action slot — members WITH a plan (any content,
  `filled_section_count > 0`) get a "My relapse plan" pill next to the
  Anchor button; members without get a "Build your relapse prevention
  plan" link in the same area. Anonymous visitors unchanged. The view
  (`CravingSOSView`) adds a `has_plan` context flag for authenticated
  users (single cheap query).
- **Nav**: an entry in the Resources dropdown and the mobile menu
  ("Relapse Prevention Plan" → `accounts:relapse_plan`).

### 5. SEO landing page

- `/relapse-prevention-plan/` in `apps.core`, name
  `core:relapse_prevention_plan`, per the landing-page playbook:
  - What a relapse prevention plan is and why it works; a static
    section-by-section template preview (readable as a worksheet without
    signing up); FAQPage JSON-LD (~5 questions) mirrored EXACTLY by
    visible FAQ copy; register CTA ("build yours free");
    `_related_tools.html` card (key `relapse_prevention_plan`) and the
    page includes the partial with that exclude key; sitemap entry 0.9;
    canonical www.

### 6. Testing

- Model: `filled_section_count` across empty/partial/full plans.
- Form: contacts JSON validation (valid rows kept, empties dropped,
  unknown keys stripped, >10 rows rejected, invalid JSON → error).
- Builder view: login required; GET pre-fills; POST round-trip saves all
  sections; second GET shows saved content.
- PDF view: free user → redirected to upgrade (per `premium_required`);
  premium user → 200 with `application/pdf` content type. The genuine
  WeasyPrint render test must tolerate the local macOS Pango env issue
  the court tests have — follow whatever skip/env pattern the court test
  suite uses (check at plan time); the gating tests mock `render_plan_pdf`
  so they never depend on WeasyPrint.
- SOS page: has-plan member sees "My relapse plan"; plan-less member sees
  the build nudge; anonymous sees neither.
- Landing page: 200, FAQPage schema present, in sitemap.
- View tests use the repo convention
  `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`.

## Verification of success

After deploy: build a plan on the live site, save, reload, export the PDF
on a premium account (and confirm the free-account lock state), see the
plan pill on /craving-sos/, and confirm `/relapse-prevention-plan/` renders
and is in the sitemap; submit the landing URL in Search Console.
