"""Weekly email reminders before a meeting, open to logged-out visitors.

Most meeting-page visitors arrive from search without an account, and until
now the only reminder (bookmark + push) required one. This asks only for an
email, confirms it (double opt-in, so nobody can sign someone else up), then
emails ~an hour before each weekly occurrence.
"""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import time_format
from django.utils.html import escape

from apps.accounts.email_service import send_email

from .models import MeetingReminder

logger = logging.getLogger(__name__)

MAX_REMINDERS_PER_EMAIL = 10
# The task runs every 15 minutes; a 30-minute window guarantees every meeting
# falls inside it on at least one run, and last_sent_at stops a second send.
WINDOW_MINUTES = (45, 75)


def _url(name, *args):
    return settings.SITE_URL.rstrip('/') + reverse(name, args=args)


def _zone(meeting):
    try:
        return ZoneInfo(meeting.timezone or 'America/Chicago')
    except Exception:
        return ZoneInfo('America/Chicago')


def minutes_until_today(meeting, now):
    """Minutes until the meeting starts today in its own timezone, or None."""
    if meeting.day is None or not meeting.time:
        return None
    local_now = now.astimezone(_zone(meeting))
    if (local_now.weekday() + 1) % 7 != meeting.day:  # model uses Sunday=0
        return None
    start = datetime.combine(local_now.date(), meeting.time, tzinfo=local_now.tzinfo)
    return (start - local_now).total_seconds() / 60


def request_reminder(email, meeting):
    """Create (or re-send) a pending reminder. Returns (reminder, error_message)."""
    email = email.strip().lower()
    existing = MeetingReminder.objects.filter(email=email, meeting=meeting).first()
    if existing:
        if not existing.confirmed_at:
            _send_confirmation(existing)
        return existing, None
    if MeetingReminder.objects.filter(email=email).count() >= MAX_REMINDERS_PER_EMAIL:
        return None, f'You already have {MAX_REMINDERS_PER_EMAIL} meeting reminders.'
    reminder = MeetingReminder.objects.create(email=email, meeting=meeting)
    _send_confirmation(reminder)
    return reminder, None


def _send_confirmation(reminder):
    meeting = reminder.meeting
    confirm = _url('support_services:meeting_reminder_confirm', reminder.token)
    plain = (
        f'Tap to confirm your weekly reminder for "{meeting.name}":\n{confirm}\n\n'
        "If you didn't ask for this, ignore this email and you won't hear from us.\n\n"
        '— MyRecoveryPal'
    )
    html = (
        f'<p>Confirm your weekly reminder for <strong>{escape(meeting.name)}</strong>:</p>'
        f'<p><a href="{confirm}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">Yes, remind me</a></p>'
        "<p style=\"color:#666;font-size:13px;\">If you didn't ask for this, ignore this "
        "email and you won't hear from us.</p>"
    )
    try:
        send_email(subject='Confirm your meeting reminder', plain_message=plain,
                   html_message=html, recipient_email=reminder.email)
    except Exception:
        logger.exception('Failed to send reminder confirmation %s', reminder.pk)


def _send_reminder(reminder):
    meeting = reminder.meeting
    starts = time_format(meeting.time, 'g:i A')
    detail = _url('support_services:meeting_detail', meeting.slug)
    unsubscribe = _url('support_services:meeting_reminder_unsubscribe', reminder.token)
    signup = _url('accounts:register')
    if meeting.conference_url:
        where_plain = f'Join online: {meeting.conference_url}'
        where_html = f'<a href="{escape(meeting.conference_url)}">Join online</a>'
    else:
        address = meeting.formatted_address or meeting.location or ''
        where_plain = f'Where: {address}' if address else ''
        where_html = f'Where: {escape(address)}' if address else ''
    plain = (
        f'{meeting.name} starts at {starts} today.\n{where_plain}\n'
        f'Meeting details: {detail}\n\n'
        f'Keeping count of your days? Track your sobriety free: {signup}\n\n'
        f'Stop these reminders: {unsubscribe}'
    )
    html = (
        f'<p><strong>{escape(meeting.name)}</strong> starts at {starts} today.</p>'
        f'<p>{where_html}</p><p><a href="{detail}">Meeting details</a></p>'
        f'<p style="color:#666;font-size:13px;">Keeping count of your days? '
        f'<a href="{signup}">Track your sobriety free</a>.</p>'
        f'<p style="color:#999;font-size:12px;"><a href="{unsubscribe}">Stop these reminders</a></p>'
    )
    send_email(subject=f'Starting in about an hour: {meeting.name}', plain_message=plain,
               html_message=html, recipient_email=reminder.email)


def send_due_reminders():
    now = timezone.now()
    sent = 0
    due = MeetingReminder.objects.filter(
        confirmed_at__isnull=False, meeting__is_active=True, meeting__is_approved=True,
    ).exclude(last_sent_at__gte=now - timedelta(hours=20)).select_related('meeting')
    for reminder in due:
        minutes = minutes_until_today(reminder.meeting, now)
        if minutes is None or not (WINDOW_MINUTES[0] <= minutes < WINDOW_MINUTES[1]):
            continue
        try:
            _send_reminder(reminder)
        except Exception:
            logger.exception('Failed to send meeting reminder %s', reminder.pk)
            continue
        reminder.last_sent_at = now
        reminder.save(update_fields=['last_sent_at'])
        sent += 1
    return sent


@shared_task
def send_meeting_email_reminders_task():
    return send_due_reminders()
