# Phase 0: Trial Expiration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the 14-day Premium trial actually expire so the paywall fires, while giving all 238 existing users a fresh 14-day window — unlocking the first possible conversions.

**Architecture:** Fix `Subscription.is_active()` to respect `trial_end` (the root bug); add an `expired` status; reset existing trials via a data migration that runs before the new gate serves traffic; add a nightly Celery task that downgrades ended trials and emails the user; make the Anchor wall's upgrade CTA actually work.

**Tech Stack:** Django 5.0, PostgreSQL, Celery beat, Resend (via `email_service.send_email`).

**Spec:** `docs/plans/2026-06-12-trial-expiration-design.md`

**Test command:** `python3 manage.py test apps.accounts.test_trial_expiration -v2`
(Django builds an ephemeral SQLite test DB with migrations applied; the local
`db.sqlite3` is stale, so always run via `manage.py test`, never against local data.)

**Note on test users:** creating a `User` fires `signals.create_user_subscription`,
which auto-creates a `Subscription(tier='premium', status='trialing',
trial_end=now+14d)`. Tests should fetch `user.subscription` and mutate it for the
scenario under test. `email` is unique and required — give each user a distinct one.

---

### Task 1: Fix the gate + add `expired` status

**Files:**
- Modify: `apps/accounts/payment_models.py` (`Subscription.STATUS_CHOICES`, `Subscription.is_active`)
- Create: `apps/accounts/test_trial_expiration.py`
- Create (generated): `apps/accounts/migrations/0046_alter_subscription_status.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/accounts/test_trial_expiration.py`:

```python
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User


def make_user(username):
    return User.objects.create_user(username, f'{username}@t.co', 'pw')


class IsActiveGateTest(TestCase):
    def test_trial_in_future_is_active_and_premium(self):
        user = make_user('future')
        sub = user.subscription  # premium / trialing / +14d
        sub.trial_end = timezone.now() + timedelta(days=5)
        sub.save()
        self.assertTrue(sub.is_active())
        self.assertTrue(sub.is_premium())

    def test_trial_in_past_is_not_active_or_premium(self):
        user = make_user('past')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(days=1)
        sub.save()
        self.assertFalse(sub.is_active())
        self.assertFalse(sub.is_premium())

    def test_trialing_with_no_trial_end_is_not_active(self):
        user = make_user('notrialend')
        sub = user.subscription
        sub.trial_end = None
        sub.save()
        self.assertFalse(sub.is_active())

    def test_paid_active_is_active(self):
        user = make_user('paid')
        sub = user.subscription
        sub.status = 'active'
        sub.trial_end = None
        sub.save()
        self.assertTrue(sub.is_active())
        self.assertTrue(sub.is_premium())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.IsActiveGateTest -v2`
Expected: FAIL — `test_trial_in_past_*` and `test_trialing_with_no_trial_end_*` fail because the current `is_active()` returns True for any `trialing` status regardless of `trial_end`.

- [ ] **Step 3: Implement the gate fix and add the `expired` status**

In `apps/accounts/payment_models.py`, add `('expired', 'Expired')` to the
`Subscription.STATUS_CHOICES` list (place it after `('trialing', 'Trialing')`):

```python
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
        ('expired', 'Expired'),
        ('incomplete', 'Incomplete'),
    ]
```

Replace the `is_active` method:

```python
    def is_active(self):
        """Active = paid-active, or a trial whose window hasn't passed."""
        if self.status == 'trialing':
            return bool(self.trial_end and self.trial_end > timezone.now())
        return self.status == 'active'
```

(`is_premium`, `is_court`, `is_supporter` already delegate to `is_active()` — no change needed. Confirm `timezone` is imported at the top of the file; it is used by `is_trialing()` already.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.IsActiveGateTest -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: Generate the choices migration**

Run: `python3 manage.py makemigrations accounts`
Expected: creates `apps/accounts/migrations/0046_alter_subscription_status.py` (an `AlterField` on `status` — state-only, no SQL). Verify it depends on `0045_support_circle_email_tracking`.

- [ ] **Step 6: Commit**

```bash
git add apps/accounts/payment_models.py apps/accounts/test_trial_expiration.py apps/accounts/migrations/0046_alter_subscription_status.py
git commit -m "fix(billing): expire trials in is_active() and add 'expired' status"
```

---

### Task 2: Fresh 14-day reset (data migration)

**Files:**
- Create: `apps/accounts/migrations/0047_reset_trials.py`
- Modify: `apps/accounts/test_trial_expiration.py` (add a class)

- [ ] **Step 1: Write the failing test**

Append to `apps/accounts/test_trial_expiration.py`:

```python
import importlib

from apps.accounts.payment_models import Subscription


class ResetTrialsMigrationTest(TestCase):
    def _run_reset(self):
        # The data migration's forward function uses apps.get_model, which works
        # with the real app registry too, so we can call it directly.
        from django.apps import apps as global_apps
        mod = importlib.import_module('apps.accounts.migrations.0047_reset_trials')
        mod.reset_trials(global_apps, None)

    def test_resets_trialing_subs_to_14_days_out(self):
        user = make_user('stale')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(days=90)
        sub.save()

        self._run_reset()

        sub.refresh_from_db()
        remaining = sub.trial_end - timezone.now()
        self.assertGreater(remaining, timedelta(days=13))
        self.assertLessEqual(remaining, timedelta(days=14))

    def test_leaves_paid_active_subs_untouched(self):
        user = make_user('payer')
        sub = user.subscription
        sub.status = 'active'
        sub.trial_end = None
        sub.save()

        self._run_reset()

        sub.refresh_from_db()
        self.assertIsNone(sub.trial_end)
        self.assertEqual(sub.status, 'active')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.ResetTrialsMigrationTest -v2`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.accounts.migrations.0047_reset_trials'`.

- [ ] **Step 3: Write the data migration**

Create `apps/accounts/migrations/0047_reset_trials.py`:

```python
from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def reset_trials(apps, schema_editor):
    """Give every in-trial subscription a fresh 14-day window from launch."""
    Subscription = apps.get_model('accounts', 'Subscription')
    Subscription.objects.filter(status='trialing').update(
        trial_end=timezone.now() + timedelta(days=14)
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0046_alter_subscription_status'),
    ]

    operations = [
        migrations.RunPython(reset_trials, noop_reverse),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.ResetTrialsMigrationTest -v2`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/migrations/0047_reset_trials.py apps/accounts/test_trial_expiration.py
git commit -m "feat(billing): data migration resets existing trials to fresh 14 days"
```

---

### Task 3: Nightly expiration task + trial-ended email

**Files:**
- Modify: `apps/accounts/tasks.py` (add `expire_ended_trials`)
- Modify: `recovery_hub/settings.py` (register beat schedule entry near line 708)
- Modify: `apps/accounts/test_trial_expiration.py` (add a class)

- [ ] **Step 1: Write the failing tests**

Append to `apps/accounts/test_trial_expiration.py`:

```python
from unittest.mock import patch


class ExpireEndedTrialsTaskTest(TestCase):
    def setUp(self):
        self.patcher = patch('apps.accounts.email_service.send_email',
                             return_value=(True, 'mock'))
        self.mock_send = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _run(self):
        from apps.accounts.tasks import expire_ended_trials
        expire_ended_trials.apply()

    def test_downgrades_ended_trial_to_free_and_emails(self):
        user = make_user('ended')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(hours=1)
        sub.save()

        self._run()

        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'free')
        self.assertEqual(sub.status, 'expired')
        self.assertEqual(self.mock_send.call_count, 1)

    def test_skips_trial_still_in_window(self):
        user = make_user('current')
        sub = user.subscription
        sub.trial_end = timezone.now() + timedelta(days=3)
        sub.save()

        self._run()

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'trialing')
        self.assertEqual(self.mock_send.call_count, 0)

    def test_skips_paid_active(self):
        user = make_user('active')
        sub = user.subscription
        sub.status = 'active'
        sub.trial_end = None
        sub.save()

        self._run()

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'active')

    def test_skips_trialing_with_real_stripe_sub(self):
        user = make_user('realstripe')
        sub = user.subscription
        sub.trial_end = timezone.now() - timedelta(hours=1)
        sub.stripe_subscription_id = 'sub_real123'
        sub.save()

        self._run()

        sub.refresh_from_db()
        self.assertEqual(sub.status, 'trialing')  # untouched
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.ExpireEndedTrialsTaskTest -v2`
Expected: FAIL — `ImportError: cannot import name 'expire_ended_trials'`.

- [ ] **Step 3: Implement the task**

Add to `apps/accounts/tasks.py` (after `send_trial_ending_notifications`). The email is built inline to mirror that sibling task:

```python
@shared_task(bind=True, max_retries=3)
def expire_ended_trials(self):
    """Downgrade trials whose 14-day window has passed to free, and email the user.

    Runs daily. Real payers are status='active' (never matched); the stripe
    guard is belt-and-suspenders against a trialing row that somehow has a
    live Stripe subscription.
    """
    from django.db.models import Q
    from .models import Notification
    from .payment_models import Subscription
    from .email_service import send_email

    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com')
    now = timezone.now()

    ended = Subscription.objects.filter(
        status='trialing',
        trial_end__lt=now,
    ).filter(
        Q(stripe_subscription_id__isnull=True) | Q(stripe_subscription_id='')
    ).select_related('user')

    count = 0
    for sub in ended:
        user = sub.user
        sub.tier = 'free'
        sub.status = 'expired'
        sub.save(update_fields=['tier', 'status'])

        try:
            Notification.objects.create(
                recipient=user,
                sender=user,
                notification_type='milestone',
                title='Your Premium Trial Ended',
                message='Upgrade to keep Anchor, unlimited groups, and analytics.',
                link='/accounts/pricing/',
            )
        except Exception as e:
            logger.error(f"Error creating trial-ended notification for {user.email}: {e}")

        try:
            name = user.first_name or user.username
            subject = f"Your Premium trial has ended, {name}"
            plain_message = (
                f"Hi {name},\n\n"
                f"Your 14-day Premium trial on MyRecoveryPal has ended, so your "
                f"account is now on the free plan.\n\n"
                f"Upgrade to Premium ($4.99/month) to get back:\n"
                f"- AI Recovery Coach Anchor (20 messages/day)\n"
                f"- Unlimited recovery groups\n"
                f"- 90-day progress analytics\n"
                f"- Journal export\n\n"
                f"Upgrade here: {site_url}/accounts/pricing/\n\n"
                f"Your recovery journey matters. We're here for you.\n"
                f"- The MyRecoveryPal Team"
            )
            html_message = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #1e4d8b, #4db8e8); padding: 30px; text-align: center; border-radius: 12px 12px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Your Premium Trial Has Ended</h1>
                </div>
                <div style="padding: 30px; background: white;">
                    <p style="color: #333; font-size: 16px;">Hi {name},</p>
                    <p style="color: #555; font-size: 15px; line-height: 1.6;">Your 14-day Premium trial has ended and your account is now on the free plan. Upgrade any time to get back:</p>
                    <ul style="color: #555; font-size: 15px; line-height: 1.8;">
                        <li><strong>AI Recovery Coach Anchor</strong> — 20 messages/day</li>
                        <li><strong>Unlimited recovery groups</strong></li>
                        <li><strong>90-day progress analytics</strong></li>
                        <li><strong>Journal export</strong></li>
                    </ul>
                    <p style="text-align: center; margin: 28px 0;">
                        <a href="{site_url}/accounts/pricing/" style="background: #1e4d8b; color: white; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600;">Upgrade to Premium</a>
                    </p>
                </div>
            </div>
            """
            send_email(subject=subject, plain_message=plain_message,
                       html_message=html_message, recipient_email=user.email)
        except Exception as e:
            logger.error(f"Error sending trial-ended email to {user.email}: {e}")

        count += 1

    logger.info(f"expire_ended_trials: downgraded {count} subscriptions")
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 manage.py test apps.accounts.test_trial_expiration.ExpireEndedTrialsTaskTest -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: Register the beat schedule**

In `recovery_hub/settings.py`, inside `CELERY_BEAT_SCHEDULE` (starts line 708), add:

```python
    'expire-ended-trials': {
        'task': 'apps.accounts.tasks.expire_ended_trials',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM, before the 10 AM email tasks
    },
```

- [ ] **Step 6: Verify settings still load**

Run: `python3 manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 7: Commit**

```bash
git add apps/accounts/tasks.py recovery_hub/settings.py apps/accounts/test_trial_expiration.py
git commit -m "feat(billing): nightly task downgrades ended trials + emails user"
```

---

### Task 4: Working upgrade CTA on the Anchor wall

**Files:**
- Modify: `apps/accounts/templates/accounts/recovery_coach.html` (send handler JS)

**Context:** `coach_send_message` already returns HTTP 429 with
`{'error': 'upgrade_required', 'upgrade_required': true}` when a free user is
gated. The page currently shows the raw `error` string ("upgrade_required") to
the user. We replace that with a real upgrade prompt.

- [ ] **Step 1: Find the send handler's error path**

Run: `grep -n "upgrade_required\|\.error\|catch\|response.json\|429\|status ===" apps/accounts/templates/accounts/recovery_coach.html`
Read the `fetch(...)` block that POSTs to `coach_send_message` and the code that handles a non-OK response. Identify where the error text is rendered into the chat.

- [ ] **Step 2: Add upgrade-prompt handling**

In the send handler, where the response is parsed, special-case the upgrade
signal *before* the generic error render. Insert:

```javascript
// data = await response.json();
if (data.upgrade_required) {
    showAnchorUpgradePrompt();
    return;
}
```

Add this function in the page's `<script>` block (use the existing brand colors;
keep it dependency-free):

```javascript
function showAnchorUpgradePrompt() {
    const thread = document.getElementById('coach-messages') || document.body;
    const card = document.createElement('div');
    card.className = 'anchor-upgrade-prompt';
    card.innerHTML = `
        <div style="border:1px solid #1e4d8b; background:#f4f8fc; border-radius:12px; padding:18px; margin:16px 0; text-align:center;">
            <p style="margin:0 0 10px; color:#1e4d8b; font-weight:600;">
                You've used your free messages with Anchor.
            </p>
            <p style="margin:0 0 14px; color:#555; font-size:14px;">
                Upgrade to Premium to keep talking — 20 messages a day, plus unlimited groups and analytics.
            </p>
            <a href="/accounts/pricing/" style="background:#1e4d8b; color:#fff; padding:10px 22px; border-radius:8px; text-decoration:none; font-weight:600;">
                Upgrade to keep talking
            </a>
        </div>`;
    thread.appendChild(card);
    thread.scrollTop = thread.scrollHeight;
}
```

(If the messages container has a different id than `coach-messages`, use the
actual id found in Step 1.)

- [ ] **Step 3: Manually verify the gated flow**

Because this is browser JS, verify with the webapp-testing tooling or by hand:
1. Run the server: `python3 manage.py runserver`
2. As a free (non-premium) user who has hit the message cap, send a message in
   `/accounts/recovery-coach/`.
3. Expected: the upgrade card appears (not the text "upgrade_required"), and its
   button navigates to `/accounts/pricing/`.
4. From pricing, click the Premium plan's subscribe button and confirm it reaches
   Stripe checkout (the premium plan + `create_checkout_session` already exist;
   the court tier was verified live). If it dead-ends, fix the premium button the
   same way the court button was wired (a `SubscriptionPlan(tier='premium')` row
   with a valid `stripe_price_id`).

- [ ] **Step 4: Commit**

```bash
git add apps/accounts/templates/accounts/recovery_coach.html
git commit -m "feat(coach): show working upgrade prompt when Anchor is gated"
```

---

### Task 5: Full-suite verification + deploy notes

- [ ] **Step 1: Run the whole new suite**

Run: `python3 manage.py test apps.accounts.test_trial_expiration -v2`
Expected: PASS (all classes — 4 + 2 + 4 = 10 tests).

- [ ] **Step 2: Confirm no migration drift**

Run: `python3 manage.py makemigrations --check --dry-run`
Expected: "No changes detected" (0046 already captured the choices change).

- [ ] **Step 3: Run the broader accounts suite for regressions**

Run: `python3 manage.py test apps.accounts.tests_signup apps.accounts.tests_court -v1`
Expected: PASS (no regressions from the `is_active()` change).

- [ ] **Step 4: Push (Railway auto-deploys; migrations run before new code serves traffic)**

```bash
git push origin main
```

**Deploy order (automatic):** migration `0047_reset_trials` runs during deploy →
all existing trialing users get a fresh 14-day window → the new `is_active()` gate
then serves traffic (no one is downgraded mid-deploy) → beat picks up
`expire_ended_trials`. Watch for `status='expired'` subscriptions to begin
appearing ~14 days after deploy, and for the first Stripe conversions to become
possible immediately for anyone who upgrades.
```
