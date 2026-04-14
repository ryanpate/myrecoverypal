from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def fanout_blog_push_notifications(self, post_id):
    """Send iOS/Android/web push notifications for a newly published blog post.

    In-app Notification records are created synchronously in the post_save
    signal via bulk_create. This task handles the slow fan-out to APNs/FCM
    so the publish request returns immediately.
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

    logger.info(
        f"fanout_blog_push_notifications: post={post_id} sent={sent} failed={failed}"
    )
