"""Program cohorts: small groups of members who start a program around the
same time, so they go through the lessons together.

Rolling rule. With a small member base, "everyone who started this calendar
week" would often be a group of one. Instead, a new member joins the newest
cohort for their program while it is still young and not full:

    join the newest cohort if it has fewer than MAX_MEMBERS members and
      - it opened within the last JOIN_WINDOW_DAYS days, or
      - it opened within the last SMALL_COHORT_MAX_AGE_DAYS days and still
        has fewer than SMALL_COHORT_SIZE members;
    otherwise open a new cohort.

So members of one cohort started at most three weeks apart, and a quiet
week doesn't strand anyone alone.

Each cohort is a secret RecoveryGroup: hidden from the group list, 404 for
non-members, and joinable only through `join_cohort`. Posts, comments,
likes, anonymous posting and moderation all come from the groups system.
Joining is opt-in and free.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import ProgramCohort

JOIN_WINDOW_DAYS = 7
SMALL_COHORT_SIZE = 5
SMALL_COHORT_MAX_AGE_DAYS = 21
MAX_MEMBERS = 30
ACTIVE_STATUSES = ('active', 'moderator', 'admin')


def _active_count(cohort):
    return cohort.group.memberships.filter(status__in=ACTIVE_STATUSES).count()


def _open_cohort(program, now):
    newest = (ProgramCohort.objects.filter(program_slug=program.slug, group__is_active=True)
              .select_related('group').first())
    if newest is None:
        return None
    age = now - newest.created_at
    size = _active_count(newest)
    if size >= MAX_MEMBERS:
        return None
    if age <= timedelta(days=JOIN_WINDOW_DAYS):
        return newest
    if age <= timedelta(days=SMALL_COHORT_MAX_AGE_DAYS) and size < SMALL_COHORT_SIZE:
        return newest
    return None


def _create_cohort(program, founder, now):
    from apps.accounts.models import RecoveryGroup

    started = timezone.localtime(now).date()
    group = RecoveryGroup.objects.create(
        name=f'{program.title} cohort · {started:%b} {started.day}',
        description=(
            f'Members who started {program.title} around the same time. Share how the '
            f'lessons are going, cheer each other on, and ask for help when a day is hard. '
            f'Posts here are only visible to members of this cohort.'
        ),
        group_type='recovery_stage',
        privacy_level='secret',
        max_members=MAX_MEMBERS,
        # `creator` is required by the model. The founding member fills it,
        # but cohort pages show the cohort card instead of a creator.
        creator=founder,
        group_color='#2d6a4f',
    )
    return ProgramCohort.objects.create(program_slug=program.slug, group=group)


def _notify_members(cohort, joiner):
    from apps.accounts.models import GroupMembership, Notification

    name = joiner.get_full_name() or joiner.username
    others = (GroupMembership.objects.filter(group=cohort.group, status__in=ACTIVE_STATUSES)
              .exclude(user=joiner).select_related('user'))
    Notification.objects.bulk_create([
        Notification(
            recipient=m.user, sender=joiner, notification_type='group_join',
            title=f'New member in your {cohort.program.title} cohort',
            message=f'{name} just joined. Say hello!',
            link=f'/accounts/groups/{cohort.group_id}/',
        ) for m in others
    ])


@transaction.atomic
def join_cohort(enrollment, now=None):
    """Put the enrollment's member in a cohort and return it.

    Idempotent. A member who left their cohort and joins again goes back to
    the same cohort rather than a new one. Returns None for a member a
    moderator banned from that cohort: a ban is never undone here.
    """
    from apps.accounts.models import GroupMembership

    user = enrollment.user
    now = now or timezone.now()
    cohort = enrollment.cohort
    if cohort is None:
        program = enrollment.program
        cohort = _open_cohort(program, now) or _create_cohort(program, user, now)

    membership, created = GroupMembership.objects.get_or_create(
        user=user, group=cohort.group,
        defaults={'status': 'active', 'joined_date': timezone.localdate()})
    newly_active = created
    if membership.status == 'banned':
        return None
    if not created and membership.status not in ACTIVE_STATUSES:
        membership.status = 'active'
        membership.joined_date = timezone.localdate()
        membership.left_date = None
        membership.save(update_fields=['status', 'joined_date', 'left_date'])
        newly_active = True

    if enrollment.cohort_id != cohort.id:
        enrollment.cohort = cohort
        enrollment.save(update_fields=['cohort'])
    if newly_active:
        _notify_members(cohort, user)
    return cohort


def is_active_member(user, cohort):
    if cohort is None or not getattr(user, 'is_authenticated', False):
        return False
    return cohort.group.memberships.filter(user=user, status__in=ACTIVE_STATUSES).exists()
