"""Views for the interactive worksheet library.

Free for everyone: read a worksheet, fill it in on screen, print it, and
download the blank PDF. Premium: save entries, edit them later, export a
filled-in PDF, and discuss an entry with Anchor.

Entries are private. Every entry lookup is scoped to request.user, so
another member's entry id returns 404. A member whose Premium lapses can
still read and delete what they wrote; we never hold someone's own words
hostage.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import premium_required

from .access import user_has_premium, user_has_supporter_access
from .models import WorksheetEntry
from .worksheet_service import render_blank_pdf, render_entry_pdf, start_coach_session
from .worksheets import WORKSHEETS, build_sections, clean_answers, get_worksheet


def _worksheet_or_404(slug):
    worksheet = get_worksheet(slug)
    if worksheet is None:
        raise Http404('No such worksheet')
    return worksheet


def can_save(user, worksheet):
    """Premium saves any worksheet; a Supporter seat also saves family ones."""
    if user_has_premium(user):
        return True
    return worksheet.audience == 'family' and user_has_supporter_access(user)


def _upgrade_redirect(worksheet):
    if worksheet.audience == 'family':
        return redirect('accounts:supporter_renew')
    return redirect('accounts:pricing')


def _pdf_response(pdf_bytes, filename):
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def worksheet_index(request):
    counts = {}
    if request.user.is_authenticated:
        counts = dict(
            WorksheetEntry.objects.filter(user=request.user)
            .values_list('worksheet_slug')
            .annotate(n=Count('id'))
        )
    cards = [{'worksheet': w, 'saved_count': counts.get(w.slug, 0)}
             for w in WORKSHEETS if w.audience != 'family']
    family_cards = [{'worksheet': w, 'saved_count': counts.get(w.slug, 0)}
                    for w in WORKSHEETS if w.audience == 'family']
    return render(request, 'resources/worksheets/index.html', {
        'cards': cards,
        'family_cards': family_cards,
        'has_premium': user_has_premium(request.user),
        'total_saved': sum(counts.values()),
    })


def worksheet_detail(request, slug):
    worksheet = _worksheet_or_404(slug)
    recent_entries = []
    if request.user.is_authenticated:
        recent_entries = WorksheetEntry.objects.filter(
            user=request.user, worksheet_slug=slug)[:10]
    return render(request, 'resources/worksheets/detail.html', {
        'worksheet': worksheet,
        'sections': build_sections(worksheet),
        # Template name kept from before family worksheets: "can save".
        'has_premium': can_save(request.user, worksheet),
        'recent_entries': recent_entries,
        'entry': None,
        'editable': True,
        'scale_points': range(11),
    })


def worksheet_blank_pdf(request, slug):
    worksheet = _worksheet_or_404(slug)
    return _pdf_response(render_blank_pdf(worksheet), f'{slug}-worksheet.pdf')


@login_required
@require_POST
def worksheet_save(request, slug):
    worksheet = _worksheet_or_404(slug)
    if not can_save(request.user, worksheet):
        messages.warning(request, 'Saving worksheets needs Premium'
                         + (' or a Supporter seat.' if worksheet.audience == 'family' else '.'))
        return _upgrade_redirect(worksheet)
    data = clean_answers(worksheet, request.POST)

    entry_id = request.POST.get('entry_id')
    entry = None
    if entry_id:
        entry = get_object_or_404(
            WorksheetEntry, pk=entry_id, user=request.user, worksheet_slug=slug)

    if not data:
        messages.warning(request, 'Fill in at least one answer before saving.')
        if entry:
            return redirect(entry.get_absolute_url())
        return redirect('resources:worksheet_detail', slug=slug)

    if entry:
        entry.data = data
        entry.save(update_fields=['data', 'updated_at'])
    else:
        entry = WorksheetEntry.objects.create(
            user=request.user, worksheet_slug=slug, data=data)

    messages.success(request, f'Your {worksheet.title} is saved. Only you can see it.')
    return redirect(entry.get_absolute_url())


@login_required
def worksheet_entry(request, pk):
    entry = get_object_or_404(WorksheetEntry, pk=pk, user=request.user)
    worksheet = entry.worksheet
    if worksheet is None:
        raise Http404('This worksheet is no longer available')
    has_premium = can_save(request.user, worksheet)
    return render(request, 'resources/worksheets/detail.html', {
        'worksheet': worksheet,
        'sections': build_sections(worksheet, entry.data),
        'has_premium': has_premium,
        'recent_entries': WorksheetEntry.objects.filter(
            user=request.user, worksheet_slug=entry.worksheet_slug,
        ).exclude(pk=entry.pk)[:10],
        'entry': entry,
        'editable': has_premium,
        'scale_points': range(11),
    })


@login_required
def worksheet_entry_pdf(request, pk):
    entry = get_object_or_404(WorksheetEntry, pk=pk, user=request.user)
    if entry.worksheet is None:
        raise Http404('This worksheet is no longer available')
    if not can_save(request.user, entry.worksheet):
        return _upgrade_redirect(entry.worksheet)
    return _pdf_response(render_entry_pdf(entry), f'{entry.worksheet_slug}.pdf')


@login_required
@premium_required
@require_POST
def worksheet_entry_coach(request, pk):
    entry = get_object_or_404(WorksheetEntry, pk=pk, user=request.user)
    # Anchor is built around the member's own recovery data, so it isn't
    # offered for the family worksheets.
    if entry.worksheet is None or entry.worksheet.audience == 'family':
        raise Http404('This worksheet is no longer available')
    start_coach_session(entry)
    return redirect('accounts:recovery_coach')


@login_required
@require_POST
def worksheet_entry_delete(request, pk):
    entry = get_object_or_404(WorksheetEntry, pk=pk, user=request.user)
    slug = entry.worksheet_slug
    entry.delete()
    messages.success(request, 'Entry deleted.')
    if get_worksheet(slug):
        return redirect('resources:worksheet_detail', slug=slug)
    return redirect('resources:my_worksheets')


@login_required
def my_worksheets(request):
    entries = WorksheetEntry.objects.filter(user=request.user)
    return render(request, 'resources/worksheets/mine.html', {
        'entries': [e for e in entries if e.worksheet is not None],
        'has_premium': user_has_premium(request.user),
    })


@login_required
def workbook_builder(request):
    """Pick sections and a date range for the "My Recovery Workbook" PDF."""
    from .workbook import DEFAULT_RANGE, RANGES, SECTIONS, section_counts

    counts = section_counts(request.user)
    sections = [
        {'key': key, 'label': label, 'description': desc, 'checked': on,
         'count': counts.get(key, 0)}
        for key, (label, desc, on) in SECTIONS.items()
    ]
    return render(request, 'resources/workbook/builder.html', {
        'sections': sections,
        'ranges': [(k, v[0]) for k, v in RANGES.items()],
        'default_range': DEFAULT_RANGE,
        'has_premium': user_has_premium(request.user),
    })


@login_required
@premium_required
def workbook_pdf(request):
    from .workbook import parse_options, render_workbook_pdf

    sections, range_key = parse_options(request.GET)
    pdf_bytes = render_workbook_pdf(request.user, sections, range_key)
    return _pdf_response(pdf_bytes, 'my-recovery-workbook.pdf')
