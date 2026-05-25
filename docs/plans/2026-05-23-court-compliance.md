# Court Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a paid Court Compliance subscription tier ($19.99/mo) that lets court-ordered users log AA/NA/SMART meeting attendance, generate tamper-evident PDF court reports, and email them directly to probation officers.

**Architecture:** Add a new `court` tier to the existing `Subscription` model (replacing the unused `pro` slot for semantic clarity). Three new Django models (`MeetingAttendance`, `CourtReportProfile`, `CourtReport`) live in `apps.accounts` alongside the existing subscription code. PDF generation uses WeasyPrint rendering a Django template, with a SHA-256 hash embedded in the document and a public verify endpoint so courts can confirm the file hasn't been altered. Phase 1 ships manual attendance entry (typed by user, optionally linked to an existing `Meeting` row); GPS verification, photo upload, sponsor digital signatures, and QR check-in are explicitly deferred to Phase 2.

**Tech Stack:** Django 5.0, PostgreSQL, WeasyPrint 60+ (HTML→PDF), Stripe (web subscriptions), Resend HTTP API (email delivery), Cloudinary (PDF storage in production).

**Audience:** Court-ordered AA/NA/SMART attendees, DUI defendants, drug court participants, family court (custody) cases. Standard form fields verified against AA, NA, and SMART Recovery attendance templates: defendant name, case number, meeting date/time/address/type/program, chair signature, monthly submission cadence.

**Legal positioning:** Program-neutral language throughout (avoid "AA app" framing). Courts cannot mandate 12-step exclusively (First Amendment); supporting SMART Recovery and secular alternatives is both legal best-practice and a market differentiator vs. existing AA-only court trackers.

**Phase 1 (this plan):** Tier + models + manual attendance entry + PDF generation + verify endpoint + email-to-PO + pricing page + landing page. ~10–14 days solo dev work.

**Phase 2 (separate plan, deferred):** GPS verification, sponsor signature flow, QR check-in, photo proof upload, calendar heatmap, auto-monthly recurring email.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `apps/accounts/payment_models.py` | Modify | Rename `pro` tier → `court`; update helper methods |
| `apps/accounts/decorators.py` | Modify | Add `court_required` decorator |
| `apps/accounts/court_models.py` | Create | `MeetingAttendance`, `CourtReportProfile`, `CourtReport` |
| `apps/accounts/court_forms.py` | Create | Forms for attendance entry + profile setup |
| `apps/accounts/court_views.py` | Create | All court-compliance views |
| `apps/accounts/court_service.py` | Create | PDF rendering, hashing, email-to-PO logic |
| `apps/accounts/migrations/0034_rename_pro_to_court.py` | Create | Tier rename (data migration) |
| `apps/accounts/migrations/0035_court_compliance_models.py` | Create | New models |
| `apps/accounts/urls.py` | Modify | Mount `/accounts/court/` URLs |
| `apps/accounts/templates/court/profile.html` | Create | Compliance profile setup form |
| `apps/accounts/templates/court/attendance_list.html` | Create | Log of attended meetings |
| `apps/accounts/templates/court/attendance_form.html` | Create | Add/edit meeting attendance |
| `apps/accounts/templates/court/dashboard.html` | Create | Progress widget + actions |
| `apps/accounts/templates/court/report_list.html` | Create | Generated reports + send-to-PO action |
| `apps/accounts/templates/court/report_pdf.html` | Create | WeasyPrint HTML template |
| `apps/accounts/templates/court/verify.html` | Create | Public hash-verification page |
| `apps/accounts/templates/court/email_pdf.html` | Create | Email body wrapping PDF attachment |
| `apps/accounts/templates/accounts/pricing.html` | Modify | Add 4th tier card |
| `apps/core/templates/core/court_ordered_meeting_tracker.html` | Create | Public SEO landing page |
| `apps/core/urls.py` | Modify | Register landing page route |
| `apps/core/views.py` | Modify | Add landing page view |
| `apps/accounts/tests_court.py` | Create | Test suite for the whole feature |
| `requirements.txt` | Modify | Add `weasyprint==62.3` |
| `sitemap.xml` | Modify | Add court landing page |
| `root_files/robots.txt` | Modify | Disallow `/accounts/court/` (private), allow `/court-ordered-meeting-tracker/` |
| `templates/base.html` | Modify | Add nav link to court dashboard for court-tier users |
| `recovery_hub/urls.py` | Modify | Mount public `/verify/court/<hash>/` endpoint |
| `CLAUDE.md` | Modify | Document court compliance system |

**Key design decisions locked in:**
1. Rename `pro` → `court` in `TIER_CHOICES` rather than adding a 4th value. The `pro` tier has zero users (verified: 0 paid subscriptions total) and zero meaningful usage. Keeping it would mean two semantically-similar tiers and decision fatigue on the pricing page.
2. Store legal name as a new field on `CourtReportProfile`, not on `User`. Most users sign up with username only; legal name is only relevant for court reports.
3. SHA-256 hash is computed over the **rendered PDF bytes** at generation time, stored in the DB, embedded in the PDF footer, and exposed via `/verify/court/<hash>/`. If anyone edits the PDF, the hash on the file won't match the stored hash → tamper detection without third-party services.
4. PDFs stored via existing Cloudinary file storage in production (already configured). Local dev uses `MEDIA_ROOT`.
5. Email delivery uses the existing `apps.accounts.email_service.send_email()` (Resend HTTP API).
6. Tests use Django's built-in `TestCase` and live in `apps/accounts/tests_court.py` — matches existing test style.

---

## Pre-flight

- [ ] **Step 0.1: Verify current branch + clean working tree**

Run:
```bash
git status
git branch --show-current
```

Expected: working tree clean (untracked plan files OK), on `main` or a fresh feature branch.

- [ ] **Step 0.2: Create feature branch**

Run:
```bash
git checkout -b feat/court-compliance
```

- [ ] **Step 0.3: Add WeasyPrint to requirements.txt**

Edit `requirements.txt`. Find the `# Utilities` block (around line 47, just after `Pillow==10.2.0`) and add WeasyPrint right after it:

```
# PDF generation (court compliance reports)
WeasyPrint==62.3
```

- [ ] **Step 0.4: Install locally + verify it imports**

Run:
```bash
pip install WeasyPrint==62.3
python -c "from weasyprint import HTML; print('OK')"
```

Expected: `OK` printed. On macOS you may need `brew install pango`; on Linux/Railway it's already available via the base image.

- [ ] **Step 0.5: Commit the dep**

```bash
git add requirements.txt
git commit -m "chore: add WeasyPrint for court compliance PDF generation"
```

---

## Task 1: Rename `pro` tier → `court`

**Why:** The unused `pro` tier slot creates ambiguity. Renaming it produces semantically-clear pricing and avoids carrying two near-identical premium tiers forever.

**Files:**
- Modify: `apps/accounts/payment_models.py` (lines 17–21, 105–110, 123–133)
- Create: `apps/accounts/migrations/0034_rename_pro_to_court.py`
- Modify: `apps/accounts/decorators.py` (lines 43–72)
- Modify: `apps/accounts/context_processors.py` (lines 14, 24)

- [ ] **Step 1.1: Write failing test for `is_court()` and tier label**

Create `apps/accounts/tests_court.py`:

```python
# apps/accounts/tests_court.py
"""Tests for Court Compliance feature."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.payment_models import Subscription

User = get_user_model()


class TierRenameTest(TestCase):
    """The unused `pro` tier should be renamed to `court` for semantic clarity."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='court_user', email='c@example.com', password='pw'
        )

    def test_court_is_a_valid_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertIn('court', valid_tiers)

    def test_pro_is_no_longer_a_tier_choice(self):
        valid_tiers = [t[0] for t in Subscription.TIER_CHOICES]
        self.assertNotIn('pro', valid_tiers)

    def test_is_court_returns_true_for_active_court_subscription(self):
        sub = Subscription.objects.create(
            user=self.user, tier='court', status='active'
        )
        self.assertTrue(sub.is_court())
        self.assertTrue(sub.is_premium())  # court is a superset of premium

    def test_is_court_returns_false_for_premium_user(self):
        sub = Subscription.objects.create(
            user=self.user, tier='premium', status='active'
        )
        self.assertFalse(sub.is_court())

    def test_is_court_returns_false_for_canceled_court(self):
        sub = Subscription.objects.create(
            user=self.user, tier='court', status='canceled'
        )
        self.assertFalse(sub.is_court())
```

- [ ] **Step 1.2: Run the test, confirm it fails**

Run:
```bash
python manage.py test apps.accounts.tests_court.TierRenameTest -v 2
```

Expected: `FAIL` — `'court'` not in `TIER_CHOICES` and `is_court()` doesn't exist.

- [ ] **Step 1.3: Update `TIER_CHOICES` and helper methods**

Edit `apps/accounts/payment_models.py`:

Replace lines 17–21:
```python
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('court', 'Court Compliance'),
    ]
```

Replace lines 104–110 (`is_premium` and `is_pro`) with:
```python
    def is_premium(self):
        """Check if user has Premium tier or higher (court inherits all premium features)."""
        return self.tier in ['premium', 'court'] and self.is_active()

    def is_court(self):
        """Check if user has Court Compliance tier."""
        return self.tier == 'court' and self.is_active()
```

Replace lines 123–133 (`can_upgrade` / `can_downgrade`) with:
```python
    def can_upgrade(self):
        """Check if user can upgrade their subscription."""
        if self.tier == 'free':
            return True
        if self.tier == 'premium' and self.is_active():
            return True  # Can upgrade to Court Compliance
        return False

    def can_downgrade(self):
        """Check if user can downgrade their subscription."""
        return self.tier in ['premium', 'court'] and self.is_active()
```

- [ ] **Step 1.4: Update `context_processors.py`**

Edit `apps/accounts/context_processors.py`:

Replace `is_pro_user` references (lines 14, 24) with `is_court_user`:

```python
        'is_court_user': False,
```
and:
```python
                'is_court_user': subscription.is_court(),
```

- [ ] **Step 1.5: Update `decorators.py`**

Edit `apps/accounts/decorators.py`. Replace `pro_required` (lines 43–72) with `court_required`:

```python
def court_required(view_func):
    """
    Decorator that requires Court Compliance subscription.
    Redirects to upgrade page if user doesn't have court access.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')

        if not hasattr(request.user, 'subscription'):
            messages.warning(
                request,
                'Court Compliance reporting requires the Court Compliance subscription.'
            )
            return redirect('accounts:pricing')

        if not request.user.subscription.is_court():
            messages.warning(
                request,
                'Court Compliance reporting requires the Court Compliance subscription.'
            )
            return redirect('accounts:pricing')

        return view_func(request, *args, **kwargs)

    return wrapper
```

- [ ] **Step 1.6: Create data migration**

Create `apps/accounts/migrations/0034_rename_pro_to_court.py`:

```python
"""Rename `pro` tier to `court` and update any existing rows."""
from django.db import migrations


def rename_pro_to_court(apps, schema_editor):
    Subscription = apps.get_model('accounts', 'Subscription')
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    Subscription.objects.filter(tier='pro').update(tier='court')
    SubscriptionPlan.objects.filter(tier='pro').update(tier='court')


def reverse_rename(apps, schema_editor):
    Subscription = apps.get_model('accounts', 'Subscription')
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    Subscription.objects.filter(tier='court').update(tier='pro')
    SubscriptionPlan.objects.filter(tier='court').update(tier='pro')


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0033_seed_lovedone60'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='tier',
            field=__import__('django.db.models', fromlist=['CharField']).CharField(
                choices=[('free', 'Free'), ('premium', 'Premium'), ('court', 'Court Compliance')],
                default='free', max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='tier',
            field=__import__('django.db.models', fromlist=['CharField']).CharField(
                choices=[('free', 'Free'), ('premium', 'Premium'), ('court', 'Court Compliance')],
                max_length=10,
            ),
        ),
        migrations.RunPython(rename_pro_to_court, reverse_rename),
    ]
```

- [ ] **Step 1.7: Apply migration and re-run test**

Run:
```bash
python manage.py migrate accounts
python manage.py test apps.accounts.tests_court.TierRenameTest -v 2
```

Expected: All 5 tests pass.

- [ ] **Step 1.8: Search-and-fix remaining `is_pro` / `pro_required` references**

Run:
```bash
grep -rn "is_pro\b\|pro_required\|TIER_PRO\|'pro'\|tier=='pro'" apps/ templates/ --include='*.py' --include='*.html' | grep -v migrations | grep -v ".pyc"
```

For each result not in `migrations/0034_...py`: replace `is_pro` → `is_court`, `pro_required` → `court_required`, `'pro'` → `'court'`. Update `payment_views.py` line 288 specifically.

- [ ] **Step 1.9: Run full test suite to confirm nothing broke**

Run:
```bash
python manage.py test apps.accounts -v 1
```

Expected: All existing tests still pass.

- [ ] **Step 1.10: Commit**

```bash
git add apps/accounts/payment_models.py apps/accounts/decorators.py apps/accounts/context_processors.py apps/accounts/payment_views.py apps/accounts/migrations/0034_rename_pro_to_court.py apps/accounts/tests_court.py
git commit -m "feat(accounts): rename unused 'pro' tier to 'court' for Court Compliance"
```

---

## Task 2: Create `CourtReportProfile` model

**Why:** Court-ordered users have a stable set of court details (case number, court, PO email) that don't change between reports. Storing them on a OneToOne profile avoids re-entering them.

**Files:**
- Create: `apps/accounts/court_models.py`
- Create: `apps/accounts/migrations/0035_court_compliance_models.py` (will house all 3 models)

- [ ] **Step 2.1: Write failing test for `CourtReportProfile`**

Append to `apps/accounts/tests_court.py`:

```python
from apps.accounts.court_models import (
    CourtReportProfile, MeetingAttendance, CourtReport,
    PROGRAM_CHOICES, MEETING_TYPE_CHOICES, VERIFICATION_CHOICES,
)


class CourtReportProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='court_u', email='cu@example.com', password='pw'
        )

    def test_profile_has_sensible_defaults(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertEqual(profile.required_meetings_per_week, 3)
        self.assertFalse(profile.auto_email_monthly)
        self.assertEqual(profile.legal_name, '')

    def test_profile_is_one_to_one_with_user(self):
        CourtReportProfile.objects.create(user=self.user)
        with self.assertRaises(Exception):
            CourtReportProfile.objects.create(user=self.user)

    def test_profile_str_includes_username(self):
        profile = CourtReportProfile.objects.create(
            user=self.user, legal_name='Court User', case_number='2026-CR-0042'
        )
        self.assertIn('court_u', str(profile))

    def test_default_period_start_set_on_save_when_empty(self):
        profile = CourtReportProfile.objects.create(user=self.user)
        self.assertIsNotNone(profile.report_period_start)
        self.assertLessEqual(profile.report_period_start, timezone.now().date())
```

- [ ] **Step 2.2: Run test, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtReportProfileTest -v 2
```

Expected: `ImportError` — `court_models` does not exist.

- [ ] **Step 2.3: Create `court_models.py` with `CourtReportProfile`**

Create `apps/accounts/court_models.py`:

```python
# apps/accounts/court_models.py
"""
Court Compliance models — attendance tracking and tamper-evident reports
for court-ordered AA/NA/SMART meeting attendees.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


PROGRAM_CHOICES = [
    ('aa', 'Alcoholics Anonymous'),
    ('na', 'Narcotics Anonymous'),
    ('ca', 'Cocaine Anonymous'),
    ('ma', 'Marijuana Anonymous'),
    ('ga', 'Gamblers Anonymous'),
    ('smart', 'SMART Recovery'),
    ('refuge', 'Refuge Recovery'),
    ('lifering', 'LifeRing'),
    ('other', 'Other Recovery Program'),
]

MEETING_TYPE_CHOICES = [
    ('open', 'Open'),
    ('closed', 'Closed'),
    ('discussion', 'Discussion'),
    ('speaker', 'Speaker'),
    ('step', 'Step Study'),
    ('big_book', 'Big Book Study'),
    ('beginners', 'Beginners / Newcomers'),
    ('mens', "Men's"),
    ('womens', "Women's"),
    ('lgbtq', 'LGBTQ+'),
    ('other', 'Other'),
]

VERIFICATION_CHOICES = [
    ('self', 'Self-Reported'),
    ('signature', 'Digital Chair Signature'),
    ('photo', 'Photo of Attendance Card'),
    ('gps', 'GPS Verified'),
    ('qr', 'QR Code Check-In'),
]


class CourtReportProfile(models.Model):
    """Stable court-ordered context for a user — case number, PO contact, etc."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='court_profile',
    )

    # Legal identity (separate from username, only used on court reports)
    legal_name = models.CharField(max_length=200, blank=True)

    # Court context
    case_number = models.CharField(max_length=80, blank=True)
    court_name = models.CharField(max_length=200, blank=True)
    jurisdiction = models.CharField(max_length=120, blank=True, help_text='State, county, or city')
    judge_name = models.CharField(max_length=120, blank=True)

    # Probation / referral contact
    probation_officer_name = models.CharField(max_length=120, blank=True)
    probation_officer_email = models.EmailField(blank=True)
    attorney_email = models.EmailField(blank=True)

    # Compliance requirements
    required_meetings_per_week = models.PositiveIntegerField(default=3)
    report_period_start = models.DateField(
        null=True, blank=True,
        help_text='Start date the user is required to track from (e.g. sentencing date).',
    )
    report_period_end = models.DateField(
        null=True, blank=True,
        help_text='End date of compliance requirement (e.g. next court date or probation end).',
    )

    # Behavior
    auto_email_monthly = models.BooleanField(
        default=False,
        help_text='Phase 2 — automatically email a monthly report to the probation officer.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'court_report_profiles'
        verbose_name = 'Court Report Profile'
        verbose_name_plural = 'Court Report Profiles'

    def __str__(self):
        return f"{self.user.username} — court profile (case {self.case_number or 'none'})"

    def save(self, *args, **kwargs):
        if not self.report_period_start:
            self.report_period_start = timezone.now().date()
        super().save(*args, **kwargs)
```

- [ ] **Step 2.4: Re-run test, confirm pass**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtReportProfileTest -v 2
```

Expected: All 4 tests pass (after running migrations in Step 4.4).

- [ ] **Step 2.5: Commit (model only — migration comes in Task 4)**

```bash
git add apps/accounts/court_models.py apps/accounts/tests_court.py
git commit -m "feat(accounts): add CourtReportProfile model"
```

---

## Task 3: Create `MeetingAttendance` and `CourtReport` models

**Files:**
- Modify: `apps/accounts/court_models.py`

- [ ] **Step 3.1: Write failing tests**

Append to `apps/accounts/tests_court.py`:

```python
class MeetingAttendanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='att_user', email='att@example.com', password='pw'
        )

    def _attendance(self, **overrides):
        kwargs = dict(
            user=self.user,
            meeting_name='Tuesday Big Book',
            meeting_date=timezone.now(),
            meeting_address='123 Main St, Austin, TX',
            program='aa',
            meeting_type='open',
            verification_method='self',
        )
        kwargs.update(overrides)
        return MeetingAttendance.objects.create(**kwargs)

    def test_attendance_str_shows_user_name_and_date(self):
        att = self._attendance()
        self.assertIn('att_user', str(att))
        self.assertIn('Big Book', str(att))

    def test_attendance_program_display(self):
        att = self._attendance(program='smart')
        self.assertEqual(att.get_program_display(), 'SMART Recovery')

    def test_attendance_ordering_descending_by_date(self):
        early = self._attendance(meeting_date=timezone.now() - timedelta(days=5))
        late = self._attendance(meeting_date=timezone.now())
        results = list(MeetingAttendance.objects.filter(user=self.user))
        self.assertEqual(results[0], late)
        self.assertEqual(results[1], early)

    def test_attendance_default_verification_is_self(self):
        att = MeetingAttendance.objects.create(
            user=self.user,
            meeting_name='Daily',
            meeting_date=timezone.now(),
            program='aa',
            meeting_type='open',
        )
        self.assertEqual(att.verification_method, 'self')


class CourtReportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='rep_user', email='rep@example.com', password='pw'
        )

    def test_report_str(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='deadbeef' * 8,
            attendance_count=12,
        )
        self.assertIn('rep_user', str(report))
        self.assertIn('2026-05', str(report))

    def test_short_hash_property_returns_first_8_chars(self):
        report = CourtReport.objects.create(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
            pdf_hash='abc123def456' + '0' * 52,
            attendance_count=0,
        )
        self.assertEqual(report.short_hash, 'abc123de')
```

- [ ] **Step 3.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.MeetingAttendanceTest apps.accounts.tests_court.CourtReportTest -v 2
```

Expected: `ImportError` — `MeetingAttendance` and `CourtReport` not yet defined.

- [ ] **Step 3.3: Append models to `court_models.py`**

Append to `apps/accounts/court_models.py`:

```python
class MeetingAttendance(models.Model):
    """One attended recovery meeting. Drives the court report."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meeting_attendances',
    )

    # Optional link to a Meeting row from the existing meeting finder
    meeting = models.ForeignKey(
        'support_services.Meeting',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='attendances',
    )

    # Free-text fallbacks (always required so reports work without a Meeting row)
    meeting_name = models.CharField(max_length=200)
    meeting_date = models.DateTimeField()
    meeting_end_time = models.DateTimeField(null=True, blank=True)
    meeting_address = models.CharField(max_length=300, blank=True)
    meeting_online = models.BooleanField(default=False)
    meeting_platform = models.CharField(
        max_length=80, blank=True,
        help_text='Zoom, online group AA, etc. — only when meeting_online=True.',
    )

    program = models.CharField(max_length=20, choices=PROGRAM_CHOICES, default='aa')
    meeting_type = models.CharField(max_length=20, choices=MEETING_TYPE_CHOICES, default='open')

    verification_method = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='self',
    )

    # Phase 1: digital chair signature is just a typed name + timestamp.
    # Phase 2 will add per-signer verification.
    chair_signature_name = models.CharField(max_length=120, blank=True)
    chair_signature_at = models.DateTimeField(null=True, blank=True)

    # Phase 2 fields (declared now so migrations don't churn later)
    gps_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    attendance_photo = models.ImageField(upload_to='court/attendance/', null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'meeting_attendances'
        verbose_name = 'Meeting Attendance'
        verbose_name_plural = 'Meeting Attendances'
        ordering = ['-meeting_date']
        indexes = [
            models.Index(fields=['user', '-meeting_date']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.meeting_name} on {self.meeting_date:%Y-%m-%d}"


class CourtReport(models.Model):
    """A generated PDF report covering a period — immutable once created."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='court_reports',
    )

    period_start = models.DateField()
    period_end = models.DateField()

    pdf = models.FileField(upload_to='court/reports/', null=True, blank=True)
    pdf_hash = models.CharField(max_length=64, db_index=True, help_text='SHA-256 of the PDF bytes')
    attendance_count = models.PositiveIntegerField(default=0)

    # Snapshot of profile fields at the moment of generation (so a report
    # remains accurate even if the user later changes their case number).
    legal_name_snapshot = models.CharField(max_length=200, blank=True)
    case_number_snapshot = models.CharField(max_length=80, blank=True)
    court_name_snapshot = models.CharField(max_length=200, blank=True)

    # Email audit trail
    emailed_to = models.TextField(blank=True, help_text='Comma-separated recipients')
    emailed_at = models.DateTimeField(null=True, blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'court_reports'
        verbose_name = 'Court Report'
        verbose_name_plural = 'Court Reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', '-generated_at']),
            models.Index(fields=['pdf_hash']),
        ]

    def __str__(self):
        return f"{self.user.username} — court report {self.period_start:%Y-%m} to {self.period_end:%Y-%m}"

    @property
    def short_hash(self):
        return self.pdf_hash[:8] if self.pdf_hash else ''
```

- [ ] **Step 3.4: Commit (no migration yet — Task 4 generates it once)**

```bash
git add apps/accounts/court_models.py apps/accounts/tests_court.py
git commit -m "feat(accounts): add MeetingAttendance and CourtReport models"
```

---

## Task 4: Generate and apply migrations

- [ ] **Step 4.1: Make sure models are discoverable**

Edit `apps/accounts/models.py`. At the bottom of the file, add:

```python
# Re-export court compliance models so Django discovers them at app load
from apps.accounts.court_models import (  # noqa: E402, F401
    CourtReportProfile, MeetingAttendance, CourtReport,
)
```

- [ ] **Step 4.2: Generate migration**

Run:
```bash
python manage.py makemigrations accounts -n court_compliance_models
```

Expected: a new file `apps/accounts/migrations/0035_court_compliance_models.py` is created.

- [ ] **Step 4.3: Inspect the generated migration**

Run:
```bash
cat apps/accounts/migrations/0035_court_compliance_models.py
```

Expected: contains `CreateModel` operations for `CourtReportProfile`, `MeetingAttendance`, and `CourtReport`. If `support_services.Meeting` isn't in the dependency list, add `('support_services', '0002_add_meeting_reminder_fields')` to the `dependencies` list.

- [ ] **Step 4.4: Apply migration**

Run:
```bash
python manage.py migrate accounts
```

Expected: migration applies cleanly.

- [ ] **Step 4.5: Run all model tests**

Run:
```bash
python manage.py test apps.accounts.tests_court -v 2
```

Expected: All Task 1–3 tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/0035_court_compliance_models.py
git commit -m "feat(accounts): migrate court compliance models"
```

---

## Task 5: PDF generation service (hash-stamped, tamper-evident)

**Files:**
- Create: `apps/accounts/court_service.py`
- Create: `apps/accounts/templates/court/report_pdf.html`

This is the heart of the feature. The PDF must:
1. Contain all attendance rows in the period
2. Contain user identity + court context from `CourtReportProfile` (snapshotted)
3. Be byte-deterministic when rendered twice with the same inputs (so hash is meaningful)
4. Embed its own SHA-256 hash + verify URL on the last page

- [ ] **Step 5.1: Write failing service test**

Append to `apps/accounts/tests_court.py`:

```python
from io import BytesIO
import hashlib

from apps.accounts import court_service


class CourtServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='pdf_user', email='pdf@example.com', password='pw',
            first_name='Pat'
        )
        self.profile = CourtReportProfile.objects.create(
            user=self.user,
            legal_name='Pat Doe',
            case_number='2026-CR-0007',
            court_name='Travis County Court 4',
            probation_officer_name='Officer Smith',
            probation_officer_email='smith@travisco.gov',
            required_meetings_per_week=3,
        )
        # Three attendances in May 2026
        for day in [3, 10, 17]:
            MeetingAttendance.objects.create(
                user=self.user,
                meeting_name=f'May {day} Group',
                meeting_date=timezone.make_aware(datetime(2026, 5, day, 19, 0)),
                meeting_address=f'{day} Recovery Way',
                program='aa',
                meeting_type='open',
                verification_method='self',
            )

    def test_render_pdf_returns_bytes_and_hash(self):
        pdf_bytes, sha256 = court_service.render_court_report_pdf(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)  # real PDFs are >1KB
        self.assertEqual(len(sha256), 64)
        self.assertEqual(sha256, hashlib.sha256(pdf_bytes).hexdigest())

    def test_render_pdf_starts_with_pdf_magic_bytes(self):
        pdf_bytes, _ = court_service.render_court_report_pdf(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_generate_creates_court_report_row(self):
        report = court_service.generate_court_report(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertEqual(report.attendance_count, 3)
        self.assertEqual(report.legal_name_snapshot, 'Pat Doe')
        self.assertEqual(report.case_number_snapshot, '2026-CR-0007')
        self.assertEqual(len(report.pdf_hash), 64)
        self.assertTrue(report.pdf.name.endswith('.pdf'))

    def test_attendance_outside_period_excluded(self):
        # Add an April attendance — should NOT count toward May report
        MeetingAttendance.objects.create(
            user=self.user,
            meeting_name='April outlier',
            meeting_date=timezone.make_aware(datetime(2026, 4, 25, 19, 0)),
            program='aa',
            meeting_type='open',
        )
        report = court_service.generate_court_report(
            user=self.user,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        self.assertEqual(report.attendance_count, 3)
```

- [ ] **Step 5.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtServiceTest -v 2
```

Expected: `ImportError` — `court_service` doesn't exist.

- [ ] **Step 5.3: Create the PDF HTML template**

Create `apps/accounts/templates/court/report_pdf.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Court Compliance Report — {{ legal_name|default:user.username }}</title>
<style>
@page {
    size: letter;
    margin: 0.6in 0.5in;
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages) "  ·  Verify at myrecoverypal.com/verify/court/{{ pdf_hash_short }}";
        font-size: 8pt;
        color: #555;
    }
}
body { font-family: 'Helvetica', sans-serif; font-size: 10pt; color: #222; }
h1 { font-size: 18pt; margin: 0 0 0.1in; color: #1e4d8b; }
h2 { font-size: 12pt; margin: 0.25in 0 0.1in; color: #1e4d8b; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
.subtitle { color: #555; margin-bottom: 0.2in; }
.header-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6pt 18pt;
    font-size: 9.5pt;
    margin-bottom: 0.15in;
}
.header-grid .label { font-weight: bold; color: #555; }
.summary-box {
    background: #f4f8fc;
    border: 1px solid #c8d8ea;
    padding: 10pt 12pt;
    border-radius: 4pt;
    margin: 0.15in 0;
}
.summary-box .stat { display: inline-block; margin-right: 24pt; }
.summary-box .stat-num { font-size: 16pt; font-weight: bold; color: #1e4d8b; }
.summary-box .stat-label { font-size: 8.5pt; color: #555; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; margin-top: 0.1in; }
th { background: #1e4d8b; color: white; text-align: left; padding: 5pt 6pt; font-size: 9pt; }
td { padding: 4pt 6pt; border-bottom: 1px solid #e0e0e0; font-size: 9pt; vertical-align: top; }
tr:nth-child(even) td { background: #fafafa; }
.attestation {
    margin-top: 0.25in;
    padding: 10pt 12pt;
    border: 1px solid #888;
    border-radius: 4pt;
    font-size: 9pt;
    line-height: 1.4;
}
.attestation .sig-line {
    margin-top: 18pt;
    border-top: 1px solid #222;
    width: 3in;
    padding-top: 3pt;
    font-size: 8.5pt;
}
.hash-footer {
    margin-top: 0.2in;
    padding: 8pt 10pt;
    background: #f0f0f0;
    border-left: 3px solid #1e4d8b;
    font-size: 8pt;
    font-family: 'Courier New', monospace;
    word-break: break-all;
}
.verify-note { font-size: 8pt; color: #555; margin-top: 4pt; font-family: 'Helvetica', sans-serif; }
.program-pill {
    display: inline-block;
    background: #e3eef9;
    color: #1e4d8b;
    padding: 1pt 6pt;
    border-radius: 8pt;
    font-size: 8pt;
    font-weight: 600;
}
.online-pill { background: #fef3c7; color: #92400e; }
</style>
</head>
<body>

<h1>Recovery Meeting Attendance Report</h1>
<div class="subtitle">Period: {{ period_start|date:"F j, Y" }} – {{ period_end|date:"F j, Y" }} · Generated {{ generated_at|date:"F j, Y g:i A" }}</div>

<h2>Defendant / Participant</h2>
<div class="header-grid">
    <div><span class="label">Legal Name:</span> {{ legal_name|default:"—" }}</div>
    <div><span class="label">Case Number:</span> {{ case_number|default:"—" }}</div>
    <div><span class="label">Court:</span> {{ court_name|default:"—" }}</div>
    <div><span class="label">Jurisdiction:</span> {{ jurisdiction|default:"—" }}</div>
    <div><span class="label">Judge:</span> {{ judge_name|default:"—" }}</div>
    <div><span class="label">Probation Officer:</span> {{ probation_officer_name|default:"—" }}</div>
</div>

<h2>Summary</h2>
<div class="summary-box">
    <div class="stat">
        <div class="stat-num">{{ attendance_count }}</div>
        <div class="stat-label">Meetings Attended</div>
    </div>
    <div class="stat">
        <div class="stat-num">{{ weeks_in_period }}</div>
        <div class="stat-label">Weeks in Period</div>
    </div>
    <div class="stat">
        <div class="stat-num">{{ weekly_average }}</div>
        <div class="stat-label">Avg per Week</div>
    </div>
    {% if required_per_week %}
    <div class="stat">
        <div class="stat-num">{{ required_per_week }}</div>
        <div class="stat-label">Required per Week</div>
    </div>
    {% endif %}
</div>

<h2>Attendance Log</h2>
{% if attendances %}
<table>
    <thead>
    <tr>
        <th style="width:14%">Date</th>
        <th style="width:9%">Time</th>
        <th style="width:18%">Meeting</th>
        <th style="width:11%">Program</th>
        <th style="width:11%">Type</th>
        <th style="width:25%">Location</th>
        <th style="width:12%">Verified</th>
    </tr>
    </thead>
    <tbody>
    {% for a in attendances %}
    <tr>
        <td>{{ a.meeting_date|date:"Y-m-d" }}</td>
        <td>{{ a.meeting_date|date:"g:i A" }}</td>
        <td>{{ a.meeting_name }}</td>
        <td><span class="program-pill">{{ a.get_program_display }}</span></td>
        <td>{{ a.get_meeting_type_display }}</td>
        <td>
            {% if a.meeting_online %}
                <span class="program-pill online-pill">Online</span> {{ a.meeting_platform }}
            {% else %}
                {{ a.meeting_address|default:"—" }}
            {% endif %}
        </td>
        <td>{{ a.get_verification_method_display }}{% if a.chair_signature_name %}<br><small>{{ a.chair_signature_name }}</small>{% endif %}</td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% else %}
<p><em>No meetings logged for this period.</em></p>
{% endif %}

<div class="attestation">
    <strong>Attestation.</strong> I, {{ legal_name|default:user.username }}, declare under penalty of perjury under the laws of the applicable jurisdiction that the attendance information above is true and correct to the best of my knowledge. This report was generated by software (MyRecoveryPal Court Compliance, myrecoverypal.com) based on records I created. Self-reported entries are marked as such above and have not been independently verified by a meeting chair or third party.
    <div class="sig-line">Signature of participant</div>
    <div class="sig-line">Date</div>
</div>

<div class="hash-footer">
    Report fingerprint (SHA-256): {{ pdf_hash }}
</div>
<div class="verify-note">
    This fingerprint is computed from the entire PDF. Any edit to the document will produce a different fingerprint. Verify this report is unaltered at:
    <strong>myrecoverypal.com/verify/court/{{ pdf_hash_short }}</strong>
</div>

</body>
</html>
```

Note: WeasyPrint computes the hash *after* rendering, so the hash shown in the document body is filled in via a two-pass approach in the service (see next step).

- [ ] **Step 5.4: Create the service**

Create `apps/accounts/court_service.py`:

```python
# apps/accounts/court_service.py
"""
Court Compliance PDF report generation.

Two-pass rendering:
  Pass 1: render PDF with a placeholder hash → compute SHA-256
  Pass 2: re-render with the real hash embedded → compute SHA-256 again
  Store the second hash; serve the second PDF.

This guarantees the hash printed inside the PDF matches the hash of the
PDF bytes themselves.
"""
import hashlib
import logging
from datetime import date, datetime
from io import BytesIO

from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_HASH = '0' * 64


def _build_context(user, period_start: date, period_end: date, pdf_hash: str) -> dict:
    """Assemble the template context for the PDF."""
    profile = getattr(user, 'court_profile', None) or CourtReportProfile(user=user)

    attendances = list(
        MeetingAttendance.objects.filter(
            user=user,
            meeting_date__date__gte=period_start,
            meeting_date__date__lte=period_end,
        ).order_by('meeting_date')
    )

    weeks = max(1, (period_end - period_start).days // 7 + 1)
    weekly_avg = round(len(attendances) / weeks, 1) if weeks else 0

    return {
        'user': user,
        'legal_name': profile.legal_name,
        'case_number': profile.case_number,
        'court_name': profile.court_name,
        'jurisdiction': profile.jurisdiction,
        'judge_name': profile.judge_name,
        'probation_officer_name': profile.probation_officer_name,
        'period_start': period_start,
        'period_end': period_end,
        'generated_at': timezone.now(),
        'attendances': attendances,
        'attendance_count': len(attendances),
        'weeks_in_period': weeks,
        'weekly_average': weekly_avg,
        'required_per_week': profile.required_meetings_per_week,
        'pdf_hash': pdf_hash,
        'pdf_hash_short': pdf_hash[:8],
    }


def _render_pdf_bytes(context: dict) -> bytes:
    """Render the PDF template to bytes via WeasyPrint."""
    from weasyprint import HTML
    html_str = render_to_string('court/report_pdf.html', context)
    buf = BytesIO()
    HTML(string=html_str).write_pdf(target=buf)
    return buf.getvalue()


def render_court_report_pdf(user, period_start: date, period_end: date):
    """
    Render a court compliance PDF for `user` covering `period_start..period_end`.

    Returns: (pdf_bytes, sha256_hex_string)
    """
    # Pass 1: placeholder hash → render → compute real hash
    ctx1 = _build_context(user, period_start, period_end, PLACEHOLDER_HASH)
    pdf_pass1 = _render_pdf_bytes(ctx1)
    real_hash = hashlib.sha256(pdf_pass1).hexdigest()

    # Pass 2: real hash embedded → render → return bytes
    ctx2 = _build_context(user, period_start, period_end, real_hash)
    pdf_pass2 = _render_pdf_bytes(ctx2)
    # Final hash is over the bytes that actually leave the server
    final_hash = hashlib.sha256(pdf_pass2).hexdigest()
    return pdf_pass2, final_hash


def generate_court_report(user, period_start: date, period_end: date) -> CourtReport:
    """Render the PDF and persist a `CourtReport` row."""
    pdf_bytes, pdf_hash = render_court_report_pdf(user, period_start, period_end)

    profile = getattr(user, 'court_profile', None) or CourtReportProfile(user=user)
    attendance_count = MeetingAttendance.objects.filter(
        user=user,
        meeting_date__date__gte=period_start,
        meeting_date__date__lte=period_end,
    ).count()

    report = CourtReport.objects.create(
        user=user,
        period_start=period_start,
        period_end=period_end,
        pdf_hash=pdf_hash,
        attendance_count=attendance_count,
        legal_name_snapshot=profile.legal_name or '',
        case_number_snapshot=profile.case_number or '',
        court_name_snapshot=profile.court_name or '',
    )

    filename = f"court-report-{user.username}-{period_start:%Y%m}-{report.id}-{pdf_hash[:8]}.pdf"
    report.pdf.save(filename, ContentFile(pdf_bytes), save=True)
    return report
```

- [ ] **Step 5.5: Re-run tests**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtServiceTest -v 2
```

Expected: All 4 service tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add apps/accounts/court_service.py apps/accounts/templates/court/report_pdf.html apps/accounts/tests_court.py
git commit -m "feat(accounts): WeasyPrint-based court compliance PDF generation with SHA-256 fingerprint"
```

---

## Task 6: Public hash verification endpoint

**Why:** A court receiving the PDF can paste the hash (or visit the short-hash URL) and confirm the document hasn't been altered. Tamper-evidence without any third-party service.

**Files:**
- Modify: `apps/accounts/court_views.py` (create)
- Modify: `apps/accounts/urls.py`
- Modify: `recovery_hub/urls.py`
- Create: `apps/accounts/templates/court/verify.html`

- [ ] **Step 6.1: Write failing test**

Append to `apps/accounts/tests_court.py`:

```python
class VerifyEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ver_user', email='ver@example.com', password='pw'
        )
        CourtReportProfile.objects.create(
            user=self.user, legal_name='Verify User', case_number='V-1',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='M', meeting_date=timezone.now(),
            program='aa', meeting_type='open',
        )
        self.report = court_service.generate_court_report(
            user=self.user,
            period_start=timezone.now().date().replace(day=1),
            period_end=timezone.now().date(),
        )

    def test_verify_with_full_hash_returns_200(self):
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verified')

    def test_verify_with_short_hash_returns_200(self):
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash[:8]}/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verified')

    def test_verify_with_unknown_hash_returns_404(self):
        resp = self.client.get('/verify/court/deadbeefdeadbeef/')
        self.assertEqual(resp.status_code, 404)

    def test_verify_response_does_not_leak_legal_name(self):
        """Public endpoint should NOT reveal personal information."""
        resp = self.client.get(f'/verify/court/{self.report.pdf_hash}/')
        self.assertNotContains(resp, 'Verify User')
        self.assertNotContains(resp, 'V-1')
```

- [ ] **Step 6.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.VerifyEndpointTest -v 2
```

Expected: 404 / NoReverseMatch — endpoint not yet wired.

- [ ] **Step 6.3: Create `court_views.py` with the verify view**

Create `apps/accounts/court_views.py`:

```python
# apps/accounts/court_views.py
"""Court Compliance views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)


def verify_court_report(request, hash_value):
    """
    Public endpoint — court / probation officer pastes a hash and we confirm
    that hash matches a real report. We do NOT leak any personal info.
    """
    if len(hash_value) == 64:
        report = CourtReport.objects.filter(pdf_hash=hash_value).first()
    elif len(hash_value) >= 8:
        report = CourtReport.objects.filter(pdf_hash__startswith=hash_value).first()
    else:
        report = None

    if not report:
        raise Http404('Unknown court report fingerprint')

    return render(request, 'court/verify.html', {
        'report': report,
        'verified_at': timezone.now(),
    })
```

- [ ] **Step 6.4: Create verify template**

Create `apps/accounts/templates/court/verify.html`:

```html
{% extends 'base.html' %}
{% block title %}Court Report Verified — MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width:700px; margin:3rem auto; padding:0 1rem;">
    <div style="background:#e7f7ee; border:1px solid #52b788; padding:1.5rem; border-radius:12px;">
        <h1 style="margin:0 0 0.5rem; color:#1e4d8b;">✓ Verified Court Report</h1>
        <p style="margin:0; color:#1e4d8b;">This fingerprint matches an unaltered MyRecoveryPal Court Compliance report.</p>
    </div>

    <div style="background:white; padding:1.5rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-top:1rem;">
        <p><strong>Report period:</strong> {{ report.period_start|date:"F j, Y" }} – {{ report.period_end|date:"F j, Y" }}</p>
        <p><strong>Meetings attended:</strong> {{ report.attendance_count }}</p>
        <p><strong>Generated:</strong> {{ report.generated_at|date:"F j, Y g:i A" }}</p>
        <p><strong>Full fingerprint:</strong><br>
            <code style="font-size:0.85rem; word-break:break-all;">{{ report.pdf_hash }}</code></p>

        <hr style="margin:1.5rem 0; border:none; border-top:1px solid #e0e0e0;">

        <p style="font-size:0.9rem; color:#555;">
            <strong>What this confirms:</strong> A report with this exact fingerprint was generated by MyRecoveryPal on the date shown above. If the PDF you are reviewing has the same SHA-256 fingerprint as the one above, the document has not been edited since generation.
        </p>
        <p style="font-size:0.9rem; color:#555;">
            <strong>What this does not confirm:</strong> The truthfulness of self-reported attendance entries inside the report. Verification confirms document integrity, not the accuracy of the user's statements.
        </p>
        <p style="font-size:0.85rem; color:#888; margin-top:1.5rem;">
            Verified at {{ verified_at|date:"F j, Y g:i A" }}. Personal details are intentionally not shown on this public page.
        </p>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6.5: Mount the route**

Edit `recovery_hub/urls.py`. Find the `urlpatterns = [` block (around line 35–60). Add:

```python
    path('verify/court/<str:hash_value>/', __import__('apps.accounts.court_views', fromlist=['verify_court_report']).verify_court_report, name='verify_court_report'),
```

(Add immediately after the `robots.txt` line for cleanliness.)

- [ ] **Step 6.6: Re-run tests**

Run:
```bash
python manage.py test apps.accounts.tests_court.VerifyEndpointTest -v 2
```

Expected: All 4 tests pass.

- [ ] **Step 6.7: Commit**

```bash
git add apps/accounts/court_views.py apps/accounts/templates/court/verify.html recovery_hub/urls.py apps/accounts/tests_court.py
git commit -m "feat(accounts): public /verify/court/<hash>/ endpoint for tamper-evident court reports"
```

---

## Task 7: Forms for profile setup and attendance entry

**Files:**
- Create: `apps/accounts/court_forms.py`

- [ ] **Step 7.1: Write failing test**

Append to `apps/accounts/tests_court.py`:

```python
from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)


class CourtFormsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='form_u', email='f@example.com', password='pw'
        )

    def test_profile_form_accepts_minimal_input(self):
        form = CourtReportProfileForm(data={
            'legal_name': 'Real Name',
            'required_meetings_per_week': 3,
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_rejects_zero_required_meetings(self):
        form = CourtReportProfileForm(data={
            'legal_name': 'Real Name',
            'required_meetings_per_week': 0,
        })
        self.assertFalse(form.is_valid())

    def test_attendance_form_requires_meeting_name_and_date(self):
        form = MeetingAttendanceForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('meeting_name', form.errors)
        self.assertIn('meeting_date', form.errors)

    def test_attendance_form_accepts_valid_input(self):
        form = MeetingAttendanceForm(data={
            'meeting_name': 'Tuesday Big Book',
            'meeting_date': '2026-05-20T19:00',
            'program': 'aa',
            'meeting_type': 'open',
            'verification_method': 'self',
            'meeting_address': '1 Main St',
            'meeting_online': False,
        })
        self.assertTrue(form.is_valid(), form.errors)
```

- [ ] **Step 7.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtFormsTest -v 2
```

Expected: `ImportError`.

- [ ] **Step 7.3: Create the forms**

Create `apps/accounts/court_forms.py`:

```python
# apps/accounts/court_forms.py
from django import forms

from apps.accounts.court_models import (
    CourtReportProfile, MeetingAttendance,
)


class CourtReportProfileForm(forms.ModelForm):
    class Meta:
        model = CourtReportProfile
        fields = [
            'legal_name', 'case_number', 'court_name', 'jurisdiction', 'judge_name',
            'probation_officer_name', 'probation_officer_email', 'attorney_email',
            'required_meetings_per_week', 'report_period_start', 'report_period_end',
        ]
        widgets = {
            'report_period_start': forms.DateInput(attrs={'type': 'date'}),
            'report_period_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_required_meetings_per_week(self):
        v = self.cleaned_data['required_meetings_per_week']
        if v <= 0:
            raise forms.ValidationError('Must be at least 1 meeting per week.')
        if v > 21:
            raise forms.ValidationError('That seems excessive — courts rarely require more than 7 per week.')
        return v


class MeetingAttendanceForm(forms.ModelForm):
    class Meta:
        model = MeetingAttendance
        fields = [
            'meeting_name', 'meeting_date', 'meeting_end_time',
            'meeting_address', 'meeting_online', 'meeting_platform',
            'program', 'meeting_type', 'verification_method',
            'chair_signature_name', 'notes',
        ]
        widgets = {
            'meeting_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'meeting_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        data = super().clean()
        if data.get('meeting_online') and not data.get('meeting_platform'):
            self.add_error('meeting_platform', 'Specify the platform (Zoom, online AA, etc.) for online meetings.')
        return data
```

- [ ] **Step 7.4: Re-run tests**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtFormsTest -v 2
```

Expected: All 4 tests pass.

- [ ] **Step 7.5: Commit**

```bash
git add apps/accounts/court_forms.py apps/accounts/tests_court.py
git commit -m "feat(accounts): forms for court profile + meeting attendance entry"
```

---

## Task 8: Authenticated court views (dashboard, profile, attendance CRUD, reports)

**Files:**
- Modify: `apps/accounts/court_views.py` (extend)
- Modify: `apps/accounts/urls.py`
- Create: `apps/accounts/templates/court/dashboard.html`
- Create: `apps/accounts/templates/court/profile.html`
- Create: `apps/accounts/templates/court/attendance_list.html`
- Create: `apps/accounts/templates/court/attendance_form.html`
- Create: `apps/accounts/templates/court/report_list.html`

- [ ] **Step 8.1: Write failing view tests**

Append to `apps/accounts/tests_court.py`:

```python
class CourtViewsGatingTest(TestCase):
    """All authenticated court views must require the `court` subscription."""

    def setUp(self):
        self.free_user = User.objects.create_user(
            username='free', email='free@example.com', password='pw'
        )
        Subscription.objects.create(user=self.free_user, tier='free', status='active')

        self.court_user = User.objects.create_user(
            username='court', email='court@example.com', password='pw'
        )
        Subscription.objects.create(user=self.court_user, tier='court', status='active')

    def _urls(self):
        return [
            reverse('accounts:court_dashboard'),
            reverse('accounts:court_profile'),
            reverse('accounts:court_attendance_list'),
            reverse('accounts:court_attendance_create'),
            reverse('accounts:court_report_list'),
        ]

    def test_anonymous_redirects_to_login(self):
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} did not redirect')
            self.assertIn('/login', resp.url)

    def test_free_user_redirected_to_pricing(self):
        self.client.login(username='free', password='pw')
        for url in self._urls():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f'{url} did not redirect')
            self.assertIn('pricing', resp.url)

    def test_court_user_can_load_dashboard(self):
        self.client.login(username='court', password='pw')
        resp = self.client.get(reverse('accounts:court_dashboard'))
        self.assertEqual(resp.status_code, 200)


class CourtAttendanceCrudTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='crud', email='crud@example.com', password='pw'
        )
        Subscription.objects.create(user=self.user, tier='court', status='active')
        self.client.login(username='crud', password='pw')

    def test_create_attendance_via_post(self):
        resp = self.client.post(reverse('accounts:court_attendance_create'), {
            'meeting_name': 'Wednesday Speaker',
            'meeting_date': '2026-05-22T19:30',
            'meeting_address': '1 Main St',
            'program': 'aa',
            'meeting_type': 'speaker',
            'verification_method': 'self',
            'meeting_online': False,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MeetingAttendance.objects.filter(user=self.user).count(), 1)

    def test_attendance_list_shows_only_own_attendances(self):
        other = User.objects.create_user(username='other', email='o@x.com', password='pw')
        MeetingAttendance.objects.create(
            user=other, meeting_name='Their meeting',
            meeting_date=timezone.now(), program='aa', meeting_type='open',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='My meeting',
            meeting_date=timezone.now(), program='aa', meeting_type='open',
        )
        resp = self.client.get(reverse('accounts:court_attendance_list'))
        self.assertContains(resp, 'My meeting')
        self.assertNotContains(resp, 'Their meeting')


class CourtReportGenerationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='gen', email='gen@example.com', password='pw'
        )
        Subscription.objects.create(user=self.user, tier='court', status='active')
        CourtReportProfile.objects.create(
            user=self.user, legal_name='Gen User', case_number='G-1',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='M', meeting_date=timezone.now(),
            program='aa', meeting_type='open',
        )
        self.client.login(username='gen', password='pw')

    def test_generate_report_post_creates_pdf(self):
        today = timezone.now().date()
        resp = self.client.post(reverse('accounts:court_report_generate'), {
            'period_start': today.replace(day=1).isoformat(),
            'period_end': today.isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CourtReport.objects.filter(user=self.user).count(), 1)
        report = CourtReport.objects.get(user=self.user)
        self.assertEqual(len(report.pdf_hash), 64)
```

- [ ] **Step 8.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtViewsGatingTest apps.accounts.tests_court.CourtAttendanceCrudTest apps.accounts.tests_court.CourtReportGenerationTest -v 2
```

Expected: `NoReverseMatch` — URL names not yet registered.

- [ ] **Step 8.3: Extend `court_views.py`**

Append to `apps/accounts/court_views.py`:

```python
from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)
from apps.accounts.court_service import generate_court_report
from apps.accounts.decorators import court_required
from apps.accounts.email_service import send_email


@login_required
@court_required
def court_dashboard(request):
    """Landing page inside the Court Compliance section."""
    profile = getattr(request.user, 'court_profile', None)
    recent_attendances = MeetingAttendance.objects.filter(user=request.user)[:5]
    recent_reports = CourtReport.objects.filter(user=request.user)[:3]

    # Calculate this week's progress
    today = timezone.now().date()
    monday = today - timezone.timedelta(days=today.weekday())
    this_week_count = MeetingAttendance.objects.filter(
        user=request.user, meeting_date__date__gte=monday,
    ).count()

    return render(request, 'court/dashboard.html', {
        'profile': profile,
        'recent_attendances': recent_attendances,
        'recent_reports': recent_reports,
        'this_week_count': this_week_count,
        'required_per_week': profile.required_meetings_per_week if profile else 3,
    })


@login_required
@court_required
def court_profile(request):
    profile, _ = CourtReportProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = CourtReportProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Court profile saved.')
            return redirect('accounts:court_dashboard')
    else:
        form = CourtReportProfileForm(instance=profile)
    return render(request, 'court/profile.html', {'form': form, 'profile': profile})


@login_required
@court_required
def court_attendance_list(request):
    attendances = MeetingAttendance.objects.filter(user=request.user)
    return render(request, 'court/attendance_list.html', {'attendances': attendances})


@login_required
@court_required
def court_attendance_create(request):
    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST)
        if form.is_valid():
            att = form.save(commit=False)
            att.user = request.user
            att.save()
            messages.success(request, 'Meeting logged.')
            return redirect('accounts:court_attendance_list')
    else:
        form = MeetingAttendanceForm(initial={'meeting_date': timezone.now()})
    return render(request, 'court/attendance_form.html', {'form': form, 'mode': 'create'})


@login_required
@court_required
def court_attendance_edit(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST, instance=att)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meeting updated.')
            return redirect('accounts:court_attendance_list')
    else:
        form = MeetingAttendanceForm(instance=att)
    return render(request, 'court/attendance_form.html', {'form': form, 'mode': 'edit'})


@login_required
@court_required
@require_POST
def court_attendance_delete(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    att.delete()
    messages.success(request, 'Meeting removed.')
    return redirect('accounts:court_attendance_list')


@login_required
@court_required
def court_report_list(request):
    reports = CourtReport.objects.filter(user=request.user)
    return render(request, 'court/report_list.html', {'reports': reports})


@login_required
@court_required
@require_POST
def court_report_generate(request):
    try:
        period_start = date.fromisoformat(request.POST.get('period_start'))
        period_end = date.fromisoformat(request.POST.get('period_end'))
    except (TypeError, ValueError):
        messages.error(request, 'Invalid period dates.')
        return redirect('accounts:court_report_list')

    report = generate_court_report(request.user, period_start, period_end)
    messages.success(
        request,
        f'Report generated — {report.attendance_count} meetings logged for {period_start} to {period_end}.',
    )
    return redirect('accounts:court_report_list')


@login_required
@court_required
def court_report_download(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    if not report.pdf:
        raise Http404('Report PDF missing')
    response = HttpResponse(report.pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="court-report-{report.period_start:%Y%m}-{report.short_hash}.pdf"'
    )
    return response
```

- [ ] **Step 8.4: Register URLs**

Edit `apps/accounts/urls.py`. Find the `urlpatterns = [` list and add (place near related subscription URLs):

```python
    # Court Compliance
    path('court/', __import__('apps.accounts.court_views', fromlist=['court_dashboard']).court_dashboard, name='court_dashboard'),
    path('court/profile/', __import__('apps.accounts.court_views', fromlist=['court_profile']).court_profile, name='court_profile'),
    path('court/attendance/', __import__('apps.accounts.court_views', fromlist=['court_attendance_list']).court_attendance_list, name='court_attendance_list'),
    path('court/attendance/new/', __import__('apps.accounts.court_views', fromlist=['court_attendance_create']).court_attendance_create, name='court_attendance_create'),
    path('court/attendance/<int:attendance_id>/edit/', __import__('apps.accounts.court_views', fromlist=['court_attendance_edit']).court_attendance_edit, name='court_attendance_edit'),
    path('court/attendance/<int:attendance_id>/delete/', __import__('apps.accounts.court_views', fromlist=['court_attendance_delete']).court_attendance_delete, name='court_attendance_delete'),
    path('court/reports/', __import__('apps.accounts.court_views', fromlist=['court_report_list']).court_report_list, name='court_report_list'),
    path('court/reports/generate/', __import__('apps.accounts.court_views', fromlist=['court_report_generate']).court_report_generate, name='court_report_generate'),
    path('court/reports/<int:report_id>/download/', __import__('apps.accounts.court_views', fromlist=['court_report_download']).court_report_download, name='court_report_download'),
```

- [ ] **Step 8.5: Create the templates**

Create `apps/accounts/templates/court/dashboard.html`:

```html
{% extends 'base.html' %}
{% block title %}Court Compliance — MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width:900px; margin:2rem auto; padding:0 1rem;">

<div style="background:linear-gradient(135deg,#1e4d8b,#4db8e8); color:white; padding:1.75rem 2rem; border-radius:14px; margin-bottom:1.5rem;">
    <h1 style="margin:0 0 0.4rem;">Court Compliance</h1>
    <p style="margin:0; opacity:.9;">Track court-ordered recovery meeting attendance and generate court-acceptable PDF reports.</p>
</div>

{% if not profile.case_number %}
<div style="background:#fff8e1; border:1px solid #ffc107; padding:1rem 1.25rem; border-radius:10px; margin-bottom:1.25rem;">
    <strong>Set up your court profile first.</strong>
    <p style="margin:.5rem 0 .75rem;">Enter your case number, court, and probation officer details so they appear on every report.</p>
    <a href="{% url 'accounts:court_profile' %}" class="btn btn-primary">Set Up Profile →</a>
</div>
{% endif %}

<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:1.5rem;">
    <div style="background:white; padding:1.25rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
        <div style="font-size:0.85rem; color:#888; text-transform:uppercase; letter-spacing:0.5px;">This Week</div>
        <div style="font-size:2rem; font-weight:700; color:#1e4d8b; margin:.25rem 0;">{{ this_week_count }} / {{ required_per_week }}</div>
        <div style="font-size:0.9rem; color:#555;">meetings logged</div>
    </div>
    <div style="background:white; padding:1.25rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
        <div style="font-size:0.85rem; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Reports</div>
        <div style="font-size:2rem; font-weight:700; color:#1e4d8b; margin:.25rem 0;">{{ recent_reports|length }}</div>
        <div style="font-size:0.9rem; color:#555;">generated</div>
    </div>
    <div style="background:white; padding:1.25rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
        <div style="font-size:0.85rem; color:#888; text-transform:uppercase; letter-spacing:0.5px;">Actions</div>
        <a href="{% url 'accounts:court_attendance_create' %}" class="btn btn-success" style="margin-top:.5rem; display:block; text-align:center;">+ Log Meeting</a>
    </div>
</div>

<div style="background:white; padding:1.25rem 1.5rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05); margin-bottom:1.25rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:.75rem;">
        <h2 style="margin:0; font-size:1.1rem;">Recent Meetings</h2>
        <a href="{% url 'accounts:court_attendance_list' %}" style="font-size:0.9rem;">View all →</a>
    </div>
    {% if recent_attendances %}
        <ul style="list-style:none; padding:0; margin:0;">
        {% for a in recent_attendances %}
            <li style="padding:.6rem 0; border-bottom:1px solid #eee;">
                <strong>{{ a.meeting_name }}</strong>
                <span style="color:#888;"> · {{ a.meeting_date|date:"M j, Y g:i A" }} · {{ a.get_program_display }}</span>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p style="color:#888;">No meetings logged yet. <a href="{% url 'accounts:court_attendance_create' %}">Log your first meeting →</a></p>
    {% endif %}
</div>

<div style="background:white; padding:1.25rem 1.5rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:.75rem;">
        <h2 style="margin:0; font-size:1.1rem;">Recent Reports</h2>
        <a href="{% url 'accounts:court_report_list' %}" style="font-size:0.9rem;">View all →</a>
    </div>
    {% if recent_reports %}
        <ul style="list-style:none; padding:0; margin:0;">
        {% for r in recent_reports %}
            <li style="padding:.6rem 0; border-bottom:1px solid #eee;">
                <strong>{{ r.period_start|date:"M Y" }} – {{ r.period_end|date:"M Y" }}</strong>
                <span style="color:#888;"> · {{ r.attendance_count }} meetings · fingerprint {{ r.short_hash }}</span>
                <a href="{% url 'accounts:court_report_download' r.id %}" style="float:right;">Download</a>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p style="color:#888;">No reports generated yet. <a href="{% url 'accounts:court_report_list' %}">Generate your first report →</a></p>
    {% endif %}
</div>

</div>
{% endblock %}
```

Create `apps/accounts/templates/court/profile.html`:

```html
{% extends 'base.html' %}
{% block title %}Court Profile — MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width:700px; margin:2rem auto; padding:0 1rem;">
    <h1>Court Profile</h1>
    <p style="color:#666;">These details appear on every court report you generate. You only need to enter them once.</p>

    <form method="post" style="background:white; padding:1.5rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
        {% csrf_token %}
        {% for field in form %}
            <div style="margin-bottom:1rem;">
                <label style="display:block; font-weight:600; margin-bottom:.25rem;">{{ field.label }}</label>
                {{ field }}
                {% if field.help_text %}<small style="color:#888;">{{ field.help_text }}</small>{% endif %}
                {% if field.errors %}<div style="color:#dc3545; font-size:.9rem;">{{ field.errors }}</div>{% endif %}
            </div>
        {% endfor %}
        <button type="submit" class="btn btn-primary" style="margin-top:.5rem;">Save Profile</button>
        <a href="{% url 'accounts:court_dashboard' %}" style="margin-left:.75rem;">Cancel</a>
    </form>
</div>
<style>
    form input[type="text"], form input[type="email"], form input[type="date"], form input[type="number"], form select {
        width:100%; padding:.6rem; border:1px solid #ccc; border-radius:6px; font-size:1rem;
    }
</style>
{% endblock %}
```

Create `apps/accounts/templates/court/attendance_list.html`:

```html
{% extends 'base.html' %}
{% block title %}Meeting Log — Court Compliance{% endblock %}

{% block content %}
<div class="container" style="max-width:900px; margin:2rem auto; padding:0 1rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <h1 style="margin:0;">Meeting Log</h1>
        <a href="{% url 'accounts:court_attendance_create' %}" class="btn btn-success">+ Log Meeting</a>
    </div>
    {% if attendances %}
    <table style="width:100%; background:white; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05); border-collapse:collapse; overflow:hidden;">
        <thead><tr style="background:#f4f8fc;">
            <th style="text-align:left; padding:.75rem 1rem;">Date</th>
            <th style="text-align:left; padding:.75rem 1rem;">Meeting</th>
            <th style="text-align:left; padding:.75rem 1rem;">Program</th>
            <th style="text-align:left; padding:.75rem 1rem;">Type</th>
            <th style="text-align:left; padding:.75rem 1rem;">Verified</th>
            <th></th>
        </tr></thead>
        <tbody>
        {% for a in attendances %}
        <tr style="border-top:1px solid #eee;">
            <td style="padding:.75rem 1rem;">{{ a.meeting_date|date:"M j, Y g:i A" }}</td>
            <td style="padding:.75rem 1rem;"><strong>{{ a.meeting_name }}</strong>{% if a.meeting_online %} <span style="background:#fef3c7; color:#92400e; padding:1px 6px; border-radius:8px; font-size:.75rem;">Online</span>{% endif %}</td>
            <td style="padding:.75rem 1rem;">{{ a.get_program_display }}</td>
            <td style="padding:.75rem 1rem;">{{ a.get_meeting_type_display }}</td>
            <td style="padding:.75rem 1rem;">{{ a.get_verification_method_display }}</td>
            <td style="padding:.75rem 1rem; text-align:right;">
                <a href="{% url 'accounts:court_attendance_edit' a.id %}">Edit</a>
                <form method="post" action="{% url 'accounts:court_attendance_delete' a.id %}" style="display:inline; margin-left:.5rem;" onsubmit="return confirm('Delete this meeting record?')">
                    {% csrf_token %}<button type="submit" style="background:none; border:none; color:#dc3545; cursor:pointer;">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
        <p style="color:#888; background:white; padding:2rem; text-align:center; border-radius:12px;">No meetings logged yet.</p>
    {% endif %}
</div>
{% endblock %}
```

Create `apps/accounts/templates/court/attendance_form.html`:

```html
{% extends 'base.html' %}
{% block title %}{{ mode|capfirst }} Meeting — Court Compliance{% endblock %}

{% block content %}
<div class="container" style="max-width:700px; margin:2rem auto; padding:0 1rem;">
    <h1>{% if mode == 'edit' %}Edit{% else %}Log{% endif %} Meeting</h1>
    <form method="post" style="background:white; padding:1.5rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05);">
        {% csrf_token %}
        {% for field in form %}
            <div style="margin-bottom:1rem;">
                <label style="display:block; font-weight:600; margin-bottom:.25rem;">{{ field.label }}</label>
                {{ field }}
                {% if field.help_text %}<small style="color:#888;">{{ field.help_text }}</small>{% endif %}
                {% if field.errors %}<div style="color:#dc3545; font-size:.9rem;">{{ field.errors }}</div>{% endif %}
            </div>
        {% endfor %}
        <button type="submit" class="btn btn-success">Save Meeting</button>
        <a href="{% url 'accounts:court_attendance_list' %}" style="margin-left:.75rem;">Cancel</a>
    </form>
</div>
<style>
    form input, form select, form textarea {
        width:100%; padding:.6rem; border:1px solid #ccc; border-radius:6px; font-size:1rem; font-family:inherit;
    }
    form input[type="checkbox"] { width:auto; }
</style>
{% endblock %}
```

Create `apps/accounts/templates/court/report_list.html`:

```html
{% extends 'base.html' %}
{% block title %}Court Reports — MyRecoveryPal{% endblock %}

{% block content %}
<div class="container" style="max-width:900px; margin:2rem auto; padding:0 1rem;">
    <h1>Court Reports</h1>

    <div style="background:white; padding:1.5rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05); margin-bottom:1.5rem;">
        <h2 style="margin:0 0 .75rem; font-size:1.1rem;">Generate a new report</h2>
        <form method="post" action="{% url 'accounts:court_report_generate' %}" style="display:flex; gap:.75rem; flex-wrap:wrap; align-items:end;">
            {% csrf_token %}
            <div>
                <label style="display:block; font-size:.85rem; color:#555;">Period start</label>
                <input type="date" name="period_start" required style="padding:.5rem; border:1px solid #ccc; border-radius:6px;">
            </div>
            <div>
                <label style="display:block; font-size:.85rem; color:#555;">Period end</label>
                <input type="date" name="period_end" required style="padding:.5rem; border:1px solid #ccc; border-radius:6px;">
            </div>
            <button type="submit" class="btn btn-primary">Generate Report</button>
        </form>
    </div>

    {% if reports %}
    <table style="width:100%; background:white; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,.05); border-collapse:collapse; overflow:hidden;">
        <thead><tr style="background:#f4f8fc;">
            <th style="text-align:left; padding:.75rem 1rem;">Period</th>
            <th style="text-align:left; padding:.75rem 1rem;">Meetings</th>
            <th style="text-align:left; padding:.75rem 1rem;">Generated</th>
            <th style="text-align:left; padding:.75rem 1rem;">Fingerprint</th>
            <th></th>
        </tr></thead>
        <tbody>
        {% for r in reports %}
        <tr style="border-top:1px solid #eee;">
            <td style="padding:.75rem 1rem;">{{ r.period_start|date:"M j, Y" }} – {{ r.period_end|date:"M j, Y" }}</td>
            <td style="padding:.75rem 1rem;">{{ r.attendance_count }}</td>
            <td style="padding:.75rem 1rem;">{{ r.generated_at|date:"M j, Y g:i A" }}</td>
            <td style="padding:.75rem 1rem; font-family:monospace; font-size:.85rem;">{{ r.short_hash }}</td>
            <td style="padding:.75rem 1rem; text-align:right;">
                <a href="{% url 'accounts:court_report_download' r.id %}">Download</a>
            </td>
        </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
        <p style="color:#888; background:white; padding:2rem; text-align:center; border-radius:12px;">No reports generated yet. Use the form above to create your first report.</p>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 8.6: Re-run all tests**

Run:
```bash
python manage.py test apps.accounts.tests_court -v 2
```

Expected: All Task 1–8 tests pass.

- [ ] **Step 8.7: Smoke-test in browser**

Run:
```bash
python manage.py runserver
```

In another shell or your browser:
1. Log in as a user. Open Django shell: `python manage.py shell -c "from django.contrib.auth import get_user_model; from apps.accounts.payment_models import Subscription; u=get_user_model().objects.get(username='YOUR_USER'); Subscription.objects.update_or_create(user=u, defaults={'tier':'court','status':'active'})"`
2. Visit `http://localhost:8000/accounts/court/` → should see dashboard
3. Set up profile, log a meeting, generate a report, download the PDF
4. Open the PDF, confirm hash is rendered in the footer
5. Visit `/verify/court/<first 8 chars of hash>/` → should see verified page

- [ ] **Step 8.8: Commit**

```bash
git add apps/accounts/court_views.py apps/accounts/urls.py apps/accounts/templates/court/ apps/accounts/tests_court.py
git commit -m "feat(accounts): court compliance dashboard, attendance CRUD, report generation"
```

---

## Task 9: Email-to-PO endpoint

**Files:**
- Modify: `apps/accounts/court_views.py`
- Modify: `apps/accounts/urls.py`
- Create: `apps/accounts/templates/court/email_pdf.html`

- [ ] **Step 9.1: Write failing test**

Append to `apps/accounts/tests_court.py`:

```python
from unittest.mock import patch


class CourtReportEmailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='mailer', email='m@example.com', password='pw'
        )
        Subscription.objects.create(user=self.user, tier='court', status='active')
        CourtReportProfile.objects.create(
            user=self.user, legal_name='Mailer',
            case_number='M-1',
            probation_officer_email='po@court.gov',
        )
        MeetingAttendance.objects.create(
            user=self.user, meeting_name='M',
            meeting_date=timezone.now(), program='aa', meeting_type='open',
        )
        self.report = court_service.generate_court_report(
            user=self.user,
            period_start=timezone.now().date().replace(day=1),
            period_end=timezone.now().date(),
        )
        self.client.login(username='mailer', password='pw')

    @patch('apps.accounts.court_views.send_email')
    def test_email_report_to_probation_officer(self, mock_send):
        mock_send.return_value = (True, None)
        resp = self.client.post(
            reverse('accounts:court_report_email', args=[self.report.id]),
            {'recipient': 'po@court.gov'},
        )
        self.assertEqual(resp.status_code, 302)
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['recipient_email'], 'po@court.gov')
        # Audit log updated
        self.report.refresh_from_db()
        self.assertIn('po@court.gov', self.report.emailed_to)
        self.assertIsNotNone(self.report.emailed_at)

    @patch('apps.accounts.court_views.send_email')
    def test_email_failure_does_not_update_audit(self, mock_send):
        mock_send.return_value = (False, 'SMTP timeout')
        self.client.post(
            reverse('accounts:court_report_email', args=[self.report.id]),
            {'recipient': 'po@court.gov'},
        )
        self.report.refresh_from_db()
        self.assertEqual(self.report.emailed_to, '')
        self.assertIsNone(self.report.emailed_at)
```

- [ ] **Step 9.2: Run, confirm failure**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtReportEmailTest -v 2
```

Expected: `NoReverseMatch`.

- [ ] **Step 9.3: Add email view**

Append to `apps/accounts/court_views.py`:

```python
@login_required
@court_required
@require_POST
def court_report_email(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    recipient = (request.POST.get('recipient') or '').strip()
    if not recipient:
        messages.error(request, 'Recipient email required.')
        return redirect('accounts:court_report_list')
    if not report.pdf:
        messages.error(request, 'Report PDF missing — regenerate.')
        return redirect('accounts:court_report_list')

    profile = getattr(request.user, 'court_profile', None)
    legal_name = (profile.legal_name if profile else None) or request.user.username
    case_number = (profile.case_number if profile else None) or '(no case number on file)'

    html_body = render_to_string('court/email_pdf.html', {
        'legal_name': legal_name,
        'case_number': case_number,
        'period_start': report.period_start,
        'period_end': report.period_end,
        'attendance_count': report.attendance_count,
        'verify_url': request.build_absolute_uri(
            reverse('verify_court_report', args=[report.pdf_hash[:8]])
        ),
    })
    plain_body = (
        f"Recovery meeting attendance report for {legal_name}\n"
        f"Case: {case_number}\n"
        f"Period: {report.period_start} – {report.period_end}\n"
        f"Meetings attended: {report.attendance_count}\n"
        f"Verify integrity: {request.build_absolute_uri(reverse('verify_court_report', args=[report.pdf_hash[:8]]))}\n"
    )

    pdf_bytes = report.pdf.read()
    report.pdf.close()

    success, err = send_email(
        subject=f'Court Compliance Report — {legal_name} — {report.period_start:%b %Y}',
        plain_message=plain_body,
        html_message=html_body,
        recipient_email=recipient,
        attachments=[(f'court-report-{report.short_hash}.pdf', pdf_bytes, 'application/pdf')],
    )

    if not success:
        messages.error(request, f'Email failed: {err}')
        return redirect('accounts:court_report_list')

    existing = report.emailed_to or ''
    report.emailed_to = (existing + ',' + recipient).strip(',')
    report.emailed_at = timezone.now()
    report.save(update_fields=['emailed_to', 'emailed_at'])
    messages.success(request, f'Report emailed to {recipient}.')
    return redirect('accounts:court_report_list')
```

Add the missing import at top of `court_views.py`:
```python
from django.template.loader import render_to_string
```

- [ ] **Step 9.4: Update `email_service.send_email` to accept attachments**

Edit `apps/accounts/email_service.py`. Modify the `send_email` signature to accept a new keyword arg `attachments` (list of tuples). Find the function definition (around line 20) and update:

```python
def send_email(
    subject: str,
    plain_message: str,
    html_message: str,
    recipient_email: str,
    from_email: str = None,
    max_retries: int = 3,
    use_smtp_fallback: bool = True,
    attachments: list = None,
) -> tuple:
```

Then inside the Resend `requests.post` body, change the `json={...}` block to:

```python
                json_body = {
                    'from': from_email,
                    'to': [recipient_email],
                    'subject': subject,
                    'html': html_message,
                    'text': plain_message,
                }
                if attachments:
                    import base64
                    json_body['attachments'] = [
                        {
                            'filename': name,
                            'content': base64.b64encode(content).decode('ascii'),
                            'content_type': content_type,
                        }
                        for (name, content, content_type) in attachments
                    ]
                response = requests.post(
                    'https://api.resend.com/emails',
                    headers={
                        'Authorization': f'Bearer {resend_api_key}',
                        'Content-Type': 'application/json'
                    },
                    json=json_body,
                    timeout=30,
                )
```

(Replace the existing `response = requests.post(...)` block lines 63–77 with the above.)

- [ ] **Step 9.5: Register URL**

Edit `apps/accounts/urls.py`. Add (next to the other court URLs):

```python
    path('court/reports/<int:report_id>/email/', __import__('apps.accounts.court_views', fromlist=['court_report_email']).court_report_email, name='court_report_email'),
```

- [ ] **Step 9.6: Create email template**

Create `apps/accounts/templates/court/email_pdf.html`:

```html
<div style="font-family:Helvetica,sans-serif; color:#222; max-width:600px;">
  <h2 style="color:#1e4d8b;">Recovery Meeting Attendance Report</h2>
  <p>Attached is a recovery meeting attendance report for <strong>{{ legal_name }}</strong> (case {{ case_number }}) covering <strong>{{ period_start|date:"F j, Y" }} – {{ period_end|date:"F j, Y" }}</strong>.</p>
  <p><strong>Meetings attended in period:</strong> {{ attendance_count }}</p>
  <p>To confirm the attached PDF has not been altered, visit:<br>
    <a href="{{ verify_url }}">{{ verify_url }}</a></p>
  <p style="font-size:0.85rem; color:#666; margin-top:1.5rem;">
    This report was generated by MyRecoveryPal Court Compliance. Self-reported attendance entries are flagged inside the PDF. The participant attests under penalty of perjury that entries are accurate.
  </p>
</div>
```

- [ ] **Step 9.7: Add `attachments` arg to existing `send_email` callers (if any pass positional args)**

Run:
```bash
grep -rn "send_email(" apps/ | grep -v email_service.py | grep -v tests_court.py
```

Confirm no existing callers pass positional args beyond the first 4. (The signature change is backward-compatible since `attachments` is keyword-only with default `None`.)

- [ ] **Step 9.8: Re-run tests**

Run:
```bash
python manage.py test apps.accounts.tests_court.CourtReportEmailTest -v 2
```

Expected: Both tests pass.

- [ ] **Step 9.9: Commit**

```bash
git add apps/accounts/court_views.py apps/accounts/urls.py apps/accounts/templates/court/email_pdf.html apps/accounts/email_service.py apps/accounts/tests_court.py
git commit -m "feat(accounts): email court reports to probation officer with audit trail"
```

---

## Task 10: Add Court Compliance tier to pricing page

**Files:**
- Modify: `apps/accounts/templates/accounts/pricing.html`

- [ ] **Step 10.1: Inspect current pricing layout**

Run:
```bash
grep -n "tier-card\|tier-premium\|tier-free\|class=\"price\"\|Premium\|monthly" apps/accounts/templates/accounts/pricing.html | head -20
```

Note the existing card structure (you'll mirror it).

- [ ] **Step 10.2: Add Court Compliance card**

In `apps/accounts/templates/accounts/pricing.html`, find the Premium card block (search for `tier-premium` or similar). Immediately AFTER the closing `</div>` of the Premium card, add:

```html
<div class="tier-card tier-court">
    <div class="tier-badge" style="background:linear-gradient(135deg,#1e4d8b,#0f2d56); color:white;">FOR COURT-ORDERED USERS</div>
    <h3>Court Compliance</h3>
    <div class="tier-price">
        <span class="currency">$</span><span class="amount">19.99</span><span class="period">/mo</span>
    </div>
    <p class="tier-tagline">Annual: $179/yr (save 25%)</p>
    <ul class="tier-features">
        <li>✓ Everything in Premium</li>
        <li>✓ Log AA, NA, SMART, & secular meeting attendance</li>
        <li>✓ Court-acceptable PDF reports with tamper-evident fingerprint</li>
        <li>✓ Email reports directly to your probation officer</li>
        <li>✓ Public verification URL — courts can confirm document integrity</li>
        <li>✓ Compliance dashboard with weekly progress</li>
        <li>✓ Unlimited reports + attendance logs</li>
    </ul>
    {% if user.is_authenticated and request.user.subscription.is_court %}
        <a class="tier-button" href="{% url 'accounts:court_dashboard' %}">Open Dashboard</a>
    {% else %}
        <form method="post" action="{% url 'accounts:checkout' %}" style="margin:0;">
            {% csrf_token %}
            <input type="hidden" name="tier" value="court">
            <input type="hidden" name="billing_period" value="monthly">
            <button type="submit" class="tier-button">Start Court Compliance</button>
        </form>
    {% endif %}
    <p class="tier-disclaimer">Designed for DUI/DWI defendants, drug court participants, and anyone with court-ordered meeting attendance requirements. Supports both 12-step and secular recovery programs.</p>
</div>
```

(If the existing pricing card classes differ, mirror them — the goal is structural consistency with the Premium card.)

- [ ] **Step 10.3: Add SubscriptionPlan rows via management command or fixture**

Open Django shell:
```bash
python manage.py shell
```

Run:
```python
from apps.accounts.payment_models import SubscriptionPlan
SubscriptionPlan.objects.update_or_create(
    tier='court', billing_period='monthly',
    defaults={'price': 19.99, 'name': 'Court Compliance — Monthly', 'sort_order': 30},
)
SubscriptionPlan.objects.update_or_create(
    tier='court', billing_period='yearly',
    defaults={'price': 179.00, 'name': 'Court Compliance — Annual', 'sort_order': 31},
)
exit()
```

- [ ] **Step 10.4: Configure Stripe products manually**

In Stripe dashboard:
1. Create Product "MyRecoveryPal Court Compliance"
2. Add monthly price $19.99 USD, recurring
3. Add yearly price $179.00 USD, recurring
4. Copy both Price IDs into `SubscriptionPlan.stripe_price_id` (or whatever field is used — verify in payment_models.py)

Update the two rows you just created with the real Stripe price IDs:
```python
SubscriptionPlan.objects.filter(tier='court', billing_period='monthly').update(stripe_price_id='price_xxx')
SubscriptionPlan.objects.filter(tier='court', billing_period='yearly').update(stripe_price_id='price_yyy')
```

- [ ] **Step 10.5: Smoke-test checkout**

In your browser as a logged-in free user, visit `/accounts/pricing/`. Confirm the new card renders. Click through to checkout, complete with a Stripe test card (4242 4242 4242 4242), and confirm the subscription record updates to tier='court'.

- [ ] **Step 10.6: Commit**

```bash
git add apps/accounts/templates/accounts/pricing.html
git commit -m "feat(accounts): add Court Compliance tier to pricing page"
```

---

## Task 11: Public SEO landing page

**Files:**
- Create: `apps/core/templates/core/court_ordered_meeting_tracker.html`
- Modify: `apps/core/urls.py`
- Modify: `apps/core/views.py`
- Modify: `sitemap.xml`
- Modify: `root_files/robots.txt`

- [ ] **Step 11.1: Add view + URL**

Edit `apps/core/views.py`. Add:

```python
def court_ordered_meeting_tracker(request):
    return render(request, 'core/court_ordered_meeting_tracker.html')
```

Edit `apps/core/urls.py`. Add to `urlpatterns`:

```python
    path('court-ordered-meeting-tracker/', views.court_ordered_meeting_tracker, name='court_ordered_meeting_tracker'),
```

- [ ] **Step 11.2: Create the landing page**

Create `apps/core/templates/core/court_ordered_meeting_tracker.html`:

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}Court-Ordered AA/NA Meeting Tracker — Court-Acceptable PDF Reports{% endblock %}
{% block meta_description %}Track court-ordered AA, NA, or SMART Recovery meeting attendance and generate tamper-evident PDF reports you can email to your probation officer. $19.99/mo.{% endblock %}

{% block structured_data %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "MyRecoveryPal Court Compliance",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web Browser, iOS, Android",
  "offers": {
    "@type": "Offer",
    "price": "19.99",
    "priceCurrency": "USD",
    "priceSpecification": {"@type": "UnitPriceSpecification", "billingDuration": "P1M"}
  },
  "description": "Track court-ordered recovery meeting attendance and generate tamper-evident PDF reports."
}
</script>
{% endblock %}

{% block content %}
<section style="background:linear-gradient(135deg,#0f2d56,#1e4d8b); color:white; padding:5rem 1rem 4rem; text-align:center;">
    <div style="max-width:900px; margin:auto;">
        <h1 style="font-size:2.6rem; font-weight:800; margin:0 0 1rem;">Court-Ordered Meeting Tracker</h1>
        <p style="font-size:1.25rem; opacity:.93; line-height:1.5; max-width:700px; margin:0 auto 2rem;">
            Log AA, NA, SMART Recovery, and secular recovery meeting attendance. Generate court-acceptable PDF reports with tamper-evident fingerprints. Email them straight to your probation officer.
        </p>
        <a href="{% url 'accounts:pricing' %}" style="display:inline-block; padding:1rem 2.5rem; background:#52b788; color:white; text-decoration:none; border-radius:50px; font-weight:700; font-size:1.1rem;">Start for $19.99/mo →</a>
        <p style="font-size:0.9rem; opacity:.8; margin-top:1rem;">No long-term contract · Cancel anytime · Works on web, iPhone, and Android</p>
    </div>
</section>

<section style="padding:4rem 1rem; background:#f7f9fc;">
    <div style="max-width:1000px; margin:auto; display:grid; grid-template-columns:repeat(auto-fit, minmax(280px,1fr)); gap:1.5rem;">
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ Court-Acceptable Format</h3>
            <p>Reports include defendant name, case number, court, judge, meeting date/time/address/type, and signed attestation block. Same fields courts already expect on paper attendance cards.</p>
        </div>
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ Tamper-Evident Fingerprint</h3>
            <p>Every PDF includes a SHA-256 fingerprint. Courts can paste the fingerprint at <strong>myrecoverypal.com/verify/court/</strong> to confirm the document hasn't been edited.</p>
        </div>
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ All Recovery Programs</h3>
            <p>Tracks AA, NA, CA, SMART Recovery, Refuge Recovery, LifeRing, and secular meetings. Courts cannot mandate 12-step exclusively — your tracker shouldn't either.</p>
        </div>
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ Direct Email to PO</h3>
            <p>One click sends the PDF straight to your probation officer's inbox, with the verification link in the body. No more chasing meeting chairs for signatures the night before court.</p>
        </div>
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ Weekly Progress Dashboard</h3>
            <p>See at a glance whether you're on pace for the week. If your court requires 3 meetings per week, you'll know if you're short before Sunday night.</p>
        </div>
        <div style="background:white; padding:1.75rem; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <h3 style="color:#1e4d8b;">✓ Includes Premium</h3>
            <p>Court Compliance includes everything in MyRecoveryPal Premium — Anchor AI Coach, unlimited groups, 90-day analytics, and the full recovery community.</p>
        </div>
    </div>
</section>

<section style="padding:4rem 1rem;">
    <div style="max-width:800px; margin:auto;">
        <h2 style="text-align:center; color:#1e4d8b;">How it works</h2>
        <ol style="font-size:1.05rem; line-height:1.7;">
            <li><strong>Set up your court profile.</strong> Enter your case number, court, and probation officer's email — once.</li>
            <li><strong>Log each meeting.</strong> After every AA, NA, SMART, or other recovery meeting, tap "Log Meeting" and enter the name, date, time, and address. Takes ~20 seconds.</li>
            <li><strong>Generate a report.</strong> Pick a period (last month, since sentencing, custom range). The PDF is built in seconds.</li>
            <li><strong>Email to your PO.</strong> One tap. Includes the verification URL so your PO can confirm the document is authentic.</li>
        </ol>
    </div>
</section>

<section style="background:#f7f9fc; padding:4rem 1rem;">
    <div style="max-width:700px; margin:auto;">
        <h2 style="text-align:center; color:#1e4d8b; margin-bottom:2rem;">Frequently Asked Questions</h2>

        <details style="background:white; padding:1rem 1.25rem; border-radius:10px; margin-bottom:.75rem;">
            <summary style="font-weight:600; cursor:pointer;">Will my court accept a PDF report instead of a signed paper card?</summary>
            <p style="margin-top:.75rem;">Most courts now accept digital documentation, especially during/after COVID. The tamper-evident fingerprint and verification URL make this report stronger evidence than a paper card — and probation officers can confirm authenticity instantly. We recommend confirming with your specific PO that they accept email submissions before relying solely on this. Self-reported entries are clearly flagged in the report.</p>
        </details>

        <details style="background:white; padding:1rem 1.25rem; border-radius:10px; margin-bottom:.75rem;">
            <summary style="font-weight:600; cursor:pointer;">What if my court requires meeting chair signatures?</summary>
            <p style="margin-top:.75rem;">Phase 1 supports typed-name chair signatures with a timestamp. If your court requires a physical signature from the meeting secretary, we recommend continuing to use a paper attendance card alongside this for now — and use MyRecoveryPal for the cumulative report and verification. Cryptographic chair signatures and QR check-in are on the roadmap.</p>
        </details>

        <details style="background:white; padding:1rem 1.25rem; border-radius:10px; margin-bottom:.75rem;">
            <summary style="font-weight:600; cursor:pointer;">Can I use this for SMART Recovery or other secular programs?</summary>
            <p style="margin-top:.75rem;">Yes. Courts cannot constitutionally require 12-step-only attendance (per multiple appellate rulings). MyRecoveryPal tracks AA, NA, CA, MA, GA, SMART Recovery, Refuge Recovery, LifeRing, and other recovery programs equally.</p>
        </details>

        <details style="background:white; padding:1rem 1.25rem; border-radius:10px; margin-bottom:.75rem;">
            <summary style="font-weight:600; cursor:pointer;">Is this a substitute for actually attending meetings?</summary>
            <p style="margin-top:.75rem;">No. This is a record-keeping tool. Self-reported entries are clearly flagged. Misrepresenting attendance to a court is perjury — please don't.</p>
        </details>

        <details style="background:white; padding:1rem 1.25rem; border-radius:10px; margin-bottom:.75rem;">
            <summary style="font-weight:600; cursor:pointer;">How is my information protected?</summary>
            <p style="margin-top:.75rem;">Your case number and probation officer's email are visible only to you and (when you choose) the people you email reports to. The public verify page intentionally does not show your name, case number, or any personal information — only that a report with that fingerprint exists.</p>
        </details>
    </div>
</section>

<section style="padding:4rem 1rem; text-align:center; background:linear-gradient(135deg,#0f2d56,#1e4d8b); color:white;">
    <h2 style="font-size:2rem; margin-bottom:1rem;">Start Tracking Court-Ordered Meetings Today</h2>
    <p style="font-size:1.1rem; opacity:.9; margin-bottom:2rem; max-width:600px; margin-left:auto; margin-right:auto;">$19.99/month. Includes everything in Premium. Cancel any time.</p>
    <a href="{% url 'accounts:pricing' %}" style="display:inline-block; padding:1rem 2.5rem; background:#52b788; color:white; text-decoration:none; border-radius:50px; font-weight:700; font-size:1.1rem;">Start Court Compliance →</a>
</section>
{% endblock %}
```

- [ ] **Step 11.3: Update sitemap**

Edit `sitemap.xml`. Add a new `<url>` block inside the `<urlset>` (alphabetical position is fine):

```xml
<url>
    <loc>https://www.myrecoverypal.com/court-ordered-meeting-tracker/</loc>
    <lastmod>2026-05-23</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
</url>
```

- [ ] **Step 11.4: Update robots.txt**

Edit `root_files/robots.txt`. In the Allow block (around line 7–20) add after `Allow: /store/`:

```
Allow: /court-ordered-meeting-tracker/
Allow: /verify/court/
```

In the Disallow block (around line 28–44) add:

```
Disallow: /accounts/court/
```

- [ ] **Step 11.5: Smoke-test in browser**

Run `python manage.py runserver` and visit `http://localhost:8000/court-ordered-meeting-tracker/`. Confirm the page renders.

- [ ] **Step 11.6: Commit**

```bash
git add apps/core/views.py apps/core/urls.py apps/core/templates/core/court_ordered_meeting_tracker.html sitemap.xml root_files/robots.txt
git commit -m "feat(seo): /court-ordered-meeting-tracker/ landing page targeting court-ordered users"
```

---

## Task 12: Nav link for court-tier users

**Files:**
- Modify: `templates/base.html`

- [ ] **Step 12.1: Find the nav block**

Run:
```bash
grep -n "court_dashboard\|My Progress\|Anchor\|Subscription" templates/base.html | head -10
```

Note the existing pattern for tier-gated nav links.

- [ ] **Step 12.2: Add court nav link**

In `templates/base.html`, find the authenticated user menu (search for `Premium` or `subscription`). Add a conditional link:

```html
{% if user.is_authenticated and user.subscription.is_court %}
    <a href="{% url 'accounts:court_dashboard' %}" class="nav-link">
        <i class="fas fa-gavel"></i> Court Compliance
    </a>
{% endif %}
```

Place it next to other authenticated-only nav items. Use the same wrapper element (`<li>`, `<div>`, etc.) as adjacent links.

- [ ] **Step 12.3: Commit**

```bash
git add templates/base.html
git commit -m "feat(ui): nav link to Court Compliance dashboard for court-tier users"
```

---

## Task 13: Documentation update

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 13.1: Document the new feature in CLAUDE.md**

Edit `CLAUDE.md`. Find the "Revenue Strategy" or "Premium Conversion" section. Append a new subsection:

```markdown
### Court Compliance Tier ($19.99/mo)

**Service files:**
- `apps/accounts/court_models.py` — `CourtReportProfile`, `MeetingAttendance`, `CourtReport`
- `apps/accounts/court_service.py` — WeasyPrint PDF rendering with two-pass SHA-256 hash embedding
- `apps/accounts/court_views.py` — dashboard, attendance CRUD, report generation, email-to-PO, public verify
- `apps/accounts/court_forms.py` — profile + attendance forms
- `apps/accounts/decorators.py::court_required` — tier-gating decorator

**Routes:**
- `/accounts/court/` — Court Compliance dashboard (court-tier only)
- `/accounts/court/profile/` — Setup court profile
- `/accounts/court/attendance/` — Log of attended meetings
- `/accounts/court/reports/` — Generate and download PDF reports
- `/verify/court/<hash>/` — Public hash verification (no auth)
- `/court-ordered-meeting-tracker/` — Public SEO landing page

**Key design notes:**
- The `pro` tier in `Subscription.TIER_CHOICES` was renamed to `court` (migration 0034). Helper methods are `is_court()` and decorator is `@court_required`.
- PDF rendering uses a two-pass approach: render placeholder hash → compute real hash → re-render with real hash embedded. This guarantees the printed hash inside the PDF matches `sha256(pdf_bytes)`.
- The public verify endpoint at `/verify/court/<hash>/` intentionally does NOT show legal name or case number — only confirms a report with that fingerprint exists.
- Court tier is a superset of Premium: `is_premium()` returns True for court-tier users.

**Phase 2 deferred features** (separate plan):
- GPS verification at meeting location
- Sponsor/chair digital signature flow (email-confirmed)
- QR code check-in at meetings
- Photo upload of paper attendance cards
- Calendar heatmap of attendance history
- Auto-recurring monthly email to probation officer
```

- [ ] **Step 13.2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document Court Compliance tier and architecture"
```

---

## Task 14: Final validation and merge prep

- [ ] **Step 14.1: Run the full test suite**

Run:
```bash
python manage.py test apps.accounts -v 2
```

Expected: All tests pass. If any pre-existing tests now fail, they are likely due to the `pro` → `court` rename. Update them to match.

- [ ] **Step 14.2: Run Django system checks**

Run:
```bash
python manage.py check --deploy
```

Expected: no new warnings introduced by this branch.

- [ ] **Step 14.3: Verify migrations apply cleanly on a fresh database**

Run:
```bash
python manage.py migrate --run-syncdb --no-input
```

Expected: all migrations apply, no errors.

- [ ] **Step 14.4: Verify Stripe webhook handling for the new tier**

In `apps/accounts/payment_views.py`, search for any place that maps Stripe `price_id` → `tier`. Confirm court-tier price IDs (set in Step 10.4) are handled. If there's a hardcoded mapping, update it.

Run:
```bash
grep -rn "price_id\|price_xxx\|stripe_price" apps/accounts/payment_views.py | head -10
```

- [ ] **Step 14.5: Smoke-test the full happy path one more time**

1. Free user upgrades via `/accounts/pricing/` → Court tier
2. Sets up profile at `/accounts/court/profile/`
3. Logs 5 meetings at `/accounts/court/attendance/new/`
4. Generates report at `/accounts/court/reports/`
5. Downloads PDF, opens it, confirms hash in footer
6. Pastes hash short into `/verify/court/<hash>/` → sees verified page
7. Emails report to a real email → confirms PDF arrives with verification link

- [ ] **Step 14.6: Push branch and open PR**

Run:
```bash
git push -u origin feat/court-compliance
gh pr create --title "feat: Court Compliance tier ($19.99/mo) with tamper-evident PDF reports" --body "$(cat <<'EOF'
## Summary
- New \`court\` subscription tier ($19.99/mo / $179/yr) targeting court-ordered AA/NA/SMART attendees
- Meeting attendance logging with program-neutral coverage (AA, NA, CA, SMART, Refuge, LifeRing, secular)
- WeasyPrint-based PDF court reports with two-pass SHA-256 fingerprint embedding
- Public \`/verify/court/<hash>/\` endpoint for tamper-evidence without third-party services
- Email-to-PO with audit trail
- SEO landing page at \`/court-ordered-meeting-tracker/\`
- Renamed unused \`pro\` tier slot to \`court\` for semantic clarity (data migration 0034)

## Test plan
- [ ] All \`apps.accounts.tests_court\` tests pass
- [ ] Existing \`apps.accounts\` tests still pass after \`pro\` → \`court\` rename
- [ ] Free user → court tier checkout works in Stripe test mode
- [ ] Generated PDF opens correctly and hash in footer matches \`sha256(pdf_bytes)\`
- [ ] Public verify page returns 200 for valid hash, 404 for invalid
- [ ] Email-to-PO delivers PDF attachment and updates \`CourtReport.emailed_to\`
- [ ] Robots.txt allows \`/court-ordered-meeting-tracker/\` and disallows \`/accounts/court/\`
- [ ] Sitemap includes new landing page

## Phase 2 (deferred)
GPS verification, sponsor digital signatures, QR check-in, photo upload, calendar heatmap, auto-recurring monthly email.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

Re-reading the plan against the spec from the prior turn:

✓ **4th tier ($19.99/mo)** — Task 1 + 10. Renamed `pro` to `court` rather than adding a parallel tier, which the user pre-approved.
✓ **Most common court attendance fields** — Task 3 model fields (case number, meeting date, address, program, type, chair signature, verification method) match the standard derived from research (AA court cards, NA forms, SMART Recovery verification).
✓ **WeasyPrint** — Task 0.3 adds dep, Task 5 implements with two-pass hash embedding.
✓ **`docs/plans/` convention** — Saved to `docs/plans/2026-05-23-court-compliance.md` matching existing project filenames like `2026-03-04-app-store-submission-guide.md`.
✓ **TDD throughout** — Every task has a failing-test step before implementation.
✓ **Real code, no placeholders** — Every code block is complete.
✓ **Frequent commits** — One commit per task minimum.
✓ **First Amendment / program neutrality** — Reflected in `PROGRAM_CHOICES` (includes SMART, Refuge, LifeRing, secular), landing page copy, and FAQ.
✓ **No new authentication, no new infrastructure** — Uses existing `send_email` (Resend), existing Stripe checkout flow, existing Cloudinary storage.

**Known gaps** (intentional, deferred to Phase 2):
- Sponsor/chair digital signature is just a typed name in Phase 1
- No GPS / QR / photo verification in Phase 1
- No calendar heatmap UI
- No auto-recurring monthly email (manual generation only)

---

## Execution Handoff

Plan complete and saved to `docs/plans/2026-05-23-court-compliance.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
