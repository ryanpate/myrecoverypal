# Relapse Prevention Plan Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A private, always-free guided relapse prevention plan per member (six sections + HALT + support contacts), with premium-gated PDF export, surfaced from the Craving SOS page, the Resources nav, and a public SEO landing page.

**Architecture:** New focused modules in `apps.accounts` following the court-tier pattern: `plan_models.py` (OneToOne model, re-exported through models.py), `plan_forms.py` (contacts-JSON validation), `plan_views.py` (builder + premium PDF view), `plan_service.py` (WeasyPrint render with lazy import). Entry points touch `craving_sos.html`/`CravingSOSView`, the nav partials, and a new core landing page.

**Tech Stack:** Django 5.0.10, WeasyPrint (already a dependency, used by the court tier), vanilla JS for contact rows. One migration.

**Spec:** `docs/superpowers/specs/2026-07-11-relapse-prevention-plan-design.md`

## Global Constraints

- The plan itself (create/edit/view) is FREE; only `/accounts/plan/pdf/` is behind `@premium_required` (existing decorator — redirects unauthenticated to login, non-premium to `accounts:pricing` with a warning message).
- Plan content is private like the journal: never rendered in feeds, activity, or any other member's view.
- URLs: `/accounts/plan/` name `accounts:relapse_plan`; `/accounts/plan/pdf/` name `accounts:relapse_plan_pdf`; landing page `/relapse-prevention-plan/` name `core:relapse_prevention_plan`.
- `support_contacts` rows: dicts with exactly `name`/`phone`/`relationship`, values stripped and capped at 100 chars, fully-empty rows dropped, max 10 rows.
- WeasyPrint is imported lazily inside the render function (module must import without it); the genuine render test is `@skipUnless(HAS_WEASYPRINT, ...)`; gating tests mock the render.
- Test gotcha: new users default to a premium TRIAL subscription (post-save signal) — free-user tests must set `user.subscription.tier = 'free'; user.subscription.save()` (see apps/accounts/test_coach_sos.py setUp for the precedent).
- Landing-page FAQ: visible copy must match the FAQPage JSON-LD text EXACTLY (rich-result parity — this bit us on /craving-sos/).
- View tests use `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`; tests run `python manage.py test <module> -v 2` from repo root.
- Surgical changes; commit per task with trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: RelapsePreventionPlan model

**Files:**
- Create: `apps/accounts/plan_models.py`
- Modify: `apps/accounts/models.py` (~line 2046, after the outreach_models re-export)
- Create: migration via `makemigrations accounts`
- Create: `apps/accounts/test_relapse_plan.py`

**Interfaces:**
- Produces (Tasks 2-5 rely on): `RelapsePreventionPlan` with `user` (OneToOne, related_name `relapse_plan`), six section TextFields (`triggers`, `warning_signs`, `coping_strategies`, `reasons`, `emergency_steps`, `halt_notes`), `support_contacts` JSONField (list), `created_at`/`updated_at`, class attr `SECTION_FIELDS` (tuple of the six field names), property `filled_section_count -> int` (0..7; six text sections counted when non-blank after strip, contacts counted when the list is non-empty). Importable as `from apps.accounts.models import RelapsePreventionPlan` (re-export) and directly from `plan_models`.

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_relapse_plan.py`:

```python
"""Tests for the relapse prevention plan: model, form, builder, PDF gate."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import RelapsePreventionPlan

User = get_user_model()


class PlanModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="p1", password="x")

    def test_empty_plan_counts_zero(self):
        plan = RelapsePreventionPlan.objects.create(user=self.user)
        self.assertEqual(plan.filled_section_count, 0)

    def test_partial_plan_counts_filled_sections(self):
        plan = RelapsePreventionPlan.objects.create(
            user=self.user,
            triggers="Payday fridays",
            reasons="My kids",
            halt_notes="   ",  # whitespace only — not counted
        )
        self.assertEqual(plan.filled_section_count, 2)

    def test_contacts_count_as_a_section(self):
        plan = RelapsePreventionPlan.objects.create(
            user=self.user,
            support_contacts=[{"name": "Sam", "phone": "555-0100",
                               "relationship": "sponsor"}],
        )
        self.assertEqual(plan.filled_section_count, 1)

    def test_one_plan_per_user(self):
        RelapsePreventionPlan.objects.create(user=self.user)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RelapsePreventionPlan.objects.create(user=self.user)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_relapse_plan -v 2`
Expected: ERROR with `ImportError: cannot import name 'RelapsePreventionPlan'`

- [ ] **Step 3: Create the model**

Create `apps/accounts/plan_models.py`:

```python
"""Relapse prevention plan — a private, guided safety worksheet.

One plan per member. Content is private like the journal: it must never be
rendered in feeds, activity streams, or any other member's view. The plan
itself is always free; only the PDF export is premium (plan_views.py).
"""
from django.conf import settings
from django.db import models


class RelapsePreventionPlan(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='relapse_plan',
    )

    triggers = models.TextField(
        blank=True, help_text="People, places, feelings that put you at risk")
    warning_signs = models.TextField(
        blank=True, help_text="Early signs you're drifting toward a slip")
    coping_strategies = models.TextField(
        blank=True, help_text="What actually works when a craving hits")
    reasons = models.TextField(
        blank=True, help_text="Your reasons for recovery")
    emergency_steps = models.TextField(
        blank=True, help_text="Exact steps if a slip happens or feels close")
    halt_notes = models.TextField(
        blank=True,
        help_text="HALT: how hunger, anger, loneliness, tiredness show up for you")

    # List of {"name": str, "phone": str, "relationship": str}
    support_contacts = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    SECTION_FIELDS = (
        'triggers', 'warning_signs', 'coping_strategies',
        'reasons', 'emergency_steps', 'halt_notes',
    )

    def __str__(self):
        return f"Relapse prevention plan — {self.user.username}"

    @property
    def filled_section_count(self):
        """0..7 — the six text sections plus the contacts list."""
        filled = sum(
            1 for f in self.SECTION_FIELDS if getattr(self, f).strip())
        if self.support_contacts:
            filled += 1
        return filled
```

In `apps/accounts/models.py`, after the outreach_models re-export (~line 2046), add:

```python
# Re-export the relapse prevention plan model so Django discovers it at app load
from apps.accounts.plan_models import RelapsePreventionPlan  # noqa: E402, F401
```

Run: `python manage.py makemigrations accounts`
Expected: one migration creating `RelapsePreventionPlan`.
Run: `python manage.py migrate accounts`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_relapse_plan -v 2`
Expected: OK, 4 tests passing

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/plan_models.py apps/accounts/models.py apps/accounts/migrations/ apps/accounts/test_relapse_plan.py
git commit -m "feat(plan): RelapsePreventionPlan model — private guided safety worksheet

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Form, builder view, template, URLs

**Files:**
- Create: `apps/accounts/plan_forms.py`
- Create: `apps/accounts/plan_views.py`
- Create: `apps/accounts/templates/accounts/relapse_prevention_plan.html`
- Modify: `apps/accounts/urls.py` (add two paths near the other feature URL groups; also import `plan_views` the same way `court_views` is imported there)
- Test: `apps/accounts/test_relapse_plan.py` (append)

**Interfaces:**
- Consumes: `RelapsePreventionPlan` (Task 1).
- Produces: URL `accounts:relapse_plan` at `/accounts/plan/`; `RelapsePreventionPlanForm` (ModelForm; `support_contacts` uses a HiddenInput carrying JSON — Django's JSONField form field decodes it; `clean_support_contacts` enforces the row rules); template context keys `form`, `plan`, `has_premium`. Task 3 adds its view to the same `plan_views.py`.

- [ ] **Step 1: Write the failing tests**

Append to `apps/accounts/test_relapse_plan.py`:

```python
import json

from django.test import override_settings
from django.urls import reverse

from apps.accounts.plan_forms import RelapsePreventionPlanForm


class PlanFormContactsTests(TestCase):
    def _form(self, contacts_json):
        return RelapsePreventionPlanForm(data={
            "triggers": "", "warning_signs": "", "coping_strategies": "",
            "reasons": "", "emergency_steps": "", "halt_notes": "",
            "support_contacts": contacts_json,
        })

    def test_valid_rows_kept_and_trimmed(self):
        form = self._form(json.dumps([
            {"name": "  Sam ", "phone": " 555-0100", "relationship": "sponsor"},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["support_contacts"], [
            {"name": "Sam", "phone": "555-0100", "relationship": "sponsor"},
        ])

    def test_empty_rows_dropped_and_unknown_keys_stripped(self):
        form = self._form(json.dumps([
            {"name": "", "phone": "", "relationship": ""},
            {"name": "Ana", "phone": "", "relationship": "", "evil": "x"},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["support_contacts"], [
            {"name": "Ana", "phone": "", "relationship": ""},
        ])

    def test_more_than_ten_rows_rejected(self):
        rows = [{"name": f"P{i}", "phone": "", "relationship": ""}
                for i in range(11)]
        form = self._form(json.dumps(rows))
        self.assertFalse(form.is_valid())
        self.assertIn("support_contacts", form.errors)

    def test_non_list_rejected(self):
        form = self._form(json.dumps({"name": "not-a-list"}))
        self.assertFalse(form.is_valid())

    def test_values_capped_at_100_chars(self):
        form = self._form(json.dumps([
            {"name": "x" * 300, "phone": "", "relationship": ""},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            len(form.cleaned_data["support_contacts"][0]["name"]), 100)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PlanBuilderViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="builder", password="x")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("accounts:relapse_plan"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])

    def test_get_creates_empty_plan_and_renders_sections(self):
        resp = self.client.get(reverse("accounts:relapse_plan"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            RelapsePreventionPlan.objects.filter(user=self.user).exists())
        for label in ("triggers", "warning_signs", "coping_strategies",
                      "reasons", "emergency_steps", "halt_notes"):
            self.assertContains(resp, f'name="{label}"')

    def test_post_saves_and_reload_shows_content(self):
        resp = self.client.post(reverse("accounts:relapse_plan"), {
            "triggers": "Payday fridays",
            "warning_signs": "Skipping meetings",
            "coping_strategies": "Call Sam; go for a run",
            "reasons": "My kids",
            "emergency_steps": "Call 988 or my sponsor",
            "halt_notes": "Tiredness hits hardest",
            "support_contacts": json.dumps([
                {"name": "Sam", "phone": "555-0100",
                 "relationship": "sponsor"},
            ]),
        })
        self.assertRedirects(resp, reverse("accounts:relapse_plan"),
                             fetch_redirect_response=False)
        plan = RelapsePreventionPlan.objects.get(user=self.user)
        self.assertEqual(plan.filled_section_count, 7)
        follow = self.client.get(reverse("accounts:relapse_plan"))
        self.assertContains(follow, "Payday fridays")
        self.assertContains(follow, "7 of 7")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_relapse_plan -v 2`
Expected: new tests ERROR (`ModuleNotFoundError: plan_forms` / `NoReverseMatch: relapse_plan`); Task 1's 4 still pass.

- [ ] **Step 3: Create the form**

Create `apps/accounts/plan_forms.py`:

```python
"""Form for the relapse prevention plan builder."""
from django import forms

from apps.accounts.plan_models import RelapsePreventionPlan

MAX_CONTACTS = 10
MAX_VALUE_LEN = 100
CONTACT_KEYS = ('name', 'phone', 'relationship')

SECTION_PLACEHOLDERS = {
    'triggers': "e.g. payday Fridays, my brother's house, feeling left out, boredom after 9pm…",
    'warning_signs': "e.g. skipping meetings, 'just one won't hurt' thoughts, isolating, poor sleep…",
    'coping_strategies': "e.g. call Sam, 4-7-8 breathing, leave the situation, hit the Craving SOS page…",
    'reasons': "e.g. my kids, my health, the person I'm becoming, mornings without shame…",
    'emergency_steps': "e.g. 1) leave, 2) call sponsor, 3) open Craving SOS, 4) if unsafe call 988…",
    'halt_notes': "e.g. anger sneaks up at work; loneliness on Sunday nights; keep snacks in the car…",
}


class RelapsePreventionPlanForm(forms.ModelForm):
    class Meta:
        model = RelapsePreventionPlan
        fields = [
            'triggers', 'warning_signs', 'coping_strategies',
            'reasons', 'emergency_steps', 'halt_notes',
            'support_contacts',
        ]
        widgets = {
            **{
                f: forms.Textarea(attrs={
                    'rows': 4,
                    'class': 'form-control',
                    'placeholder': SECTION_PLACEHOLDERS[f],
                })
                for f in RelapsePreventionPlan.SECTION_FIELDS
            },
            # JS-managed rows serialize into this hidden JSON field;
            # Django's JSONField form field decodes the string for us.
            'support_contacts': forms.HiddenInput(),
        }

    def clean_support_contacts(self):
        value = self.cleaned_data.get('support_contacts') or []
        if not isinstance(value, list):
            raise forms.ValidationError("Contacts must be a list.")
        cleaned = []
        for row in value:
            if not isinstance(row, dict):
                raise forms.ValidationError("Each contact must be an object.")
            contact = {
                key: str(row.get(key, '')).strip()[:MAX_VALUE_LEN]
                for key in CONTACT_KEYS
            }
            if any(contact.values()):
                cleaned.append(contact)
        if len(cleaned) > MAX_CONTACTS:
            raise forms.ValidationError(
                f"Please keep it to {MAX_CONTACTS} contacts or fewer.")
        return cleaned
```

- [ ] **Step 4: Create the view**

Create `apps/accounts/plan_views.py`:

```python
"""Views for the relapse prevention plan.

The plan itself is always free (never paywall a safety tool); only the PDF
export below is premium. Plan content is private — these views only ever
render the requesting user's own plan.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import premium_required
from apps.accounts.plan_forms import RelapsePreventionPlanForm
from apps.accounts.plan_models import RelapsePreventionPlan


@login_required
def relapse_plan_view(request):
    plan, _ = RelapsePreventionPlan.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = RelapsePreventionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(
                request, 'Your relapse prevention plan has been saved.')
            return redirect('accounts:relapse_plan')
    else:
        form = RelapsePreventionPlanForm(instance=plan)

    sub = getattr(request.user, 'subscription', None)
    has_premium = bool(sub and sub.is_premium())
    return render(request, 'accounts/relapse_prevention_plan.html', {
        'form': form,
        'plan': plan,
        'has_premium': has_premium,
    })
```

(Task 3 appends the PDF view to this file.)

- [ ] **Step 5: Create the template**

Create `apps/accounts/templates/accounts/relapse_prevention_plan.html`:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}My Relapse Prevention Plan - MyRecoveryPal{% endblock %}

{% block extra_css %}
<style>
    .rpp-wrap { max-width: 860px; margin: 1.5rem auto 3rem; padding: 0 1rem; }
    .rpp-wrap h1 { font-size: 1.7rem; margin-bottom: 0.3rem; }
    .rpp-sub { opacity: 0.8; margin-bottom: 0.4rem; }
    .rpp-progress {
        display: inline-block; font-weight: 700; font-size: 0.85rem;
        background: rgba(82,183,136,0.15); color: #2f7d56;
        border-radius: 999px; padding: 0.3rem 0.9rem; margin-bottom: 1.2rem;
    }
    .rpp-card {
        border: 1px solid rgba(128,128,128,0.25); border-radius: 14px;
        padding: 1.2rem 1.3rem; margin-bottom: 1.1rem;
    }
    .rpp-card h2 { font-size: 1.12rem; margin-bottom: 0.25rem; }
    .rpp-why { opacity: 0.75; font-size: 0.9rem; margin-bottom: 0.7rem; }
    .rpp-card textarea { width: 100%; }
    .rpp-contact-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
    .rpp-contact-row input { flex: 1 1 140px; }
    .rpp-remove { background: none; border: none; color: #b02a37; cursor: pointer; font-size: 1rem; }
    .rpp-actions { display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; margin-top: 1.2rem; }
    .rpp-save {
        background: var(--primary-color, #2c7a7b); color: #fff; border: none;
        font-weight: 700; font-size: 1rem; padding: 0.75rem 1.8rem;
        border-radius: 8px; cursor: pointer;
    }
    .rpp-pdf, .rpp-pdf-locked {
        display: inline-flex; align-items: center; gap: 0.45rem;
        font-weight: 600; text-decoration: none;
        border-radius: 8px; padding: 0.7rem 1.3rem;
    }
    .rpp-pdf { background: #1e4d8b; color: #fff; }
    .rpp-pdf-locked { background: rgba(128,128,128,0.15); color: inherit; }
    .rpp-add-contact { background: none; border: 1px dashed rgba(128,128,128,0.5);
        border-radius: 8px; padding: 0.45rem 1rem; cursor: pointer; font-weight: 600; }
</style>
{% endblock %}

{% block content %}
<div class="rpp-wrap">
    <h1><i class="fas fa-clipboard-list" aria-hidden="true"></i> My Relapse Prevention Plan</h1>
    <p class="rpp-sub">A plan written on a calm day is what future-you reaches for on a hard one.
        Private, like your journal — only you can see it.</p>
    <span class="rpp-progress">{{ plan.filled_section_count }} of 7 sections filled</span>

    {% if messages %}{% for message in messages %}
    <div class="alert alert-{{ message.tags }}" style="margin-bottom: 1rem;">{{ message }}</div>
    {% endfor %}{% endif %}

    <form method="post" id="rpp-form">
        {% csrf_token %}

        <div class="rpp-card">
            <h2>1. My triggers</h2>
            <p class="rpp-why">Knowing the people, places, and feelings that put you at risk turns ambushes into forecasts.</p>
            {{ form.triggers }}
        </div>

        <div class="rpp-card">
            <h2>2. My early warning signs</h2>
            <p class="rpp-why">Relapse starts before the first drink or use — name the drift so you can catch it early.</p>
            {{ form.warning_signs }}
        </div>

        <div class="rpp-card">
            <h2>3. Coping strategies that work for me</h2>
            <p class="rpp-why">In the moment, you won't invent a strategy — you'll reach for one you wrote down.</p>
            {{ form.coping_strategies }}
        </div>

        <div class="rpp-card">
            <h2>4. My support contacts</h2>
            <p class="rpp-why">Two minutes on the phone beats two hours in your head. Add the people you can actually call.</p>
            <div id="rpp-contacts"></div>
            <button type="button" class="rpp-add-contact" id="rpp-add-contact">
                <i class="fas fa-plus" aria-hidden="true"></i> Add a contact</button>
            {{ form.support_contacts }}
        </div>

        <div class="rpp-card">
            <h2>5. My reasons for recovery</h2>
            <p class="rpp-why">On the hardest days, the "why" carries you when willpower can't.</p>
            {{ form.reasons }}
        </div>

        <div class="rpp-card">
            <h2>6. HALT self-check</h2>
            <p class="rpp-why">Hungry, Angry, Lonely, Tired — how does each one show up for you, and what heads it off?</p>
            {{ form.halt_notes }}
        </div>

        <div class="rpp-card">
            <h2>7. If a slip happens — my emergency steps</h2>
            <p class="rpp-why">A slip is an event, not an identity. Decide now what the next hour looks like.</p>
            {{ form.emergency_steps }}
        </div>

        <div class="rpp-actions">
            <button type="submit" class="rpp-save">Save my plan</button>
            {% if has_premium %}
            <a class="rpp-pdf" href="{% url 'accounts:relapse_plan_pdf' %}">
                <i class="fas fa-file-pdf" aria-hidden="true"></i> Export PDF</a>
            {% else %}
            <a class="rpp-pdf-locked" href="{% url 'accounts:pricing' %}"
                title="PDF export is a Premium feature">
                <i class="fas fa-lock" aria-hidden="true"></i> Export PDF (Premium)</a>
            {% endif %}
        </div>
    </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
(function () {
    var hidden = document.querySelector('input[name="support_contacts"]');
    var wrap = document.getElementById('rpp-contacts');
    var addBtn = document.getElementById('rpp-add-contact');
    var form = document.getElementById('rpp-form');

    function row(contact) {
        var div = document.createElement('div');
        div.className = 'rpp-contact-row';
        div.innerHTML =
            '<input type="text" maxlength="100" placeholder="Name" value="' + esc(contact.name) + '" data-k="name">' +
            '<input type="tel" maxlength="100" placeholder="Phone" value="' + esc(contact.phone) + '" data-k="phone">' +
            '<input type="text" maxlength="100" placeholder="Relationship (sponsor, friend…)" value="' + esc(contact.relationship) + '" data-k="relationship">' +
            '<button type="button" class="rpp-remove" title="Remove" aria-label="Remove contact">&times;</button>';
        div.querySelector('.rpp-remove').addEventListener('click', function () { div.remove(); });
        wrap.appendChild(div);
    }
    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    }
    function serialize() {
        var rows = [];
        wrap.querySelectorAll('.rpp-contact-row').forEach(function (r) {
            var c = {};
            r.querySelectorAll('input').forEach(function (i) { c[i.dataset.k] = i.value; });
            rows.push(c);
        });
        hidden.value = JSON.stringify(rows);
    }

    var initial = [];
    try { initial = JSON.parse(hidden.value || '[]'); } catch (e) { initial = []; }
    if (!Array.isArray(initial)) initial = [];
    initial.forEach(row);
    if (!initial.length) row({});

    addBtn.addEventListener('click', function () { row({}); });
    form.addEventListener('submit', serialize);
})();
</script>
{% endblock %}
```

- [ ] **Step 6: Add the URLs**

In `apps/accounts/urls.py`: import `plan_views` next to the existing `court_views`-style import at the top (check how `court_views` is imported there and mirror it), then add near the other feature URL groups:

```python
    # Relapse prevention plan
    path('plan/', plan_views.relapse_plan_view, name='relapse_plan'),
    path('plan/pdf/', plan_views.relapse_plan_pdf_view, name='relapse_plan_pdf'),
```

NOTE: `relapse_plan_pdf_view` doesn't exist until Task 3 — for THIS task add only the first path plus the import, and add the pdf path in Task 3. (The Step 1 tests only reverse `accounts:relapse_plan`.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_relapse_plan -v 2`
Expected: OK, 12 tests passing (4 + 8)

- [ ] **Step 8: Commit**

```bash
git add apps/accounts/plan_forms.py apps/accounts/plan_views.py apps/accounts/templates/accounts/relapse_prevention_plan.html apps/accounts/urls.py apps/accounts/test_relapse_plan.py
git commit -m "feat(plan): guided relapse prevention plan builder at /accounts/plan/

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: PDF export (premium)

**Files:**
- Create: `apps/accounts/plan_service.py`
- Modify: `apps/accounts/plan_views.py` (append the PDF view)
- Modify: `apps/accounts/urls.py` (add the `plan/pdf/` path from Task 2's note)
- Create: `apps/accounts/templates/accounts/relapse_plan_pdf.html`
- Test: `apps/accounts/test_relapse_plan.py` (append)

**Interfaces:**
- Consumes: `RelapsePreventionPlan`, `premium_required` (redirects non-premium to `accounts:pricing`).
- Produces: `render_plan_pdf(user) -> bytes` in `plan_service.py` (lazy WeasyPrint import); URL `accounts:relapse_plan_pdf` returning an `application/pdf` attachment named `relapse-prevention-plan.pdf`.

- [ ] **Step 1: Write the failing tests**

Append to `apps/accounts/test_relapse_plan.py`:

```python
from unittest import skipUnless
from unittest.mock import patch

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except Exception:
    HAS_WEASYPRINT = False


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PlanPdfGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pdfu", password="x")
        self.client.force_login(self.user)

    def test_free_user_redirected_to_pricing(self):
        self.user.subscription.tier = 'free'
        self.user.subscription.save()
        resp = self.client.get(reverse("accounts:relapse_plan_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:pricing"), resp["Location"])

    def test_premium_user_gets_pdf_response(self):
        # New users default to a premium trial (signal), which is_premium().
        with patch("apps.accounts.plan_views.render_plan_pdf",
                   return_value=b"%PDF-fake") as mock_render:
            resp = self.client.get(reverse("accounts:relapse_plan_pdf"))
        mock_render.assert_called_once_with(self.user)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("relapse-prevention-plan.pdf",
                      resp["Content-Disposition"])

    @skipUnless(HAS_WEASYPRINT, "WeasyPrint not available in this env")
    def test_real_render_produces_pdf_bytes(self):
        from apps.accounts.plan_service import render_plan_pdf
        RelapsePreventionPlan.objects.create(
            user=self.user, triggers="Payday fridays",
            support_contacts=[{"name": "Sam", "phone": "555-0100",
                               "relationship": "sponsor"}])
        pdf = render_plan_pdf(self.user)
        self.assertTrue(pdf.startswith(b"%PDF"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_relapse_plan.PlanPdfGateTests -v 2`
Expected: ERROR with `NoReverseMatch: relapse_plan_pdf`

- [ ] **Step 3: Create the service**

Create `apps/accounts/plan_service.py`:

```python
"""PDF rendering for the relapse prevention plan (premium export).

WeasyPrint is imported lazily so this module (and everything importing it)
loads fine in environments without the native Pango libraries — same
pattern as court_service.py.
"""
from io import BytesIO

from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.plan_models import RelapsePreventionPlan


def render_plan_pdf(user) -> bytes:
    from weasyprint import HTML

    plan, _ = RelapsePreventionPlan.objects.get_or_create(user=user)
    html_str = render_to_string('accounts/relapse_plan_pdf.html', {
        'plan_user': user,
        'plan': plan,
        'generated': timezone.now(),
    })
    buf = BytesIO()
    HTML(string=html_str).write_pdf(target=buf)
    return buf.getvalue()
```

- [ ] **Step 4: Append the view and URL**

Append to `apps/accounts/plan_views.py`:

```python
@login_required
@premium_required
def relapse_plan_pdf_view(request):
    """Premium: download the plan as a print-ready PDF."""
    from apps.accounts.plan_service import render_plan_pdf

    pdf_bytes = render_plan_pdf(request.user)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = (
        'attachment; filename="relapse-prevention-plan.pdf"')
    return response
```

(The test patches `apps.accounts.plan_views.render_plan_pdf`, so ALSO add a module-level import at the top of plan_views.py — `from apps.accounts.plan_service import render_plan_pdf` — and call it directly instead of the function-local import. Function-local would break the patch target; module-level is required here.)

In `apps/accounts/urls.py`, add the second path from Task 2's note:

```python
    path('plan/pdf/', plan_views.relapse_plan_pdf_view, name='relapse_plan_pdf'),
```

- [ ] **Step 5: Create the PDF template**

Create `apps/accounts/templates/accounts/relapse_plan_pdf.html`:

```django
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page { size: letter; margin: 2cm 1.8cm; }
    body { font-family: Helvetica, Arial, sans-serif; color: #1a2733; font-size: 11pt; }
    h1 { font-size: 19pt; color: #1e4d8b; margin-bottom: 2pt; }
    .meta { color: #667; font-size: 9pt; margin-bottom: 14pt; }
    h2 { font-size: 12.5pt; color: #1e4d8b; border-bottom: 1.5pt solid #cfe0f5;
         padding-bottom: 3pt; margin: 14pt 0 6pt; }
    .body-text { white-space: pre-wrap; line-height: 1.45; }
    .empty { color: #99a; font-style: italic; }
    table { width: 100%; border-collapse: collapse; margin-top: 4pt; }
    th, td { text-align: left; padding: 4pt 6pt; border-bottom: 0.75pt solid #dde5ee; font-size: 10.5pt; }
    th { color: #556; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.06em; }
    .footer { margin-top: 20pt; padding-top: 8pt; border-top: 1.5pt solid #cfe0f5;
              font-size: 9.5pt; color: #556; }
    .footer strong { color: #b02a37; }
</style>
</head>
<body>
    <h1>Relapse Prevention Plan</h1>
    <div class="meta">{{ plan_user.get_full_name|default:plan_user.username }}
        &middot; generated {{ generated|date:"F j, Y" }} &middot; myrecoverypal.com</div>

    <h2>1. My triggers</h2>
    <div class="body-text">{% if plan.triggers %}{{ plan.triggers }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <h2>2. My early warning signs</h2>
    <div class="body-text">{% if plan.warning_signs %}{{ plan.warning_signs }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <h2>3. Coping strategies that work for me</h2>
    <div class="body-text">{% if plan.coping_strategies %}{{ plan.coping_strategies }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <h2>4. My support contacts</h2>
    {% if plan.support_contacts %}
    <table>
        <tr><th>Name</th><th>Phone</th><th>Relationship</th></tr>
        {% for c in plan.support_contacts %}
        <tr><td>{{ c.name }}</td><td>{{ c.phone }}</td><td>{{ c.relationship }}</td></tr>
        {% endfor %}
    </table>
    {% else %}<span class="empty">Not filled in yet</span>{% endif %}

    <h2>5. My reasons for recovery</h2>
    <div class="body-text">{% if plan.reasons %}{{ plan.reasons }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <h2>6. HALT self-check</h2>
    <div class="body-text">{% if plan.halt_notes %}{{ plan.halt_notes }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <h2>7. If a slip happens &mdash; my emergency steps</h2>
    <div class="body-text">{% if plan.emergency_steps %}{{ plan.emergency_steps }}{% else %}<span class="empty">Not filled in yet</span>{% endif %}</div>

    <div class="footer">
        In crisis or thinking about harming yourself? Call or text <strong>988</strong>
        (Suicide &amp; Crisis Lifeline) or 911. &middot; More tools:
        myrecoverypal.com/craving-sos
    </div>
</body>
</html>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_relapse_plan -v 2`
Expected: OK, 15 tests (14 + 1 skipped locally if WeasyPrint env is broken — the skip prints as `s`, which is acceptable; on an env with working Pango, 15 pass).

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/plan_service.py apps/accounts/plan_views.py apps/accounts/urls.py apps/accounts/templates/accounts/relapse_plan_pdf.html apps/accounts/test_relapse_plan.py
git commit -m "feat(plan): premium PDF export of the relapse prevention plan

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Entry points — Craving SOS page + nav

**Files:**
- Modify: `apps/core/views.py` (`CravingSOSView.get_context_data`)
- Modify: `apps/core/templates/core/craving_sos.html` (members' action slot)
- Modify: `templates/partials/_resources_nav_dropdown.html` (add entry)
- Modify: `templates/base.html` (mobile menu Resources section, ~line 470-490)
- Create: `apps/core/test_sos_plan_entry.py`

**Interfaces:**
- Consumes: `accounts:relapse_plan` (Task 2); `RelapsePreventionPlan.filled_section_count` (Task 1).
- Produces: `has_plan` context flag on the SOS page (authenticated only).

- [ ] **Step 1: Write the failing tests**

Create `apps/core/test_sos_plan_entry.py`:

```python
"""Tests for the relapse-plan entry points on the Craving SOS page."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import RelapsePreventionPlan

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SosPlanEntryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sosplan", password="x")

    def test_member_with_plan_sees_my_plan_pill(self):
        RelapsePreventionPlan.objects.create(
            user=self.user, triggers="Payday fridays")
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "My relapse plan")
        self.assertContains(resp, reverse("accounts:relapse_plan"))

    def test_member_without_plan_sees_build_nudge(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Build your relapse prevention plan")
        self.assertNotContains(resp, "My relapse plan")

    def test_empty_plan_row_counts_as_no_plan(self):
        RelapsePreventionPlan.objects.create(user=self.user)  # all blank
        self.client.force_login(self.user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Build your relapse prevention plan")

    def test_anonymous_sees_neither(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertNotContains(resp, "My relapse plan")
        self.assertNotContains(resp, "Build your relapse prevention plan")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.core.test_sos_plan_entry -v 2`
Expected: the first three FAIL (strings absent); the anonymous test passes trivially.

- [ ] **Step 3: Add the context flag**

In `apps/core/views.py`, inside `CravingSOSView.get_context_data` (after the existing `soon_meetings` line), add:

```python
        if self.request.user.is_authenticated:
            from apps.accounts.plan_models import RelapsePreventionPlan
            plan = RelapsePreventionPlan.objects.filter(
                user=self.request.user).first()
            context['has_plan'] = bool(plan and plan.filled_section_count)
        return context
```

(Merge with the existing `return context` — one return, flag added above it.)

- [ ] **Step 4: Add the pills to the SOS template**

In `apps/core/templates/core/craving_sos.html`, inside the authenticated branch of the Anchor tool card (directly after the closing `</form>` of the "Talk to Anchor now" form, before the explanatory `<p>`), add:

```django
        {% if has_plan %}
        <a class="sos-btn secondary" href="{% url 'accounts:relapse_plan' %}"
            style="margin-left: 0.6rem;">
            <i class="fas fa-clipboard-list" aria-hidden="true"></i> My relapse plan</a>
        {% endif %}
```

And after the explanatory `<p>` (still inside the authenticated branch), add:

```django
        {% if not has_plan %}
        <p style="margin-top: 0.6rem; font-size: 0.95rem;">
            <a href="{% url 'accounts:relapse_plan' %}">Build your relapse prevention plan</a>
            &mdash; ten calm minutes now is what future-you reaches for at 2 AM.</p>
        {% endif %}
```

(Read the current card first; keep the form + button layout intact — the pill sits beside the Anchor button, the nudge below the caption.)

- [ ] **Step 5: Add the nav entries**

In `templates/partials/_resources_nav_dropdown.html`, after the Meeting Finder `<li>`, add:

```django
        <li><a href="{% url 'accounts:relapse_plan' %}"><i class="fas fa-clipboard-list" aria-hidden="true"></i> Relapse Prevention Plan</a></li>
```

In `templates/base.html`, in the mobile menu's Resources section (the block containing the Meeting Finder link, ~line 480), add after the Meeting Finder `<a>`:

```django
                <a href="{% url 'accounts:relapse_plan' %}">
                    <i class="fas fa-clipboard-list" style="margin-right: 0.5rem;"></i> Relapse Prevention Plan
                </a>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.core.test_sos_plan_entry apps.core.test_craving_sos -v 2`
Expected: OK, 9 tests (4 new + 5 existing SOS tests still green)

- [ ] **Step 7: Commit**

```bash
git add apps/core/views.py apps/core/templates/core/craving_sos.html templates/partials/_resources_nav_dropdown.html templates/base.html apps/core/test_sos_plan_entry.py
git commit -m "feat(plan): surface the relapse plan from Craving SOS and the nav

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: SEO landing page /relapse-prevention-plan/

**Files:**
- Modify: `apps/core/views.py` (add view after `CravingSOSView`)
- Modify: `apps/core/urls.py` (after the `craving-sos/` line)
- Create: `apps/core/templates/core/relapse_prevention_plan.html`
- Modify: `recovery_hub/sitemaps.py` (SEO landing pages block)
- Modify: `apps/core/templates/core/partials/_related_tools.html` (add card)
- Create: `apps/core/test_relapse_plan_landing.py`

**Interfaces:**
- Consumes: `accounts:register`, `accounts:relapse_plan`, the related-tools partial's exclude-key pattern.
- Produces: URL name `core:relapse_prevention_plan` at `/relapse-prevention-plan/`.

- [ ] **Step 1: Write the failing tests**

Create `apps/core/test_relapse_plan_landing.py`:

```python
"""Tests for the /relapse-prevention-plan/ SEO landing page."""
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RelapsePlanLandingTests(TestCase):
    def test_renders_with_template_preview_and_schema(self):
        resp = self.client.get(reverse("core:relapse_prevention_plan"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '"@type": "FAQPage"')
        # The six template sections are previewed on the page
        for section in ("My triggers", "early warning signs",
                        "Coping strategies", "support contacts",
                        "reasons for recovery", "emergency steps"):
            self.assertContains(resp, section)
        self.assertContains(resp, "988")

    def test_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/relapse-prevention-plan/")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.core.test_relapse_plan_landing -v 2`
Expected: ERROR with `NoReverseMatch: relapse_prevention_plan`

- [ ] **Step 3: Add the view and URL**

In `apps/core/views.py`, after `CravingSOSView`:

```python
class RelapsePreventionPlanLandingView(TemplateView):
    """SEO landing page targeting "relapse prevention plan" queries.

    Static content (worksheet preview + FAQ); the interactive builder
    lives behind login at accounts:relapse_plan."""
    template_name = 'core/relapse_prevention_plan.html'
```

In `apps/core/urls.py`, after the `craving-sos/` line:

```python
    path('relapse-prevention-plan/', views.RelapsePreventionPlanLandingView.as_view(), name='relapse_prevention_plan'),
```

- [ ] **Step 4: Create the template**

Create `apps/core/templates/core/relapse_prevention_plan.html`. FAQ RULE: the five visible FAQ answers below are the SOURCE OF TRUTH — the JSON-LD `acceptedAnswer.text` values must be copied from them character-for-character (entities rendered: `&mdash;` in HTML = "—" in JSON-LD).

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Relapse Prevention Plan: Free Template & Guided Builder{% endblock %}
{% block meta_description %}Build a relapse prevention plan in 10 minutes: triggers, warning signs, coping strategies, support contacts & emergency steps. Free guided template, printable PDF.{% endblock %}
{% block meta_keywords %}relapse prevention plan, relapse prevention plan template, relapse prevention worksheet, how to make a relapse prevention plan, recovery plan template{% endblock %}

{% block canonical_url %}https://www.myrecoverypal.com/relapse-prevention-plan/{% endblock %}

{% block structured_data %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is a relapse prevention plan?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "A relapse prevention plan is a written document that maps your personal triggers, early warning signs, coping strategies, support contacts, and exact steps to take if a slip happens or feels close. Therapists and counselors assign it because relapse usually starts days or weeks before the first drink or use — a plan catches the drift early."
      }
    },
    {
      "@type": "Question",
      "name": "What should a relapse prevention plan include?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "The standard structure has six parts: your triggers (people, places, feelings), early warning signs, coping strategies that work for you, support contacts with phone numbers, your reasons for recovery, and emergency steps for a slip. Many plans add a HALT self-check — how hunger, anger, loneliness, and tiredness show up for you."
      }
    },
    {
      "@type": "Question",
      "name": "Do relapse prevention plans actually work?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Relapse prevention planning comes from cognitive-behavioral relapse prevention therapy, one of the most-studied approaches in addiction treatment. The core insight holds up: people who can name their triggers and have a decided response ready are far better at interrupting a lapse before it becomes a relapse. A plan works because you write it on a calm day and read it on a hard one."
      }
    },
    {
      "@type": "Question",
      "name": "How often should I update my plan?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Review it after anything it didn't predict: a close call, a new trigger, a changed relationship, a slip. Many people also revisit it at recovery milestones. A plan that never changes is a plan that has stopped describing your life."
      }
    },
    {
      "@type": "Question",
      "name": "Is a relapse prevention plan a substitute for treatment?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "No. It's a tool that supports treatment, meetings, therapy, and community — not a replacement for professional care. If you are in crisis or thinking about harming yourself, call or text 988 (Suicide and Crisis Lifeline) or 911 right away."
      }
    }
  ]
}
</script>
{% endblock %}

{% block extra_css %}
<style>
    .rpl-hero { text-align: center; padding: 3rem 1rem 1.5rem; max-width: 800px; margin: 0 auto; }
    .rpl-hero h1 { font-size: 2.1rem; margin-bottom: 1rem; }
    .rpl-section { max-width: 800px; margin: 0 auto; padding: 1.2rem 1rem; }
    .rpl-cta {
        display: inline-block; background: var(--primary-color, #2c7a7b); color: #fff;
        padding: 0.8rem 1.8rem; border-radius: 8px; font-weight: 600;
        text-decoration: none; margin-top: 1rem;
    }
    .rpl-card {
        border: 1px solid rgba(128,128,128,0.25); border-radius: 12px;
        padding: 1rem 1.2rem; margin-bottom: 0.9rem;
    }
    .rpl-card h3 { font-size: 1.05rem; margin-bottom: 0.3rem; }
    .rpl-card p { opacity: 0.85; font-size: 0.95rem; margin: 0; }
    .rpl-faq h3 { margin-top: 1.3rem; font-size: 1.05rem; }
</style>
{% endblock %}

{% block content %}
<div class="rpl-hero">
    <h1>Build Your Relapse Prevention Plan</h1>
    <p>Ten calm minutes now is what future-you reaches for on a hard day.
        Free guided builder, private like a journal, printable as a PDF.</p>
    <a class="rpl-cta" href="{% url 'accounts:relapse_plan' %}">Start your plan free</a>
</div>

<div class="rpl-section">
    <h2>What goes in the plan — the template</h2>
    <div class="rpl-card"><h3>1. My triggers</h3>
        <p>People, places, and feelings that put you at risk. Knowing them turns ambushes into forecasts.</p></div>
    <div class="rpl-card"><h3>2. My early warning signs</h3>
        <p>Relapse starts before the first drink or use &mdash; skipped meetings, "just one" thoughts, isolating.</p></div>
    <div class="rpl-card"><h3>3. Coping strategies that work for me</h3>
        <p>In the moment you won't invent a strategy. You'll reach for one you wrote down.</p></div>
    <div class="rpl-card"><h3>4. My support contacts</h3>
        <p>Names and numbers of people you can actually call. Two minutes on the phone beats two hours in your head.</p></div>
    <div class="rpl-card"><h3>5. My reasons for recovery</h3>
        <p>On the hardest days, the "why" carries you when willpower can't.</p></div>
    <div class="rpl-card"><h3>6. HALT self-check + emergency steps</h3>
        <p>How hunger, anger, loneliness, and tiredness show up for you &mdash; and the exact steps if a slip happens.</p></div>
    <a class="rpl-cta" href="{% url 'accounts:register' %}">Create a free account to save yours</a>
</div>

<div class="rpl-section rpl-faq">
    <h2>Relapse prevention plan FAQ</h2>
    <h3>What is a relapse prevention plan?</h3>
    <p>A relapse prevention plan is a written document that maps your personal triggers, early warning signs, coping strategies, support contacts, and exact steps to take if a slip happens or feels close. Therapists and counselors assign it because relapse usually starts days or weeks before the first drink or use &mdash; a plan catches the drift early.</p>
    <h3>What should a relapse prevention plan include?</h3>
    <p>The standard structure has six parts: your triggers (people, places, feelings), early warning signs, coping strategies that work for you, support contacts with phone numbers, your reasons for recovery, and emergency steps for a slip. Many plans add a HALT self-check &mdash; how hunger, anger, loneliness, and tiredness show up for you.</p>
    <h3>Do relapse prevention plans actually work?</h3>
    <p>Relapse prevention planning comes from cognitive-behavioral relapse prevention therapy, one of the most-studied approaches in addiction treatment. The core insight holds up: people who can name their triggers and have a decided response ready are far better at interrupting a lapse before it becomes a relapse. A plan works because you write it on a calm day and read it on a hard one.</p>
    <h3>How often should I update my plan?</h3>
    <p>Review it after anything it didn't predict: a close call, a new trigger, a changed relationship, a slip. Many people also revisit it at recovery milestones. A plan that never changes is a plan that has stopped describing your life.</p>
    <h3>Is a relapse prevention plan a substitute for treatment?</h3>
    <p>No. It's a tool that supports treatment, meetings, therapy, and community &mdash; not a replacement for professional care. If you are in crisis or thinking about harming yourself, call or text 988 (Suicide and Crisis Lifeline) or 911 right away.</p>
</div>

{% include 'core/partials/_related_tools.html' with exclude='relapse_prevention_plan' %}
{% endblock %}
```

- [ ] **Step 5: Sitemap + related-tools card**

In `recovery_hub/sitemaps.py`, after the `core:craving_sos` line, add:

```python
            ('core:relapse_prevention_plan', 0.9),  # "relapse prevention plan template" — guided builder landing
```

In `apps/core/templates/core/partials/_related_tools.html`, after the `craving_sos` card's `{% endif %}`, add (matching the sibling markup exactly):

```django
            {% if exclude != 'relapse_prevention_plan' %}
            <a href="{% url 'core:relapse_prevention_plan' %}" style="background: white; padding: 1.5rem; border-radius: 12px; text-decoration: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;"><i class="fas fa-clipboard-list" aria-hidden="true"></i></div>
                <h3 style="color: var(--primary-dark); font-size: 1.1rem; margin-bottom: 0.5rem;">Relapse Prevention Plan</h3>
                <p style="color: #666; font-size: 0.9rem; margin: 0;">Free guided template: triggers, warning signs, coping strategies, and emergency steps.</p>
            </a>
            {% endif %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.core.test_relapse_plan_landing -v 2`
Expected: OK, 2 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/core/views.py apps/core/urls.py apps/core/templates/core/relapse_prevention_plan.html recovery_hub/sitemaps.py apps/core/templates/core/partials/_related_tools.html apps/core/test_relapse_plan_landing.py
git commit -m "feat(seo): /relapse-prevention-plan/ landing page with template preview

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Verify, changelog, final review, merge, deploy

**Files:**
- Modify: `docs/CHANGELOG.md` (new dated entry at the top)

- [ ] **Step 1: Full test sweep**

Run: `python manage.py test apps.accounts.test_relapse_plan apps.core.test_sos_plan_entry apps.core.test_relapse_plan_landing apps.core.test_craving_sos -v 1`
Expected: OK, 26 tests (15 incl. possible 1 skip + 4 + 2 + 5)

- [ ] **Step 2: End-to-end verification**

Per `.claude/skills/verify/SKILL.md`: run the dev server, log in as a scratch user, build a plan (fill sections, add/remove contacts), save, reload (content + "7 of 7" persist), check the free lock state on Export, flip the scratch user premium and download the PDF (with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` for local WeasyPrint), check the SOS page pill states, and the landing page.

- [ ] **Step 3: Changelog entry**

Add at the top of the list in `docs/CHANGELOG.md`:

```markdown
- **2026-07-11:** Relapse prevention plan builder. New private guided plan per member at `/accounts/plan/` — six sections (triggers, warning signs, coping strategies, reasons, emergency steps, HALT) plus structured support contacts (add/remove rows, JSON-validated), "X of 7 sections" progress hint, always free. Premium PDF export at `/accounts/plan/pdf/` (`@premium_required`, WeasyPrint via new `plan_service.py` following the court pattern; lazy import; 988 footer). New files follow the court-tier layout: `plan_models.py` (re-exported, migration), `plan_forms.py`, `plan_views.py`. Entry points: Craving SOS page ("My relapse plan" pill when filled, build-nudge otherwise), Resources nav dropdown + mobile menu, and a public SEO landing page `/relapse-prevention-plan/` (template preview, FAQPage schema with visible-copy parity, sitemap 0.9, related-tools cross-links). ~21 new tests.
```

- [ ] **Step 4: Commit, merge, deploy**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for relapse prevention plan builder

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then superpowers:finishing-a-development-branch (merge to main deploys via Railway; migration runs via start.sh). Post-deploy: build/save a plan live, confirm free lock vs premium download, SOS pill, landing page render + sitemap; submit `/relapse-prevention-plan/` in Search Console (manual, Ryan).

---

## Self-Review Notes

- Spec coverage: §1 model → T1; §2 builder (form validation rules, placeholders, progress hint, contacts JS) → T2; §3 PDF (lazy import, premium gate, lock state, 988 footer) → T3; §4 SOS + nav entry points → T4; §5 landing page (preview, FAQ parity, sitemap, related tools) → T5; §6 testing map → T1-T5 tests; verification → T6.
- Type consistency: `RelapsePreventionPlan.filled_section_count` (T1) used in T2 template ("7 of 7"), T4 context flag; `accounts:relapse_plan`/`accounts:relapse_plan_pdf` names consistent across T2/T3/T4/T5; `render_plan_pdf(user)` module-level import in plan_views (T3 explicitly requires it for the patch target); `has_premium` context key matches template conditional.
- Deliberate notes baked in: Task 2 defers the pdf URL to Task 3 (view doesn't exist yet); T3 warns the implementer that a function-local import would break the mock patch target; the free-user test uses the tier-reset precedent from test_coach_sos.
- Test arithmetic: T1=4, T2=+8 (12), T3=+3 (15, one env-dependent skip), T4=4, T5=2 → sweep 26 with the 5 existing SOS tests.
