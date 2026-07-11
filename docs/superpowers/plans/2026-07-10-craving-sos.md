# Craving SOS Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A public `/craving-sos/` page with instantly usable craving tools (breathing, urge surfing, grounding, meetings starting soon, crisis line), logged-in extras (never-rate-limited Anchor SOS session, pledge reason/photo), and a persistent SOS pill in the nav.

**Architecture:** One `TemplateView` in `apps.core` with inline-JS tools (sobriety-calculator pattern, no build step). A new read-side query module `apps/support_services/meeting_queries.py` computes "meetings starting soon" per-timezone over the directory shipped 2026-07-10. The Anchor button follows the existing `coach_start_from_checkin` view pattern with a new `sos` trigger that shares the `checkin_support` rate-limit exemption.

**Tech Stack:** Django 5.0.10, vanilla JS, zoneinfo. One trivial migration (choices change on `RecoveryCoachSession.trigger`).

**Spec:** `docs/superpowers/specs/2026-07-10-craving-sos-design.md`

## Global Constraints

- URL is exactly `/craving-sos/`, name `core:craving_sos`, public (no login).
- SOS coach sessions (`trigger='sos'`) are NEVER rate-limited and their messages do not count toward the daily total — identical treatment to `checkin_support`.
- The SOS opener message is static text (no Anthropic API call) — instant response in a crisis moment.
- The only schema change on the branch is adding `('sos', 'Craving SOS')` to `RecoveryCoachSession.TRIGGER_CHOICES` (choices-only migration).
- View tests use the repo convention `@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)`.
- Tests run with `python manage.py test <module> -v 2` from the repo root.
- Surgical changes; match existing style. Commit per task with the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: meetings-starting-soon query helper

**Files:**
- Create: `apps/support_services/meeting_queries.py`
- Create: `apps/support_services/test_meeting_queries.py`

**Interfaces:**
- Consumes: `apps.support_services.models.Meeting` (fields: `day` 0=Sunday..6=Saturday, `time`, `timezone` IANA string, `attendance_option`, `is_active`, `is_approved`).
- Produces: `starting_soon(hours: int = 3, limit: int = 6) -> list[Meeting]` — active approved online meetings whose next occurrence starts within `hours`, each annotated with an int attribute `minutes_until`, sorted ascending by `minutes_until`, trimmed to `limit`. Used by Task 3's view.

- [ ] **Step 1: Write the failing tests**

Create `apps/support_services/test_meeting_queries.py`:

```python
"""Tests for meetings-starting-soon.

'Now' is frozen by patching the datetime symbol inside meeting_queries with
a subclass whose now() returns a fixed moment: Wednesday 2026-07-08 22:00
America/Chicago (day index 3 in the Meeting model's 0=Sunday scheme).
"""
from datetime import datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.support_services.meeting_queries import starting_soon
from apps.support_services.models import Meeting

FIXED_NOW = datetime(2026, 7, 8, 22, 0, tzinfo=ZoneInfo("America/Chicago"))


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW.astimezone(tz) if tz else FIXED_NOW.replace(tzinfo=None)


def make_meeting(slug, day, t, tz="America/Chicago", **kw):
    defaults = dict(
        name=slug, slug=slug, day=day, time=t, timezone=tz,
        attendance_option="online", conference_url="https://zoom.us/j/1",
        is_active=True, is_approved=True,
    )
    defaults.update(kw)
    return Meeting.objects.create(**defaults)


@patch("apps.support_services.meeting_queries.datetime", FixedDatetime)
class StartingSoonTests(TestCase):
    # Fixed now: Wed 22:00 Chicago. Window (3h): 22:00 Wed .. 01:00 Thu.
    # Meeting day indexes: Wed=3, Thu=4.

    def test_meeting_within_window_included_with_minutes_until(self):
        make_meeting("in-window", day=3, t=time(22, 30))
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["in-window"])
        self.assertEqual(result[0].minutes_until, 30)

    def test_meeting_already_started_excluded(self):
        make_meeting("past", day=3, t=time(21, 0))
        self.assertEqual(starting_soon(), [])

    def test_meeting_beyond_window_excluded(self):
        make_meeting("too-late", day=4, t=time(2, 0))  # Thu 02:00, window ends 01:00
        self.assertEqual(starting_soon(), [])

    def test_midnight_spillover_included(self):
        make_meeting("after-midnight", day=4, t=time(0, 30))  # Thu 00:30
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["after-midnight"])
        self.assertEqual(result[0].minutes_until, 150)

    def test_cross_zone_ordering(self):
        # 22:00 Chicago == 23:00 New York.
        make_meeting("chicago-2300", day=3, t=time(23, 0))                      # 60 min out
        make_meeting("ny-2330", day=3, t=time(23, 30), tz="America/New_York")   # 30 min out
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["ny-2330", "chicago-2300"])

    def test_inactive_in_person_and_unscheduled_excluded(self):
        make_meeting("inactive", day=3, t=time(22, 30), is_active=False)
        make_meeting("in-person", day=3, t=time(22, 30),
                     attendance_option="in_person")
        make_meeting("no-time", day=3, t=None)
        self.assertEqual(starting_soon(), [])

    def test_limit_applies_after_sorting(self):
        for i in range(8):
            make_meeting(f"m-{i}", day=3, t=time(22, 10 + i))
        result = starting_soon(limit=3)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].minutes_until, 10)

    def test_invalid_timezone_skipped_not_crashing(self):
        make_meeting("bad-tz", day=3, t=time(22, 30), tz="Not/AZone")
        make_meeting("good", day=3, t=time(22, 30))
        self.assertEqual([m.slug for m in starting_soon()], ["good"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.support_services.test_meeting_queries -v 2`
Expected: ERROR on every test with `ModuleNotFoundError: No module named 'apps.support_services.meeting_queries'`

- [ ] **Step 3: Write the helper**

Create `apps/support_services/meeting_queries.py`:

```python
"""Read-side queries over the meeting directory.

Meetings store day + time in their home IANA timezone, so "starting soon"
must be computed per zone: local-now differs between the Seattle, Houston,
and NYC feeds, and a window that crosses local midnight has to look at the
next day's meetings too.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apps.support_services.models import Meeting


def starting_soon(hours=3, limit=6):
    """Active online meetings starting within `hours`, soonest first.

    Each returned Meeting gets a `minutes_until` int attribute. Meetings
    with no day/time, or an unparseable timezone, are skipped.
    """
    online = (
        Meeting.objects
        .filter(is_active=True, is_approved=True, attendance_option='online')
        .exclude(time__isnull=True)
        .exclude(day__isnull=True)
    )

    results = []
    zones = online.values_list('timezone', flat=True).distinct()
    for tz_name in zones:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            continue
        now_local = datetime.now(tz)
        end_local = now_local + timedelta(hours=hours)
        today = (now_local.weekday() + 1) % 7  # Meeting model: 0=Sunday
        crosses_midnight = end_local.date() != now_local.date()

        zone_qs = online.filter(timezone=tz_name)

        # Today's slice of the window.
        today_qs = zone_qs.filter(day=today, time__gte=now_local.time())
        if not crosses_midnight:
            today_qs = today_qs.filter(time__lt=end_local.time())
        for meeting in today_qs:
            results.append(_annotate(meeting, now_local, days_ahead=0))

        # Spillover past local midnight.
        if crosses_midnight:
            tomorrow = (today + 1) % 7
            for meeting in zone_qs.filter(day=tomorrow,
                                          time__lt=end_local.time()):
                results.append(_annotate(meeting, now_local, days_ahead=1))

    results.sort(key=lambda m: m.minutes_until)
    return results[:limit]


def _annotate(meeting, now_local, days_ahead):
    starts = now_local.replace(
        hour=meeting.time.hour, minute=meeting.time.minute,
        second=0, microsecond=0,
    ) + timedelta(days=days_ahead)
    meeting.minutes_until = max(0, int((starts - now_local).total_seconds() // 60))
    return meeting
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.support_services.test_meeting_queries -v 2`
Expected: OK, 8 tests passing

- [ ] **Step 5: Commit**

```bash
git add apps/support_services/meeting_queries.py apps/support_services/test_meeting_queries.py
git commit -m "feat(meetings): timezone-aware starting_soon query for the directory

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Anchor SOS trigger — exemption, view, URL

**Files:**
- Modify: `apps/accounts/models.py` (`RecoveryCoachSession.TRIGGER_CHOICES`, ~line 2003)
- Modify: `apps/accounts/coach_service.py` (`get_message_count_today` ~line 118, `can_send_message` ~line 128)
- Modify: `apps/accounts/views.py` (add `coach_start_sos` directly after `coach_start_from_checkin`, ~line 5060)
- Modify: `apps/accounts/urls.py` (after the `coach_start_from_checkin` entry, ~line 218)
- Create: migration via `makemigrations` (choices-only)
- Create: `apps/accounts/test_coach_sos.py`

**Interfaces:**
- Consumes: existing `RecoveryCoachSession`, `CoachMessage` models; `can_send_message(user, session=None)`.
- Produces: URL name `accounts:coach_start_sos` at `/accounts/recovery-coach/sos/` (used by Task 3's template); trigger value `'sos'` exempt from rate limits.

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_coach_sos.py`:

```python
"""Tests for the Craving SOS coach trigger: exemption + session view."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.coach_service import can_send_message, get_message_count_today
from apps.accounts.models import CoachMessage, RecoveryCoachSession

User = get_user_model()


class SosExemptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sos", password="x")

    def _spam_routine_messages(self, n):
        session = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual')
        for _ in range(n):
            CoachMessage.objects.create(
                session=session, role='user', content='hi')

    def test_sos_session_never_limited_for_free_user(self):
        self._spam_routine_messages(3)  # free daily limit exhausted
        sos = RecoveryCoachSession.objects.create(
            user=self.user, trigger='sos')
        allowed, reason = can_send_message(self.user, session=sos)
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_sos_messages_do_not_count_toward_daily_total(self):
        sos = RecoveryCoachSession.objects.create(
            user=self.user, trigger='sos')
        for _ in range(5):
            CoachMessage.objects.create(
                session=sos, role='user', content='wave')
        self.assertEqual(get_message_count_today(self.user), 0)

    def test_routine_session_still_limited(self):
        self._spam_routine_messages(3)
        manual = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual')
        allowed, reason = can_send_message(self.user, session=manual)
        self.assertFalse(allowed)
        self.assertEqual(reason, "upgrade_required")


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CoachStartSosViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sos2", password="x")
        self.client.force_login(self.user)

    def test_creates_sos_session_with_static_opener(self):
        resp = self.client.get(reverse("accounts:coach_start_sos"))
        self.assertRedirects(
            resp, reverse("accounts:recovery_coach"),
            fetch_redirect_response=False)
        session = RecoveryCoachSession.objects.get(
            user=self.user, trigger='sos')
        self.assertTrue(session.is_active)
        opener = session.messages.get()
        self.assertEqual(opener.role, 'assistant')
        self.assertIn("Cravings", opener.content)

    def test_reuses_todays_sos_session(self):
        self.client.get(reverse("accounts:coach_start_sos"))
        self.client.get(reverse("accounts:coach_start_sos"))
        self.assertEqual(
            RecoveryCoachSession.objects.filter(
                user=self.user, trigger='sos').count(), 1)

    def test_deactivates_other_active_sessions(self):
        other = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual', is_active=True)
        self.client.get(reverse("accounts:coach_start_sos"))
        other.refresh_from_db()
        self.assertFalse(other.is_active)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("accounts:coach_start_sos"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_coach_sos -v 2`
Expected: exemption tests FAIL (sos not exempt → `can_send_message` returns False / count is 5); view tests ERROR with `NoReverseMatch: 'coach_start_sos'`

- [ ] **Step 3: Add the trigger choice + migration**

In `apps/accounts/models.py` (~line 2003), change:

```python
    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('checkin_support', 'Check-in support'),
    ]
```

to:

```python
    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('checkin_support', 'Check-in support'),
        ('sos', 'Craving SOS'),
    ]
```

Then run: `python manage.py makemigrations accounts`
Expected: one migration with a single `AlterField` on `recoverycoachsession.trigger`.

- [ ] **Step 4: Extend the exemption in coach_service.py**

In `apps/accounts/coach_service.py`, change the exclude in `get_message_count_today`:

```python
    ).exclude(session__trigger='checkin_support').count()
```

to:

```python
    ).exclude(session__trigger__in=('checkin_support', 'sos')).count()
```

And in `can_send_message`, change:

```python
    Crisis-triggered (checkin_support) sessions are never limited.
    Free users get 3 routine messages/day; premium gets 20/day.
    """
    if session is not None and session.trigger == 'checkin_support':
        return True, None
```

to:

```python
    Crisis-triggered (checkin_support, sos) sessions are never limited.
    Free users get 3 routine messages/day; premium gets 20/day.
    """
    if session is not None and session.trigger in ('checkin_support', 'sos'):
        return True, None
```

- [ ] **Step 5: Add the view and URL**

In `apps/accounts/views.py`, directly after `coach_start_from_checkin` (~line 5060 — find the end of that function), add:

```python
@login_required
def coach_start_sos(request):
    """Open (or reuse) a Craving SOS coach session from the SOS page.

    The opener is static — no API call — so the coach responds instantly
    in a craving moment. SOS sessions share the checkin_support rate-limit
    exemption (see coach_service.can_send_message).
    """
    from apps.accounts.models import RecoveryCoachSession, CoachMessage

    today_start = timezone.now().replace(
        hour=0, minute=0, second=0, microsecond=0)
    session = RecoveryCoachSession.objects.filter(
        user=request.user, trigger='sos', created_at__gte=today_start,
    ).first()

    if session is None:
        RecoveryCoachSession.objects.filter(
            user=request.user, is_active=True).update(is_active=False)
        session = RecoveryCoachSession.objects.create(
            user=request.user, trigger='sos', is_active=True,
            title='Craving SOS',
        )
        CoachMessage.objects.create(
            session=session, role='assistant',
            content=(
                "I'm right here with you. Cravings feel overwhelming, but "
                "they rise, peak, and pass — usually within 20-30 minutes. "
                "Reaching out instead of giving in is exactly the right "
                "move. What's happening right now?"
            ),
        )
    else:
        RecoveryCoachSession.objects.filter(
            user=request.user, is_active=True,
        ).exclude(id=session.id).update(is_active=False)
        session.is_active = True
        session.save(update_fields=['is_active'])

    return redirect('accounts:recovery_coach')
```

(`login_required`, `timezone`, and `redirect` are already imported at the top of views.py — verify, and add only if genuinely missing.)

In `apps/accounts/urls.py`, after the `coach_start_from_checkin` entry (~line 218), add:

```python
    path('recovery-coach/sos/', views.coach_start_sos, name='coach_start_sos'),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_coach_sos -v 2`
Expected: OK, 7 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/models.py apps/accounts/coach_service.py apps/accounts/views.py apps/accounts/urls.py apps/accounts/migrations/ apps/accounts/test_coach_sos.py
git commit -m "feat(coach): never-rate-limited Craving SOS sessions with static opener

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: /craving-sos/ page — view, template, sitemap, cross-links

**Files:**
- Modify: `apps/core/views.py` (add view after `OnlineAAMeetingsView`)
- Modify: `apps/core/urls.py` (after the `online-aa-meetings/` line)
- Create: `apps/core/templates/core/craving_sos.html`
- Modify: `recovery_hub/sitemaps.py` (SEO landing pages block)
- Modify: `apps/core/templates/core/partials/_related_tools.html` (add card)
- Create: `apps/core/test_craving_sos.py`

**Interfaces:**
- Consumes: `starting_soon(hours=3, limit=6)` from Task 1 (each meeting has `minutes_until`, `timezone_display`, `conference_url`, `name`); URL `accounts:coach_start_sos` from Task 2; `user.pledge_reason` / `user.pledge_photo` (existing User fields).
- Produces: URL name `core:craving_sos` at `/craving-sos/`.

- [ ] **Step 1: Write the failing tests**

Create `apps/core/test_craving_sos.py`:

```python
"""Tests for the /craving-sos/ page."""
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CravingSOSPageTests(TestCase):
    def test_anonymous_gets_tools_but_no_anchor(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "id=\"sos-breathing\"")
        self.assertContains(resp, "id=\"sos-urge\"")
        self.assertContains(resp, "id=\"sos-grounding\"")
        self.assertContains(resp, "988")
        self.assertContains(resp, '"@type": "FAQPage"')
        self.assertNotContains(resp, "Talk to Anchor")

    def test_logged_in_gets_anchor_and_pledge_reason(self):
        user = User.objects.create_user(
            username="m", password="x", pledge_reason="For my daughter")
        self.client.force_login(user)
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Talk to Anchor")
        self.assertContains(resp, reverse("accounts:coach_start_sos"))
        self.assertContains(resp, "For my daughter")

    def test_soon_meetings_render_when_present(self):
        from unittest.mock import patch
        from apps.support_services.models import Meeting
        meeting = Meeting.objects.create(
            name="Wave Riders", slug="online-t-wave", day=1, time=time(19, 0),
            timezone="America/Chicago", attendance_option="online",
            conference_url="https://zoom.us/j/9",
            is_active=True, is_approved=True,
        )
        meeting.minutes_until = 25
        with patch("apps.core.views.starting_soon", return_value=[meeting]):
            resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "Wave Riders")
        self.assertContains(resp, "25 min")

    def test_sos_pill_in_nav(self):
        resp = self.client.get(reverse("core:craving_sos"))
        self.assertContains(resp, "sos-pill")

    def test_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/craving-sos/")
```

(`test_sos_pill_in_nav` will only pass after Task 4 adds the pill to base.html — mark it `@unittest.skip` is NOT allowed; instead Task 4 runs this file again. For this task's GREEN check, run the other four tests individually as shown in Step 6.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.core.test_craving_sos -v 2`
Expected: ERROR with `NoReverseMatch: 'craving_sos'`

- [ ] **Step 3: Add the view and URL**

In `apps/core/views.py`, add near the top of the file's import block (only if not already present): `from apps.support_services.meeting_queries import starting_soon` — import it at module level so tests can patch `apps.core.views.starting_soon`. Then add after `OnlineAAMeetingsView`:

```python
class CravingSOSView(TemplateView):
    """Craving SOS — the "2 AM toolbox".

    Public: breathing / urge surfing / grounding tools, crisis line, and
    online meetings starting soon. Logged-in members additionally get a
    one-tap never-rate-limited Anchor session and their pledge reason."""
    template_name = 'core/craving_sos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['soon_meetings'] = starting_soon(hours=3, limit=6)
        return context
```

In `apps/core/urls.py`, after the `online-aa-meetings/` line:

```python
    path('craving-sos/', views.CravingSOSView.as_view(), name='craving_sos'),
```

- [ ] **Step 4: Create the template**

Create `apps/core/templates/core/craving_sos.html`:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Craving SOS: Stop an Alcohol or Drug Craving Right Now{% endblock %}
{% block meta_description %}Free craving emergency toolbox: guided breathing, urge surfing timer, 5-4-3-2-1 grounding, and online AA meetings starting in the next 3 hours. No signup needed.{% endblock %}
{% block meta_keywords %}how to stop alcohol cravings, how to stop drug cravings, urge surfing, craving help, breathing exercise for cravings, craving emergency{% endblock %}

{% block canonical_url %}https://www.myrecoverypal.com/craving-sos/{% endblock %}

{% block structured_data %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "How long does a craving last?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Most cravings rise, peak, and pass within 20 to 30 minutes — even intense ones. They feel endless in the moment, but they are waves, not tides. Riding one out with a distraction, breathing, or a meeting makes the next one weaker."
      }
    },
    {
      "@type": "Question",
      "name": "What is urge surfing?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Urge surfing is a mindfulness technique: instead of fighting a craving, you observe it like a wave — noticing where you feel it, letting it build, peak, and fade without acting on it. Research shows it reduces both the intensity and the frequency of cravings over time."
      }
    },
    {
      "@type": "Question",
      "name": "Does deep breathing really help with cravings?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Slow, structured breathing like the 4-7-8 pattern activates the parasympathetic nervous system, lowering the stress response that fuels cravings. A few minutes of guided breathing gives the craving time to peak and pass."
      }
    },
    {
      "@type": "Question",
      "name": "When should I call 988 instead?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "If you are thinking about harming yourself, feel unsafe, or are in medical danger (severe withdrawal symptoms like seizures or hallucinations), call or text 988 (Suicide & Crisis Lifeline) or 911 immediately. Cravings are survivable; a crisis needs professional help now."
      }
    },
    {
      "@type": "Question",
      "name": "Can I really join an online AA meeting right now?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Online AA meetings run around the clock across every US time zone, are free, and are open to anyone. You can join with your camera off and just listen. This page shows meetings starting within the next 3 hours."
      }
    }
  ]
}
</script>
{% endblock %}

{% block extra_css %}
<style>
    .sos-crisis-strip {
        background: #b02a37; color: #fff; text-align: center;
        padding: 0.7rem 1rem; font-weight: 600;
    }
    .sos-crisis-strip a { color: #fff; text-decoration: underline; }
    .sos-wrap { max-width: 760px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
    .sos-wrap h1 { text-align: center; font-size: 1.9rem; margin: 1rem 0 0.5rem; }
    .sos-lede { text-align: center; opacity: 0.85; margin-bottom: 1.5rem; }
    .sos-tool {
        border: 1px solid rgba(128,128,128,0.25); border-radius: 14px;
        padding: 1.3rem; margin-bottom: 1.2rem;
    }
    .sos-tool h2 { font-size: 1.25rem; margin-bottom: 0.4rem; }
    .sos-tool p.sos-sub { opacity: 0.8; margin-bottom: 0.9rem; }
    .sos-btn {
        display: inline-block; border: none; cursor: pointer;
        background: var(--primary-color, #2c7a7b); color: #fff;
        font-weight: 600; font-size: 1rem;
        padding: 0.7rem 1.6rem; border-radius: 8px; text-decoration: none;
    }
    .sos-btn.secondary { background: #6c757d; }
    /* Breathing */
    #breath-circle {
        width: 130px; height: 130px; border-radius: 50%;
        background: var(--primary-color, #2c7a7b); opacity: 0.85;
        margin: 1rem auto; transition: transform 4s ease-in-out;
        transform: scale(0.6);
    }
    #breath-circle.inhale { transition-duration: 4s; transform: scale(1); }
    #breath-circle.hold { transition-duration: 0s; transform: scale(1); }
    #breath-circle.exhale { transition-duration: 8s; transform: scale(0.6); }
    #breath-phase { text-align: center; font-size: 1.15rem; font-weight: 600; min-height: 1.6em; }
    /* Urge surfing */
    #urge-bar-track {
        background: rgba(128,128,128,0.2); border-radius: 999px;
        height: 12px; margin: 0.9rem 0; overflow: hidden;
    }
    #urge-bar { background: var(--primary-color, #2c7a7b); height: 100%; width: 0%; }
    #urge-message { min-height: 3em; font-size: 1.05rem; }
    /* Grounding */
    #grounding-step { font-size: 1.1rem; min-height: 3.5em; margin-bottom: 0.6rem; }
    /* Meetings */
    .sos-meeting {
        display: flex; justify-content: space-between; align-items: center;
        gap: 0.8rem; padding: 0.7rem 0;
        border-bottom: 1px solid rgba(128,128,128,0.15);
    }
    .sos-meeting:last-child { border-bottom: none; }
    .sos-faq h3 { margin-top: 1.3rem; font-size: 1.05rem; }
</style>
{% endblock %}

{% block content %}
<div class="sos-crisis-strip">
    In danger or thinking of harming yourself? Call or text <a href="tel:988">988</a> now
    &middot; <a href="{% url 'core:crisis' %}">More crisis resources</a>
</div>

<div class="sos-wrap">
    <h1>Craving SOS</h1>
    <p class="sos-lede">This craving will pass — usually within 20&ndash;30 minutes.
        Pick a tool below and ride it out. You don't need an account.</p>

    {% if user.is_authenticated %}
    <div class="sos-tool" style="text-align:center;">
        {% if user.pledge_reason %}
        <p style="font-size:1.05rem; margin-bottom:0.8rem;">Remember why you started:
            <strong>&ldquo;{{ user.pledge_reason }}&rdquo;</strong></p>
        {% endif %}
        {% if user.pledge_photo %}
        <img src="{{ user.pledge_photo.url }}" alt="Your reason"
            style="max-width:180px; border-radius:12px; margin-bottom:0.8rem;">
        {% endif %}
        <a class="sos-btn" href="{% url 'accounts:coach_start_sos' %}">
            <i class="fas fa-anchor" aria-hidden="true"></i> Talk to Anchor now</a>
        <p style="opacity:0.75; margin-top:0.5rem; font-size:0.9rem;">
            Your AI recovery coach &mdash; SOS chats are never limited.</p>
    </div>
    {% else %}
    <div class="sos-tool" style="text-align:center;">
        <p style="margin-bottom:0.8rem;">Want a coach in your pocket for moments like this?</p>
        <a class="sos-btn" href="{% url 'accounts:register' %}">Get free support</a>
    </div>
    {% endif %}

    <div class="sos-tool" id="sos-breathing">
        <h2><i class="fas fa-wind" aria-hidden="true"></i> Guided breathing (4-7-8)</h2>
        <p class="sos-sub">Breathe in 4 seconds, hold 7, out 8. Four rounds takes about 80 seconds.</p>
        <div id="breath-circle"></div>
        <div id="breath-phase">Press start and follow the circle</div>
        <div style="text-align:center; margin-top:0.8rem;">
            <button class="sos-btn" id="breath-toggle" type="button">Start breathing</button>
            <span id="breath-count" style="margin-left:0.8rem; opacity:0.8;"></span>
        </div>
    </div>

    <div class="sos-tool" id="sos-urge">
        <h2><i class="fas fa-water" aria-hidden="true"></i> Urge surfing (10 minutes)</h2>
        <p class="sos-sub">Don't fight the wave &mdash; watch it. It will peak and pass.</p>
        <div id="urge-message">Press start. For the next 10 minutes your only job is to notice the craving, not act on it.</div>
        <div id="urge-bar-track"><div id="urge-bar"></div></div>
        <button class="sos-btn" id="urge-toggle" type="button">Start surfing</button>
        <span id="urge-clock" style="margin-left:0.8rem; opacity:0.8;"></span>
    </div>

    <div class="sos-tool" id="sos-grounding">
        <h2><i class="fas fa-hand" aria-hidden="true"></i> Grounding (5-4-3-2-1)</h2>
        <p class="sos-sub">Pull your mind back into the room, one sense at a time.</p>
        <div id="grounding-step">Press start when you're ready.</div>
        <button class="sos-btn" id="grounding-next" type="button">Start grounding</button>
    </div>

    <div class="sos-tool">
        <h2><i class="fas fa-video" aria-hidden="true"></i> Meetings starting soon</h2>
        <p class="sos-sub">Real people, right now. Camera off is fine &mdash; just listen.</p>
        {% for meeting in soon_meetings %}
        <div class="sos-meeting">
            <div>
                <strong>{{ meeting.name }}</strong><br>
                <span style="opacity:0.75;">in {{ meeting.minutes_until }} min
                    ({{ meeting.time|time:"g:i A" }} {{ meeting.timezone_display }})</span>
            </div>
            <a class="sos-btn" href="{{ meeting.conference_url }}"
                target="_blank" rel="noopener">Join</a>
        </div>
        {% empty %}
        <p>No meetings in the next 3 hours &mdash; but the
            <a href="{% url 'core:online_aa_meetings' %}">full directory</a> has
            1,500+ online meetings across every time zone.</p>
        {% endfor %}
        <p style="margin-top:0.8rem;"><a href="{% url 'support_services:meeting_list' %}?attendance=online">Browse all online meetings &rarr;</a></p>
    </div>

    <div class="sos-faq">
        <h2>Craving questions, answered</h2>
        <h3>How long does a craving last?</h3>
        <p>Most cravings rise, peak, and pass within 20&ndash;30 minutes — even intense ones. They feel endless in the moment, but they are waves, not tides.</p>
        <h3>What is urge surfing?</h3>
        <p>A mindfulness technique: instead of fighting a craving, you observe it like a wave — noticing where you feel it, letting it build, peak, and fade without acting on it.</p>
        <h3>Does deep breathing really help?</h3>
        <p>Yes. Slow, structured breathing like 4-7-8 activates the parasympathetic nervous system, lowering the stress response that fuels cravings.</p>
        <h3>When should I call 988 instead?</h3>
        <p>If you are thinking about harming yourself, feel unsafe, or have severe withdrawal symptoms (seizures, hallucinations), call or text 988 or 911 immediately.</p>
        <h3>Can I really join an AA meeting right now?</h3>
        <p>Yes — online AA meetings run around the clock, are free, and you can join with your camera off and just listen.</p>
    </div>
</div>

{% include 'core/partials/_related_tools.html' with exclude='craving_sos' %}
{% endblock %}

{% block extra_js %}
<script>
(function () {
    // ---- Breathing: 4-7-8, four rounds ----
    var breathBtn = document.getElementById('breath-toggle');
    var circle = document.getElementById('breath-circle');
    var phaseEl = document.getElementById('breath-phase');
    var countEl = document.getElementById('breath-count');
    var breathTimer = null, round = 0;
    var PHASES = [
        {cls: 'inhale', label: 'Breathe in…', secs: 4},
        {cls: 'hold',   label: 'Hold…',       secs: 7},
        {cls: 'exhale', label: 'Breathe out…', secs: 8},
    ];
    function runPhase(i) {
        if (i === 0) {
            round += 1;
            if (round > 4) { stopBreathing('Nice work. Notice how you feel.'); return; }
            countEl.textContent = 'Round ' + round + ' of 4';
        }
        var p = PHASES[i];
        circle.className = p.cls;
        phaseEl.textContent = p.label;
        breathTimer = setTimeout(function () { runPhase((i + 1) % 3); }, p.secs * 1000);
    }
    function stopBreathing(msg) {
        clearTimeout(breathTimer); breathTimer = null; round = 0;
        circle.className = ''; countEl.textContent = '';
        phaseEl.textContent = msg || 'Press start and follow the circle';
        breathBtn.textContent = 'Start breathing';
    }
    breathBtn.addEventListener('click', function () {
        if (breathTimer) { stopBreathing(); return; }
        breathBtn.textContent = 'Stop';
        runPhase(0);
    });

    // ---- Urge surfing: 10-minute staged walkthrough ----
    var urgeBtn = document.getElementById('urge-toggle');
    var urgeBar = document.getElementById('urge-bar');
    var urgeMsg = document.getElementById('urge-message');
    var urgeClock = document.getElementById('urge-clock');
    var URGE_TOTAL = 600; // seconds
    var urgeElapsed = 0, urgeTimer = null;
    var STAGES = [
        [0,   'Find where the craving lives in your body. Chest? Stomach? Jaw? Just notice it.'],
        [120, 'It may be building. That’s the wave rising — it cannot rise forever.'],
        [300, 'Halfway. Waves peak. If it hasn’t already, it will soon — keep watching it, not fighting it.'],
        [480, 'It’s losing power. You’ve out-lasted the worst of it.'],
    ];
    function urgeTick() {
        urgeElapsed += 1;
        urgeBar.style.width = (urgeElapsed / URGE_TOTAL * 100) + '%';
        var m = Math.floor((URGE_TOTAL - urgeElapsed) / 60);
        var s = (URGE_TOTAL - urgeElapsed) % 60;
        urgeClock.textContent = m + ':' + (s < 10 ? '0' : '') + s + ' left';
        for (var i = STAGES.length - 1; i >= 0; i--) {
            if (urgeElapsed >= STAGES[i][0]) { urgeMsg.textContent = STAGES[i][1]; break; }
        }
        if (urgeElapsed >= URGE_TOTAL) {
            stopUrge('You rode it out. That craving passed — and so will the next one.');
        }
    }
    function stopUrge(msg) {
        clearInterval(urgeTimer); urgeTimer = null; urgeElapsed = 0;
        urgeClock.textContent = '';
        if (msg) { urgeMsg.textContent = msg; urgeBar.style.width = '100%'; }
        else { urgeMsg.textContent = 'Press start. For the next 10 minutes your only job is to notice the craving, not act on it.'; urgeBar.style.width = '0%'; }
        urgeBtn.textContent = 'Start surfing';
    }
    urgeBtn.addEventListener('click', function () {
        if (urgeTimer) { stopUrge(); return; }
        urgeBtn.textContent = 'Stop';
        urgeBar.style.width = '0%';
        urgeMsg.textContent = STAGES[0][1];
        urgeTimer = setInterval(urgeTick, 1000);
    });

    // ---- Grounding: 5-4-3-2-1 tap-through ----
    var gBtn = document.getElementById('grounding-next');
    var gStep = document.getElementById('grounding-step');
    var G_STEPS = [
        'Name 5 things you can SEE. Look around slowly — anything counts.',
        'Name 4 things you can HEAR. The hum of a fridge, traffic, your own breath.',
        'Name 3 things you can TOUCH. Feel their texture for a moment.',
        'Name 2 things you can SMELL (or two smells you like).',
        'Name 1 thing you can TASTE. Take a sip of water if you have one.',
        'You’re here, in this room, in this moment. The craving is just a visitor — and it’s leaving.',
    ];
    var gIndex = -1;
    gBtn.addEventListener('click', function () {
        gIndex += 1;
        if (gIndex >= G_STEPS.length) {
            gIndex = -1;
            gStep.textContent = 'Press start when you’re ready.';
            gBtn.textContent = 'Start grounding';
            return;
        }
        gStep.textContent = G_STEPS[gIndex];
        gBtn.textContent = gIndex === G_STEPS.length - 1 ? 'Done' : 'Next';
    });
})();
</script>
{% endblock %}
```

- [ ] **Step 5: Sitemap + related-tools card**

In `recovery_hub/sitemaps.py`, after the `core:online_aa_meetings` line, add:

```python
            ('core:craving_sos', 0.9),  # "how to stop cravings" — interactive SOS toolbox
```

In `apps/core/templates/core/partials/_related_tools.html`, after the `online_aa_meetings` card's `{% endif %}`, add (matching the existing card markup exactly):

```django
            {% if exclude != 'craving_sos' %}
            <a href="{% url 'core:craving_sos' %}" style="background: white; padding: 1.5rem; border-radius: 12px; text-decoration: none; box-shadow: 0 2px 8px rgba(0,0,0,0.08); transition: transform 0.2s;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;"><i class="fas fa-life-ring" aria-hidden="true"></i></div>
                <h3 style="color: var(--primary-dark); font-size: 1.1rem; margin-bottom: 0.5rem;">Craving SOS</h3>
                <p style="color: #666; font-size: 0.9rem; margin: 0;">Guided breathing, urge surfing, and grounding tools for craving moments. Free, no signup.</p>
            </a>
            {% endif %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.core.test_craving_sos -v 2`
Expected: 4 of 5 pass; `test_sos_pill_in_nav` FAILS (the pill lands in Task 4). Verify the other four are green:
`python manage.py test apps.core.test_craving_sos.CravingSOSPageTests.test_anonymous_gets_tools_but_no_anchor apps.core.test_craving_sos.CravingSOSPageTests.test_logged_in_gets_anchor_and_pledge_reason apps.core.test_craving_sos.CravingSOSPageTests.test_soon_meetings_render_when_present apps.core.test_craving_sos.CravingSOSPageTests.test_in_sitemap -v 2`
Expected: OK, 4 tests passing

- [ ] **Step 7: Commit**

```bash
git add apps/core/views.py apps/core/urls.py apps/core/templates/core/craving_sos.html recovery_hub/sitemaps.py apps/core/templates/core/partials/_related_tools.html apps/core/test_craving_sos.py
git commit -m "feat(sos): /craving-sos/ page with breathing, urge surfing, grounding, meetings soon

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: SOS pill in the nav

**Files:**
- Modify: `templates/base.html` (inside `<div class="nav-right">`, ~line 246)
- Modify: `static/css/base-inline.css` (append)
- Test: `apps/core/test_craving_sos.py` (`test_sos_pill_in_nav`, written in Task 3)

**Interfaces:**
- Consumes: URL name `core:craving_sos` from Task 3.
- Produces: `.sos-pill` nav element on every page (base.html is the global layout).

- [ ] **Step 1: Run the failing test**

Run: `python manage.py test apps.core.test_craving_sos.CravingSOSPageTests.test_sos_pill_in_nav -v 2`
Expected: FAIL — response does not contain "sos-pill"

- [ ] **Step 2: Add the pill to base.html**

In `templates/base.html`, immediately after the `<div class="nav-right">` opening tag (~line 246, BEFORE `{% if user.is_authenticated %}`), add:

```django
                <a href="{% url 'core:craving_sos' %}" class="sos-pill"
                    title="Craving SOS — get help right now">SOS</a>
```

- [ ] **Step 3: Add the CSS**

Append to `static/css/base-inline.css`:

```css
/* Craving SOS nav pill — always visible, including in the native apps
   (the native ultra-minimal nav hides other extras; SOS must survive). */
.sos-pill {
    background: #dc3545;
    color: #fff !important;
    font-weight: 700;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    text-decoration: none;
    margin-right: 0.5rem;
    flex-shrink: 0;
    align-self: center;
}
.sos-pill:hover { background: #b02a37; color: #fff; }
.ios-native-app .sos-pill,
.android-native-app .sos-pill { display: inline-block !important; }
```

- [ ] **Step 4: Run the full page test file**

Run: `python manage.py test apps.core.test_craving_sos -v 2`
Expected: OK, 5 tests passing

- [ ] **Step 5: Visual check**

Launch per `.claude/skills/verify/SKILL.md` (`DEBUG=true python3 manage.py runserver 8765`, curl with `Host: www.myrecoverypal.com`) and confirm the pill markup appears in the nav on `/` and `/craving-sos/`. The full interactive browser pass happens at the end of the plan.

- [ ] **Step 6: Commit**

```bash
git add templates/base.html static/css/base-inline.css
git commit -m "feat(sos): persistent SOS pill in the site nav

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Verify, changelog, merge, deploy

**Files:**
- Modify: `docs/CHANGELOG.md` (new dated entry at the top of the list)

- [ ] **Step 1: Full test sweep of touched modules**

Run: `python manage.py test apps.support_services.test_meeting_queries apps.accounts.test_coach_sos apps.core.test_craving_sos apps.support_services.test_meeting_sync apps.core.test_online_aa_meetings -v 1`
Expected: OK, 40 tests (8 + 7 + 5 + 17 + 3)

- [ ] **Step 2: End-to-end browser verification**

Per `.claude/skills/verify/SKILL.md`: run the dev server, then drive `/craving-sos/` in a real browser (breathing circle animates through in/hold/out; urge-surfing bar advances and stage copy changes; grounding steps advance and reset; meetings-soon list or fallback renders; anonymous vs logged-in Anchor slot). Probe: double-click start buttons (toggle cleanly), Stop mid-cycle resets state.

- [ ] **Step 3: Changelog entry**

Add at the top of the list in `docs/CHANGELOG.md`:

```markdown
- **2026-07-10:** Craving SOS page — public "2 AM toolbox" at `/craving-sos/`: pinned 988 crisis strip, guided 4-7-8 breathing (animated), 10-minute urge-surfing walkthrough, 5-4-3-2-1 grounding, and online meetings starting within 3 hours (new timezone-aware `apps/support_services/meeting_queries.py::starting_soon`). Logged-in members get their pledge reason/photo and one-tap "Talk to Anchor" via new `coach_start_sos` view — `sos` trigger added to `RecoveryCoachSession.TRIGGER_CHOICES` and exempted from rate limits like `checkin_support` (never paywalled mid-craving; static opener, no API latency). Persistent SOS pill added to the nav (web + native). SEO: FAQPage schema, sitemap 0.9, `_related_tools` cross-links. 20 new tests.
```

- [ ] **Step 4: Commit, merge, deploy**

```bash
git add docs/CHANGELOG.md
git commit -m "docs: changelog entry for Craving SOS page

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then follow superpowers:finishing-a-development-branch (merge to main deploys via Railway). Post-deploy: `python manage.py migrate` runs automatically via start.sh; verify `https://www.myrecoverypal.com/craving-sos/` renders, the SOS pill shows in the nav, and (logged in) the Anchor button opens a coach session. Submit the URL in Google Search Console (manual, Ryan).

---

## Self-Review Notes

- Spec coverage: §1 view/URL/sitemap/related-tools → Task 3; §2 `starting_soon` + tz/midnight tests → Task 1; §3 three inline-JS tools → Task 3 template; §4 crisis strip + `sos` trigger/exemption/`coach_start_sos` → Tasks 2-3; §5 nav pill incl. native visibility → Task 4; §6 SEO → Task 3; spec's testing list → Tasks 1-4; manual JS pass + success verification → Task 5.
- Cross-task consistency: `starting_soon(hours=3, limit=6)` (T1) is what T3's view imports at module level (patchable as `apps.core.views.starting_soon`); `accounts:coach_start_sos` (T2) is what T3's template reverses; `core:craving_sos` (T3) is what T4's pill reverses. `test_sos_pill_in_nav` is written in T3 but goes green in T4 — intentional, called out in both tasks.
- Test-count arithmetic: T1=8, T2=7, T3=5 (4 green in T3, 5th in T4), plus the prior feature's 20 → 40 in the Task 5 sweep.
