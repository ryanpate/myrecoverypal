"""Views for guided day-by-day programs.

Overviews are public (and indexable). Lessons need an account and an
enrollment. The first FREE_DAYS lessons are free; later ones need Premium.
Completed lessons stay readable after Premium lapses.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .access import user_has_premium
from .models import ProgramEnrollment
from .program_service import complete_day, get_progress
from .programs import FREE_DAYS, PROGRAMS, get_program


def _program_or_404(slug):
    program = get_program(slug)
    if program is None:
        raise Http404('No such program')
    return program


def _enrollment(user, program):
    if not user.is_authenticated:
        return None
    return ProgramEnrollment.objects.filter(user=user, program_slug=program.slug).first()


def _weeks(program, progress):
    """[(week_title, [(lesson, status)])] for the overview."""
    weeks = []
    for lesson in program.lessons:
        title = program.week_title(lesson.day)
        status = progress.status(lesson.day) if progress else (
            'free' if lesson.day <= FREE_DAYS else 'premium-preview')
        if not weeks or weeks[-1][0] != title:
            weeks.append((title, []))
        weeks[-1][1].append((lesson, status))
    return weeks


def program_index(request):
    cards = []
    for program in PROGRAMS:
        enrollment = _enrollment(request.user, program)
        progress = get_progress(enrollment, request.user) if enrollment else None
        cards.append({'program': program, 'progress': progress})
    return render(request, 'resources/programs/index.html', {
        'cards': cards,
        'free_days': FREE_DAYS,
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
        'free_days': FREE_DAYS,
        'has_premium': user_has_premium(request.user),
    })


@login_required
@require_POST
def program_enroll(request, slug):
    program = _program_or_404(slug)
    ProgramEnrollment.objects.get_or_create(user=request.user, program_slug=program.slug)
    return redirect('resources:program_day', slug=slug, day=1)


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
        'free_days': FREE_DAYS,
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
            return redirect('accounts:pricing')
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
