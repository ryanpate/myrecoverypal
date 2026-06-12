# Phase 1a: Anchor Conversion Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Anchor convert free users by triggering a context-aware coach session at struggling/high-craving check-ins, reworking the free limit from 10-lifetime to 3/day, and exempting crisis sessions so a struggling user is never paywalled away from support.

**Architecture:** Tag coach sessions with a `trigger` (`manual` vs `checkin_support`); the gating function becomes session-aware (crisis sessions exempt, free routine 3/day); a check-in confirmation screen offers Anchor via a card that opens a `checkin_support` session pre-seeded with a proactive opener.

**Tech Stack:** Django 5.0, PostgreSQL, Anthropic Claude Haiku (`claude-haiku-4-5-20251001`).

**Spec:** `docs/plans/2026-06-12-anchor-conversion-engine-design.md`

**Test command:** `python3 manage.py test apps.accounts.test_anchor_conversion -v2`
(Ephemeral SQLite test DB; local `db.sqlite3` is stale — always use `manage.py test`.)

**Test-user helpers** (used across tasks; defined once in Task 1's test file): creating a `User` auto-creates a `Subscription(tier='premium', status='trialing', trial_end=now+14d)` → `is_premium()` True. For free-tier tests, downgrade it. `DailyCheckIn` requires `mood`, `craving_level`, AND `energy_level` (no default). `email` is unique+required.

---

### Task 1: Data model — session trigger fields + `needs_support()`

**Files:**
- Modify: `apps/accounts/models.py` (`RecoveryCoachSession`, `DailyCheckIn`)
- Create: `apps/accounts/test_anchor_conversion.py`
- Create (generated): `apps/accounts/migrations/0048_*.py`

- [ ] **Step 1: Write the failing tests** — create `apps/accounts/test_anchor_conversion.py`:

```python
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import (
    User, DailyCheckIn, RecoveryCoachSession, CoachMessage,
)


def make_free_user(username):
    u = User.objects.create_user(username, f'{username}@t.co', 'pw')
    sub = u.subscription
    sub.tier = 'free'
    sub.status = 'expired'
    sub.trial_end = None
    sub.save()
    return u


def make_premium_user(username):
    u = User.objects.create_user(username, f'{username}@t.co', 'pw')
    sub = u.subscription
    sub.tier = 'premium'
    sub.status = 'active'
    sub.trial_end = None
    sub.save()
    return u


def make_checkin(user, mood, craving, challenge=''):
    return DailyCheckIn.objects.create(
        user=user, mood=mood, craving_level=craving,
        energy_level=3, challenge=challenge,
    )


class NeedsSupportTest(TestCase):
    def setUp(self):
        self.user = make_free_user('ns')

    def test_low_mood_needs_support(self):
        self.assertTrue(make_checkin(self.user, mood=2, craving=0).needs_support())

    def test_okay_mood_no_craving_does_not(self):
        self.assertFalse(make_checkin(self.user, mood=3, craving=2).needs_support())

    def test_high_craving_needs_support(self):
        self.assertTrue(make_checkin(self.user, mood=5, craving=3).needs_support())

    def test_calm_does_not(self):
        self.assertFalse(make_checkin(self.user, mood=5, craving=0).needs_support())
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.NeedsSupportTest -v2`
Expected: FAIL — `AttributeError: 'DailyCheckIn' object has no attribute 'needs_support'`.

- [ ] **Step 3: Implement model changes**

In `apps/accounts/models.py`, add to `RecoveryCoachSession` (after the `is_active` field):
```python
    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('checkin_support', 'Check-in support'),
    ]
    trigger = models.CharField(
        max_length=20, choices=TRIGGER_CHOICES, default='manual')
    triggering_checkin = models.ForeignKey(
        'DailyCheckIn', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='coach_sessions')
```
Add to `DailyCheckIn` (after the `needs`/before `__str__`, anywhere in the class body):
```python
    def needs_support(self):
        """True when this check-in indicates a struggling/high-craving moment."""
        return self.mood <= 2 or self.craving_level >= 3
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.NeedsSupportTest -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: Generate migration**

Run: `python3 manage.py makemigrations accounts`
Expected: one migration (next number, e.g. `0048_...`) adding `RecoveryCoachSession.trigger` and `.triggering_checkin`. If it picks up anything unrelated, STOP and report.

- [ ] **Step 6: Commit**
```bash
git add apps/accounts/models.py apps/accounts/test_anchor_conversion.py apps/accounts/migrations/0048_*.py
git commit -m "feat(coach): add session trigger fields + DailyCheckIn.needs_support()"
```

---

### Task 2: Gating rework (session-aware, 3/day free)

**Files:**
- Modify: `apps/accounts/coach_service.py` (`get_message_count_today`, `can_send_message`)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — append to `apps/accounts/test_anchor_conversion.py`:

```python
from apps.accounts.coach_service import (
    can_send_message, get_message_count_today,
)


def add_user_messages(user, n, trigger='manual'):
    session = RecoveryCoachSession.objects.create(
        user=user, trigger=trigger, title='t')
    for i in range(n):
        CoachMessage.objects.create(session=session, role='user', content=f'm{i}')
    return session


class GatingTest(TestCase):
    def test_free_user_allowed_under_3_then_blocked(self):
        user = make_free_user('g1')
        add_user_messages(user, 2)
        allowed, reason = can_send_message(user)
        self.assertTrue(allowed)
        add_user_messages(user, 1)  # now 3 routine today
        allowed, reason = can_send_message(user)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'upgrade_required')

    def test_checkin_support_session_is_exempt(self):
        user = make_free_user('g2')
        add_user_messages(user, 5)  # well over the routine limit
        crisis = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support', title='c')
        allowed, reason = can_send_message(user, crisis)
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_checkin_support_messages_not_counted(self):
        user = make_free_user('g3')
        add_user_messages(user, 3, trigger='checkin_support')
        self.assertEqual(get_message_count_today(user), 0)
        allowed, _ = can_send_message(user)  # routine still open
        self.assertTrue(allowed)

    def test_premium_allowed_until_20(self):
        user = make_premium_user('g4')
        add_user_messages(user, 19)
        self.assertTrue(can_send_message(user)[0])
        add_user_messages(user, 1)  # 20
        self.assertFalse(can_send_message(user)[0])
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.GatingTest -v2`
Expected: FAIL — `test_free_user_allowed_under_3_then_blocked` fails (current free limit is 10 lifetime, not 3/day) and `test_checkin_support_messages_not_counted` fails (current count includes all sessions).

- [ ] **Step 3: Implement** — in `apps/accounts/coach_service.py`:

Replace `get_message_count_today`:
```python
def get_message_count_today(user):
    """Count routine (non-exempt) coach messages the user has sent today."""
    from apps.accounts.models import CoachMessage

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return CoachMessage.objects.filter(
        session__user=user,
        role='user',
        created_at__gte=today_start,
    ).exclude(session__trigger='checkin_support').count()
```

Replace `can_send_message`:
```python
def can_send_message(user, session=None):
    """Check if user can send a coach message. Returns (allowed, reason).

    Crisis-triggered (checkin_support) sessions are never limited.
    Free users get 3 routine messages/day; premium gets 20/day.
    """
    if session is not None and session.trigger == 'checkin_support':
        return True, None

    is_premium = hasattr(user, 'subscription') and user.subscription.is_premium()
    today_count = get_message_count_today(user)
    if is_premium:
        if today_count >= 20:
            return False, "You've reached your daily limit of 20 messages. Your limit resets at midnight."
        return True, None
    if today_count >= 3:
        return False, "upgrade_required"
    return True, None
```

(Leave `get_total_free_messages` defined for now — Task 6 removes it after its last caller is gone.)

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.GatingTest -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**
```bash
git add apps/accounts/coach_service.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): session-aware gating — 3/day free, crisis sessions exempt"
```

---

### Task 3: Proactive opener (`generate_checkin_opener`)

**Files:**
- Modify: `apps/accounts/coach_service.py` (new function)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — append:

```python
from apps.accounts.coach_service import generate_checkin_opener


class OpenerTest(TestCase):
    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_uses_api_text_when_available(self):
        user = make_free_user('o1')
        checkin = make_checkin(user, mood=1, craving=4, challenge='work stress')

        class FakeBlock:
            text = 'Hey, I can see today is really hard.'

        class FakeResp:
            content = [FakeBlock()]

        with patch('anthropic.Anthropic') as MockClient:
            MockClient.return_value.messages.create.return_value = FakeResp()
            text = generate_checkin_opener(user, checkin)
        self.assertEqual(text, 'Hey, I can see today is really hard.')

    @override_settings(ANTHROPIC_API_KEY='test-key')
    def test_falls_back_on_api_error(self):
        user = make_free_user('o2')
        checkin = make_checkin(user, mood=1, craving=4)
        with patch('anthropic.Anthropic', side_effect=Exception('boom')):
            text = generate_checkin_opener(user, checkin)
        self.assertIn("I'm here", text)

    @override_settings(ANTHROPIC_API_KEY='')
    def test_falls_back_with_no_api_key(self):
        user = make_free_user('o3')
        checkin = make_checkin(user, mood=2, craving=0)
        text = generate_checkin_opener(user, checkin)
        self.assertIn("I'm here", text)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.OpenerTest -v2`
Expected: FAIL — `ImportError: cannot import name 'generate_checkin_opener'`.

- [ ] **Step 3: Implement** — add to `apps/accounts/coach_service.py` (after `send_coach_message`). It reuses `build_user_context`, `RECOVERY_COACH_SYSTEM_PROMPT`, `settings`, and `logger`, all already in the module:

```python
def generate_checkin_opener(user, checkin):
    """Anchor's proactive opening message for a check-in-triggered session.

    Returns assistant text; falls back to a static warm message on any error.
    """
    import anthropic

    fallback = ("I saw your check-in — sounds like today's been heavy. "
                "I'm here. What's going on right now?")
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return fallback
    try:
        user_context = build_user_context(user)
        system_prompt = RECOVERY_COACH_SYSTEM_PROMPT.format(user_context=user_context)
        challenge = (checkin.challenge or '').strip()
        seed = (
            f"The user just logged a daily check-in: mood "
            f"'{checkin.get_mood_display()}', craving level "
            f"'{checkin.get_craving_level_display()}'."
            + (f" They wrote their challenge today is: \"{challenge}\"." if challenge else "")
            + " Open the conversation: gently acknowledge how they're doing right "
              "now and invite them to talk. 2-3 sentences, warm, no lists."
        )
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": seed}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"generate_checkin_opener failed: {e}")
        return fallback
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.OpenerTest -v2`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git add apps/accounts/coach_service.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): generate_checkin_opener with static fallback"
```

---

### Task 4: `coach_start_from_checkin` view + URL

**Files:**
- Modify: `apps/accounts/views.py` (new view)
- Modify: `apps/accounts/urls.py` (new URL)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — append:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class StartFromCheckinTest(TestCase):
    def setUp(self):
        self.user = make_free_user('sfc')
        self.checkin = make_checkin(self.user, mood=1, craving=4)

    @patch('apps.accounts.coach_service.generate_checkin_opener', return_value='Opener text.')
    def test_creates_exempt_session_with_opener(self, _mock):
        from django.urls import reverse
        self.client.force_login(self.user)
        resp = self.client.get(reverse('accounts:coach_start_from_checkin', args=[self.checkin.id]))
        self.assertEqual(resp.status_code, 302)  # redirects to coach
        session = RecoveryCoachSession.objects.get(user=self.user, trigger='checkin_support')
        self.assertEqual(session.triggering_checkin_id, self.checkin.id)
        opener = session.messages.get(role='assistant')
        self.assertEqual(opener.content, 'Opener text.')

    @patch('apps.accounts.coach_service.generate_checkin_opener', return_value='Opener text.')
    def test_retap_reuses_session(self, _mock):
        from django.urls import reverse
        self.client.force_login(self.user)
        url = reverse('accounts:coach_start_from_checkin', args=[self.checkin.id])
        self.client.get(url)
        self.client.get(url)  # second tap
        self.assertEqual(
            RecoveryCoachSession.objects.filter(
                user=self.user, trigger='checkin_support').count(), 1)
        # opener generated only once
        self.assertEqual(_mock.call_count, 1)

    def test_other_users_checkin_404(self):
        from django.urls import reverse
        other = make_free_user('other')
        self.client.force_login(other)
        resp = self.client.get(reverse('accounts:coach_start_from_checkin', args=[self.checkin.id]))
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.StartFromCheckinTest -v2`
Expected: FAIL — `NoReverseMatch: 'coach_start_from_checkin' is not a valid view function or pattern name`.

- [ ] **Step 3: Implement the view** — add to `apps/accounts/views.py` (near the other coach views, e.g. after `coach_new_session`). `DailyCheckIn`, `get_object_or_404`, `login_required`, `redirect` are already imported in this module:

```python
@login_required
def coach_start_from_checkin(request, checkin_id):
    """Open (or reuse) a crisis-support coach session for a check-in."""
    from apps.accounts.models import RecoveryCoachSession, CoachMessage
    from apps.accounts.coach_service import generate_checkin_opener

    checkin = get_object_or_404(DailyCheckIn, id=checkin_id, user=request.user)

    session = RecoveryCoachSession.objects.filter(
        user=request.user, trigger='checkin_support', triggering_checkin=checkin,
    ).first()

    if session is None:
        RecoveryCoachSession.objects.filter(
            user=request.user, is_active=True).update(is_active=False)
        session = RecoveryCoachSession.objects.create(
            user=request.user, trigger='checkin_support',
            triggering_checkin=checkin, is_active=True, title='Check-in support',
        )
        opener = generate_checkin_opener(request.user, checkin)
        CoachMessage.objects.create(session=session, role='assistant', content=opener)
    else:
        RecoveryCoachSession.objects.filter(
            user=request.user, is_active=True).exclude(id=session.id).update(is_active=False)
        session.is_active = True
        session.save(update_fields=['is_active', 'updated_at'])

    return redirect('accounts:recovery_coach')
```

- [ ] **Step 4: Add the URL** — in `apps/accounts/urls.py`, near the other `recovery-coach/` paths:
```python
    path('recovery-coach/from-checkin/<int:checkin_id>/',
         views.coach_start_from_checkin, name='coach_start_from_checkin'),
```

- [ ] **Step 5: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.StartFromCheckinTest -v2`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**
```bash
git add apps/accounts/views.py apps/accounts/urls.py apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): coach_start_from_checkin opens exempt session w/ opener"
```

---

### Task 5: Check-in confirmation screen + card

**Files:**
- Modify: `apps/accounts/views.py` (new `checkin_confirmation` view; change `daily_checkin_view` redirect)
- Modify: `apps/accounts/urls.py` (new URL)
- Create: `apps/accounts/templates/accounts/checkin_confirmation.html`
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — append:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class CheckinConfirmationTest(TestCase):
    def setUp(self):
        self.user = make_free_user('cc')

    def test_card_shown_when_needs_support(self):
        from django.urls import reverse
        checkin = make_checkin(self.user, mood=1, craving=4)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('accounts:checkin_confirmation') + f'?checkin={checkin.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'talk it through with Anchor')

    def test_card_hidden_when_calm(self):
        from django.urls import reverse
        checkin = make_checkin(self.user, mood=5, craving=0)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('accounts:checkin_confirmation') + f'?checkin={checkin.id}')
        self.assertNotContains(resp, 'talk it through with Anchor')

    def test_other_users_checkin_not_used(self):
        from django.urls import reverse
        other_checkin = make_checkin(make_free_user('cc2'), mood=1, craving=4)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('accounts:checkin_confirmation') + f'?checkin={other_checkin.id}')
        # not the requester's check-in → treated as no check-in → no card
        self.assertNotContains(resp, 'talk it through with Anchor')
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CheckinConfirmationTest -v2`
Expected: FAIL — `NoReverseMatch: 'checkin_confirmation'`.

- [ ] **Step 3: Implement the view** — add to `apps/accounts/views.py`:
```python
@login_required
def checkin_confirmation(request):
    """Brief post-check-in screen; offers Anchor when the check-in needs support."""
    checkin = None
    checkin_id = request.GET.get('checkin')
    if checkin_id:
        checkin = DailyCheckIn.objects.filter(id=checkin_id, user=request.user).first()
    return render(request, 'accounts/checkin_confirmation.html', {'checkin': checkin})
```

- [ ] **Step 4: Change the check-in redirect** — in `apps/accounts/views.py`, the success redirect in `daily_checkin_view` (currently `return redirect('accounts:dashboard')` at ~line 833) becomes:
```python
            return redirect(
                f"{reverse('accounts:checkin_confirmation')}?checkin={checkin.id}")
```
Confirm `reverse` is imported at the top of `views.py` (`from django.urls import reverse`); add it if missing.

- [ ] **Step 5: Add the URL** — in `apps/accounts/urls.py`:
```python
    path('checkin/done/', views.checkin_confirmation, name='checkin_confirmation'),
```

- [ ] **Step 6: Create the template** — `apps/accounts/templates/accounts/checkin_confirmation.html`:
```html
{% extends 'base.html' %}
{% block title %}Checked in — MyRecoveryPal{% endblock %}
{% block content %}
<div class="container" style="max-width: 600px; margin: 3rem auto; padding: 0 1rem; text-align: center;">
    <div style="font-size: 3rem;">✓</div>
    <h1 style="color: var(--primary-dark, #1e4d8b);">You're checked in.</h1>
    <p style="color: #555;">Nice work showing up for yourself today.</p>

    {% if checkin and checkin.needs_support %}
    <div style="border:1px solid #1e4d8b; background:#f4f8fc; border-radius:12px; padding:20px; margin:1.5rem 0; text-align:center;">
        <p style="margin:0 0 8px; color:#1e4d8b; font-weight:600;">Today sounds heavy.</p>
        <p style="margin:0 0 16px; color:#555; font-size:14px;">
            Want to talk it through with Anchor? It's here whenever you need it.
        </p>
        <a href="{% url 'accounts:coach_start_from_checkin' checkin.id %}"
           style="background:#1e4d8b; color:#fff; padding:11px 24px; border-radius:8px; text-decoration:none; font-weight:600;">
            Talk it through with Anchor
        </a>
    </div>
    {% endif %}

    <p style="margin-top: 1.5rem;">
        <a href="{% url 'accounts:dashboard' %}" style="color:#1e4d8b;">Continue to your feed →</a>
    </p>
</div>
{% endblock %}
```

- [ ] **Step 7: Run to verify pass**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.CheckinConfirmationTest -v2`
Expected: PASS (3 tests). The card test passes because the template renders the literal string "talk it through with Anchor" only when `checkin.needs_support` is truthy.

- [ ] **Step 8: Commit**
```bash
git add apps/accounts/views.py apps/accounts/urls.py apps/accounts/templates/accounts/checkin_confirmation.html apps/accounts/test_anchor_conversion.py
git commit -m "feat(checkin): confirmation screen offers Anchor on hard days"
```

---

### Task 6: Session-aware send endpoint + daily-count display

**Files:**
- Modify: `apps/accounts/views.py` (`coach_send_message`, `recovery_coach`)
- Modify: `apps/accounts/templates/accounts/recovery_coach.html` (remaining-count copy)
- Modify: `apps/accounts/coach_service.py` (remove now-unused `get_total_free_messages`)
- Modify: `apps/accounts/test_anchor_conversion.py` (append a class)

- [ ] **Step 1: Write the failing tests** — append:

```python
@override_settings(SECURE_SSL_REDIRECT=False, PREPEND_WWW=False, ALLOWED_HOSTS=['*'])
class SendEndpointTest(TestCase):
    @patch('apps.accounts.coach_service.send_coach_message', return_value=('reply', None))
    def test_free_user_blocked_after_3_routine(self, _mock):
        from django.urls import reverse
        user = make_free_user('se1')
        add_user_messages(user, 3)  # already at routine cap today
        session = RecoveryCoachSession.objects.create(user=user, trigger='manual', title='t')
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts:coach_send_message'),
                                {'message': 'hi', 'session_id': session.id})
        self.assertEqual(resp.status_code, 429)
        self.assertTrue(resp.json().get('upgrade_required'))

    @patch('apps.accounts.coach_service.send_coach_message', return_value=('reply', None))
    def test_free_user_can_send_in_crisis_session_past_cap(self, _mock):
        from django.urls import reverse
        user = make_free_user('se2')
        add_user_messages(user, 3)  # routine cap reached
        crisis = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support', title='c')
        self.client.force_login(user)
        resp = self.client.post(reverse('accounts:coach_send_message'),
                                {'message': 'help', 'session_id': crisis.id})
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion.SendEndpointTest -v2`
Expected: FAIL — `test_free_user_can_send_in_crisis_session_past_cap` returns 429 because the current `coach_send_message` checks `can_send_message(request.user)` without the session, so it blocks even the crisis session.

- [ ] **Step 3: Reorder `coach_send_message`** — in `apps/accounts/views.py`, move the session load ABOVE the limit check and pass the session. Replace this block:
```python
    # Check rate limits
    allowed, reason = can_send_message(request.user)
    if not allowed:
        return JsonResponse({'error': reason, 'upgrade_required': reason == 'upgrade_required'}, status=429)

    # Get session
    try:
        session = RecoveryCoachSession.objects.get(id=session_id, user=request.user)
    except RecoveryCoachSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
```
with:
```python
    # Get session first so crisis (checkin_support) sessions are exempt
    try:
        session = RecoveryCoachSession.objects.get(id=session_id, user=request.user)
    except RecoveryCoachSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)

    # Check rate limits (session-aware)
    allowed, reason = can_send_message(request.user, session)
    if not allowed:
        return JsonResponse({'error': reason, 'upgrade_required': reason == 'upgrade_required'}, status=429)
```
Also update the import line at the top of `coach_send_message` to drop `get_total_free_messages` (no longer used there): change
`from apps.accounts.coach_service import can_send_message, send_coach_message, get_message_count_today, get_total_free_messages`
to
`from apps.accounts.coach_service import can_send_message, send_coach_message, get_message_count_today`.

- [ ] **Step 4: Update `recovery_coach` view for the daily model** — in `apps/accounts/views.py`, the `recovery_coach` view currently sets `messages_used` from `get_total_free_messages` and `message_limit = ... else 10`. Replace those context lines so both tiers use the daily count and the free limit is 3:
Compute the daily values just before the existing `context = {` line, and inside that dict keep every other existing key (e.g. `sessions`, the active session/messages) exactly as-is — only set these:
```python
    # add immediately before the existing `context = {` line:
    limit = 20 if is_premium else 3
    used = get_message_count_today(request.user)
    # then, inside the existing context dict, these keys become:
    #     'messages_used': used,
    #     'message_limit': limit,
    #     'messages_remaining': max(0, limit - used),
```
And drop `get_total_free_messages` from that view's local import line (`from apps.accounts.coach_service import can_send_message, get_message_count_today, get_total_free_messages` → `from apps.accounts.coach_service import can_send_message, get_message_count_today`).

- [ ] **Step 5: Update the coach template copy** — in `apps/accounts/templates/accounts/recovery_coach.html`, find where `messages_used` / `message_limit` are displayed and change the wording to a daily frame, e.g. `{{ messages_remaining }} messages left today` (replace any "free messages left" / lifetime wording). Verify the template still renders: `python3 manage.py shell -c "from django.template.loader import get_template; get_template('accounts/recovery_coach.html'); print('RENDER_OK')"`.

- [ ] **Step 6: Remove the dead `get_total_free_messages`** — confirm no remaining references, then delete the function from `coach_service.py`:
```bash
grep -rn "get_total_free_messages" --include="*.py" .
```
If the only hits are the function definition (and none import/call it), delete the `def get_total_free_messages(...)` block. If anything still references it, STOP and report.

- [ ] **Step 7: Run tests + check**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v2` (expect all classes pass)
Run: `python3 manage.py check` (expect no issues)

- [ ] **Step 8: Commit**
```bash
git add apps/accounts/views.py apps/accounts/coach_service.py apps/accounts/templates/accounts/recovery_coach.html apps/accounts/test_anchor_conversion.py
git commit -m "feat(coach): session-aware send limit + daily count display; drop lifetime counter"
```

---

### Task 7: Full-suite verification

- [ ] **Step 1: Whole new suite**

Run: `python3 manage.py test apps.accounts.test_anchor_conversion -v1`
Expected: PASS (NeedsSupport 4 + Gating 4 + Opener 3 + StartFromCheckin 3 + CheckinConfirmation 3 + SendEndpoint 2 = 19 tests).

- [ ] **Step 2: Migration drift**

Run: `python3 manage.py makemigrations --check --dry-run`
Expected: "No changes detected".

- [ ] **Step 3: Regression — coach + signup suites**

Run: `python3 manage.py test apps.accounts.tests_signup apps.accounts.test_trial_expiration -v1`
Expected: PASS (no regressions from the gating/model changes).

- [ ] **Step 4: System check**

Run: `python3 manage.py check`
Expected: `System check identified no issues`.

This plan is implemented on a feature branch; integration/merge is handled by the finishing-a-development-branch skill after the final review (do NOT push to main from within the tasks).
