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
