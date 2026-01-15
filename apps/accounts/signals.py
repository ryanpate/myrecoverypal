from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import User, Milestone, ActivityFeed, DailyCheckIn
from .payment_models import Subscription
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_joined_activity(sender, instance, created, **kwargs):
    """Create activity when user joins"""
    if created:
        ActivityFeed.objects.create(
            user=instance,
            activity_type='user_joined',
            title=f"{instance.get_full_name() or instance.username} joined the community!",
            description=f"Welcome {instance.get_full_name() or instance.username} to our recovery community!",
            is_public=True,
            extra_data={'join_date': instance.date_joined.isoformat()}
        )


@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """Create a 14-day Premium trial subscription for new users"""
    if created:
        from django.utils import timezone
        from datetime import timedelta

        trial_end = timezone.now() + timedelta(days=14)

        Subscription.objects.get_or_create(
            user=instance,
            defaults={
                'tier': 'premium',
                'status': 'trialing',
                'trial_end': trial_end,
            }
        )


@receiver(post_save, sender=User)
def send_welcome_email_on_registration(sender, instance, created, **kwargs):
    """Send welcome email after user completes onboarding, not immediately after registration.
    This gives users time to complete onboarding before receiving email prompts."""
    if not created and instance.has_completed_onboarding:
        # Only send if they just completed onboarding and email hasn't been sent yet
        if not instance.welcome_email_1_sent:
            try:
                from .tasks import send_welcome_email_day_1
                # Delay 5 minutes to let them explore first
                send_welcome_email_day_1.apply_async(args=[instance.id], countdown=300)
                logger.info(f"Queued welcome email for user {instance.id}")
            except Exception as e:
                # Celery broker unavailable - send email directly as fallback
                logger.warning(f"Could not queue welcome email for user {instance.id}: {e}. Sending directly...")
                try:
                    _send_welcome_email_directly(instance)
                except Exception as direct_error:
                    logger.error(f"Failed to send welcome email directly for user {instance.id}: {direct_error}")


def _send_welcome_email_directly(user):
    """Fallback to send welcome email directly when Celery is unavailable."""
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.utils import timezone
    from django.conf import settings
    from .email_service import send_email

    if not user.email_notifications:
        logger.info(f"Skipping welcome email for {user.email} - notifications disabled")
        return

    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    html_message = render_to_string('emails/welcome_day_1.html', {
        'user': user,
        'site_url': site_url,
        'current_year': timezone.now().year,
    })
    plain_message = strip_tags(html_message)

    success, error = send_email(
        subject="Welcome to MyRecoveryPal! 🌟",
        plain_message=plain_message,
        html_message=html_message,
        recipient_email=user.email,
    )

    if success:
        user.welcome_email_1_sent = timezone.now()
        user.save(update_fields=['welcome_email_1_sent'])
        logger.info(f"Welcome email sent directly to {user.email}")
    else:
        raise Exception(f"Email service failed for {user.email}: {error}")


@receiver(post_save, sender=Milestone)
def create_milestone_activity(sender, instance, created, **kwargs):
    """Create activity when milestone is created"""
    if created:
        # Determine if this is a significant milestone
        is_significant = False
        if instance.milestone_type == 'days' and instance.days_sober:
            significant_days = [1, 7, 30, 60, 90, 180,
                                365, 730, 1095]  # Including 3 years
            is_significant = instance.days_sober in significant_days

        # Create activity
        activity_title = instance.title
        if instance.milestone_type == 'days' and instance.days_sober:
            activity_title = f"🎉 {instance.user.get_full_name() or instance.user.username} reached {instance.days_sober} days sober!"

        ActivityFeed.objects.create(
            user=instance.user,
            activity_type='milestone_created',
            content_object=instance,
            title=activity_title,
            description=instance.description,
            is_public=True,
            extra_data={
                'milestone_type': instance.milestone_type,
                'days_sober': instance.days_sober,
                'is_significant': is_significant
            }
        )


@receiver(post_save, sender=DailyCheckIn)
def create_checkin_activity(sender, instance, created, **kwargs):
    """Create activity when daily check-in is shared"""
    if created and instance.is_shared:
        mood_display = instance.get_mood_display_with_emoji()

        activity_title = f"{instance.user.get_full_name() or instance.user.username} checked in"
        description = f"Feeling {mood_display.lower()}"

        if instance.gratitude:
            description += f" • Grateful for: {instance.gratitude[:100]}{'...' if len(instance.gratitude) > 100 else ''}"

        ActivityFeed.objects.create(
            user=instance.user,
            activity_type='check_in_posted',
            content_object=instance,
            title=activity_title,
            description=description,
            is_public=True,
            extra_data={
                'mood': instance.mood,
                'mood_display': mood_display,
                'craving_level': instance.craving_level,
                'energy_level': instance.energy_level
            }
        )


def create_blog_post_activity(user, blog_post):
    """Helper function to create blog post activity - call this from blog app"""
    ActivityFeed.objects.create(
        user=user,
        activity_type='blog_post_published',
        content_object=blog_post,
        title=f"{user.get_full_name() or user.username} shared their story",
        description=f"New post: {blog_post.title}",
        is_public=True,
        extra_data={
            'post_title': blog_post.title,
            'is_personal_story': getattr(blog_post, 'is_personal_story', False),
            'has_trigger_warning': getattr(blog_post, 'trigger_warning', False)
        }
    )


def create_comment_activity(user, comment, parent_object):
    """Helper function to create comment activity"""
    parent_name = parent_object.__class__.__name__.lower()

    ActivityFeed.objects.create(
        user=user,
        activity_type='comment_posted',
        content_object=comment,
        title=f"{user.get_full_name() or user.username} left a comment",
        description=f"Commented on a {parent_name}",
        is_public=True,
        extra_data={
            'parent_type': parent_name,
            'comment_preview': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content
        }
    )


def create_profile_update_activity(user):
    """Helper function to create profile update activity"""
    ActivityFeed.objects.create(
        user=user,
        activity_type='profile_updated',
        title=f"{user.get_full_name() or user.username} updated their profile",
        description="Check out their updated profile information",
        is_public=True,
        extra_data={'update_date': user.last_login.isoformat()
                    if user.last_login else None}
    )
