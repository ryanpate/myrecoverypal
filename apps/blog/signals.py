from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Post
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def notify_users_on_blog_publish(sender, instance, created, **kwargs):
    """Create in-app notifications for all active users when a blog post is published."""
    if instance.status != 'published':
        return

    # Only notify on first publish (published_at just set by save())
    # Check update_fields to avoid re-notifying on subsequent edits
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'status' not in update_fields:
        return

    # For existing posts being re-saved while already published, skip
    if not created:
        # Check if this is a status change by looking for existing notifications
        from apps.accounts.models import Notification
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Post)
        already_notified = Notification.objects.filter(
            notification_type='new_blog_post',
            content_type=ct,
            object_id=instance.pk,
        ).exists()
        if already_notified:
            return

    # Bulk-create notifications for all active users
    from apps.accounts.models import User, Notification
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(Post)
    active_users = User.objects.filter(is_active=True).exclude(pk=instance.author_id)

    excerpt = instance.excerpt or instance.title
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + '...'

    notifications = [
        Notification(
            recipient=user,
            sender=instance.author,
            notification_type='new_blog_post',
            title='New Blog Post',
            message=f'"{instance.title}" — {excerpt}',
            link=instance.get_absolute_url(),
            content_type=ct,
            object_id=instance.pk,
        )
        for user in active_users
    ]

    if notifications:
        Notification.objects.bulk_create(notifications)
        logger.info(
            f"Created {len(notifications)} notifications for blog post: {instance.title}"
        )

        # bulk_create bypasses post_save, so fan out push notifications via Celery
        # to keep the publish request fast. Defer the enqueue until after the
        # surrounding transaction commits so we never publish a task for a post
        # that could still roll back. The kombu retry policy covers brief Redis
        # blips (Railway Redis restarts can take 15-30s); beyond that the
        # enqueue fails and recovery is via the `retry_blog_push_fanout`
        # management command.
        post_id = instance.pk
        transaction.on_commit(lambda: _enqueue_blog_push_fanout(post_id))


def _enqueue_blog_push_fanout(post_id):
    try:
        from apps.blog.tasks import fanout_blog_push_notifications
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
        logger.error(
            f"Failed to enqueue blog push fan-out for post {post_id} "
            f"after retries: {e}. Recover with: "
            f"python manage.py retry_blog_push_fanout {post_id}"
        )
