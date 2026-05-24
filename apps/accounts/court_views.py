# apps/accounts/court_views.py
"""Court Compliance views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)


def verify_court_report(request, hash_value):
    """
    Public endpoint — court / probation officer pastes a hash and we confirm
    that hash matches a real report. We do NOT leak any personal info.
    """
    if len(hash_value) == 64:
        report = CourtReport.objects.filter(pdf_hash=hash_value).first()
    elif len(hash_value) >= 8:
        report = CourtReport.objects.filter(pdf_hash__startswith=hash_value).first()
    else:
        report = None

    if not report:
        raise Http404('Unknown court report fingerprint')

    return render(request, 'court/verify.html', {
        'report': report,
        'verified_at': timezone.now(),
    })


from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)
from apps.accounts.court_service import generate_court_report
from apps.accounts.decorators import court_required
from datetime import date


@login_required
@court_required
def court_dashboard(request):
    """Landing page inside the Court Compliance section."""
    profile = getattr(request.user, 'court_profile', None)
    recent_attendances = MeetingAttendance.objects.filter(user=request.user)[:5]
    recent_reports = CourtReport.objects.filter(user=request.user)[:3]

    # Calculate this week's progress
    today = timezone.now().date()
    monday = today - timezone.timedelta(days=today.weekday())
    this_week_count = MeetingAttendance.objects.filter(
        user=request.user, meeting_date__date__gte=monday,
    ).count()

    return render(request, 'court/dashboard.html', {
        'profile': profile,
        'recent_attendances': recent_attendances,
        'recent_reports': recent_reports,
        'this_week_count': this_week_count,
        'required_per_week': profile.required_meetings_per_week if profile else 3,
    })


@login_required
@court_required
def court_profile(request):
    profile, _ = CourtReportProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = CourtReportProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Court profile saved.')
            return redirect('accounts:court_dashboard')
    else:
        form = CourtReportProfileForm(instance=profile)
    return render(request, 'court/profile.html', {'form': form, 'profile': profile})


@login_required
@court_required
def court_attendance_list(request):
    attendances = MeetingAttendance.objects.filter(user=request.user)
    return render(request, 'court/attendance_list.html', {'attendances': attendances})


@login_required
@court_required
def court_attendance_create(request):
    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST)
        if form.is_valid():
            att = form.save(commit=False)
            att.user = request.user
            att.save()
            messages.success(request, 'Meeting logged.')
            return redirect('accounts:court_attendance_list')
    else:
        form = MeetingAttendanceForm(initial={'meeting_date': timezone.now()})
    return render(request, 'court/attendance_form.html', {'form': form, 'mode': 'create'})


@login_required
@court_required
def court_attendance_edit(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST, instance=att)
        if form.is_valid():
            form.save()
            messages.success(request, 'Meeting updated.')
            return redirect('accounts:court_attendance_list')
    else:
        form = MeetingAttendanceForm(instance=att)
    return render(request, 'court/attendance_form.html', {'form': form, 'mode': 'edit'})


@login_required
@court_required
@require_POST
def court_attendance_delete(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    att.delete()
    messages.success(request, 'Meeting removed.')
    return redirect('accounts:court_attendance_list')


@login_required
@court_required
def court_report_list(request):
    reports = CourtReport.objects.filter(user=request.user)
    return render(request, 'court/report_list.html', {'reports': reports})


@login_required
@court_required
@require_POST
def court_report_generate(request):
    try:
        period_start = date.fromisoformat(request.POST.get('period_start'))
        period_end = date.fromisoformat(request.POST.get('period_end'))
    except (TypeError, ValueError):
        messages.error(request, 'Invalid period dates.')
        return redirect('accounts:court_report_list')

    report = generate_court_report(request.user, period_start, period_end)
    messages.success(
        request,
        f'Report generated — {report.attendance_count} meetings logged for {period_start} to {period_end}.',
    )
    return redirect('accounts:court_report_list')


@login_required
@court_required
def court_report_download(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    if not report.pdf:
        raise Http404('Report PDF missing')
    response = HttpResponse(report.pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="court-report-{report.period_start:%Y%m}-{report.short_hash}.pdf"'
    )
    return response
