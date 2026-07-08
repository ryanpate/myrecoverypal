# Member Email Sequences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current 3-email welcome drip with the 6-email onboarding sequence and add the 3-email re-engagement sequence from `~/Downloads/pack/email-sequences.md`, running automatically via Celery Beat.

**Architecture:** Sequence definitions and eligibility helpers live in a new `apps/accounts/email_sequences.py`. Two thin daily Celery tasks in `apps/accounts/tasks.py` (`send_onboarding_sequence_emails` for E2–E6, `send_reengagement_emails` for R1–R3) iterate users and send whichever email is due. E1 stays signal-triggered on onboarding completion (existing `send_welcome_email_day_1`, rewritten). Per-email sent-timestamps on `User` make everything idempotent, matching the existing `welcome_email_N_sent` pattern.

**Tech Stack:** Django 5.0.10, Celery 5.3.4 (Beat schedule in `recovery_hub/settings.py::CELERY_BEAT_SCHEDULE`), `apps/accounts/email_service.py::send_email` (Resend API), Django template emails.

## Global Constraints

- **Voice rules (from spec):** warm, peer-to-peer, no shame, no medical claims, program-neutral. **Never guilt-trip absence** — never state how long a user has been gone. Copy in this plan is final; do not rewrite it.
- **Crisis suppression is non-negotiable (from spec):** a user with a crisis-triggered coach session (`RecoveryCoachSession.trigger='checkin_support'`) updated in the last 48 hours receives NO sequence email.
- **Suppression (both sequences):** `is_active=True`, `email_notifications=True`, `marketing_emails_enabled=True` required; crisis check on top.
- `send_email(...)` returns a `(success: bool, error: str|None)` tuple — always unpack it.
- All new user-facing emails include the marketing unsubscribe link (`/email/unsubscribe/<token>/`, view `apps/accounts/email_views.py::unsubscribe_marketing`, token = `signing.dumps({'user_id': X, 'kind': 'marketing'})`).
- Match existing code style in `apps/accounts/tasks.py` (logging, `time.sleep(0.5)` between sends, `save(update_fields=[...])`).
- Tests: Django `TestCase`, run with `python manage.py test apps.accounts.test_email_sequences -v 2`. Patch `apps.accounts.tasks.send_email` (it's imported into the tasks module namespace) to return `(True, None)`.
- Run migrations/tests from repo root `/Users/ryanpate/myrecoverypal`.

## Feature → codebase mapping (used throughout)

| Spec concept | Codebase reality | CTA URL |
|---|---|---|
| "Start your streak" | Daily check-in on progress home | `{site_url}/accounts/progress/` |
| Anchor | AI Recovery Coach | `{site_url}/accounts/recovery-coach/` |
| Journal | `apps.journal.models.JournalEntry` (related_name `journal_entries`) | `{site_url}/journal/write/` |
| Community feed | Social feed | `{site_url}/accounts/social-feed/` |
| "Medallion" | Milestone/streak on progress home | `{site_url}/accounts/progress/` |
| Anchor used | `CoachMessage.objects.filter(session__user=u, role='user').exists()` | — |
| Community action | authored `social_posts` OR `post_comments` OR `post_reactions` OR `liked_posts` | — |
| Login/activity | max of `User.last_seen`, `User.last_login`, `User.date_joined` | — |
| Crisis flag | `RecoveryCoachSession(trigger='checkin_support')` updated in last 48h | — |
| "Newsletter list" exit | No-op — weekly digest already goes to all users; exiting just stops the drip | — |

---

### Task 1: User model fields + migration

**Files:**
- Modify: `apps/accounts/models.py` (after `premium_nudge_sent`, ~line 121)
- Create: `apps/accounts/migrations/0059_user_email_sequence_fields.py` (via makemigrations)

**Interfaces:**
- Produces: 8 nullable `DateTimeField`s on `User`: `onboarding_email_2_sent` … `onboarding_email_6_sent`, `reengagement_email_1_sent` … `reengagement_email_3_sent`. Later tasks read/write them via `getattr`/`setattr`.
- Note: existing `welcome_email_1_sent` is reused as the E1 sent-marker; `welcome_email_2_sent`/`welcome_email_3_sent` stay untouched (historical data for the retired day-3/day-7 emails).

- [ ] **Step 1: Add the fields**

In `apps/accounts/models.py`, directly below the `premium_nudge_sent` field definition, add:

```python
    # Onboarding email sequence (E2–E6; E1 uses welcome_email_1_sent)
    onboarding_email_2_sent = models.DateTimeField(null=True, blank=True,
        help_text="Onboarding E2 (Anchor, day 1) sent/skipped timestamp")
    onboarding_email_3_sent = models.DateTimeField(null=True, blank=True,
        help_text="Onboarding E3 (journal, day 3) sent/skipped timestamp")
    onboarding_email_4_sent = models.DateTimeField(null=True, blank=True,
        help_text="Onboarding E4 (community, day 6) sent/skipped timestamp")
    onboarding_email_5_sent = models.DateTimeField(null=True, blank=True,
        help_text="Onboarding E5 (milestone, day 9) sent/skipped timestamp")
    onboarding_email_6_sent = models.DateTimeField(null=True, blank=True,
        help_text="Onboarding E6 (check-in, day 14) sent/skipped timestamp")

    # Re-engagement email sequence (triggered after 21 days inactive)
    reengagement_email_1_sent = models.DateTimeField(null=True, blank=True,
        help_text="Re-engagement R1 (door open) sent timestamp")
    reengagement_email_2_sent = models.DateTimeField(null=True, blank=True,
        help_text="Re-engagement R2 (what's new) sent timestamp")
    reengagement_email_3_sent = models.DateTimeField(null=True, blank=True,
        help_text="Re-engagement R3 (honest ask) sent timestamp")
```

- [ ] **Step 2: Generate and run the migration**

Run: `python manage.py makemigrations accounts -n user_email_sequence_fields && python manage.py migrate accounts`
Expected: creates `0059_user_email_sequence_fields.py` (or next free number), applies cleanly.

- [ ] **Step 3: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/
git commit -m "feat(emails): add sequence tracking fields to User"
```

---

### Task 2: `email_sequences.py` — eligibility helpers + sequence config

**Files:**
- Create: `apps/accounts/email_sequences.py`
- Test: `apps/accounts/test_email_sequences.py` (new file, grows in later tasks)

**Interfaces:**
- Consumes: Task 1 fields; `RecoveryCoachSession`, `CoachMessage`, `JournalEntry` models.
- Produces (used by Tasks 4–6):
  - `has_started_streak(user) -> bool`
  - `has_journal_entry(user) -> bool`
  - `has_community_action(user) -> bool`
  - `has_used_anchor(user) -> bool`
  - `is_activated(user) -> bool` (all three key actions)
  - `is_crisis_suppressed(user) -> bool` (48h window)
  - `get_last_activity(user) -> datetime`
  - `marketing_unsubscribe_url(user) -> str`
  - `ONBOARDING_EMAILS: list[dict]` with keys `number:int, day:int, template:str, subject:str, field:str, skip: callable|None`

- [ ] **Step 1: Write failing tests**

Create `apps/accounts/test_email_sequences.py`:

```python
"""Tests for the onboarding + re-engagement email sequences."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import (
    User, DailyCheckIn, SocialPost, RecoveryCoachSession, CoachMessage,
)
from apps.journal.models import JournalEntry
from apps.accounts import email_sequences as seq


def make_user(username='pal', days_ago=0, **kwargs):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='x',
        **kwargs,
    )
    if days_ago:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=days_ago))
        user.refresh_from_db()
    return user


class EligibilityHelperTests(TestCase):
    def test_activation_requires_all_three_actions(self):
        user = make_user()
        self.assertFalse(seq.is_activated(user))
        DailyCheckIn.objects.create(user=user, mood=3, energy_level=3)
        JournalEntry.objects.create(user=user, content='one line')
        self.assertFalse(seq.is_activated(user))
        SocialPost.objects.create(author=user, content='hello')
        self.assertTrue(seq.is_activated(user))

    def test_has_used_anchor(self):
        user = make_user()
        self.assertFalse(seq.has_used_anchor(user))
        session = RecoveryCoachSession.objects.create(user=user)
        CoachMessage.objects.create(session=session, role='user', content='hi')
        self.assertTrue(seq.has_used_anchor(user))

    def test_crisis_suppression_window(self):
        user = make_user()
        self.assertFalse(seq.is_crisis_suppressed(user))
        session = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support')
        self.assertTrue(seq.is_crisis_suppressed(user))
        # Age the session past 48h
        RecoveryCoachSession.objects.filter(pk=session.pk).update(
            updated_at=timezone.now() - timedelta(hours=49))
        self.assertFalse(seq.is_crisis_suppressed(user))

    def test_get_last_activity_takes_most_recent_signal(self):
        user = make_user(days_ago=30)
        self.assertEqual(seq.get_last_activity(user), user.date_joined)
        user.last_seen = timezone.now() - timedelta(days=2)
        self.assertEqual(seq.get_last_activity(user), user.last_seen)

    def test_unsubscribe_url_contains_token_path(self):
        user = make_user()
        url = seq.marketing_unsubscribe_url(user)
        self.assertIn('/email/unsubscribe/', url)
        self.assertTrue(url.startswith('http'))
```

Note: check `SocialPost` field names against the model before finalizing — the author FK is `author` (related_name `social_posts`) and the text field is `content` (verify with `grep -n "content\|body" apps/accounts/models.py | sed -n '/1834/,/1919/p'`; if the field is `body`, adjust the test). Same for `DailyCheckIn` required fields (`mood`, `energy_level` are required; `date` defaults to today).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: FAIL — `ImportError`/`ModuleNotFoundError: apps.accounts.email_sequences`

- [ ] **Step 3: Implement the module**

Create `apps/accounts/email_sequences.py`:

```python
"""Eligibility helpers and definitions for the member email sequences.

Two sequences (spec: ~/Downloads/pack/email-sequences.md):
- Onboarding: E1 immediately (signal-triggered), E2–E6 on days 1/3/6/9/14.
  Early exit once the user has done the three actions that predict
  retention: a check-in (streak), a journal entry, a community action.
- Re-engagement: R1/R2/R3 at days 0/5/12 after 21 days of inactivity.

Suppression (both): unsubscribed, notifications off, or a crisis-triggered
coach session in the last 48h. A person in crisis must never receive
"check your streak!".
"""
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

CRISIS_SUPPRESSION_HOURS = 48
INACTIVITY_DAYS = 21
REENGAGEMENT_REENTRY_DAYS = 90


def has_started_streak(user):
    return user.daily_checkins.exists()


def has_journal_entry(user):
    return user.journal_entries.exists()


def has_community_action(user):
    return (
        user.social_posts.exists()
        or user.post_comments.exists()
        or user.post_reactions.exists()
        or user.liked_posts.exists()
    )


def is_activated(user):
    """All three retention-predicting actions done -> exit onboarding early."""
    return (
        has_started_streak(user)
        and has_journal_entry(user)
        and has_community_action(user)
    )


def has_used_anchor(user):
    from .models import CoachMessage
    return CoachMessage.objects.filter(
        session__user=user, role='user').exists()


def is_crisis_suppressed(user):
    """True if the user opened a crisis-triggered coach session recently."""
    from .models import RecoveryCoachSession
    cutoff = timezone.now() - timedelta(hours=CRISIS_SUPPRESSION_HOURS)
    return RecoveryCoachSession.objects.filter(
        user=user, trigger='checkin_support', updated_at__gte=cutoff,
    ).exists()


def get_last_activity(user):
    """Most recent activity signal we have for the user."""
    candidates = [user.date_joined]
    if user.last_login:
        candidates.append(user.last_login)
    if user.last_seen:
        candidates.append(user.last_seen)
    return max(candidates)


def marketing_unsubscribe_url(user):
    token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com')
    return f"{site_url}/email/unsubscribe/{token}/"


# E1 (welcome, day 0) is signal-triggered; see tasks.send_welcome_email_day_1.
ONBOARDING_EMAILS = [
    {
        'number': 2, 'day': 1,
        'template': 'emails/onboarding_2.html',
        'subject': "Meet Anchor (it's awake when no one else is)",
        'field': 'onboarding_email_2_sent',
        'skip': has_used_anchor,  # spec: skip if member already used Anchor
    },
    {
        'number': 3, 'day': 3,
        'template': 'emails/onboarding_3.html',
        'subject': "The journal only you can read",
        'field': 'onboarding_email_3_sent',
        'skip': None,
    },
    {
        'number': 4, 'day': 6,
        'template': 'emails/onboarding_4.html',
        'subject': "Someone in the community said this today",
        'field': 'onboarding_email_4_sent',
        'skip': None,
    },
    {
        'number': 5, 'day': 9,
        'template': 'emails/onboarding_5.html',
        'subject': "Your first medallion is closer than you think",
        'field': 'onboarding_email_5_sent',
        'skip': None,
    },
    {
        'number': 6, 'day': 14,
        'template': 'emails/onboarding_6.html',
        'subject': "How's it going? (really)",
        'field': 'onboarding_email_6_sent',
        'skip': None,
    },
]

REENGAGEMENT_EMAILS = [
    {
        'number': 1, 'day': 0,
        'template': 'emails/reengagement_1.html',
        'subject': "Your seat's still here 💙",
        'field': 'reengagement_email_1_sent',
    },
    {
        'number': 2, 'day': 5,
        'template': 'emails/reengagement_2.html',
        'subject': "What you've missed (the good kind)",
        'field': 'reengagement_email_2_sent',
    },
    {
        'number': 3, 'day': 12,
        'template': 'emails/reengagement_3.html',
        'subject': "One honest question",
        'field': 'reengagement_email_3_sent',
    },
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/email_sequences.py apps/accounts/test_email_sequences.py
git commit -m "feat(emails): add sequence eligibility helpers and definitions"
```

---

### Task 3: Email templates (base + 9 emails)

**Files:**
- Create: `apps/accounts/templates/emails/sequence_base.html`
- Create: `apps/accounts/templates/emails/onboarding_1.html` … `onboarding_6.html`
- Create: `apps/accounts/templates/emails/reengagement_1.html` … `reengagement_3.html`
- Test: `apps/accounts/test_email_sequences.py` (append render smoke test)

**Interfaces:**
- Consumes: nothing from other tasks (pure templates).
- Produces: templates rendered by Tasks 4–6 with context keys `user`, `site_url`, `current_year`, `unsubscribe_url` (+ `streak`, `has_streak` for onboarding_5 only).

- [ ] **Step 1: Write failing render smoke test**

Append to `apps/accounts/test_email_sequences.py`:

```python
from django.template.loader import render_to_string


class TemplateRenderTests(TestCase):
    def test_all_sequence_templates_render(self):
        user = make_user(username='render')
        templates = (
            ['emails/onboarding_1.html']
            + [e['template'] for e in seq.ONBOARDING_EMAILS]
            + [e['template'] for e in seq.REENGAGEMENT_EMAILS]
        )
        for tpl in templates:
            html = render_to_string(tpl, {
                'user': user,
                'site_url': 'https://www.myrecoverypal.com',
                'current_year': 2026,
                'unsubscribe_url': 'https://www.myrecoverypal.com/email/unsubscribe/x/',
                'streak': 3,
                'has_streak': True,
            })
            self.assertIn('unsubscribe', html.lower(), tpl)
            self.assertIn('render', html, tpl)  # greeting uses username fallback
```

- [ ] **Step 2: Run to verify it fails**

Run: `python manage.py test apps.accounts.test_email_sequences.TemplateRenderTests -v 2`
Expected: FAIL — `TemplateDoesNotExist: emails/sequence_base.html` (or onboarding_1)

- [ ] **Step 3: Create the base template**

`apps/accounts/templates/emails/sequence_base.html` (style lifted from `welcome_day_1.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MyRecoveryPal{% endblock %}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .email-container {
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .logo {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #1e4d8b 0%, #4db8e8 60%, #52b788 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        p { color: #555; font-size: 15px; }
        .cta-wrap { text-align: center; margin: 30px 0; }
        .cta {
            display: inline-block;
            background: linear-gradient(135deg, #52b788, #40916c);
            color: white !important;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 50px;
            font-weight: 600;
            font-size: 16px;
        }
        .signoff { color: #555; font-size: 15px; margin-top: 28px; }
        .footer {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
        }
        .footer a { color: #999; }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <div class="logo">MyRecoveryPal</div>
        </div>
        {% block content %}{% endblock %}
        <p class="signoff">One day at a time,<br>The MyRecoveryPal team</p>
        {% block postscript %}{% endblock %}
    </div>
    <div class="footer">
        <p>&copy; {{ current_year }} MyRecoveryPal · No judgment, no ads, ever.</p>
        <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> from these emails anytime.</p>
    </div>
</body>
</html>
```

- [ ] **Step 4: Create the 9 email templates**

`apps/accounts/templates/emails/onboarding_1.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}Welcome to MyRecoveryPal{% endblock %}
{% block content %}
<p>Hi {{ user.first_name|default:user.username }},</p>
<p>Welcome to MyRecoveryPal. Whatever brought you here — day one, year ten, or
somewhere in the messy middle — you belong here.</p>
<p>This community runs on three promises: <strong>no judgment, no ads,
ever.</strong> Just tools and people for the road ahead.</p>
<p>Here's the one thing worth doing today (it takes 10 seconds): start your
streak. It becomes your first medallion sooner than you'd think.</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/accounts/progress/">Start my streak &rarr;</a>
</div>
{% endblock %}
{% block postscript %}
<p style="color: #888; font-size: 13px;">P.S. This inbox is a real one. Reply
anytime — a human reads it.</p>
{% endblock %}
```

`apps/accounts/templates/emails/onboarding_2.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}Meet Anchor{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>Cravings and racing thoughts don't make appointments. They show up at 2am,
in the car, at the family dinner.</p>
<p>That's what <strong>Anchor</strong> is for — an AI recovery coach inside
MyRecoveryPal you can talk to any hour, about anything, with zero judgment.
It's not therapy, and it doesn't replace your people. It's the thing you reach
for in the gap.</p>
<p>Try it now so it's familiar before you need it:</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/accounts/recovery-coach/">Say hi to Anchor &rarr;</a>
</div>
{% endblock %}
```

`apps/accounts/templates/emails/onboarding_3.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}The journal only you can read{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>Some things are easier to write than to say out loud.</p>
<p>Your MyRecoveryPal journal is completely private — visible to you and no one
else, ever. People use it for cravings they rode out, wins nobody else noticed,
and the stuff that's not ready to be said in a meeting.</p>
<p>Today's ask is tiny: write <strong>one line.</strong> "Today was hard but
I'm here" counts.</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/journal/write/">Write one line &rarr;</a>
</div>
{% endblock %}
```

`apps/accounts/templates/emails/onboarding_4.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}You're not doing this alone{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>The best recovery advice doesn't come from ads or algorithms. It comes from
people a few steps ahead on the same road.</p>
<p>That's the community feed: people celebrating 24 hours, people on year eight
answering questions, people just saying "today was rough" and getting twenty
replies that say "same, and here's what helped."</p>
<p>Drop in and leave one comment or one 💙 on someone's post. That's how
belonging starts.</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/accounts/social-feed/">See what people are sharing &rarr;</a>
</div>
{% endblock %}
```

`apps/accounts/templates/emails/onboarding_5.html` (variant per spec: if no streak yet, swap first line and CTA):

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}Your first medallion is closer than you think{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
{% if has_streak %}
<p>Quick check-in: your streak is building toward your first medallion — a
marker you've <em>earned</em>, that nobody can take.</p>
{% else %}
<p>It's not too late to start counting — day one starts whenever you say it
does. Your streak becomes your first medallion — a marker you've
<em>earned</em>, that nobody can take.</p>
{% endif %}
<p>People keep them private, share them with a sponsor, or post them to the
feed and collect a wall of congratulations. Your call. Your recovery.</p>
<div class="cta-wrap">
    {% if has_streak %}
    <a class="cta" href="{{ site_url }}/accounts/progress/">Check my streak &rarr;</a>
    {% else %}
    <a class="cta" href="{{ site_url }}/accounts/progress/">Start my streak today &rarr;</a>
    {% endif %}
</div>
{% endblock %}
```

`apps/accounts/templates/emails/onboarding_6.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}Two weeks in — one question{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>You've been a member for two weeks, so — honestly — how's it going?</p>
<p>Not a survey. Just hit reply and tell us one thing: what's working, what's
confusing, or what you wish MyRecoveryPal did. A real human reads every reply,
and member answers have already shaped the site.</p>
<p>And if the last two weeks have been heavy: that's not failure, that's the
road. The community and Anchor are there on the hard days especially.</p>
{% endblock %}
```

`apps/accounts/templates/emails/reengagement_1.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}Your seat's still here{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>Just one thing, said plainly: your seat in the community is still here, and
it doesn't matter how long it's been.</p>
<p>Streak broken? Streaks restart. Rough stretch? That's exactly what this
place is for. Nothing to explain, nothing to catch up on.</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/accounts/social-feed/">Come say hi &rarr;</a>
</div>
{% endblock %}
```

`apps/accounts/templates/emails/reengagement_2.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}New since you were here{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>Since you were last here: new members joining daily, new milestones on the
feed every week, and Anchor's been there for a lot of 2am conversations.</p>
<p>The door's open whenever. One tap and you're back in the room.</p>
<div class="cta-wrap">
    <a class="cta" href="{{ site_url }}/accounts/social-feed/">See what's new &rarr;</a>
</div>
{% endblock %}
```

`apps/accounts/templates/emails/reengagement_3.html`:

```html
{% extends 'emails/sequence_base.html' %}
{% block title %}One honest question{% endblock %}
{% block content %}
<p>{{ user.first_name|default:user.username }},</p>
<p>Last note from us for a while — we don't believe in nagging.</p>
<p>If MyRecoveryPal wasn't what you needed, would you hit reply and tell us
why? One sentence helps us build something better for the next person on day
one.</p>
<p>And if you're doing this season of life without an app — genuinely, we're
rooting for you. The door stays open, no expiration.</p>
{% endblock %}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/templates/emails/ apps/accounts/test_email_sequences.py
git commit -m "feat(emails): add onboarding + re-engagement email templates"
```

---

### Task 4: Rewrite E1 (welcome) task + signal fallback

**Files:**
- Modify: `apps/accounts/tasks.py:20-71` (`send_welcome_email_day_1`)
- Modify: `apps/accounts/signals.py:65-95` (`_send_welcome_email_directly`)
- Delete: `apps/accounts/templates/emails/welcome_day_1.html`
- Test: `apps/accounts/test_email_sequences.py` (append)

**Interfaces:**
- Consumes: `email_sequences.marketing_unsubscribe_url`, `emails/onboarding_1.html`.
- Produces: unchanged task name `send_welcome_email_day_1(user_id)`; still sets `welcome_email_1_sent`. Trigger (signal on onboarding completion, `signals.py:44-62`) is unchanged.

- [ ] **Step 1: Write failing test**

Append to `apps/accounts/test_email_sequences.py`:

```python
class WelcomeEmailE1Tests(TestCase):
    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_e1_uses_new_subject_and_marks_sent(self, mock_send):
        from apps.accounts.tasks import send_welcome_email_day_1
        user = make_user(username='e1user')
        send_welcome_email_day_1(user.id)
        user.refresh_from_db()
        self.assertIsNotNone(user.welcome_email_1_sent)
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['subject'],
                         "Welcome in. You're a founding member. 💙")
        self.assertIn('unsubscribe', kwargs['html_message'].lower())
```

- [ ] **Step 2: Run to verify it fails**

Run: `python manage.py test apps.accounts.test_email_sequences.WelcomeEmailE1Tests -v 2`
Expected: FAIL — subject is `"Welcome to MyRecoveryPal! 🌟"`

- [ ] **Step 3: Update the task**

In `apps/accounts/tasks.py::send_welcome_email_day_1`, replace the render+send block (keep the guards and field-marking around it):

```python
        from .email_sequences import marketing_unsubscribe_url

        site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

        html_message = render_to_string('emails/onboarding_1.html', {
            'user': user,
            'site_url': site_url,
            'current_year': timezone.now().year,
            'unsubscribe_url': marketing_unsubscribe_url(user),
        })
        plain_message = strip_tags(html_message)

        success, error = send_email(
            subject="Welcome in. You're a founding member. 💙",
            plain_message=plain_message,
            html_message=html_message,
            recipient_email=user.email,
        )
```

- [ ] **Step 4: Update the signal fallback**

In `apps/accounts/signals.py::_send_welcome_email_directly`, apply the same template/subject/context change (`emails/onboarding_1.html`, subject `"Welcome in. You're a founding member. 💙"`, add `'unsubscribe_url': marketing_unsubscribe_url(user)` importing from `.email_sequences`).

- [ ] **Step 5: Delete the old template**

Run: `git rm apps/accounts/templates/emails/welcome_day_1.html`
Then: `grep -rn "welcome_day_1" apps/ recovery_hub/ --include=*.py --include=*.html`
Expected: no remaining references.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add -A apps/accounts/tasks.py apps/accounts/signals.py apps/accounts/templates/emails/
git commit -m "feat(emails): rewrite welcome email (E1) to spec copy"
```

---

### Task 5: Onboarding drip task (E2–E6), retire day-3/day-7 tasks

**Files:**
- Modify: `apps/accounts/tasks.py` (replace `send_welcome_emails_day_3` at lines 74-134 and `send_welcome_emails_day_7` at lines 137-205 with one new task)
- Delete: `apps/accounts/templates/emails/welcome_day_3.html`, `welcome_day_7.html`
- Test: `apps/accounts/test_email_sequences.py` (append)

**Interfaces:**
- Consumes: `ONBOARDING_EMAILS`, `is_activated`, `is_crisis_suppressed`, `marketing_unsubscribe_url`, `has_started_streak` from `email_sequences`; Task 1 fields.
- Produces: Celery task `apps.accounts.tasks.send_onboarding_sequence_emails()` returning `{'sent': int, 'skipped': int, 'exited': int}`. Registered in Beat in Task 7.

**Behavior rules:**
- Candidates: `is_active=True, email_notifications=True, marketing_emails_enabled=True, welcome_email_1_sent__isnull=False, onboarding_email_6_sent__isnull=True, date_joined__gte=now-25d` (the 25-day window mirrors the old "too late" guard).
- Crisis-suppressed users are skipped this run (retried next day — a 48h flag must delay, not cancel).
- If `is_activated(user)`: stamp ALL remaining null onboarding fields with `now` without sending (sequence exit → they only keep getting the regular weekly digest, which already exists).
- Only the **latest** due email is sent per run; earlier missed ones are stamped as skipped (prevents blasting 4 emails at users mid-migration from the old sequence).
- E2's `skip` condition (already used Anchor): stamp the field, send nothing, and let E3 go out on day 3 as normal.
- E5 renders with `streak=user.get_checkin_streak()`, `has_streak=has_started_streak(user)`.

- [ ] **Step 1: Write failing tests**

Append to `apps/accounts/test_email_sequences.py`:

```python
class OnboardingSequenceTests(TestCase):
    def run_task(self):
        from apps.accounts.tasks import send_onboarding_sequence_emails
        with patch('apps.accounts.tasks.send_email',
                   return_value=(True, None)) as mock_send:
            send_onboarding_sequence_emails()
        return mock_send

    def make_onboarded_user(self, username, days_ago):
        user = make_user(username=username, days_ago=days_ago)
        User.objects.filter(pk=user.pk).update(
            welcome_email_1_sent=timezone.now() - timedelta(days=days_ago))
        user.refresh_from_db()
        return user

    def test_day_1_sends_anchor_email(self):
        user = self.make_onboarded_user('day1', days_ago=1)
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertIsNotNone(user.onboarding_email_2_sent)
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "Meet Anchor (it's awake when no one else is)")

    def test_anchor_user_skips_e2_silently(self):
        user = self.make_onboarded_user('anchored', days_ago=1)
        session = RecoveryCoachSession.objects.create(user=user)
        CoachMessage.objects.create(session=session, role='user', content='hi')
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertIsNotNone(user.onboarding_email_2_sent)  # stamped
        mock_send.assert_not_called()                        # not sent

    def test_only_latest_due_email_sent(self):
        user = self.make_onboarded_user('midway', days_ago=9)
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "Your first medallion is closer than you think")
        # earlier ones stamped as skipped
        self.assertIsNotNone(user.onboarding_email_2_sent)
        self.assertIsNotNone(user.onboarding_email_3_sent)
        self.assertIsNotNone(user.onboarding_email_4_sent)

    def test_activated_user_exits_sequence(self):
        user = self.make_onboarded_user('activated', days_ago=3)
        DailyCheckIn.objects.create(user=user, mood=4, energy_level=4)
        JournalEntry.objects.create(user=user, content='line')
        SocialPost.objects.create(author=user, content='hello all')
        mock_send = self.run_task()
        user.refresh_from_db()
        mock_send.assert_not_called()
        self.assertIsNotNone(user.onboarding_email_6_sent)  # sequence closed

    def test_crisis_flag_suppresses_send_but_not_sequence(self):
        user = self.make_onboarded_user('crisis', days_ago=3)
        RecoveryCoachSession.objects.create(user=user, trigger='checkin_support')
        mock_send = self.run_task()
        user.refresh_from_db()
        mock_send.assert_not_called()
        self.assertIsNone(user.onboarding_email_3_sent)  # retried next run

    def test_unsubscribed_user_gets_nothing(self):
        user = self.make_onboarded_user('unsub', days_ago=3)
        User.objects.filter(pk=user.pk).update(marketing_emails_enabled=False)
        mock_send = self.run_task()
        mock_send.assert_not_called()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python manage.py test apps.accounts.test_email_sequences.OnboardingSequenceTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'send_onboarding_sequence_emails'`

- [ ] **Step 3: Implement the task**

In `apps/accounts/tasks.py`, delete `send_welcome_emails_day_3` and `send_welcome_emails_day_7` entirely and add in their place:

```python
@shared_task(bind=True, max_retries=3)
def send_onboarding_sequence_emails(self):
    """
    Daily driver for onboarding emails E2-E6 (days 1/3/6/9/14 after signup).

    Per user, sends only the latest due unsent email and stamps earlier
    missed ones as skipped. Users who complete all three activation actions
    (streak + journal + community action) exit the sequence early. Users
    with a crisis-triggered coach session in the last 48h are deferred to
    the next run — never emailed mid-crisis.
    """
    from .models import User
    from .email_sequences import (
        ONBOARDING_EMAILS, is_activated, is_crisis_suppressed,
        has_started_streak, marketing_unsubscribe_url,
    )

    now = timezone.now()
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    users = User.objects.filter(
        is_active=True,
        email_notifications=True,
        marketing_emails_enabled=True,
        welcome_email_1_sent__isnull=False,
        onboarding_email_6_sent__isnull=True,
        date_joined__gte=now - timedelta(days=25),
    )

    sent_count = 0
    skipped_count = 0
    exited_count = 0

    for user in users:
        try:
            if is_crisis_suppressed(user):
                skipped_count += 1
                continue

            remaining = [e for e in ONBOARDING_EMAILS
                         if getattr(user, e['field']) is None]

            if is_activated(user):
                # Sequence goal reached - close out without sending.
                for email in remaining:
                    setattr(user, email['field'], now)
                user.save(update_fields=[e['field'] for e in remaining])
                exited_count += 1
                continue

            days = (now - user.date_joined).days
            due = [e for e in remaining if days >= e['day']]
            if not due:
                continue

            email = due[-1]
            stamped_fields = []
            # Stamp earlier missed emails as skipped rather than blasting them.
            for missed in due[:-1]:
                setattr(user, missed['field'], now)
                stamped_fields.append(missed['field'])

            if email['skip'] and email['skip'](user):
                setattr(user, email['field'], now)
                stamped_fields.append(email['field'])
                user.save(update_fields=stamped_fields)
                skipped_count += 1
                continue

            context = {
                'user': user,
                'site_url': site_url,
                'current_year': now.year,
                'unsubscribe_url': marketing_unsubscribe_url(user),
            }
            if email['number'] == 5:
                context['streak'] = user.get_checkin_streak()
                context['has_streak'] = has_started_streak(user)

            html_message = render_to_string(email['template'], context)
            plain_message = strip_tags(html_message)

            success, error = send_email(
                subject=email['subject'],
                plain_message=plain_message,
                html_message=html_message,
                recipient_email=user.email,
            )
            if not success:
                raise Exception(f"send failed: {error}")

            setattr(user, email['field'], now)
            stamped_fields.append(email['field'])
            user.save(update_fields=stamped_fields)
            sent_count += 1

            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in onboarding sequence for {user.email}: {e}")

    logger.info(
        f"Onboarding sequence: sent={sent_count}, skipped={skipped_count}, "
        f"exited={exited_count}")
    return {'sent': sent_count, 'skipped': skipped_count, 'exited': exited_count}
```

- [ ] **Step 4: Delete orphaned templates and check references**

Run: `git rm apps/accounts/templates/emails/welcome_day_3.html apps/accounts/templates/emails/welcome_day_7.html`
Then: `grep -rn "welcome_day_3\|welcome_day_7\|send_welcome_emails_day" apps/ recovery_hub/ --include=*.py --include=*.html`
Expected: only the two `CELERY_BEAT_SCHEDULE` entries in `recovery_hub/settings.py` remain (removed in Task 7).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A apps/accounts/tasks.py apps/accounts/templates/emails/ apps/accounts/test_email_sequences.py
git commit -m "feat(emails): onboarding drip task E2-E6, retire day-3/7 emails"
```

---

### Task 6: Re-engagement task (R1–R3)

**Files:**
- Modify: `apps/accounts/tasks.py` (add task after `send_onboarding_sequence_emails`)
- Test: `apps/accounts/test_email_sequences.py` (append)

**Interfaces:**
- Consumes: `REENGAGEMENT_EMAILS`, `get_last_activity`, `is_crisis_suppressed`, `marketing_unsubscribe_url`, `INACTIVITY_DAYS`, `REENGAGEMENT_REENTRY_DAYS` from `email_sequences`; Task 1 fields.
- Produces: Celery task `apps.accounts.tasks.send_reengagement_emails()` returning `{'sent': int}`. Registered in Beat in Task 7.

**Behavior rules (from spec flow logic):**
- Trigger: `get_last_activity(user)` older than 21 days. Any activity → user simply stops matching (exit).
- R1 starts a cycle (also restarts one if the previous R1 is >90 days old); starting a cycle resets R2/R3 to null.
- R2 at ≥5 days after R1, R3 at ≥12 days after R1, each only while still inactive.
- After R3: suppress re-entry for 90 days (checked against `reengagement_email_3_sent`).
- Suppress: onboarding window (`date_joined` within 21 days — implied by the inactivity floor since `date_joined` counts as activity, but filtered explicitly anyway), unsubscribed/notifications off, crisis flag (48h).

- [ ] **Step 1: Write failing tests**

Append to `apps/accounts/test_email_sequences.py`:

```python
class ReengagementSequenceTests(TestCase):
    def run_task(self):
        from apps.accounts.tasks import send_reengagement_emails
        with patch('apps.accounts.tasks.send_email',
                   return_value=(True, None)) as mock_send:
            send_reengagement_emails()
        return mock_send

    def test_inactive_21_days_gets_r1(self):
        user = make_user(username='ghost', days_ago=30)
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertIsNotNone(user.reengagement_email_1_sent)
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "Your seat's still here 💙")

    def test_active_user_gets_nothing(self):
        user = make_user(username='alive', days_ago=30)
        User.objects.filter(pk=user.pk).update(last_seen=timezone.now())
        mock_send = self.run_task()
        mock_send.assert_not_called()

    def test_r2_after_5_days_r3_after_12(self):
        user = make_user(username='drip', days_ago=60)
        User.objects.filter(pk=user.pk).update(
            reengagement_email_1_sent=timezone.now() - timedelta(days=5))
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertIsNotNone(user.reengagement_email_2_sent)
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "What you've missed (the good kind)")

        User.objects.filter(pk=user.pk).update(
            reengagement_email_1_sent=timezone.now() - timedelta(days=12))
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertIsNotNone(user.reengagement_email_3_sent)
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "One honest question")

    def test_90_day_reentry_suppression(self):
        user = make_user(username='done', days_ago=120)
        User.objects.filter(pk=user.pk).update(
            reengagement_email_1_sent=timezone.now() - timedelta(days=40),
            reengagement_email_2_sent=timezone.now() - timedelta(days=35),
            reengagement_email_3_sent=timezone.now() - timedelta(days=28),
        )
        mock_send = self.run_task()
        mock_send.assert_not_called()

    def test_new_cycle_after_90_days_restarts_at_r1(self):
        user = make_user(username='cycle', days_ago=400)
        User.objects.filter(pk=user.pk).update(
            reengagement_email_1_sent=timezone.now() - timedelta(days=200),
            reengagement_email_2_sent=timezone.now() - timedelta(days=195),
            reengagement_email_3_sent=timezone.now() - timedelta(days=188),
        )
        mock_send = self.run_task()
        user.refresh_from_db()
        self.assertEqual(mock_send.call_args.kwargs['subject'],
                         "Your seat's still here 💙")
        self.assertIsNone(user.reengagement_email_2_sent)  # cycle reset
        self.assertIsNone(user.reengagement_email_3_sent)

    def test_crisis_flag_suppresses(self):
        user = make_user(username='rcrisis', days_ago=30)
        RecoveryCoachSession.objects.create(user=user, trigger='checkin_support')
        mock_send = self.run_task()
        mock_send.assert_not_called()
```

- [ ] **Step 2: Run to verify they fail**

Run: `python manage.py test apps.accounts.test_email_sequences.ReengagementSequenceTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'send_reengagement_emails'`

- [ ] **Step 3: Implement the task**

Add to `apps/accounts/tasks.py` after `send_onboarding_sequence_emails`:

```python
@shared_task(bind=True, max_retries=3)
def send_reengagement_emails(self):
    """
    Daily driver for the re-engagement sequence (R1/R2/R3 at days 0/5/12
    after 21 days of inactivity). Any activity exits the sequence naturally.
    After R3, the user is left alone for 90 days before a new cycle can
    start. Tone rule from the spec: never guilt-trip absence.
    """
    from .models import User
    from .email_sequences import (
        REENGAGEMENT_EMAILS, get_last_activity, is_crisis_suppressed,
        marketing_unsubscribe_url, INACTIVITY_DAYS, REENGAGEMENT_REENTRY_DAYS,
    )

    now = timezone.now()
    inactivity_cutoff = now - timedelta(days=INACTIVITY_DAYS)
    reentry_cutoff = now - timedelta(days=REENGAGEMENT_REENTRY_DAYS)
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    users = User.objects.filter(
        is_active=True,
        email_notifications=True,
        marketing_emails_enabled=True,
        date_joined__lt=inactivity_cutoff,  # never during onboarding
    )

    sent_count = 0

    def render_and_send(user, email):
        context = {
            'user': user,
            'site_url': site_url,
            'current_year': now.year,
            'unsubscribe_url': marketing_unsubscribe_url(user),
        }
        html_message = render_to_string(email['template'], context)
        plain_message = strip_tags(html_message)
        success, error = send_email(
            subject=email['subject'],
            plain_message=plain_message,
            html_message=html_message,
            recipient_email=user.email,
        )
        if not success:
            raise Exception(f"send failed: {error}")

    for user in users:
        try:
            if get_last_activity(user) > inactivity_cutoff:
                continue  # active -> exit sequence
            if is_crisis_suppressed(user):
                continue

            r1 = user.reengagement_email_1_sent
            r3 = user.reengagement_email_3_sent

            if r3 and r3 > reentry_cutoff:
                continue  # sequence finished recently; leave them alone

            if r1 is None or r1 < reentry_cutoff:
                # Start (or restart) a cycle with R1.
                render_and_send(user, REENGAGEMENT_EMAILS[0])
                user.reengagement_email_1_sent = now
                user.reengagement_email_2_sent = None
                user.reengagement_email_3_sent = None
                user.save(update_fields=[
                    'reengagement_email_1_sent',
                    'reengagement_email_2_sent',
                    'reengagement_email_3_sent',
                ])
            elif user.reengagement_email_2_sent is None and \
                    r1 <= now - timedelta(days=5):
                render_and_send(user, REENGAGEMENT_EMAILS[1])
                user.reengagement_email_2_sent = now
                user.save(update_fields=['reengagement_email_2_sent'])
            elif user.reengagement_email_3_sent is None and \
                    r1 <= now - timedelta(days=12):
                render_and_send(user, REENGAGEMENT_EMAILS[2])
                user.reengagement_email_3_sent = now
                user.save(update_fields=['reengagement_email_3_sent'])
            else:
                continue

            sent_count += 1
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in re-engagement sequence for {user.email}: {e}")

    logger.info(f"Re-engagement sequence: sent={sent_count}")
    return {'sent': sent_count}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test apps.accounts.test_email_sequences -v 2`
Expected: PASS (all classes)

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/tasks.py apps/accounts/test_email_sequences.py
git commit -m "feat(emails): re-engagement sequence R1-R3 for inactive members"
```

---

### Task 7: Celery Beat schedule + full test suite + changelog

**Files:**
- Modify: `recovery_hub/settings.py:760-768` (replace the two welcome-email entries)
- Modify: `docs/CHANGELOG.md` (new entry at top)

**Interfaces:**
- Consumes: task names `apps.accounts.tasks.send_onboarding_sequence_emails`, `apps.accounts.tasks.send_reengagement_emails`.

- [ ] **Step 1: Update the Beat schedule**

In `recovery_hub/settings.py`, replace:

```python
    # Welcome email sequence - Day 3 and Day 7 (Day 1 is triggered on registration)
    'send-welcome-emails-day-3': {
        'task': 'apps.accounts.tasks.send_welcome_emails_day_3',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'send-welcome-emails-day-7': {
        'task': 'apps.accounts.tasks.send_welcome_emails_day_7',
        'schedule': crontab(hour=10, minute=15),  # Daily at 10:15 AM
    },
```

with:

```python
    # Onboarding email sequence E2-E6 (E1 is signal-triggered on registration)
    'send-onboarding-sequence-emails': {
        'task': 'apps.accounts.tasks.send_onboarding_sequence_emails',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    # Re-engagement sequence R1-R3 for members inactive 21+ days
    'send-reengagement-emails': {
        'task': 'apps.accounts.tasks.send_reengagement_emails',
        'schedule': crontab(hour=10, minute=45),  # Daily at 10:45 AM
    },
```

- [ ] **Step 2: Verify no dangling references to retired tasks**

Run: `grep -rn "send_welcome_emails_day" apps/ recovery_hub/ --include=*.py`
Expected: no matches.

- [ ] **Step 3: Run the accounts test suite (regression check)**

Run: `python manage.py test apps.accounts -v 1`
Expected: PASS (pre-existing failures, if any, must be shown to be pre-existing by `git stash && python manage.py test apps.accounts -v 1 && git stash pop`).

- [ ] **Step 4: Add changelog entry**

Add at the top of the entries in `docs/CHANGELOG.md`:

```markdown
## 2026-07-08 — Member email sequences (onboarding + re-engagement)

- Replaced the 3-email welcome drip with the 6-email onboarding sequence
  (days 0/1/3/6/9/14): welcome, Anchor, journal, community, milestone,
  feedback ask. Early exit once a member has a check-in, a journal entry,
  and a community action. E2 skipped if Anchor already used; E5 has a
  no-streak variant.
- New re-engagement sequence (R1/R2/R3 at days 0/5/12) for members with no
  activity in 21 days; any activity exits; 90-day re-entry suppression
  after R3.
- Crisis suppression on both sequences: a crisis-triggered coach session
  (`trigger='checkin_support'`) in the last 48h blocks all sequence email.
- All sequence emails now carry the marketing unsubscribe link and respect
  `marketing_emails_enabled` in addition to `email_notifications`.
- New: `apps/accounts/email_sequences.py`, 10 templates under
  `emails/onboarding_*.html` / `emails/reengagement_*.html` /
  `emails/sequence_base.html`, tasks `send_onboarding_sequence_emails` +
  `send_reengagement_emails` (Beat: daily 10:00 / 10:45 UTC).
- Removed: `send_welcome_emails_day_3/7` tasks and `welcome_day_*.html`.
```

- [ ] **Step 5: Commit**

```bash
git add recovery_hub/settings.py docs/CHANGELOG.md
git commit -m "feat(emails): schedule onboarding + re-engagement sequences in Celery Beat"
```

---

## Self-review notes

- **Spec coverage:** E1–E6 (Tasks 3–5), E2 skip condition (Task 5), E5 variant (Tasks 3+5), early exit (Task 5), R1–R3 + 90-day re-entry (Task 6), crisis/unsubscribe suppression both sequences (Tasks 5+6), onboarding-window suppression for re-engagement (Task 6 filter). A/B tests and open/CTR benchmarks from the spec are platform-analytics concerns — out of scope for this code release (tracking = the sent-timestamp fields + Resend dashboard).
- **Reply-to (E6/R3 "hit reply"):** `send_email` has no reply-to param; replies go to `DEFAULT_FROM_EMAIL`. Confirm that inbox is monitored — no code change needed.
- **Mid-migration users:** anyone currently between old day-3 and day-7 gets, at most, the single latest-due new email (earlier ones stamped skipped) — no double-welcome, no blast.
