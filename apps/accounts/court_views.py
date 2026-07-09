# apps/accounts/court_views.py
"""Court Compliance views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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

    Matches either the file hash (SHA-256 of the PDF bytes) or the embedded
    hash (the fingerprint printed inside the PDF) — they are necessarily
    different values, and a PO may be holding either one.
    """
    if len(hash_value) == 64:
        report = CourtReport.objects.filter(
            Q(pdf_hash=hash_value) | Q(pdf_embedded_hash=hash_value)).first()
    elif len(hash_value) >= 8:
        report = CourtReport.objects.filter(
            Q(pdf_hash__startswith=hash_value)
            | Q(pdf_embedded_hash__startswith=hash_value)).first()
    else:
        report = None

    if not report:
        raise Http404('Unknown court report fingerprint')

    return render(request, 'court/verify.html', {
        'report': report,
        'verified_at': timezone.now(),
    })


from django.template.loader import render_to_string

from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)
from apps.accounts.court_service import generate_court_report
from apps.accounts.decorators import court_required
from apps.accounts.email_service import send_email
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


@login_required
@court_required
@require_POST
def court_report_email(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    recipient = (request.POST.get('recipient') or '').strip()
    if not recipient:
        messages.error(request, 'Recipient email required.')
        return redirect('accounts:court_report_list')
    if not report.pdf:
        messages.error(request, 'Report PDF missing — regenerate.')
        return redirect('accounts:court_report_list')

    profile = getattr(request.user, 'court_profile', None)
    legal_name = (profile.legal_name if profile else None) or request.user.username
    case_number = (profile.case_number if profile else None) or '(no case number on file)'

    verify_url = request.build_absolute_uri(
        reverse('verify_court_report', args=[report.pdf_hash[:8]])
    )

    html_body = render_to_string('court/email_pdf.html', {
        'legal_name': legal_name,
        'case_number': case_number,
        'period_start': report.period_start,
        'period_end': report.period_end,
        'attendance_count': report.attendance_count,
        'verify_url': verify_url,
    })
    plain_body = (
        f"Recovery meeting attendance report for {legal_name}\n"
        f"Case: {case_number}\n"
        f"Period: {report.period_start} – {report.period_end}\n"
        f"Meetings attended: {report.attendance_count}\n"
        f"Verify integrity: {verify_url}\n"
    )

    pdf_bytes = report.pdf.read()
    report.pdf.close()

    success, err = send_email(
        subject=f'Court Compliance Report — {legal_name} — {report.period_start:%b %Y}',
        plain_message=plain_body,
        html_message=html_body,
        recipient_email=recipient,
        attachments=[(f'court-report-{report.short_hash}.pdf', pdf_bytes, 'application/pdf')],
    )

    if not success:
        messages.error(request, f'Email failed: {err}')
        return redirect('accounts:court_report_list')

    existing = report.emailed_to or ''
    report.emailed_to = (existing + ',' + recipient).strip(',')
    report.emailed_at = timezone.now()
    report.save(update_fields=['emailed_to', 'emailed_at'])
    messages.success(request, f'Report emailed to {recipient}.')
    return redirect('accounts:court_report_list')
