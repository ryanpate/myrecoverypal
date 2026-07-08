"""Eligibility helpers and definitions for the member email sequences.

Two sequences (spec: docs/plans/2026-07-08-email-sequences.md):
- Onboarding: E1 immediately (signal-triggered), E2–E6 on days 1/3/6/9/14.
  Early exit once the user has done the three actions that predict
  retention: a check-in (streak), a journal entry, a community action.
- Re-engagement: R1/R2/R3 at days 0/5/12 after 21 days of inactivity.

Suppression (both): unsubscribed, notifications off, or a crisis-triggered
coach session in the last 48h. A person in crisis must never receive
"check your streak!".
"""
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils import timezone

CRISIS_SUPPRESSION_HOURS = 48
INACTIVITY_DAYS = 21
REENGAGEMENT_REENTRY_DAYS = 90


def has_started_streak(user):
    return user.daily_checkins.exists()


def has_journal_entry(user):
    return user.journal_entries.exists()


def has_community_action(user):
    return (
        user.social_posts.exists()
        or user.post_comments.exists()
        or user.post_reactions.exists()
        or user.liked_posts.exists()
    )


def is_activated(user):
    """All three retention-predicting actions done -> exit onboarding early."""
    return (
        has_started_streak(user)
        and has_journal_entry(user)
        and has_community_action(user)
    )


def has_used_anchor(user):
    from .models import CoachMessage
    return CoachMessage.objects.filter(
        session__user=user, role='user').exists()


def is_crisis_suppressed(user):
    """True if the user opened a crisis-triggered coach session recently."""
    from .models import RecoveryCoachSession
    cutoff = timezone.now() - timedelta(hours=CRISIS_SUPPRESSION_HOURS)
    return RecoveryCoachSession.objects.filter(
        user=user, trigger='checkin_support', updated_at__gte=cutoff,
    ).exists()


def get_last_activity(user):
    """Most recent activity signal we have for the user.

    ANY activity should exit the re-engagement sequence, so this looks past
    `last_login`/`last_seen` (which are only updated by explicit login and a
    single page) to the user's most recent check-in, post, or journal entry.
    """
    candidates = [user.date_joined]
    if user.last_login:
        candidates.append(user.last_login)
    if user.last_seen:
        candidates.append(user.last_seen)

    last_checkin = user.daily_checkins.order_by(
        '-created_at').values_list('created_at', flat=True).first()
    if last_checkin:
        candidates.append(last_checkin)

    last_post = user.social_posts.order_by(
        '-created_at').values_list('created_at', flat=True).first()
    if last_post:
        candidates.append(last_post)

    from apps.journal.models import JournalEntry
    last_journal = JournalEntry.objects.filter(user=user).order_by(
        '-created_at').values_list('created_at', flat=True).first()
    if last_journal:
        candidates.append(last_journal)

    return max(candidates)


def marketing_unsubscribe_url(user):
    token = signing.dumps({'user_id': user.id, 'kind': 'marketing'})
    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com')
    return f"{site_url}/email/unsubscribe/{token}/"


# E1 (welcome, day 0) is signal-triggered; see tasks.send_welcome_email_day_1.
ONBOARDING_EMAILS = [
    {
        'number': 2, 'day': 1,
        'template': 'emails/onboarding_2.html',
        'subject': "Meet Anchor (it's awake when no one else is)",
        'field': 'onboarding_email_2_sent',
        'skip': has_used_anchor,  # spec: skip if member already used Anchor
    },
    {
        'number': 3, 'day': 3,
        'template': 'emails/onboarding_3.html',
        'subject': "The journal only you can read",
        'field': 'onboarding_email_3_sent',
        'skip': None,
    },
    {
        'number': 4, 'day': 6,
        'template': 'emails/onboarding_4.html',
        'subject': "Someone in the community said this today",
        'field': 'onboarding_email_4_sent',
        'skip': None,
    },
    {
        'number': 5, 'day': 9,
        'template': 'emails/onboarding_5.html',
        'subject': "Your first medallion is closer than you think",
        'field': 'onboarding_email_5_sent',
        'skip': None,
    },
    {
        'number': 6, 'day': 14,
        'template': 'emails/onboarding_6.html',
        'subject': "How's it going? (really)",
        'field': 'onboarding_email_6_sent',
        'skip': None,
    },
]

REENGAGEMENT_EMAILS = [
    {
        'number': 1, 'day': 0,
        'template': 'emails/reengagement_1.html',
        'subject': "Your seat's still here 💙",
        'field': 'reengagement_email_1_sent',
    },
    {
        'number': 2, 'day': 5,
        'template': 'emails/reengagement_2.html',
        'subject': "What you've missed (the good kind)",
        'field': 'reengagement_email_2_sent',
    },
    {
        'number': 3, 'day': 12,
        'template': 'emails/reengagement_3.html',
        'subject': "One honest question",
        'field': 'reengagement_email_3_sent',
    },
]
