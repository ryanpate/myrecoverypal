"""Views for guided day-by-day programs.

Overviews are public (and indexable). Lessons need an account and an
enrollment. The first `program.free_days` lessons are free; later ones need Premium.
Completed lessons stay readable after Premium lapses.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .access import has_program_access, user_has_premium
from .models import ProgramEnrollment
from .program_service import complete_day, get_progress
from .programs import CORE_PROGRAMS, FAMILY_PROGRAMS, TRACK_PROGRAMS, get_program


def _program_or_404(slug):
    program = get_program(slug)
    if program is None:
        raise Http404('No such program')
    return program


def _enrollment(user, program):
    if not user.is_authenticated:
        return None
    return ProgramEnrollment.objects.filter(user=user, program_slug=program.slug).first()


def _cohort_context(user, enrollment):
    """{'cohort', 'cohort_size'} for an enrolled member who is in their cohort."""
    from .cohorts import ACTIVE_STATUSES, is_active_member

    cohort = enrollment.cohort if enrollment else None
    if not is_active_member(user, cohort):
        blocked = bool(cohort and cohort.group.memberships.filter(user=user, status='banned').exists())
        return {'cohort': None, 'cohort_size': 0, 'cohort_blocked': blocked}
    size = cohort.group.memberships.filter(status__in=ACTIVE_STATUSES).count()
    return {'cohort': cohort, 'cohort_size': size, 'cohort_blocked': False}


def _weeks(program, progress):
    """[(week_title, [(lesson, status)])] for the overview."""
    weeks = []
    for lesson in program.lessons:
        title = program.week_title(lesson.day)
        status = progress.status(lesson.day) if progress else (
            'free' if lesson.day <= program.free_days else 'premium-preview')
        if not weeks or weeks[-1][0] != title:
            weeks.append((title, []))
        weeks[-1][1].append((lesson, status))
    return weeks


def program_index(request):
    def cards(programs):
        out = []
        for program in programs:
            enrollment = _enrollment(request.user, program)
            progress = get_progress(enrollment, request.user) if enrollment else None
            out.append({'program': program, 'progress': progress})
        return out

    return render(request, 'resources/programs/index.html', {
        'core_cards': cards(CORE_PROGRAMS),
        'track_cards': cards(TRACK_PROGRAMS),
        'family_cards': cards(FAMILY_PROGRAMS),
        'has_premium': user_has_premium(request.user),
    })


def program_detail(request, slug):
    program = _program_or_404(slug)
    enrollment = _enrollment(request.user, program)
    progress = get_progress(enrollment, request.user) if enrollment else None
    return render(request, 'resources/programs/detail.html', {
        'program': program,
        'progress': progress,
        'weeks': _weeks(program, progress),
        'free_days': program.free_days,
        'has_premium': user_has_premium(request.user),
        'has_access': has_program_access(request.user, program),
        **_cohort_context(request.user, enrollment),
    })


@login_required
@require_POST
def program_enroll(request, slug):
    program = _program_or_404(slug)
    ProgramEnrollment.objects.get_or_create(user=request.user, program_slug=program.slug)
    return redirect('resources:program_day', slug=slug, day=1)


@login_required
@require_POST
def program_cohort_join(request, slug):
    """Opt in to this program's cohort group (free)."""
    from .cohorts import join_cohort

    program = _program_or_404(slug)
    enrollment = _enrollment(request.user, program)
    if enrollment is None:
        messages.info(request, f'Start {program.title} first, then join a cohort.')
        return redirect('resources:program_detail', slug=slug)
    cohort = join_cohort(enrollment)
    if cohort is None:
        messages.error(request, 'You can\'t rejoin this cohort.')
        return redirect('resources:program_detail', slug=slug)
    messages.success(request, f'Welcome to your cohort. Say hello to the people starting {program.title} with you!')
    return redirect('accounts:group_detail', pk=cohort.group_id)


@login_required
@require_POST
def program_reminders(request, slug):
    """Turn daily lesson reminders on or off for this enrollment."""
    program = _program_or_404(slug)
    enrollment = _enrollment(request.user, program)
    if enrollment is None:
        raise Http404('Not enrolled')
    enrollment.reminders_enabled = request.POST.get('enabled') == '1'
    enrollment.save(update_fields=['reminders_enabled'])
    messages.success(request, 'Daily lesson reminders are on.' if enrollment.reminders_enabled
                     else 'Daily lesson reminders are off. You can turn them back on any time.')
    return redirect('resources:program_detail', slug=slug)


@login_required
@require_POST
def program_restart(request, slug):
    program = _program_or_404(slug)
    enrollment = _enrollment(request.user, program)
    if enrollment:
        enrollment.delete()
    ProgramEnrollment.objects.create(
        user=request.user, program_slug=program.slug,
        reminders_enabled=enrollment.reminders_enabled if enrollment else True)
    messages.success(request, f'{program.title} restarted. Day 1 is ready when you are.')
    return redirect('resources:program_day', slug=slug, day=1)


def _lesson_access(request, program, day):
    """(enrollment, progress, lesson, redirect_response_or_None)."""
    lesson = program.lesson(day)
    if lesson is None:
        raise Http404('No such day')
    enrollment = _enrollment(request.user, program)
    if enrollment is None:
        messages.info(request, f'Start {program.title} to open its lessons.')
        return None, None, lesson, redirect('resources:program_detail', slug=program.slug)
    progress = get_progress(enrollment, request.user)
    return enrollment, progress, lesson, None


@login_required
def program_day(request, slug, day):
    program = _program_or_404(slug)
    enrollment, progress, lesson, bounce = _lesson_access(request, program, day)
    if bounce:
        return bounce

    status = progress.status(day)
    if status == 'locked':
        messages.info(request, f'Day {day} opens after Day {progress.next_day}.')
        return redirect('resources:program_detail', slug=slug)
    if status == 'waiting':
        messages.info(request, f'Nice work today. Day {day} opens tomorrow.')
        return redirect('resources:program_detail', slug=slug)

    return render(request, 'resources/programs/day.html', {
        'program': program,
        'lesson': lesson,
        'progress': progress,
        'status': status,
        'week_title': program.week_title(day),
        'next_lesson': program.lesson(day + 1),
        'just_completed': request.GET.get('done') == '1' and status == 'done',
        'free_days': program.free_days,
        **_cohort_context(request.user, enrollment),
    })


@login_required
@require_POST
def program_complete(request, slug, day):
    program = _program_or_404(slug)
    enrollment, progress, lesson, bounce = _lesson_access(request, program, day)
    if bounce:
        return bounce
    if not complete_day(enrollment, request.user, day):
        if progress.status(day) == 'premium':
            return redirect('accounts:supporter_renew' if program.access == 'family'
                            else 'accounts:pricing')
        messages.info(request, 'That lesson isn\'t open yet.')
        return redirect('resources:program_detail', slug=slug)
    return redirect(reverse('resources:program_day', args=[slug, day]) + '?done=1')


@login_required
def program_journal(request, slug, day):
    """Journal entry pre-filled with a lesson's prompt; POST goes to the
    journal's own create_entry."""
    program = _program_or_404(slug)
    enrollment, progress, lesson, bounce = _lesson_access(request, program, day)
    if bounce:
        return bounce
    if not progress.can_read(day):
        return redirect('resources:program_day', slug=slug, day=day)

    from apps.journal.views import create_entry
    if request.method == 'POST':
        return create_entry(request)

    from apps.journal.forms import JournalEntryForm
    form = JournalEntryForm(initial={
        'title': f'{program.title}, Day {day}: {lesson.title}',
        'content': f'{lesson.prompt}\n\n',
    })
    return render(request, 'journal/entry_form.html', {'form': form})
