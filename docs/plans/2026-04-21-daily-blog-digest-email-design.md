# Daily Blog Digest Email — Design

**Date:** 2026-04-21
**Status:** Approved, ready for implementation plan

## Problem

Blog posts only reach users via in-app notifications and iOS push. Email reach is currently limited to welcome sequence, weekly digest, check-in reminders, and transactional emails. New blog posts (averaging ~1/day) are a strong retention hook, but most users will not open the app daily to see them.

## Goal

Send one email per day summarizing blog posts published in the previous 24 hours. Zero posts = no email. One or more posts = one digest email per recipient.

## Non-Goals

- Per-post immediate emails (rejected — fatigue risk, and the iOS push already covers immediacy for native-app users).
- Timezone-aware per-user send times (rejected — 18-user beta, UTC is sufficient).
- A new `blog_email_notifications` preference field (rejected — existing `email_notifications` kill-switch is granular enough at current scale; can be split later if complaints arrive).
- Per-user unsubscribe token URLs (rejected — link to Edit Profile is acceptable for beta).

## Architecture

### Beat task

Fires daily at **7 AM UTC** (3 AM EDT). Placed in the existing `CELERY_BEAT_SCHEDULE` in `recovery_hub/settings.py`.

```python
'send-daily-blog-digest': {
    'task': 'apps.blog.tasks.send_daily_blog_digest',
    'schedule': crontab(hour=7, minute=0),
},
```

### Task logic

Location: `apps/blog/tasks.py` (same module as `fanout_blog_push_notifications`).

Pseudocode:

```python
@shared_task
def send_daily_blog_digest():
    # Idempotency gate — skip if already sent today.
    today_key = f"blog_digest_sent_{timezone.now().date().isoformat()}"
    if cache.get(today_key):
        logger.info("Blog digest already sent today, skipping.")
        return

    window_start = timezone.now() - timedelta(hours=24)
    posts = list(
        Post.objects
            .filter(status='published', published_at__gte=window_start)
            .select_related('author')
            .order_by('-published_at')
    )
    if not posts:
        logger.info("No posts in last 24h — no digest to send.")
        return

    author_ids = {p.author_id for p in posts}
    recipients = (
        User.objects
            .filter(is_active=True, email_notifications=True)
            .exclude(email='')
            .exclude(pk__in=author_ids)
    )

    sent = failed = 0
    for user in recipients.iterator():
        try:
            html = render_to_string('emails/blog_daily_digest.html', {
                'user': user,
                'posts': posts,
                'unsubscribe_url': f"{settings.SITE_URL}/accounts/edit-profile/#email-prefs",
            })
            subject = _build_subject(posts)
            send_email(
                subject=subject,
                plain_message=strip_tags(html),
                html_message=html,
                recipient_email=user.email,
            )
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Blog digest to user {user.pk} failed: {e}")

    cache.set(today_key, True, timeout=82800)  # 23 hours
    logger.info(f"Blog digest: sent={sent} failed={failed} posts={len(posts)}")
```

Subject builder:

```python
def _build_subject(posts):
    if len(posts) == 1:
        return f"New on MyRecoveryPal: {posts[0].title}"
    return f"{len(posts)} new posts on MyRecoveryPal today"
```

### Email template

Location: `apps/accounts/templates/emails/blog_daily_digest.html`.

Structure (matching existing `welcome_day_3.html` / `weekly_digest.html`):

- Site header (logo + brand color)
- Greeting: "Hi {{ user.first_name|default:user.username }},"
- Intro line: "Here's what's new on MyRecoveryPal today."
- `{% for post in posts %}` block:
  - Post title (h2, linked to post URL)
  - Author name + relative publish time ("by Ryan · 3 hours ago")
  - Excerpt (truncated to ~120 chars; falls back to first 120 chars of body if no excerpt)
  - "Read full post →" button linking to `{{ site_url }}{{ post.get_absolute_url }}`
- Footer: small print with unsubscribe link to Edit Profile email preferences anchor.

Plain-text version: auto-generated via `strip_tags(html)` at send time (matches weekly_digest pattern — no separate `.txt` template required).

### Delivery

- Uses `apps.accounts.email_service.send_email` (Resend HTTP API primary, SMTP fallback, retry with exponential backoff — already in place).
- Per-user try/except so a single bad address doesn't abort the batch.
- Counts logged; no Sentry noise on individual user failures.

### Idempotency

Cache key `blog_digest_sent_{YYYY-MM-DD}` with 23h TTL. If beat fires twice the same day (Railway redeploy bumping beat near 7 AM), the second invocation no-ops. The key lives in the `default` cache backend (Redis), shared across web and celery-worker.

### Manual trigger

Management command `apps/blog/management/commands/send_blog_digest.py`:

- `python manage.py send_blog_digest` — runs the task synchronously against the production DB (bypasses the idempotency cache so operators can retry).
- `python manage.py send_blog_digest --dry-run` — renders the email for the first recipient and prints to stdout without sending. No DB writes, no cache writes, no email sent.

## Data Flow

```
Beat scheduler (celery-worker, 7 AM UTC)
   │
   ▼
send_daily_blog_digest task
   │
   ├──► Cache GET  blog_digest_sent_{date}   ── hit ──► return (no-op)
   │
   ├──► Post.objects.filter(published_at >= now-24h)
   │       │
   │       └──► zero posts ──► return (log, no-op)
   │
   ├──► User.objects.filter(active, email_notifications)
   │       exclude(author_ids)
   │
   ├──► for each user: render → send_email (Resend → SMTP fallback)
   │
   └──► Cache SET  blog_digest_sent_{date}   TTL=23h
```

## Error Handling

- **Zero posts in window:** log and return, no email sent.
- **Zero recipients (all authors, all opted out):** loop runs zero iterations, logs `sent=0 failed=0`, cache still set to prevent retry.
- **Individual user send failure:** caught, counted in `failed`, loop continues.
- **Redis/cache unavailable:** cache.get returns None, cache.set silently fails; task proceeds without idempotency but still sends. Acceptable degradation.
- **Template render error:** caught by per-user try/except; one user's bad data doesn't block others.
- **Broker unreachable when beat tries to enqueue:** existing Celery worker with `-A recovery_hub` uses the correctly-configured app (fix just landed for the web-service variant); beat enqueues through the local broker connection which is healthy by construction.

## Testing Plan

1. **Unit test — subject builder:** one post → "New on MyRecoveryPal: ...", N posts → "N new posts...".
2. **Unit test — zero-posts branch:** no Posts in window → task returns early, no emails attempted.
3. **Unit test — author exclusion:** author of the only post in window is excluded from recipients.
4. **Unit test — email_notifications=False excluded.**
5. **Unit test — idempotency:** call task twice, second invocation no-ops (mock cache).
6. **Integration check:** run `send_blog_digest --dry-run` against current prod DB to eyeball the rendered email.

## Observability

- Log lines:
  - `"No posts in last 24h — no digest to send."`
  - `"Blog digest already sent today, skipping."`
  - `"Blog digest: sent=N failed=M posts=P"` (success summary)
  - `"Blog digest to user X failed: ..."` (per-user warning)
- No new metrics. Existing Resend dashboard shows delivery/open/click rates.

## Files to Create / Modify

**Create:**
- `apps/accounts/templates/emails/blog_daily_digest.html`
- `apps/blog/management/commands/send_blog_digest.py`

**Modify:**
- `apps/blog/tasks.py` — add `send_daily_blog_digest` task and `_build_subject` helper
- `recovery_hub/settings.py` — add `'send-daily-blog-digest'` entry to `CELERY_BEAT_SCHEDULE`

**Tests:**
- `apps/blog/tests/test_daily_digest.py` (new file if module doesn't exist)

## Rollout

1. Merge and deploy.
2. Celery-worker picks up the new beat entry on restart.
3. First digest fires at the next 7 AM UTC tick.
4. Verify with `railway logs --service celery-worker | grep "Blog digest"` after the tick.
5. Check Resend dashboard for delivery counts.

No migration required. No feature flag. `email_notifications` already defaults to `True` on existing users, so everyone is opted in by default.

## Open Questions

None — all pre-design questions resolved with the user.
