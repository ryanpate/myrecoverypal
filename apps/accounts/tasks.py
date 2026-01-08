from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# ========================================
# Welcome Email Sequence (Day 1, 3, 7)
# ========================================

@shared_task(bind=True, max_retries=3)
def send_welcome_email_day_1(self, user_id):
    """
    Welcome email sent immediately after registration.
    Welcomes user and encourages profile completion.
    """
    from .models import User

    try:
        user = User.objects.get(id=user_id)

        # Skip if user disabled email notifications
        if not user.email_notifications:
            logger.info(f"Skipping welcome email for {user.email} - notifications disabled")
            return False

        # Skip if already sent
        if user.welcome_email_1_sent:
            logger.info(f"Welcome email 1 already sent to {user.email}")
            return False

        site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

        html_message = render_to_string('emails/welcome_day_1.html', {
            'user': user,
            'site_url': site_url,
            'current_year': timezone.now().year,
        })
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Welcome to MyRecoveryPal! 🌟",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        user.welcome_email_1_sent = timezone.now()
        user.save(update_fields=['welcome_email_1_sent'])

        logger.info(f"Welcome email Day 1 sent to {user.email}")
        return True

    except User.DoesNotExist:
        logger.error(f"User {user_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error sending welcome email Day 1: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_welcome_emails_day_3():
    """
    Scheduled task to send Day 3 welcome emails.
    Sent to users who joined 3+ days ago and haven't received this email yet.
    Uses date (not datetime) to avoid missing users if Celery runs inconsistently.
    """
    from .models import User

    # Target users who joined 3+ days ago (using date to be more reliable)
    three_days_ago = (timezone.now() - timedelta(days=3)).date()

    # Users who joined 3+ days ago but haven't received Day 3 email
    users = User.objects.filter(
        date_joined__date__lte=three_days_ago,
        email_notifications=True,
        welcome_email_2_sent__isnull=True,
        welcome_email_1_sent__isnull=False,  # Must have received Day 1
    ).exclude(
        # Don't send to users who joined more than 10 days ago (too late)
        date_joined__date__lt=(timezone.now() - timedelta(days=10)).date()
    )

    sent_count = 0
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    for user in users:
        try:
            html_message = render_to_string('emails/welcome_day_3.html', {
                'user': user,
                'site_url': site_url,
                'has_completed_onboarding': user.has_completed_onboarding,
                'days_sober': user.get_days_sober(),
                'current_year': timezone.now().year,
            })
            plain_message = strip_tags(html_message)

            send_mail(
                subject="How's your recovery journey going? 💪",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            user.welcome_email_2_sent = timezone.now()
            user.save(update_fields=['welcome_email_2_sent'])
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending Day 3 email to {user.email}: {e}")

    logger.info(f"Welcome email Day 3 sent to {sent_count} users")
    return sent_count


@shared_task
def send_welcome_emails_day_7():
    """
    Scheduled task to send Day 7 welcome emails.
    Celebrates their first week and encourages engagement.
    Uses date (not datetime) to avoid missing users if Celery runs inconsistently.
    """
    from .models import User

    # Target users who joined 7+ days ago (using date to be more reliable)
    seven_days_ago = (timezone.now() - timedelta(days=7)).date()

    users = User.objects.filter(
        date_joined__date__lte=seven_days_ago,
        email_notifications=True,
        welcome_email_3_sent__isnull=True,
        welcome_email_2_sent__isnull=False,  # Must have received Day 3
    ).exclude(
        # Don't send to users who joined more than 21 days ago (too late)
        date_joined__date__lt=(timezone.now() - timedelta(days=21)).date()
    )

    sent_count = 0
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    for user in users:
        try:
            # Get some engagement stats
            post_count = user.social_posts.count()
            follower_count = user.followers.filter(status='active').count()
            following_count = user.following.filter(status='active').count()
            checkin_count = user.daily_checkins.count()

            html_message = render_to_string('emails/welcome_day_7.html', {
                'user': user,
                'site_url': site_url,
                'post_count': post_count,
                'follower_count': follower_count,
                'following_count': following_count,
                'checkin_count': checkin_count,
                'days_sober': user.get_days_sober(),
                'current_year': timezone.now().year,
            })
            plain_message = strip_tags(html_message)

            send_mail(
                subject="🎉 One week with MyRecoveryPal!",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            user.welcome_email_3_sent = timezone.now()
            user.save(update_fields=['welcome_email_3_sent'])
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending Day 7 email to {user.email}: {e}")

    logger.info(f"Welcome email Day 7 sent to {sent_count} users")
    return sent_count


# ========================================
# Daily Check-in Reminder
# ========================================

@shared_task
def send_checkin_reminders():
    """
    Send check-in reminders to users who haven't checked in today.
    Only sends to users who have checked in before (engaged users).
    """
    from .models import User, DailyCheckIn

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_reminder_cutoff = timezone.now() - timedelta(hours=20)

    # Users who:
    # - Have email notifications enabled
    # - Have checked in at least once before
    # - Haven't checked in today
    # - Haven't received a reminder in the last 20 hours
    users_with_prior_checkins = User.objects.filter(
        email_notifications=True,
        daily_checkins__isnull=False,
    ).exclude(
        daily_checkins__date=today
    ).exclude(
        last_checkin_reminder_sent__gte=last_reminder_cutoff
    ).distinct()

    sent_count = 0
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    for user in users_with_prior_checkins:
        try:
            # Get their streak info
            streak = user.get_checkin_streak()
            last_checkin = user.daily_checkins.order_by('-date').first()

            html_message = render_to_string('emails/checkin_reminder.html', {
                'user': user,
                'site_url': site_url,
                'streak': streak,
                'last_checkin_date': last_checkin.date if last_checkin else None,
                'days_sober': user.get_days_sober(),
                'current_year': timezone.now().year,
            })
            plain_message = strip_tags(html_message)

            send_mail(
                subject="Don't break your streak! Check in today 🔥",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            user.last_checkin_reminder_sent = timezone.now()
            user.save(update_fields=['last_checkin_reminder_sent'])
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending check-in reminder to {user.email}: {e}")

    logger.info(f"Check-in reminders sent to {sent_count} users")
    return sent_count


# ========================================
# Weekly Digest Email
# ========================================

@shared_task
def send_weekly_digests():
    """
    Send weekly digest emails summarizing activity.
    Includes: new followers, missed posts, community highlights.
    """
    from .models import User, SocialPost, UserConnection, Notification
    from django.db import models as db_models

    one_week_ago = timezone.now() - timedelta(days=7)
    last_digest_cutoff = timezone.now() - timedelta(days=6)

    # Users who haven't received a digest in the last 6 days
    users = User.objects.filter(
        email_notifications=True,
        is_active=True,
    ).exclude(
        last_weekly_digest_sent__gte=last_digest_cutoff
    )

    sent_count = 0
    site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')

    for user in users:
        try:
            # Gather digest content
            new_followers = UserConnection.objects.filter(
                target=user,
                status='active',
                created_at__gte=one_week_ago
            ).select_related('user')[:5]

            # Unread notifications count
            unread_notifications = Notification.objects.filter(
                recipient=user,
                is_read=False,
                created_at__gte=one_week_ago
            ).count()

            # Popular posts from people they follow
            following_ids = user.following.filter(status='active').values_list('target_id', flat=True)
            popular_posts = SocialPost.objects.filter(
                user_id__in=following_ids,
                created_at__gte=one_week_ago,
                visibility='public'
            ).annotate(
                like_count=db_models.Count('likes')
            ).order_by('-like_count')[:3]

            # If no activity, skip sending
            if not new_followers.exists() and unread_notifications == 0 and not popular_posts.exists():
                continue

            html_message = render_to_string('emails/weekly_digest.html', {
                'user': user,
                'site_url': site_url,
                'new_followers': new_followers,
                'new_follower_count': new_followers.count(),
                'unread_notifications': unread_notifications,
                'popular_posts': popular_posts,
                'days_sober': user.get_days_sober(),
                'current_year': timezone.now().year,
            })
            plain_message = strip_tags(html_message)

            send_mail(
                subject="Your weekly recovery recap 📬",
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            user.last_weekly_digest_sent = timezone.now()
            user.save(update_fields=['last_weekly_digest_sent'])
            sent_count += 1

        except Exception as e:
            logger.error(f"Error sending weekly digest to {user.email}: {e}")

    logger.info(f"Weekly digests sent to {sent_count} users")
    return sent_count


# ========================================
# Invite Email (existing)
# ========================================

@shared_task(bind=True, max_retries=3)
def send_invite_email_task(self, invite_code_id):
    """
    Celery task to send invite email asynchronously
    """
    from .invite_models import InviteCode
    
    try:
        invite_code = InviteCode.objects.get(id=invite_code_id)
        success = invite_code.send_invite_email()
        
        if success:
            logger.info(f"Successfully sent invite email to {invite_code.email}")
        else:
            logger.warning(f"Failed to send invite email to {invite_code.email}")
            
        return success
    except InviteCode.DoesNotExist:
        logger.error(f"InviteCode {invite_code_id} does not exist")
        return False
    except Exception as e:
        logger.error(f"Error sending invite email: {e}")
        # Retry after 60 seconds
        raise self.retry(exc=e, countdown=60)