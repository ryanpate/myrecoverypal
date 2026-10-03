"""Daily lesson reminders for guided programs.

`send_program_reminders` runs hourly (CELERY_BEAT_SCHEDULE) and acts on each
member at REMINDER_LOCAL_HOUR in their own time zone, at most once per local
day:

  * Today's lesson is open: an in-app notification plus push, for the first
    PUSH_MAX_DAYS_OPEN days the lesson sits unread. An email nudge goes out
    only once a lesson has been open EMAIL_AFTER_DAYS_OPEN days, then at most
    every EMAIL_EVERY_DAYS days. Everything stops after GIVE_UP_DAYS_OPEN
    days; the member can come back any time and reminders resume.
  * A free member who finished the free days: one in-app notification plus
    push pointing to Premium, ever. Never repeated.
  * Waiting for tomorrow, finished, or unknown program: nothing.

Skipped entirely: reminders turned off for that enrollment, notifications
turned off on the account, or a crisis-triggered coach session in the last
48 hours (same rule as the email sequences). Emails also need marketing
emails on, and carry the standard unsubscribe link.
"""
import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

REMINDER_LOCAL_HOUR = 9
PUSH_MAX_DAYS_OPEN = 7
EMAIL_AFTER_DAYS_OPEN = 2
EMAIL_EVERY_DAYS = 3
GIVE_UP_DAYS_OPEN = 14
# Members whose browser hasn't reported a time zone yet. Most members are in
# the US, and 9 AM Central is a reasonable morning across US zones.
FALLBACK_TZ = 'America/Chicago'


def _member_zone(user):
    try:
        return ZoneInfo(user.timezone) if getattr(user, 'timezone', '') else ZoneInfo(FALLBACK_TZ)
    except Exception:
        return ZoneInfo(FALLBACK_TZ)


def _open_since(enrollment, progress):
    """Local date the current lesson became available."""
    if progress.next_day == 1:
        return timezone.localtime(enrollment.started_at).date()
    return progress.completed[progress.next_day - 1] + timedelta(days=1)


def _notify(user, notification_type, push_type, title, message, link):
    from apps.accounts.models import Notification
    from apps.accounts.push_notifications import PushNotificationService

    Notification.objects.create(
        recipient=user, sender=None, notification_type=notification_type,
        title=title, message=message, link=link,
    )
    try:
        PushNotificationService._send_push(
            recipient=user, notification_type=push_type, sender=None,
            data={'type': push_type, 'link': link},
        )
    except Exception as err:
        logger.warning(f'Program reminder push failed for user {user.id}: {err}')


def _email(user, program, lesson, days_open, link):
    from apps.accounts.email_sequences import marketing_unsubscribe_url
    from apps.accounts.email_service import send_email

    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    html = render_to_string('emails/program_nudge.html', {
        'user': user,
        'program': program,
        'lesson': lesson,
        'days_open': days_open,
        'lesson_url': f'{site_url}{link}',
        'program_url': f"{site_url}{reverse('resources:program_detail', args=[program.slug])}",
        'unsubscribe_url': marketing_unsubscribe_url(user),
        'current_year': timezone.now().year,
    })
    ok, error = send_email(
        subject=f'Day {lesson.day} of {program.title} is waiting for you',
        plain_message=strip_tags(html),
        html_message=html,
        recipient_email=user.email,
    )
    if not ok:
        raise RuntimeError(error)


def remind_enrollment(enrollment, now=None):
    """Send whatever this enrollment is due right now. Returns what was sent:
    a subset of {'push', 'email', 'premium'}."""
    from apps.accounts.email_sequences import is_crisis_suppressed

    from .program_service import get_progress
    from .programs import FREE_DAYS

    user = enrollment.user
    program = enrollment.program
    if program is None or enrollment.completed_at or not enrollment.reminders_enabled:
        return set()
    if not user.is_active or not user.email_notifications or is_crisis_suppressed(user):
        return set()

    sent = set()
    with timezone.override(_member_zone(user)):
        local_now = timezone.localtime(now or timezone.now())
        today = local_now.date()
        if local_now.hour != REMINDER_LOCAL_HOUR or enrollment.last_reminder_on == today:
            return sent

        progress = get_progress(enrollment, user, today)
        if progress.next_status == 'current':
            lesson = program.lesson(progress.next_day)
            days_open = (today - _open_since(enrollment, progress)).days
            if days_open > GIVE_UP_DAYS_OPEN:
                return sent
            link = reverse('resources:program_day', args=[program.slug, lesson.day])
            if days_open < PUSH_MAX_DAYS_OPEN:
                _notify(user, 'program_reminder', 'program_reminder',
                        f'{program.title}: Day {lesson.day} is ready',
                        f'"{lesson.title}". About 5 minutes.', link)
                sent.add('push')
            email_due = (days_open >= EMAIL_AFTER_DAYS_OPEN and (
                enrollment.last_email_on is None
                or (today - enrollment.last_email_on).days >= EMAIL_EVERY_DAYS))
            if email_due and user.marketing_emails_enabled and user.email:
                try:
                    _email(user, program, lesson, days_open, link)
                    enrollment.last_email_on = today
                    sent.add('email')
                except Exception as err:
                    logger.error(f'Program nudge email failed for user {user.id}: {err}')
        elif progress.next_status == 'premium' and not enrollment.premium_nudge_sent:
            link = reverse('resources:program_detail', args=[program.slug])
            _notify(user, 'program_reminder', 'program_premium',
                    f'You finished week one of {program.title}',
                    f'That\'s {FREE_DAYS} days of showing up. Premium opens the rest of the program.',
                    link)
            enrollment.premium_nudge_sent = True
            sent.add('premium')

        if sent:
            enrollment.last_reminder_on = today
            enrollment.save(update_fields=[
                'last_reminder_on', 'last_email_on', 'premium_nudge_sent'])
    return sent


@shared_task
def send_program_reminders():
    from .models import ProgramEnrollment

    counts = {'push': 0, 'email': 0, 'premium': 0}
    enrollments = ProgramEnrollment.objects.filter(
        completed_at__isnull=True, reminders_enabled=True,
    ).select_related('user')
    for enrollment in enrollments:
        try:
            for kind in remind_enrollment(enrollment):
                counts[kind] += 1
        except Exception as err:
            logger.error(f'Program reminder failed for enrollment {enrollment.id}: {err}')
    logger.info(f'Program reminders sent: {counts}')
    return counts
