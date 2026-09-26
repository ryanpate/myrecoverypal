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

import secrets
from datetime import timedelta

import segno
import stripe
from django.conf import settings

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, CourtReportPurchase, MeetingAttendance,
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


from apps.accounts.court_forms import (
    CourtReportProfileForm, MeetingAttendanceForm,
)
from apps.accounts.court_service import generate_court_report
from apps.support_services.models import Meeting
from apps.core.analytics import queue_ga_event
from datetime import date


@login_required
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
def court_profile(request):
    profile, _ = CourtReportProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        # get_or_create above makes a blank row on first GET, so "new" has to
        # mean "had no case number yet", not "row didn't exist".
        was_blank = not profile.case_number
        form = CourtReportProfileForm(request.POST, instance=profile)
        if form.is_valid():
            saved = form.save()
            if was_blank and saved.case_number:
                # The activation moment for the Court tier — a subscriber
                # who never fills this in never generates a report.
                queue_ga_event(request, 'court_profile_completed')
            messages.success(request, 'Court profile saved.')
            return redirect('accounts:court_dashboard')
    else:
        form = CourtReportProfileForm(instance=profile)
    return render(request, 'court/profile.html', {'form': form, 'profile': profile})


@login_required
def court_attendance_list(request):
    attendances = MeetingAttendance.objects.filter(user=request.user)
    return render(request, 'court/attendance_list.html', {'attendances': attendances})


@login_required
def court_attendance_create(request):
    # ?meeting=<slug> prefills from the directory, so "Log this meeting" on a
    # meeting page lands on a filled-in form instead of a blank one. The
    # Meeting row is kept on the FK; the denormalised fields still carry the
    # values so a report renders even if the meeting is later removed.
    meeting = None
    slug = request.GET.get('meeting')
    if slug:
        meeting = Meeting.objects.filter(
            slug=slug, is_approved=True, is_active=True).first()

    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST)
        if form.is_valid():
            att = form.save(commit=False)
            att.user = request.user
            att.meeting = meeting
            att.save()
            messages.success(request, 'Meeting logged.')
            return redirect('accounts:court_attendance_list')
    else:
        initial = {'meeting_date': timezone.now()}
        if meeting:
            initial.update({
                'meeting_name': meeting.name,
                'meeting_address': meeting.formatted_address or meeting.address,
                'meeting_online': meeting.attendance_option in ('online', 'hybrid'),
                'meeting_platform': 'Zoom' if meeting.conference_url else '',
            })
        form = MeetingAttendanceForm(initial=initial)
    return render(request, 'court/attendance_form.html',
                  {'form': form, 'mode': 'create', 'prefill_meeting': meeting})


@login_required
def court_attendance_edit(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    if request.method == 'POST':
        form = MeetingAttendanceForm(request.POST, instance=att)
        if form.is_valid():
            att = form.save(commit=False)
            if att.chair_signature_at and form.has_changed():
                # The chair confirmed the details as they were; they no longer apply.
                _clear_chair_confirmation(att)
                messages.warning(request, 'Chair confirmation removed because the details changed.')
            att.save()
            messages.success(request, 'Meeting updated.')
            return redirect('accounts:court_attendance_list')
    else:
        form = MeetingAttendanceForm(instance=att)
    return render(request, 'court/attendance_form.html', {'form': form, 'mode': 'edit'})


@login_required
@require_POST
def court_attendance_delete(request, attendance_id):
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    att.delete()
    messages.success(request, 'Meeting removed.')
    return redirect('accounts:court_attendance_list')


@login_required
def court_report_list(request):
    reports = CourtReport.objects.filter(user=request.user)
    return render(request, 'court/report_list.html', {'reports': reports})


@login_required
@require_POST
def court_report_generate(request):
    try:
        period_start = date.fromisoformat(request.POST.get('period_start'))
        period_end = date.fromisoformat(request.POST.get('period_end'))
    except (TypeError, ValueError):
        messages.error(request, 'Invalid period dates.')
        return redirect('accounts:court_report_list')

    if period_end < period_start:
        messages.error(request, 'The period must end after it starts.')
        return redirect('accounts:court_report_list')

    subscription = getattr(request.user, 'subscription', None)
    if not (subscription and subscription.is_court()):
        return _single_report_checkout(request, period_start, period_end)

    report = generate_court_report(request.user, period_start, period_end)
    messages.success(
        request,
        f'Report generated — {report.attendance_count} meetings logged for {period_start} to {period_end}.',
    )
    return redirect('accounts:court_report_list')


@login_required
def court_report_download(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    pdf_bytes = report.get_pdf_bytes()
    if not pdf_bytes:
        raise Http404('Report PDF missing')
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="court-report-{report.period_start:%Y%m}-{report.short_hash}.pdf"'
    )
    return response


@login_required
@require_POST
def court_report_email(request, report_id):
    report = get_object_or_404(CourtReport, pk=report_id, user=request.user)
    recipient = (request.POST.get('recipient') or '').strip()
    if not recipient:
        messages.error(request, 'Recipient email required.')
        return redirect('accounts:court_report_list')
    from apps.accounts.court_service import email_report_to_po
    success, err = email_report_to_po(report, recipient)
    if not success:
        messages.error(request, f'Email failed: {err}')
        return redirect('accounts:court_report_list')

    messages.success(request, f'Report emailed to {recipient}.')
    return redirect('accounts:court_report_list')



# --- $9.99 single report (no Court subscription) -----------------------------

stripe.api_key = settings.STRIPE_SECRET_KEY


def _single_report_checkout(request, period_start, period_end):
    from apps.accounts.court_purchase import COURT_REPORT_KIND, SINGLE_REPORT_PRICE_CENTS
    from apps.accounts.medallion_pack_views import _see_other

    purchase = CourtReportPurchase.objects.create(
        user=request.user, period_start=period_start, period_end=period_end,
        amount_cents=SINGLE_REPORT_PRICE_CENTS)
    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            customer_email=request.user.email,
            line_items=[{
                'quantity': 1,
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': SINGLE_REPORT_PRICE_CENTS,
                    'product_data': {
                        'name': f'Court attendance report: {period_start:%b %-d} – {period_end:%b %-d, %Y}',
                        'description': 'Tamper-evident PDF with a verification fingerprint '
                                       'your probation officer can check online.',
                    },
                },
            }],
            metadata={'kind': COURT_REPORT_KIND, 'purchase_id': str(purchase.id)},
            client_reference_id=str(purchase.id),
            success_url=request.build_absolute_uri(reverse('accounts:court_report_success'))
                        + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('accounts:court_report_list')),
        )
    except stripe.error.StripeError:
        purchase.delete()
        messages.error(request, 'Checkout is unavailable right now. Please try again shortly.')
        return redirect('accounts:court_report_list')
    purchase.stripe_session_id = session.id
    purchase.save(update_fields=['stripe_session_id'])
    return _see_other(session.url)


@login_required
def court_report_success(request):
    from apps.accounts.court_purchase import fulfil_court_report_session
    session_id = request.GET.get('session_id', '')
    purchase = get_object_or_404(CourtReportPurchase, stripe_session_id=session_id, user=request.user)
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        session = None
    purchase = (fulfil_court_report_session(session) if session else None) or purchase
    if purchase.report_id:
        if not request.session.get(f'court_ga_{purchase.pk}'):
            request.session[f'court_ga_{purchase.pk}'] = True
            queue_ga_event(request, 'purchase', currency='USD',
                           value=purchase.amount_cents / 100, item_name='court_single_report')
        messages.success(request, 'Payment received. Your report is ready below.')
    else:
        messages.info(request, "Payment is still confirming. Your report will appear here in a moment; refresh the page.")
    return redirect('accounts:court_report_list')


# --- Chair QR confirmation ---------------------------------------------------

# The chair can confirm from an hour before the meeting until 6 hours after it.
CHAIR_WINDOW_BEFORE = timedelta(hours=1)
CHAIR_WINDOW_AFTER = timedelta(hours=6)
CHAIR_ROLES = [('chair', 'Chair'), ('secretary', 'Secretary'), ('member', 'Group member')]


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
    return ip or None


def _clear_chair_confirmation(att):
    att.verification_method = 'self'
    att.chair_signature_name = ''
    att.chair_signature_at = None
    att.chair_role = ''
    att.chair_confirm_token = None
    att.chair_confirm_ip = None
    att.chair_confirm_user_agent = ''


def _chair_window_open(att, now=None):
    now = now or timezone.now()
    return att.meeting_date - CHAIR_WINDOW_BEFORE <= now <= att.meeting_date + CHAIR_WINDOW_AFTER


def _display_name(user):
    """First name + last initial only: enough for the chair, respectful of anonymity."""
    first = (user.first_name or '').strip()
    last = (user.last_name or '').strip()
    if first:
        return f'{first} {last[0]}.' if last else first
    return 'this member'


@login_required
def court_attendance_chair(request, attendance_id):
    """Member shows this QR at the meeting; the chair scans it on their own phone."""
    att = get_object_or_404(MeetingAttendance, pk=attendance_id, user=request.user)
    if not att.chair_signature_at and not att.chair_confirm_token:
        att.chair_confirm_token = secrets.token_urlsafe(24)
    if not att.chair_signature_at:
        att.qr_shown_ip = _client_ip(request)
        att.save(update_fields=['chair_confirm_token', 'qr_shown_ip'])
    confirm_url = request.build_absolute_uri(
        reverse('accounts:court_chair_confirm', args=[att.chair_confirm_token])) \
        if att.chair_confirm_token else ''
    qr_svg = segno.make(confirm_url, error='m').svg_inline(scale=6, dark='#1e4d8b') if confirm_url else ''
    return render(request, 'court/attendance_chair.html', {
        'att': att, 'confirm_url': confirm_url, 'qr_svg': qr_svg,
        'window_open': _chair_window_open(att),
    })


def court_chair_confirm(request, token):
    """Public page the chair lands on after scanning. No account needed."""
    att = MeetingAttendance.objects.filter(chair_confirm_token=token).select_related('user').first()
    if not att:
        raise Http404('Unknown confirmation link')
    context = {'att': att, 'member_name': _display_name(att.user), 'roles': CHAIR_ROLES}

    if att.chair_signature_at:
        return render(request, 'court/chair_confirm.html', {**context, 'state': 'done'})
    if not _chair_window_open(att):
        return render(request, 'court/chair_confirm.html', {**context, 'state': 'expired'})
    if request.user.is_authenticated and request.user == att.user:
        return render(request, 'court/chair_confirm.html', {**context, 'state': 'own_device'})

    if request.method == 'POST':
        name = (request.POST.get('chair_name') or '').strip()[:120]
        role = request.POST.get('chair_role')
        if not name or role not in dict(CHAIR_ROLES) or not request.POST.get('attest'):
            return render(request, 'court/chair_confirm.html', {
                **context, 'state': 'form',
                'error': 'Please enter your name, choose your role and tick the confirmation box.'})
        att.verification_method = 'qr'
        att.chair_signature_name = name
        att.chair_role = role
        att.chair_signature_at = timezone.now()
        att.chair_confirm_ip = _client_ip(request)
        att.chair_confirm_user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]
        att.save()
        return render(request, 'court/chair_confirm.html', {**context, 'state': 'done'})

    return render(request, 'court/chair_confirm.html', {**context, 'state': 'form'})
