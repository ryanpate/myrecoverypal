# Daily Blog Digest Email — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send one email per day (7 AM UTC) to opted-in users summarizing blog posts published in the previous 24 hours.

**Architecture:** Celery Beat triggers a task on `celery-worker`; the task queries recent posts, renders an HTML digest, and loops over recipients via the existing Resend-backed `send_email` helper. A Redis-backed daily cache key prevents duplicate sends if Beat double-fires.

**Tech Stack:** Django 5.0.10, Celery 5.3.4, Redis (via `django_redis`), Resend HTTP API (fallback to SMTP), Django template engine, `django.test.TestCase` for tests.

**Spec:** `docs/plans/2026-04-21-daily-blog-digest-email-design.md`

---

## File Plan

**Create:**
- `apps/accounts/templates/emails/blog_daily_digest.html` — HTML email template
- `apps/blog/management/commands/send_blog_digest.py` — manual trigger + `--dry-run`
- `apps/blog/tests.py` — Django `TestCase` suite (file does not yet exist)

**Modify:**
- `apps/blog/tasks.py` — add `_build_subject()` helper and `send_daily_blog_digest` task
- `recovery_hub/settings.py` — add one entry to `CELERY_BEAT_SCHEDULE`

---

## Task 1: Email Template

**Files:**
- Create: `apps/accounts/templates/emails/blog_daily_digest.html`

- [ ] **Step 1: Create the template**

Create `apps/accounts/templates/emails/blog_daily_digest.html` with this exact content (matches the visual system used by `weekly_digest.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New on MyRecoveryPal</title>
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
        .logo {
            text-align: center;
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #1e4d8b 0%, #4db8e8 60%, #52b788 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        .tagline {
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .intro {
            font-size: 16px;
            color: #333;
            margin-bottom: 24px;
        }
        .post-card {
            border: 1px solid #e6ebf1;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 16px;
            background: #fafbfc;
        }
        .post-title {
            font-size: 18px;
            font-weight: 600;
            margin: 0 0 6px 0;
        }
        .post-title a {
            color: #1e4d8b;
            text-decoration: none;
        }
        .post-meta {
            color: #666;
            font-size: 13px;
            margin-bottom: 10px;
        }
        .post-excerpt {
            color: #444;
            font-size: 14px;
            margin-bottom: 14px;
        }
        .read-button {
            display: inline-block;
            padding: 8px 18px;
            background: linear-gradient(135deg, #1e4d8b 0%, #4db8e8 100%);
            color: white !important;
            text-decoration: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        .footer a {
            color: #4db8e8;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="logo">MyRecoveryPal</div>
        <div class="tagline">Your recovery community</div>

        <p class="intro">
            Hi {{ user.first_name|default:user.username }},<br>
            Here's what's new on the blog in the last 24 hours.
        </p>

        {% for post in posts %}
        <div class="post-card">
            <h2 class="post-title">
                <a href="{{ site_url }}{{ post.get_absolute_url }}">{{ post.title }}</a>
            </h2>
            <div class="post-meta">
                by {{ post.author.first_name|default:post.author.username }}
                · {{ post.published_at|date:"M j, g:i A" }} UTC
            </div>
            <div class="post-excerpt">
                {% if post.excerpt %}{{ post.excerpt|truncatechars:160 }}{% else %}{{ post.content|striptags|truncatechars:160 }}{% endif %}
            </div>
            <a href="{{ site_url }}{{ post.get_absolute_url }}" class="read-button">Read full post →</a>
        </div>
        {% endfor %}

        <div class="footer">
            You're getting this because you have email notifications turned on.
            <br>
            <a href="{{ unsubscribe_url }}">Manage email preferences</a>
            &nbsp;·&nbsp;
            &copy; {{ current_year }} MyRecoveryPal
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add apps/accounts/templates/emails/blog_daily_digest.html
git commit -m "feat: add blog daily digest email template"
```

---

## Task 2: Task Helper — `_build_subject`

**Files:**
- Modify: `apps/blog/tasks.py` (append at end)
- Modify: `apps/blog/tests.py` (create file)

- [ ] **Step 1: Write the failing tests**

Create `apps/blog/tests.py` with this exact content:

```python
from django.test import TestCase

from apps.blog.tasks import _build_subject


class FakePost:
    def __init__(self, title):
        self.title = title


class BuildSubjectTest(TestCase):
    def test_single_post_uses_title(self):
        posts = [FakePost("Faith Didn't Come With the Lightning Bolt")]
        self.assertEqual(
            _build_subject(posts),
            "New on MyRecoveryPal: Faith Didn't Come With the Lightning Bolt",
        )

    def test_multiple_posts_uses_count(self):
        posts = [FakePost("a"), FakePost("b"), FakePost("c")]
        self.assertEqual(
            _build_subject(posts),
            "3 new posts on MyRecoveryPal today",
        )

    def test_two_posts(self):
        posts = [FakePost("a"), FakePost("b")]
        self.assertEqual(
            _build_subject(posts),
            "2 new posts on MyRecoveryPal today",
        )
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
python manage.py test apps.blog.tests.BuildSubjectTest -v 2
```

Expected: `ImportError: cannot import name '_build_subject' from 'apps.blog.tasks'` — the failure is the import, which is the right failure mode.

- [ ] **Step 3: Add the helper to `apps/blog/tasks.py`**

Append this function to the end of `apps/blog/tasks.py` (after the existing `retry_stuck_blog_push_fanouts` task):

```python


def _build_subject(posts):
    """Build the subject line for the daily blog digest.

    One post → "New on MyRecoveryPal: {title}"
    N posts  → "{N} new posts on MyRecoveryPal today"
    """
    if len(posts) == 1:
        return f"New on MyRecoveryPal: {posts[0].title}"
    return f"{len(posts)} new posts on MyRecoveryPal today"
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
python manage.py test apps.blog.tests.BuildSubjectTest -v 2
```

Expected: `OK` with 3 tests passing.

- [ ] **Step 5: Commit**

```bash
git add apps/blog/tasks.py apps/blog/tests.py
git commit -m "feat: add _build_subject helper for blog daily digest"
```

---

## Task 3: Core Task — `send_daily_blog_digest`

**Files:**
- Modify: `apps/blog/tasks.py` (add new task at end)
- Modify: `apps/blog/tests.py` (extend test file)

- [ ] **Step 1: Write the failing tests**

Append this content to `apps/blog/tests.py` (the file created in Task 2):

```python
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.tasks import send_daily_blog_digest

User = get_user_model()


class SendDailyBlogDigestTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='x',
            email_notifications=True,
        )
        self.reader = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='x',
            email_notifications=True,
        )
        self.optout = User.objects.create_user(
            username='optout',
            email='optout@example.com',
            password='x',
            email_notifications=False,
        )

    def _create_post(self, title="Post", hours_ago=1, author=None):
        """Helper: create a published post N hours ago."""
        post = Post.objects.create(
            title=title,
            content="body text for the post",
            excerpt="Short excerpt",
            status='published',
            author=author or self.author,
        )
        # Post.save() sets published_at; override for test timing.
        Post.objects.filter(pk=post.pk).update(
            published_at=timezone.now() - timedelta(hours=hours_ago)
        )
        post.refresh_from_db()
        return post

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_no_posts_in_window_sends_nothing(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        send_daily_blog_digest()
        mock_send.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_posts_older_than_24h_are_excluded(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        self._create_post(hours_ago=48)  # outside window
        send_daily_blog_digest()
        mock_send.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_author_is_excluded_from_recipients(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertNotIn('author@example.com', recipients)
        self.assertIn('reader@example.com', recipients)

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_users_with_email_notifications_off_excluded(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertNotIn('optout@example.com', recipients)

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_idempotency_cache_hit_is_noop(self, mock_send, mock_cache):
        mock_cache.get.return_value = True  # already sent today
        self._create_post(author=self.author)
        send_daily_blog_digest()
        mock_send.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_successful_run_sets_cache(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        mock_cache.set.assert_called_once()
        # First positional arg should be today's key
        args, _ = mock_cache.set.call_args
        self.assertTrue(args[0].startswith('blog_digest_sent_'))

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_per_user_failure_does_not_abort_batch(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        # First recipient raises, second succeeds
        mock_send.side_effect = [Exception("boom"), (True, None)]
        # Need 2 recipients (not including author): reader + one more
        extra = User.objects.create_user(
            username='extra', email='extra@example.com', password='x',
            email_notifications=True,
        )
        self._create_post(author=self.author)
        send_daily_blog_digest()
        # Both recipients attempted
        self.assertEqual(mock_send.call_count, 2)
        # Cache still set (run completed)
        mock_cache.set.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test apps.blog.tests.SendDailyBlogDigestTest -v 2
```

Expected: `ImportError: cannot import name 'send_daily_blog_digest'` — correct failure.

- [ ] **Step 3: Add the task to `apps/blog/tasks.py`**

At the top of `apps/blog/tasks.py`, replace the existing import block:

```python
from celery import shared_task
from django.utils import timezone
import logging
```

...with:

```python
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
import logging
```

Then append this task to the end of `apps/blog/tasks.py` (after `_build_subject` which was added in Task 2):

```python


@shared_task
def send_daily_blog_digest():
    """Send a single email per opted-in user summarizing the last 24h of blog posts.

    Runs daily at 7 AM UTC via Celery Beat. Skips entirely if no posts were
    published in the window. Guards against double-sends with a daily cache
    key so a Beat double-fire doesn't spam users.

    Recipients:
      - is_active=True
      - email_notifications=True
      - has a non-empty email
      - NOT the author of any post in this batch

    Delivery uses apps.accounts.email_service.send_email (Resend HTTP API
    with SMTP fallback). Per-user failures are caught so one bad address
    doesn't abort the batch.
    """
    from apps.blog.models import Post
    from apps.accounts.models import User
    from apps.accounts.email_service import send_email

    today_key = f"blog_digest_sent_{timezone.now().date().isoformat()}"
    if cache.get(today_key):
        logger.info(f"send_daily_blog_digest: {today_key} already set, skipping")
        return

    window_start = timezone.now() - timedelta(hours=24)
    posts = list(
        Post.objects
        .filter(status='published', published_at__gte=window_start)
        .select_related('author')
        .order_by('-published_at')
    )

    if not posts:
        logger.info("send_daily_blog_digest: no posts in last 24h, no email sent")
        return

    author_ids = {p.author_id for p in posts}
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')
    unsubscribe_url = f"{site_url}/accounts/edit-profile/#email-prefs"
    subject = _build_subject(posts)
    current_year = timezone.now().year

    recipients = (
        User.objects
        .filter(is_active=True, email_notifications=True)
        .exclude(email='')
        .exclude(pk__in=author_ids)
    )

    sent = 0
    failed = 0
    for user in recipients.iterator():
        try:
            html_message = render_to_string('emails/blog_daily_digest.html', {
                'user': user,
                'posts': posts,
                'site_url': site_url,
                'unsubscribe_url': unsubscribe_url,
                'current_year': current_year,
            })
            plain_message = strip_tags(html_message)
            success, error = send_email(
                subject=subject,
                plain_message=plain_message,
                html_message=html_message,
                recipient_email=user.email,
            )
            if success:
                sent += 1
            else:
                failed += 1
                logger.warning(
                    f"send_daily_blog_digest: send to user {user.pk} returned error: {error}"
                )
        except Exception as e:
            failed += 1
            logger.warning(
                f"send_daily_blog_digest: send to user {user.pk} raised: {e}"
            )

    # Mark the day complete so a second Beat fire today no-ops.
    cache.set(today_key, True, timeout=82800)  # 23 hours

    logger.info(
        f"send_daily_blog_digest: sent={sent} failed={failed} posts={len(posts)}"
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python manage.py test apps.blog.tests.SendDailyBlogDigestTest -v 2
```

Expected: 7 tests pass.

- [ ] **Step 5: Run the full blog test module to check nothing regressed**

```bash
python manage.py test apps.blog -v 2
```

Expected: all tests pass (10 tests: 3 subject + 7 digest).

- [ ] **Step 6: Commit**

```bash
git add apps/blog/tasks.py apps/blog/tests.py
git commit -m "feat: send_daily_blog_digest Celery task"
```

---

## Task 4: Celery Beat Entry

**Files:**
- Modify: `recovery_hub/settings.py` (CELERY_BEAT_SCHEDULE dict)

- [ ] **Step 1: Add the beat entry**

In `recovery_hub/settings.py`, locate `CELERY_BEAT_SCHEDULE` (around line 705) and add this entry immediately after the `'retry-stuck-blog-push-fanouts'` entry (around line 758), still inside the dict:

```python
    # Daily blog digest — 7 AM UTC roundup of the last 24h of published posts
    'send-daily-blog-digest': {
        'task': 'apps.blog.tasks.send_daily_blog_digest',
        'schedule': crontab(hour=7, minute=0),
    },
```

The final block should look like:

```python
    # Reconcile blog push fan-outs dropped by Redis outages
    'retry-stuck-blog-push-fanouts': {
        'task': 'apps.blog.tasks.retry_stuck_blog_push_fanouts',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    # Daily blog digest — 7 AM UTC roundup of the last 24h of published posts
    'send-daily-blog-digest': {
        'task': 'apps.blog.tasks.send_daily_blog_digest',
        'schedule': crontab(hour=7, minute=0),
    },
}
```

- [ ] **Step 2: Verify Django still starts**

```bash
python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Commit**

```bash
git add recovery_hub/settings.py
git commit -m "feat: schedule send_daily_blog_digest at 7 AM UTC"
```

---

## Task 5: Management Command for Manual Trigger + Dry-Run

**Files:**
- Create: `apps/blog/management/commands/send_blog_digest.py`

- [ ] **Step 1: Create the command**

Create `apps/blog/management/commands/send_blog_digest.py` with this exact content:

```python
"""Manually trigger the daily blog digest email.

Usage:
    python manage.py send_blog_digest           # run synchronously, bypass idempotency cache
    python manage.py send_blog_digest --dry-run # render email for first recipient and print HTML; send nothing
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone


class Command(BaseCommand):
    help = "Send the daily blog digest now (bypasses the idempotency cache) or preview with --dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Render the email for the first eligible recipient and print to stdout. No emails sent, no cache writes.',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self._dry_run()
            return

        # Clear today's idempotency key so the task actually runs.
        today_key = f"blog_digest_sent_{timezone.now().date().isoformat()}"
        cache.delete(today_key)
        self.stdout.write(f"Cleared cache key {today_key}, running task...")

        from apps.blog.tasks import send_daily_blog_digest
        send_daily_blog_digest()
        self.stdout.write(self.style.SUCCESS("send_daily_blog_digest completed."))

    def _dry_run(self):
        from apps.blog.models import Post
        from apps.accounts.models import User

        window_start = timezone.now() - timedelta(hours=24)
        posts = list(
            Post.objects
            .filter(status='published', published_at__gte=window_start)
            .select_related('author')
            .order_by('-published_at')
        )
        if not posts:
            self.stdout.write(self.style.WARNING(
                "No posts in last 24h. Task would log and exit with no email sent."
            ))
            return

        author_ids = {p.author_id for p in posts}
        recipient = (
            User.objects
            .filter(is_active=True, email_notifications=True)
            .exclude(email='')
            .exclude(pk__in=author_ids)
            .first()
        )
        if recipient is None:
            self.stdout.write(self.style.WARNING(
                "No eligible recipients. Task would log and exit with no email sent."
            ))
            return

        site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')
        html = render_to_string('emails/blog_daily_digest.html', {
            'user': recipient,
            'posts': posts,
            'site_url': site_url,
            'unsubscribe_url': f"{site_url}/accounts/edit-profile/#email-prefs",
            'current_year': timezone.now().year,
        })
        self.stdout.write(f"--- Would send to: {recipient.email} ---")
        self.stdout.write(f"--- Posts in digest: {len(posts)} ---")
        for p in posts:
            self.stdout.write(f"  · {p.title} (by {p.author.username}, {p.published_at})")
        self.stdout.write("\n--- Rendered HTML (first 2000 chars) ---")
        self.stdout.write(html[:2000])
```

- [ ] **Step 2: Verify command registers**

```bash
python manage.py send_blog_digest --help
```

Expected: Usage help printed, including `--dry-run` argument.

- [ ] **Step 3: Commit**

```bash
git add apps/blog/management/commands/send_blog_digest.py
git commit -m "feat: send_blog_digest management command with --dry-run"
```

---

## Task 6: Deploy + Production Smoke Test

- [ ] **Step 1: Push to main**

```bash
git push origin main
```

Railway auto-deploys both `web` and `celery-worker` services.

- [ ] **Step 2: Wait for celery-worker redeploy to pick up the new beat entry**

```bash
until railway ssh --service celery-worker "grep -q send-daily-blog-digest /app/recovery_hub/settings.py && echo DEPLOYED" 2>&1 | grep -q DEPLOYED; do
  echo "waiting..."; sleep 20
done
echo "new beat schedule deployed"
```

Expected: prints `new beat schedule deployed` within a few minutes.

(If `railway ssh --service celery-worker` doesn't accept --service due to project linkage, link celery-worker first: `railway service` and choose it interactively, or run the grep via `railway logs` confirmation instead — watch for a `Scheduler: Sending due task send-daily-blog-digest` line at the next 7 AM UTC tick.)

- [ ] **Step 3: Dry-run in production to preview the email**

```bash
railway ssh "python manage.py send_blog_digest --dry-run"
```

Expected: Either

- `No posts in last 24h. Task would log and exit with no email sent.` (if it's been >24h since the last post), or
- A recipient line + post list + a block of HTML starting with `<!DOCTYPE html>`.

Eyeball the HTML for formatting issues (quotes, broken tags, missing context vars).

- [ ] **Step 4: Wait for next 7 AM UTC tick and verify**

```bash
railway logs --service celery-worker --json > /tmp/worker_logs.json 2>&1 &
LPID=$!
sleep 25
kill $LPID 2>/dev/null
wait $LPID 2>/dev/null
grep -E "send-daily-blog-digest|send_daily_blog_digest" /tmp/worker_logs.json | tail -20
```

Expected log lines on the next 7 AM UTC firing:
- `Scheduler: Sending due task send-daily-blog-digest`
- `Task apps.blog.tasks.send_daily_blog_digest[...] received`
- Either `send_daily_blog_digest: no posts in last 24h, no email sent`
- OR `send_daily_blog_digest: sent=N failed=M posts=P`
- `Task apps.blog.tasks.send_daily_blog_digest[...] succeeded in ...s: None`

- [ ] **Step 5: Confirm via Resend dashboard**

Open the Resend dashboard. Confirm N delivered emails (where N matches the `sent=N` log count) with subject either `New on MyRecoveryPal: ...` or `N new posts on MyRecoveryPal today`.

---

## Verification Checklist

After Task 6 completes:

- [ ] `python manage.py test apps.blog` passes all 10 tests locally
- [ ] `python manage.py check` reports no issues
- [ ] Beat schedule entry is present in production `settings.py` (Step 2 above)
- [ ] `send_blog_digest --dry-run` produces plausible HTML against production data
- [ ] First automated 7 AM UTC run logs `sent=N failed=M posts=P` (or the no-posts branch)
- [ ] Resend dashboard shows expected delivery count
- [ ] `blog_digest_sent_YYYY-MM-DD` key present in Redis for today (optional manual check)

## Rollback

If sends go wrong (spam complaints, mass bounces, etc.):

1. Remove the `'send-daily-blog-digest'` entry from `CELERY_BEAT_SCHEDULE` and redeploy. Beat will stop firing it within minutes of restart.
2. The task itself remains callable via `python manage.py send_blog_digest` for debugging.
3. No DB migration to roll back.
