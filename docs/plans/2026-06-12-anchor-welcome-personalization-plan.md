# Phase 1c: Personalize the Anchor welcome state — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the coach's welcome state greet the user by name and surface days sober + check-in streak (proving Anchor knows them), with a graceful fallback to the generic greeting for new users.

**Architecture:** The `recovery_coach` view passes three existing-method values into the context; the server-rendered welcome state uses Django conditionals — no JS, no migration.

**Tech Stack:** Django 5.0 template.

**Spec:** `docs/plans/2026-06-12-anchor-welcome-personalization-design.md`

**Test command:** `python3 manage.py test apps.accounts.test_anchor_conversion -v2` (ephemeral DB; local sqlite stale). The file `apps/accounts/test_anchor_conversion.py` has helpers `make_free_user`, `make_checkin` and imports (`TestCase`, `override_settings`, `timezone`, `timedelta`, models) at the top — APPEND.

**Facts:** Home coach view = `accounts:recovery_coach` (`recovery_coach` in views.py → `recovery_coach.html`). `User.get_days_sober()` returns the int days or **0** (no sobriety date). `User.get_checkin_streak()` returns an int. The welcome state (`#welcomeState`) renders only when the active session has no messages (a fresh user qualifies). Current heading/desc:
```html
                    <div class="welcome-heading">Hi, I'm Anchor</div>
                    <div class="welcome-desc">
                        I'm your AI recovery companion. I'm here to listen, support, and encourage you on your journey.
                        Whether you need to talk through cravings, celebrate a milestone, or just process your day &mdash; I'm here for you.
                    </div>
```

---

### Task 1: Backend — pass greeting context

**Files:**
- Modify: `apps/accounts/views.py` (`recovery_coach` context dict)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing test** — APPEND to `apps/accounts/test_anchor_conversion.py`:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class CoachWelcomeContextTest(TestCase):
    def test_context_has_greeting_values(self):
        from django.urls import reverse
        user = make_free_user('cw0')
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:recovery_coach'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('coach_first_name', resp.context)
        self.assertIn('coach_days_sober', resp.context)
        self.assertIn('coach_streak', resp.context)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CoachWelcomeContextTest -v2`
Expected: FAIL — the keys aren't in the context yet.

- [ ] **Step 3: Implement** — in `apps/accounts/views.py`, the `recovery_coach` view's `context = {` dict gains three keys (place them with the other context entries, before `return render`):

```python
        'coach_first_name': request.user.first_name or request.user.username,
        'coach_days_sober': request.user.get_days_sober(),
        'coach_streak': request.user.get_checkin_streak(),
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CoachWelcomeContextTest -v2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): pass name/days-sober/streak to the coach welcome state"
```

---

### Task 2: Frontend — personalized welcome state

**Files:**
- Modify: `apps/accounts/templates/accounts/recovery_coach.html` (`#welcomeState` heading + desc)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — APPEND to `apps/accounts/test_anchor_conversion.py`:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class CoachWelcomeRenderTest(TestCase):
    def test_days_sober_shown_for_user_with_sobriety_date(self):
        from datetime import timedelta
        from django.urls import reverse
        user = make_free_user('cw1')
        user.sobriety_date = timezone.now().date() - timedelta(days=47)
        user.save()
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:recovery_coach'))
        self.assertContains(resp, '47 days sober')

    def test_streak_shown_when_present(self):
        from datetime import timedelta
        from django.urls import reverse
        from apps.accounts.models import DailyCheckIn
        user = make_free_user('cw2')
        # check-ins today + yesterday → 2-day streak
        DailyCheckIn.objects.create(user=user, mood=4, craving_level=0, energy_level=3,
                                    date=timezone.now().date())
        DailyCheckIn.objects.create(user=user, mood=4, craving_level=0, energy_level=3,
                                    date=timezone.now().date() - timedelta(days=1))
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:recovery_coach'))
        self.assertContains(resp, 'check-in streak')

    def test_new_user_gets_generic_greeting(self):
        from django.urls import reverse
        user = make_free_user('cw3')  # no sobriety date, no check-ins
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:recovery_coach'))
        self.assertContains(resp, 'AI recovery companion')
        self.assertNotContains(resp, 'days sober')
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CoachWelcomeRenderTest -v2`
Expected: FAIL — `test_days_sober_shown_for_user_with_sobriety_date` and `test_streak_shown_when_present` fail (welcome desc is still generic). `test_new_user_gets_generic_greeting` already passes.

- [ ] **Step 3: Implement** — in `apps/accounts/templates/accounts/recovery_coach.html`, replace this exact block:

```html
                    <div class="welcome-heading">Hi, I'm Anchor</div>
                    <div class="welcome-desc">
                        I'm your AI recovery companion. I'm here to listen, support, and encourage you on your journey.
                        Whether you need to talk through cravings, celebrate a milestone, or just process your day &mdash; I'm here for you.
                    </div>
```

with:

```html
                    <div class="welcome-heading">Hi {{ coach_first_name }}, I'm Anchor</div>
                    <div class="welcome-desc">
                        {% if coach_days_sober %}
                        I can see you're <strong>{{ coach_days_sober }} days sober</strong>{% if coach_streak > 1 %} with a <strong>{{ coach_streak }}-day check-in streak</strong>{% endif %}. I'm here whenever you need to talk through cravings, celebrate a win, or just process your day.
                        {% elif coach_streak > 1 %}
                        That's a <strong>{{ coach_streak }}-day check-in streak</strong> you're building. I'm here whenever you need to talk through cravings, celebrate a win, or just process your day.
                        {% else %}
                        I'm your AI recovery companion. I'm here to listen, support, and encourage you on your journey.
                        Whether you need to talk through cravings, celebrate a milestone, or just process your day &mdash; I'm here for you.
                        {% endif %}
                    </div>
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CoachWelcomeRenderTest -v2`
Expected: PASS (3 tests).
Also: `python3 manage.py shell -c "from django.template.loader import get_template; get_template('accounts/recovery_coach.html'); print('RENDER_OK')"` → `RENDER_OK`.

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/templates/accounts/recovery_coach.html apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): personalized welcome state (name + days sober + streak)"
```

---

### Task 3: Verification

- [ ] **Step 1: Full anchor suite**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v1`
Expected: PASS (prior 27 + 1 context + 3 render = 31 tests).

- [ ] **Step 2: Check + migration drift**

Run: `python3 manage.py check` → no issues.
Run: `python3 manage.py makemigrations --check --dry-run` → No changes detected.

- [ ] **Step 3: Manual smoke**

Open the coach (`/accounts/recovery-coach/`) as a user with a sobriety date and a check-in streak → the welcome state greets by name and shows "X days sober with a Y-day check-in streak". A brand-new user sees the generic greeting (no fabricated numbers).

This plan is implemented on a feature branch; integration/merge is handled by the finishing-a-development-branch skill after the final review (do NOT push to main from within the tasks).
