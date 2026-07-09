# apps/accounts/court_service.py
"""
Court Compliance PDF report generation.

Two-pass rendering:
  Pass 1: render PDF with a placeholder hash → compute SHA-256 (the
          "embedded hash", printed inside the pass-2 PDF)
  Pass 2: re-render with the embedded hash → compute SHA-256 of the bytes
          that actually leave the server (the "file hash")

A hash embedded in the bytes cannot also be the hash of those bytes, so the
two are necessarily different. We store BOTH and the public verify endpoint
accepts either — a PO can verify from the fingerprint printed on the page or
by hashing the PDF file itself.
"""
import hashlib
import logging
from datetime import date, datetime
from io import BytesIO

from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)

logger = logging.getLogger(__name__)

PLACEHOLDER_HASH = '0' * 64


def _build_context(user, period_start: date, period_end: date, pdf_hash: str) -> dict:
    """Assemble the template context for the PDF."""
    profile = getattr(user, 'court_profile', None) or CourtReportProfile(user=user)

    attendances = list(
        MeetingAttendance.objects.filter(
            user=user,
            meeting_date__date__gte=period_start,
            meeting_date__date__lte=period_end,
        ).order_by('meeting_date')
    )

    weeks = max(1, (period_end - period_start).days // 7 + 1)
    weekly_avg = round(len(attendances) / weeks, 1) if weeks else 0

    return {
        'user': user,
        'legal_name': profile.legal_name,
        'case_number': profile.case_number,
        'court_name': profile.court_name,
        'jurisdiction': profile.jurisdiction,
        'judge_name': profile.judge_name,
        'probation_officer_name': profile.probation_officer_name,
        'period_start': period_start,
        'period_end': period_end,
        'generated_at': timezone.now(),
        'attendances': attendances,
        'attendance_count': len(attendances),
        'weeks_in_period': weeks,
        'weekly_average': weekly_avg,
        'required_per_week': profile.required_meetings_per_week,
        'pdf_hash': pdf_hash,
        'pdf_hash_short': pdf_hash[:8],
    }


def _render_pdf_bytes(context: dict) -> bytes:
    """Render the PDF template to bytes via WeasyPrint."""
    from weasyprint import HTML
    html_str = render_to_string('court/report_pdf.html', context)
    buf = BytesIO()
    HTML(string=html_str).write_pdf(target=buf)
    return buf.getvalue()


def render_court_report_pdf(user, period_start: date, period_end: date):
    """
    Render a court compliance PDF for `user` covering `period_start..period_end`.

    Returns: (pdf_bytes, file_hash, embedded_hash) where file_hash is the
    SHA-256 of pdf_bytes and embedded_hash is the fingerprint printed inside
    the document. Both must be stored — the verify endpoint accepts either.
    """
    # Pass 1: placeholder hash → render → compute the embedded hash
    ctx1 = _build_context(user, period_start, period_end, PLACEHOLDER_HASH)
    pdf_pass1 = _render_pdf_bytes(ctx1)
    embedded_hash = hashlib.sha256(pdf_pass1).hexdigest()

    # Pass 2: embedded hash printed in the document → render → return bytes
    ctx2 = _build_context(user, period_start, period_end, embedded_hash)
    pdf_pass2 = _render_pdf_bytes(ctx2)
    # File hash is over the bytes that actually leave the server
    file_hash = hashlib.sha256(pdf_pass2).hexdigest()
    return pdf_pass2, file_hash, embedded_hash


def email_report_to_po(report: CourtReport, recipient: str):
    """Email a report PDF to `recipient` (PO, attorney, etc.).

    Shared by the manual send button and the monthly auto-email task, so it
    builds the verify URL from settings.SITE_URL rather than a request.
    Returns (success: bool, err: str|None) and records the send on success.
    """
    from django.conf import settings
    from django.urls import reverse

    from apps.accounts.email_service import send_email

    pdf_bytes = report.get_pdf_bytes()
    if not pdf_bytes:
        return False, 'Report PDF missing'

    user = report.user
    profile = getattr(user, 'court_profile', None)
    legal_name = (profile.legal_name if profile else None) or user.username
    case_number = (profile.case_number if profile else None) or '(no case number on file)'

    site_url = getattr(settings, 'SITE_URL', 'https://www.myrecoverypal.com').rstrip('/')
    verify_url = site_url + reverse('verify_court_report', args=[report.pdf_hash[:8]])

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

    success, err = send_email(
        subject=f'Court Compliance Report — {legal_name} — {report.period_start:%b %Y}',
        plain_message=plain_body,
        html_message=html_body,
        recipient_email=recipient,
        attachments=[(f'court-report-{report.short_hash}.pdf', pdf_bytes, 'application/pdf')],
    )
    if not success:
        return False, err

    existing = report.emailed_to or ''
    report.emailed_to = (existing + ',' + recipient).strip(',')
    report.emailed_at = timezone.now()
    report.save(update_fields=['emailed_to', 'emailed_at'])
    return True, None


def generate_court_report(user, period_start: date, period_end: date) -> CourtReport:
    """Render the PDF and persist a `CourtReport` row."""
    pdf_bytes, pdf_hash, embedded_hash = render_court_report_pdf(user, period_start, period_end)

    profile = getattr(user, 'court_profile', None) or CourtReportProfile(user=user)
    attendance_count = MeetingAttendance.objects.filter(
        user=user,
        meeting_date__date__gte=period_start,
        meeting_date__date__lte=period_end,
    ).count()

    # PDF bytes live in Postgres (pdf_data), not external storage: reports
    # are small and privacy-sensitive, and Cloudinary refuses PDF delivery.
    report = CourtReport.objects.create(
        user=user,
        period_start=period_start,
        period_end=period_end,
        pdf_hash=pdf_hash,
        pdf_embedded_hash=embedded_hash,
        pdf_data=pdf_bytes,
        attendance_count=attendance_count,
        legal_name_snapshot=profile.legal_name or '',
        case_number_snapshot=profile.case_number or '',
        court_name_snapshot=profile.court_name or '',
    )
    return report
