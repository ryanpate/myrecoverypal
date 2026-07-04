# Daily Pledge (Phase 2 Retention Engine) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the pledge idea into the app's daily retention ritual — a prominent, one-tap "I pledge to stay sober today" card at the top of the progress home, anchored to the user's own photo + personal reason, showing a pledge streak they emotionally own.

**Architecture:** A dedicated tiny `DailyPledge` model (one row per user per day) is the single source of truth for "pledged today" and the pledge streak — kept **separate from `DailyCheckIn`** so a one-tap pledge never pollutes the mood/craving analytics and the pledge streak stays distinct from the check-in streak (design decision 2026-07-03). Add two User fields (`pledge_reason`, `pledge_photo`) captured in onboarding and editable in profile. Add `User.get_pledge_streak()` reading `DailyPledge`. Add a lightweight AJAX `pledge_today` endpoint so pledging is one tap, and record a `DailyPledge` when the full check-in form's pledge box is ticked so both paths agree.

**Tech Stack:** Django 5.0.10, PostgreSQL, Cloudinary (prod media for `pledge_photo`, same backend as `avatar`), vanilla JS + fetch for the AJAX pledge, Capacitor haptics on mobile (optional confirm).

**Parent roadmap:** `docs/plans/2026-07-03-revenue-roadmap.md` (Phase 2). This is the "detailed sub-plan" that phase points to. Chosen scope: **Full — dedicated reason + pledge photo** (decided 2026-07-03).

## Global Constraints

- Match existing repo style: function-based views in `apps/accounts/views.py`, plain `request.POST` reads (no DRF), feature test file `apps/accounts/tests_pledge.py` (mirrors `tests_court.py`). Use `python3` to run commands; run tests locally (no `SENTRY_DSN`) — never `railway run` (prod env crashes on an eventlet/sentry conflict).
- **Never gate the pledge behind Premium.** The pledge, streak, and counter are free forever (roadmap guardrail — paywall protects the asset, never the asset itself).
- **The pledge is stored in `DailyPledge`, NOT by mutating `DailyCheckIn`.** A one-tap pledge must never create or alter a `DailyCheckIn` row (that would inject placeholder mood/energy into the analytics and conflate the two streaks).
- The pledge is a **once-per-day** action; enforce via `DailyPledge` `unique_together = ['user','date']`. Pledging must be idempotent within a day (`get_or_create`).
- `pledge_photo` is optional; the card falls back to `avatar`, then to a default asset. `pledge_reason` is optional; the card falls back to `recovery_goals`, then to generic copy. The card must render for a user who set none of them.
- Leave the existing `DailyCheckIn.pledge_taken`/`pledge_time` fields and the pledge card inside `daily_checkin.html` in place (surgical) — but the full check-in view must also upsert a `DailyPledge` when its pledge box is ticked, so the streak counts it.
- Mobile: the home card must work inside the Capacitor WebView (no desktop-only APIs).

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `apps/accounts/models.py` | Modify | Add `DailyPledge` model (near `DailyCheckIn`, ~line 690); add `User.pledge_reason` + `User.pledge_photo` fields (~line 68, near `recovery_goals`); add `User.get_pledge_streak()` reading `daily_pledges` (after `get_checkin_streak()`, ~line 203) |
| `apps/accounts/migrations/00NN_daily_pledge_model.py` | Create (via makemigrations) | `DailyPledge` table |
| `apps/accounts/migrations/00NN_add_pledge_fields.py` | Create (via makemigrations) | `pledge_reason` + `pledge_photo` on User |
| `apps/accounts/views.py` | Modify | Add `pledge_today` AJAX view; upsert `DailyPledge` in `daily_checkin_view` when pledge ticked; add pledge context to `progress_view` (~line 1185); capture pledge fields in `onboarding_view` step 3 (~line 281); redirect onboarding completion to `accounts:progress` (line 286) |
| `apps/accounts/urls.py` | Modify | Add `pledge-today/` route |
| `apps/accounts/forms.py` | Modify | Add `pledge_reason` + `pledge_photo` to `UserProfileForm.Meta.fields` + help_texts (~line 217) |
| `apps/accounts/templates/accounts/progress.html` | Modify | Add the pledge card at the top of the page |
| `apps/accounts/templates/accounts/onboarding.html` | Modify | Add pledge_reason + pledge_photo inputs to step 3 |
| `apps/accounts/templates/accounts/edit_profile.html` | Modify | Render the new form fields |
| `apps/accounts/tests_pledge.py` | Create | Test suite for model, streak, endpoint, form, onboarding, context |

**Key design decisions locked in:**
1. **Dedicated `DailyPledge` model** (`user`, `date`, `created_at`, `unique_together=['user','date']`). It is the single source of "pledged today" and the pledge streak. Chosen over reusing `DailyCheckIn.pledge_taken` because `DailyCheckIn.mood`/`energy_level` are required (no default) and feed the mood analytics — a one-tap pledge reusing that model would force placeholder mood data and merge the check-in/pledge streaks (decided with the founder 2026-07-03).
2. **Pledge streak ≠ check-in streak.** `get_pledge_streak()` counts consecutive `DailyPledge` days; `get_checkin_streak()` is untouched.
3. **Two write paths, one store.** The one-tap `pledge_today` endpoint and the full check-in form (when its pledge box is ticked) both upsert the same `DailyPledge` row, so the streak is consistent however the user pledges.
4. **Onboarding completion lands on `accounts:progress`** (the pledge home), not `social_feed` — serves the Phase 2 "solo home is the front door" goal.

---

## Task 1: `DailyPledge` model + `User.get_pledge_streak()`

> **Execution note (2026-07-03):** An earlier build of this task added `get_pledge_streak()` reading `DailyCheckIn.pledge_taken` (commit `65f54441`) before the `DailyPledge` decision. This task now supersedes it: add the model and repoint the method + tests to `DailyPledge`. Deliver as a new commit on top (do not rewrite history).

**Files:**
- Modify: `apps/accounts/models.py` (add `DailyPledge` near `DailyCheckIn` ~line 690; rewrite `get_pledge_streak()` ~line 204)
- Create: `apps/accounts/migrations/00NN_daily_pledge_model.py` (via makemigrations)
- Test: `apps/accounts/tests_pledge.py` (rewrite `PledgeStreakTests` to use `DailyPledge`)

**Interfaces:**
- Produces: `DailyPledge(user FK related_name='daily_pledges', date DateField default=timezone.now, created_at auto_now_add)` with `unique_together=['user','date']`.
- Produces: `User.get_pledge_streak() -> int` — consecutive days ending today or yesterday with a `DailyPledge`.

- [ ] **Step 1: Rewrite the failing tests** to use `DailyPledge`

```python
# apps/accounts/tests_pledge.py
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.accounts.models import DailyPledge

User = get_user_model()


class PledgeStreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ren', password='x')

    def _pledge_on(self, d):
        DailyPledge.objects.create(user=self.user, date=d)

    def test_no_pledges_is_zero(self):
        self.assertEqual(self.user.get_pledge_streak(), 0)

    def test_today_only_is_one(self):
        self._pledge_on(timezone.now().date())
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_three_consecutive_days(self):
        today = timezone.now().date()
        for i in range(3):
            self._pledge_on(today - timedelta(days=i))
        self.assertEqual(self.user.get_pledge_streak(), 3)

    def test_gap_breaks_streak(self):
        today = timezone.now().date()
        self._pledge_on(today)
        self._pledge_on(today - timedelta(days=2))
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_yesterday_only_still_active(self):
        self._pledge_on(timezone.now().date() - timedelta(days=1))
        self.assertEqual(self.user.get_pledge_streak(), 1)

    def test_one_pledge_per_day(self):
        d = timezone.now().date()
        self._pledge_on(d)
        obj, created = DailyPledge.objects.get_or_create(user=self.user, date=d)
        self.assertFalse(created)
        self.assertEqual(DailyPledge.objects.filter(user=self.user, date=d).count(), 1)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 manage.py test apps.accounts.tests_pledge.PledgeStreakTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'DailyPledge'`.

- [ ] **Step 3: Add the model** (near `DailyCheckIn`, after its class ends ~line 690)

```python
# apps/accounts/models.py
class DailyPledge(models.Model):
    """A single daily sobriety pledge. One row per user per day. Kept separate
    from DailyCheckIn so a one-tap pledge never touches mood/craving analytics."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='daily_pledges')
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} pledged {self.date}"
```

- [ ] **Step 4: Rewrite `get_pledge_streak()`** to read `DailyPledge` (replace the body added in `65f54441`, ~line 204)

```python
# apps/accounts/models.py — after get_checkin_streak()
    def get_pledge_streak(self):
        """Consecutive days with a DailyPledge ending today or yesterday."""
        from datetime import timedelta
        today = timezone.now().date()
        pledge_dates = set(
            self.daily_pledges.values_list('date', flat=True)
        )
        if not pledge_dates:
            return 0
        if today in pledge_dates:
            streak, current_date = 1, today - timedelta(days=1)
        elif (today - timedelta(days=1)) in pledge_dates:
            streak, current_date = 1, today - timedelta(days=2)
        else:
            return 0
        while current_date in pledge_dates:
            streak += 1
            current_date -= timedelta(days=1)
        return streak
```

- [ ] **Step 5: Make the migration**

Run: `python3 manage.py makemigrations accounts`
Expected: a migration creating `DailyPledge`. Note the generated number.

- [ ] **Step 6: Migrate + run tests green**

Run: `python3 manage.py migrate && python3 manage.py test apps.accounts.tests_pledge.PledgeStreakTests -v 2`
Expected: 6 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/ apps/accounts/tests_pledge.py
git commit -m "feat(pledge): DailyPledge model + get_pledge_streak() reads it"
```

---

## Task 2: `pledge_reason` + `pledge_photo` User fields + migration

**Files:**
- Modify: `apps/accounts/models.py` (~line 68, right after `recovery_goals`)
- Create: `apps/accounts/migrations/00NN_add_pledge_fields.py` (via makemigrations)
- Test: `apps/accounts/tests_pledge.py`

**Interfaces:**
- Produces: `User.pledge_reason: CharField(max_length=120, blank=True)`, `User.pledge_photo: ImageField(upload_to='pledge_photos/', blank=True, null=True)`.

- [ ] **Step 1: Add the fields**

```python
# apps/accounts/models.py — after recovery_goals (~line 68)
    pledge_reason = models.CharField(
        max_length=120, blank=True,
        help_text="A short reason you're staying sober, e.g. 'my daughter'. Shown on your daily pledge.")
    pledge_photo = models.ImageField(
        upload_to='pledge_photos/', blank=True, null=True,
        help_text="Optional photo shown on your daily pledge card.")
```

- [ ] **Step 2: Generate the migration**

Run: `python3 manage.py makemigrations accounts`
Expected: a migration adding the two fields.

- [ ] **Step 3: Write a defaults test**

```python
# apps/accounts/tests_pledge.py
class PledgeFieldDefaultTests(TestCase):
    def test_fields_default_blank(self):
        u = User.objects.create_user(username='a', password='x')
        self.assertEqual(u.pledge_reason, '')
        self.assertFalse(u.pledge_photo)
```

- [ ] **Step 4: Migrate + test**

Run: `python3 manage.py migrate && python3 manage.py test apps.accounts.tests_pledge.PledgeFieldDefaultTests -v 2`
Expected: migration applies; test PASSES.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/ apps/accounts/tests_pledge.py
git commit -m "feat(pledge): add pledge_reason and pledge_photo user fields"
```

---

## Task 3: `pledge_today` endpoint + full-check-in upsert

**Files:**
- Modify: `apps/accounts/views.py` (add `pledge_today` near `quick_checkin` ~line 850; upsert `DailyPledge` in `daily_checkin_view` where it currently sets `pledge_taken` ~line 779-828)
- Modify: `apps/accounts/urls.py` (add route ~line 77)
- Test: `apps/accounts/tests_pledge.py`

**Interfaces:**
- Consumes: `DailyPledge` (Task 1), `User.get_pledge_streak()`.
- Produces: `POST /accounts/pledge-today/` (name `accounts:pledge_today`) → JSON `{"success": true, "pledged": true, "streak": <int>}`. Login required. Idempotent per day.

- [ ] **Step 1: Write the failing tests**

```python
# apps/accounts/tests_pledge.py
from django.urls import reverse
import json


class PledgeTodayEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='p', password='x')
        self.client.force_login(self.user)
        self.url = reverse('accounts:pledge_today')

    def test_first_pledge_creates_row_and_returns_streak(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data['pledged'])
        self.assertEqual(data['streak'], 1)
        self.assertTrue(DailyPledge.objects.filter(
            user=self.user, date=timezone.now().date()).exists())

    def test_pledge_is_idempotent_same_day(self):
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(DailyPledge.objects.filter(user=self.user).count(), 1)

    def test_pledge_does_not_create_a_checkin(self):
        from apps.accounts.models import DailyCheckIn
        self.client.post(self.url)
        self.assertFalse(DailyCheckIn.objects.filter(user=self.user).exists())

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (302, 401, 403))
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 manage.py test apps.accounts.tests_pledge.PledgeTodayEndpointTests -v 2`
Expected: FAIL — `NoReverseMatch: 'pledge_today'`.

- [ ] **Step 3: Add the view**

```python
# apps/accounts/views.py — near quick_checkin (~line 850)
@login_required
@require_POST
def pledge_today(request):
    """One-tap daily pledge. Records a DailyPledge for today (idempotent).
    Deliberately does NOT touch DailyCheckIn / mood analytics."""
    DailyPledge.objects.get_or_create(user=request.user, date=timezone.now().date())
    return JsonResponse({
        'success': True,
        'pledged': True,
        'streak': request.user.get_pledge_streak(),
    })
```

Ensure imports at the top of `views.py`: `from django.views.decorators.http import require_POST`, `from django.http import JsonResponse`, `from django.contrib.auth.decorators import login_required`, `from django.utils import timezone`, and that `DailyPledge` is importable (it's in `apps.accounts.models`; add to the existing models import). Add only what's missing.

- [ ] **Step 4: Upsert on the full check-in path** — in `daily_checkin_view`, where the check-in is created with `pledge_taken` (~line 779-828), after the check-in is saved add:

```python
        if checkin.pledge_taken:
            from .models import DailyPledge
            DailyPledge.objects.get_or_create(user=request.user, date=checkin.date)
```

(Use whatever the local variable for the saved check-in is; match the existing code. This keeps the streak consistent when a user pledges via the full form.)

- [ ] **Step 5: Add the URL**

```python
# apps/accounts/urls.py — near the check-in routes (~line 77)
    path('pledge-today/', views.pledge_today, name='pledge_today'),
```

- [ ] **Step 6: Add a test for the full-form upsert**

```python
# apps/accounts/tests_pledge.py — in a new test class
class FullCheckinPledgeUpsertTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='f', password='x')
        self.client.force_login(self.user)

    def test_checkin_with_pledge_records_dailypledge(self):
        self.client.post(reverse('accounts:daily_checkin'), {
            'mood': '4', 'energy_level': '3', 'craving_level': '0',
            'pledge_taken': 'on',
        })
        self.assertTrue(DailyPledge.objects.filter(user=self.user).exists())
```

(Verify the check-in URL name via `apps/accounts/urls.py` — it may be `daily_checkin`; adjust the `reverse()` name and POST fields to match `daily_checkin_view`'s actual expected inputs. If the view requires other fields, include them so the check-in saves.)

- [ ] **Step 7: Run tests green + commit**

Run: `python3 manage.py test apps.accounts.tests_pledge -v 2`
Expected: all pledge tests PASS.

```bash
git add apps/accounts/views.py apps/accounts/urls.py apps/accounts/tests_pledge.py
git commit -m "feat(pledge): one-tap pledge_today endpoint + full-checkin upsert"
```

---

## Task 4: Surface pledge in `progress_view` context

**Files:**
- Modify: `apps/accounts/views.py` (`progress_view` context block, ~line 1185)
- Test: `apps/accounts/tests_pledge.py`

**Interfaces:**
- Consumes: `User.get_pledge_streak()` (Task 1), `DailyPledge` (Task 1).
- Produces: context keys `pledge_streak: int`, `pledged_today: bool`.

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_pledge.py
class ProgressPledgeContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='c', password='x')
        self.client.force_login(self.user)

    def test_context_has_pledge_keys(self):
        resp = self.client.get(reverse('accounts:progress'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('pledge_streak', resp.context)
        self.assertEqual(resp.context['pledged_today'], False)

    def test_pledged_today_true_after_pledge(self):
        self.client.post(reverse('accounts:pledge_today'))
        resp = self.client.get(reverse('accounts:progress'))
        self.assertTrue(resp.context['pledged_today'])
        self.assertEqual(resp.context['pledge_streak'], 1)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 manage.py test apps.accounts.tests_pledge.ProgressPledgeContextTests -v 2`
Expected: FAIL — missing `pledge_streak`/`pledged_today`.

- [ ] **Step 3: Add the context keys** in `progress_view` (in the `context = {...}` dict, ~line 1185)

```python
        'pledge_streak': user.get_pledge_streak(),
        'pledged_today': DailyPledge.objects.filter(user=user, date=timezone.now().date()).exists(),
```

Ensure `DailyPledge` is imported in `views.py`.

- [ ] **Step 4: Run tests, verify pass; commit**

Run: `python3 manage.py test apps.accounts.tests_pledge.ProgressPledgeContextTests -v 2`
Expected: PASS

```bash
git add apps/accounts/views.py apps/accounts/tests_pledge.py
git commit -m "feat(pledge): expose pledge_streak and pledged_today on progress home"
```

---

## Task 5: The pledge card on the progress home

**Files:**
- Modify: `apps/accounts/templates/accounts/progress.html` (add card at the very top of the content block)

No new automated test (template render covered by Task 4's 200 response). Manual verification below.

- [ ] **Step 1: Add the card markup** at the top of the main content in `progress.html`. Requirements:
  - Show `user.pledge_photo` if set, else `user.avatar` if set, else a default asset `{% static 'images/pledge-default.png' %}`.
  - Heading "I pledge to stay sober today"; reason line uses `user.pledge_reason`, else `user.recovery_goals|truncatewords:8`, else "one day at a time".
  - `🔥 {{ pledge_streak }}-day pledge streak`, hidden when `pledge_streak == 0`.
  - One primary button `#pledgeTodayBtn`; if `pledged_today`, render the fulfilled state instead.

```html
{# top of content block #}
<div class="pledge-card" id="pledgeCard" data-pledged="{{ pledged_today|yesno:'1,0' }}">
  <div class="pledge-photo">
    {% if user.pledge_photo %}<img src="{{ user.pledge_photo.url }}" alt="">
    {% elif user.avatar %}<img src="{{ user.avatar.url }}" alt="">
    {% else %}<img src="{% static 'images/pledge-default.png' %}" alt="">{% endif %}
  </div>
  <div class="pledge-body">
    <h2 class="pledge-title">I pledge to stay sober today</h2>
    <p class="pledge-reason">Staying sober for:
      <strong>{{ user.pledge_reason|default:user.recovery_goals|truncatewords:8|default:"one day at a time" }}</strong>
    </p>
    <p class="pledge-streak" {% if pledge_streak == 0 %}hidden{% endif %}>
      🔥 <span id="pledgeStreakCount">{{ pledge_streak }}</span>-day pledge streak
    </p>
    <button type="button" class="btn btn-primary btn-lg" id="pledgeTodayBtn"
            {% if pledged_today %}hidden{% endif %}>I pledge to stay sober today</button>
    <div class="pledge-done" id="pledgeDone" {% if not pledged_today %}hidden{% endif %}>
      ✅ Pledged today — see you tomorrow.
    </div>
  </div>
</div>
```

Ensure `{% load static %}` is present at the top of the template (add if missing).

- [ ] **Step 2: Wire the button** (inline `<script>`)

```html
<script>
(function () {
  const btn = document.getElementById('pledgeTodayBtn');
  if (!btn) return;
  btn.addEventListener('click', function () {
    btn.disabled = true;
    fetch("{% url 'accounts:pledge_today' %}", {
      method: 'POST',
      headers: {'X-CSRFToken': '{{ csrf_token }}'},
    }).then(r => r.json()).then(data => {
      if (!data.success) { btn.disabled = false; return; }
      const streakEl = document.getElementById('pledgeStreakCount');
      const streakP = document.querySelector('.pledge-streak');
      if (streakEl) streakEl.textContent = data.streak;
      if (streakP) streakP.hidden = false;
      btn.hidden = true;
      const done = document.getElementById('pledgeDone');
      if (done) done.hidden = false;
      if (window.Capacitor && window.MRPNative && window.MRPNative.haptic) {
        window.MRPNative.haptic('success');
      }
    }).catch(() => { btn.disabled = false; });
  });
})();
</script>
```

(Verify the haptic helper name against `static/js/capacitor-native.js`; if different, adjust or drop the haptic call — it's progressive enhancement.)

- [ ] **Step 3: Add a default asset** `static/images/pledge-default.png` (reuse an existing logo/milestone image if one exists; otherwise a simple placeholder). Run `python3 manage.py collectstatic --noinput` locally to confirm it resolves.

- [ ] **Step 4: Manual verification**

Run: `python3 manage.py runserver`, log in, visit `/accounts/progress/`.
Verify: card renders at top; clicking flips to "Pledged today" and shows `🔥 1-day pledge streak`; reload keeps the fulfilled state; a user with no avatar/reason still sees a valid card; no new `DailyCheckIn` row was created (check admin or shell).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/templates/accounts/progress.html static/images/pledge-default.png
git commit -m "feat(pledge): daily pledge card on the progress home"
```

---

## Task 6: Capture pledge_reason + pledge_photo in onboarding step 3

**Files:**
- Modify: `apps/accounts/views.py` (`onboarding_view`, step 3 POST branch ~line 281; completion redirect line 286)
- Modify: `apps/accounts/templates/accounts/onboarding.html` (step 3 inputs)
- Test: `apps/accounts/tests_pledge.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_pledge.py
class OnboardingPledgeCaptureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='o', password='x')
        self.client.force_login(self.user)

    def test_step3_saves_pledge_reason_and_completes(self):
        url = reverse('accounts:onboarding') + '?step=3'
        resp = self.client.post(url, {'pledge_reason': 'my daughter'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.pledge_reason, 'my daughter')
        self.assertTrue(self.user.has_completed_onboarding)
        self.assertRedirects(resp, reverse('accounts:progress'),
                             fetch_redirect_response=False)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 manage.py test apps.accounts.tests_pledge.OnboardingPledgeCaptureTests -v 2`
Expected: FAIL — `pledge_reason` empty and/or redirect goes to `social_feed`.

- [ ] **Step 3: Update step 3 handling** in `onboarding_view` (replace the `elif step == 3:` branch, ~line 281-286)

```python
        elif step == 3:
            pledge_reason = request.POST.get('pledge_reason', '').strip()
            if pledge_reason:
                user.pledge_reason = pledge_reason[:120]
            if request.FILES.get('pledge_photo'):
                user.pledge_photo = request.FILES['pledge_photo']
            user.has_completed_onboarding = True
            user.save()
            ABTestingService.track_conversion(user, 'onboarding_flow', 'completed_onboarding')
            messages.success(request, "Welcome to MyRecoveryPal!")
            return redirect('accounts:progress')
```

- [ ] **Step 4: Add the inputs to step 3** in `onboarding.html` (inside the step-3 form; ensure the form has `enctype="multipart/form-data"`)

```html
{# step 3 form — before the submit button #}
<label for="pledge_reason">Who or what are you staying sober for?</label>
<input type="text" name="pledge_reason" id="pledge_reason" maxlength="120"
       class="form-control" placeholder="e.g. my daughter, my health, my future">
<label for="pledge_photo">Add a photo (optional)</label>
<input type="file" name="pledge_photo" id="pledge_photo" accept="image/*" class="form-control">
```

Confirm the step-3 `<form>` tag includes `method="post" enctype="multipart/form-data"` and `{% csrf_token %}`.

- [ ] **Step 5: Run tests, verify pass; commit**

Run: `python3 manage.py test apps.accounts.tests_pledge.OnboardingPledgeCaptureTests -v 2`
Expected: PASS

```bash
git add apps/accounts/views.py apps/accounts/templates/accounts/onboarding.html apps/accounts/tests_pledge.py
git commit -m "feat(pledge): capture pledge reason + photo in onboarding, land on progress"
```

---

## Task 7: Make pledge fields editable in profile

**Files:**
- Modify: `apps/accounts/forms.py` (`UserProfileForm`, ~line 217-239)
- Modify: `apps/accounts/templates/accounts/edit_profile.html`
- Test: `apps/accounts/tests_pledge.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/accounts/tests_pledge.py
from apps.accounts.forms import UserProfileForm


class UserProfileFormPledgeTests(TestCase):
    def test_form_includes_pledge_fields(self):
        self.assertIn('pledge_reason', UserProfileForm.Meta.fields)
        self.assertIn('pledge_photo', UserProfileForm.Meta.fields)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python3 manage.py test apps.accounts.tests_pledge.UserProfileFormPledgeTests -v 2`
Expected: FAIL — fields not present.

- [ ] **Step 3: Add fields to the form** (`UserProfileForm.Meta.fields`, after `'recovery_goals', 'avatar',` ~line 217)

```python
            'sobriety_date', 'recovery_goals', 'avatar',
            'pledge_reason', 'pledge_photo',
```

Add a help text entry:

```python
            'pledge_reason': "Shown on your daily pledge, e.g. 'my daughter'.",
```

- [ ] **Step 4: Render fields in `edit_profile.html`** where form fields are laid out (match the `recovery_goals`/`avatar` pattern):

```html
<div class="form-group">
  {{ form.pledge_reason.label_tag }} {{ form.pledge_reason }}
  <small class="form-text text-muted">{{ form.pledge_reason.help_text }}</small>
</div>
<div class="form-group">
  {{ form.pledge_photo.label_tag }} {{ form.pledge_photo }}
</div>
```

Confirm the edit-profile `<form>` already has `enctype="multipart/form-data"` (it must, since `avatar` is there).

- [ ] **Step 5: Run tests + full pledge suite; commit**

Run: `python3 manage.py test apps.accounts.tests_pledge -v 2`
Expected: all pledge tests PASS.

```bash
git add apps/accounts/forms.py apps/accounts/templates/accounts/edit_profile.html apps/accounts/tests_pledge.py
git commit -m "feat(pledge): make pledge reason + photo editable in profile"
```

---

## Final verification

- [ ] `python3 manage.py test apps.accounts -v 1` → green.
- [ ] Manual end-to-end: register fresh user → onboarding step 3 captures reason + photo → lands on `/accounts/progress/` → card shows photo + reason + button → tap → `🔥 1` → reload persists → no `DailyCheckIn` row created by the pledge → edit profile changes the reason → reflected on the card.
- [ ] User with no pledge_photo/reason/avatar still gets a valid card.
- [ ] `python3 manage.py makemigrations --check` → no missing migrations.
- [ ] Update `CLAUDE.md`: new `DailyPledge` model, `pledge-today/` route, `get_pledge_streak()`, two User fields; correct the stale note that onboarding lands on `social_feed` (now `progress`).

## Deferred (Phase 2b / later)

- Push/local-notification morning nudge to prompt the daily pledge.
- Pledge streak "freeze"/grace mechanic for a single missed day.
- Pledge-broken re-engagement email.
- Analytics event on pledge tap to measure the retention lift (instrument before/after in the admin dashboard).

---

## Self-review

- **Spec coverage:** DailyPledge model + streak (T1), photo + reason fields (T2, captured T6, editable T7), one-tap endpoint + full-form upsert (T3), home context (T4), card (T5), solo-home redirect (T6). ✅
- **Type consistency:** `get_pledge_streak() -> int` used in T3/T4; `pledge_today` returns `{success, pledged, streak}` consumed by T5 JS; context keys `pledge_streak`/`pledged_today` produced T4, consumed T5; `DailyPledge` produced T1, consumed T3/T4. ✅
- **Placeholders:** migration numbers are `00NN` (resolved by makemigrations); `pledge-default.png` is "reuse an existing asset or a simple placeholder." No logic placeholders. ✅
