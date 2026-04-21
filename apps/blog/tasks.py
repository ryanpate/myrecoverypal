from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fanout_blog_push_notifications(self, post_id):
    """Send iOS/Android/web push notifications for a newly published blog post.

    In-app Notification records are created synchronously in the post_save
    signal via bulk_create. This task handles the slow fan-out to APNs/FCM
    so the publish request returns immediately.

    Idempotent: skips if `push_fanout_completed_at` is already set. This
    protects against duplicate pushes when the beat reconciliation task races
    with a slow in-flight fan-out.
    """
    from apps.blog.models import Post
    from apps.accounts.models import User
    from apps.accounts.push_notifications import send_push_to_user

    try:
        post = Post.objects.select_related('author').get(pk=post_id)
    except Post.DoesNotExist:
        logger.warning(f"fanout_blog_push_notifications: post {post_id} not found")
        return

    if post.status != 'published':
        return

    if post.push_fanout_completed_at is not None:
        logger.info(
            f"fanout_blog_push_notifications: post {post_id} already completed"
            f" at {post.push_fanout_completed_at.isoformat()}, skipping"
        )
        return

    excerpt = post.excerpt or post.title
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + '...'

    push_title = 'New Blog Post'
    push_body = f'"{post.title}" — {excerpt}'
    push_data = {
        'type': 'new_blog_post',
        'link': post.get_absolute_url(),
        'post_id': str(post.pk),
    }

    sent = 0
    failed = 0
    recipients = User.objects.filter(is_active=True).exclude(pk=post.author_id)
    for user in recipients.iterator():
        try:
            send_push_to_user(user, push_title, push_body, push_data)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Blog push to user {user.pk} failed: {e}")

    # Mark done so the beat reconciliation task doesn't re-enqueue us.
    Post.objects.filter(pk=post_id).update(push_fanout_completed_at=timezone.now())

    logger.info(
        f"fanout_blog_push_notifications: post={post_id} sent={sent} failed={failed}"
    )


@shared_task
def retry_stuck_blog_push_fanouts():
    """Reconcile dropped blog push fan-outs.

    Finds published posts within the last 2 days whose fan-out never finished
    (push_fanout_completed_at is NULL) and re-enqueues them. Runs on beat so
    that when Redis recovers from an outage longer than the kombu retry
    window, the fan-out eventually completes without manual intervention.

    Skips posts published in the last 5 minutes to avoid racing with a
    healthy enqueue path or an in-flight task.
    """
    from datetime import timedelta
    from apps.blog.models import Post

    now = timezone.now()
    lookback_floor = now - timedelta(days=2)
    grace_ceiling = now - timedelta(minutes=5)

    stuck = Post.objects.filter(
        status='published',
        published_at__gte=lookback_floor,
        published_at__lte=grace_ceiling,
        push_fanout_completed_at__isnull=True,
    ).values_list('pk', flat=True)

    stuck_ids = list(stuck)
    if not stuck_ids:
        return

    logger.warning(
        f"retry_stuck_blog_push_fanouts: re-enqueuing {len(stuck_ids)} "
        f"dropped fan-outs: {stuck_ids}"
    )

    for post_id in stuck_ids:
        try:
            fanout_blog_push_notifications.apply_async(
                args=[post_id],
                retry=True,
                retry_policy={
                    'max_retries': 5,
                    'interval_start': 1.0,
                    'interval_step': 2.0,
                    'interval_max': 5.0,
                },
            )
        except Exception as e:
            # Redis still down — next beat tick will try again.
            logger.warning(
                f"retry_stuck_blog_push_fanouts: re-enqueue of post "
                f"{post_id} failed: {e}"
            )


def _build_subject(posts):
    """Build the subject line for the daily blog digest.

    One post → "New on MyRecoveryPal: {title}"
    N posts  → "{N} new posts on MyRecoveryPal today"
    """
    if len(posts) == 1:
        return f"New on MyRecoveryPal: {posts[0].title}"
    return f"{len(posts)} new posts on MyRecoveryPal today"


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
