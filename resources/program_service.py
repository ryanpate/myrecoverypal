"""Pacing and access rules for guided programs.

Day statuses:
    done     completed (always readable, even after Premium lapses)
    current  the next lesson, open now
    waiting  the next lesson, but the previous one was finished today; it
             opens tomorrow (member's local date)
    premium  the next lesson, waiting only on Premium (day > program.free_days)
    locked   further ahead
"""
from dataclasses import dataclass
from typing import Dict, List

from django.utils import timezone

from .access import has_program_access
from .models import ProgramDayCompletion, ProgramEnrollment


@dataclass
class Progress:
    enrollment: ProgramEnrollment
    completed: Dict[int, object]  # day -> completed_on
    next_day: int                 # 1..length, or length + 1 when finished
    next_status: str              # current | waiting | premium | finished
    statuses: List[str]           # index 0 = day 1

    @property
    def finished(self):
        return self.next_status == 'finished'

    @property
    def done_count(self):
        return len(self.completed)

    @property
    def percent(self):
        length = len(self.statuses)
        return round(100 * self.done_count / length) if length else 0

    def status(self, day):
        return self.statuses[day - 1]

    def can_read(self, day):
        return self.status(day) in ('done', 'current')


def get_progress(enrollment, user, today=None):
    program = enrollment.program
    today = today or timezone.localdate()
    completed = dict(enrollment.completions.values_list('day', 'completed_on'))

    # Lessons are strictly sequential, so the next lesson is the first gap.
    next_day = 1
    while next_day in completed:
        next_day += 1

    if next_day > program.length:
        next_status = 'finished'
    elif next_day > program.free_days and not has_program_access(user, program):
        next_status = 'premium'
    elif next_day > 1 and completed.get(next_day - 1) and completed[next_day - 1] >= today:
        next_status = 'waiting'
    else:
        next_status = 'current'

    statuses = []
    for day in range(1, program.length + 1):
        if day in completed:
            statuses.append('done')
        elif day == next_day:
            statuses.append(next_status)
        else:
            statuses.append('locked')
    return Progress(enrollment, completed, next_day, next_status, statuses)


def complete_day(enrollment, user, day, today=None):
    """Mark `day` complete if it's the current lesson. Returns True on success."""
    today = today or timezone.localdate()
    progress = get_progress(enrollment, user, today)
    if progress.status(day) != 'current':
        return False
    ProgramDayCompletion.objects.get_or_create(
        enrollment=enrollment, day=day, defaults={'completed_on': today})
    if day == enrollment.program.length and enrollment.completed_at is None:
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=['completed_at'])
    return True


def active_enrollment(user):
    """The member's most recent unfinished enrollment in a live program."""
    if not getattr(user, 'is_authenticated', False):
        return None
    for enrollment in ProgramEnrollment.objects.filter(user=user, completed_at__isnull=True):
        if enrollment.program is not None:
            return enrollment
    return None
