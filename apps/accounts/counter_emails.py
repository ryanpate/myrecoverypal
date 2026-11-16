"""Milestone emails for calculator visitors who don't want an account yet.

Most people who use the sobriety and clean-time calculators leave without
signing up. This asks only for an email: after a confirmation click (double
opt-in by a button press, so nobody can sign someone else up and a mail
scanner following the link can't either) it sends one email on each
milestone day, with their medallion and a link that turns the date into a
saved counter. Someone who later creates an account stops getting these,
because members have their own milestone emails.
"""
import logging
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.analytics import queue_ga_event

from .email_service import send_email
from .forms import CustomUserCreationForm
from .models import CounterEmail, User

logger = logging.getLogger(__name__)

KINDS = {'sober': 'core:sobriety_calculator', 'clean': 'core:clean_time_calculator'}
MILESTONE_DAYS = (7, 30, 60, 90, 180, 270, 365)
SEND_LOCAL_HOUR = 9
FALLBACK_TZ = 'America/Chicago'
RESEND_AFTER = timedelta(hours=1)        # one confirmation an hour per address
LINK_MAX_AGE = timedelta(days=30)
SIGNING_SALT = 'counter-email-confirm'
PURGE_UNCONFIRMED_AFTER = timedelta(days=30)
SIGNUP_MESSAGE = 'Check your inbox and tap the link to confirm.'


def milestone_for(start, today):
    """The milestone `today` is for a counter that began on `start`, as
    (days, label), or None. Past the first year it is each calendar anniversary."""
    days = (today - start).days
    if days in MILESTONE_DAYS:
        if days == 365:
            return days, '1 year'
        if days in (180, 270):
            return days, f'{days // 30} months'
        return days, f'{days} days'
    if days > 365:
        try:
            anniversary = start.replace(year=today.year)
        except ValueError:  # February 29 in a non-leap year
            anniversary = date(today.year, 2, 28)
        if anniversary == today:
            years = today.year - start.year
            return days, f'{years} years'
    return None


def _zone(name):
    try:
        return ZoneInfo(name or FALLBACK_TZ)
    except Exception:
        return ZoneInfo(FALLBACK_TZ)


def _url(name, *args, query=''):
    return settings.SITE_URL.rstrip('/') + reverse(name, args=args) + query


def request_emails(email, start_date, kind, tz_name):
    """Send a confirmation link for this address, date and kind.

    The link carries the date (signed), and nothing about an already-confirmed
    signup changes until that link is used: knowing someone's address is not
    enough to pause or redate their emails. One confirmation an hour per
    address, whatever date is sent. Returns False when the email could not be
    sent, so the visitor can be told.
    """
    email = email.strip().lower()
    tz_name = tz_name[:64]
    now = timezone.now()
    row = CounterEmail.objects.filter(email=email).first()
    if row and row.confirmed_at and (row.start_date, row.kind) == (start_date, kind):
        return True  # already getting exactly this
    if row and row.confirmation_sent_at and now - row.confirmation_sent_at < RESEND_AFTER:
        return True  # a confirmation is already on its way
    if row is None:
        row = CounterEmail.objects.create(
            email=email, start_date=start_date, kind=kind, timezone=tz_name)
    if not _send_confirmation(row, start_date, kind, tz_name):
        return False
    row.confirmation_sent_at = now  # only a delivered confirmation starts the wait
    row.save(update_fields=['confirmation_sent_at'])
    return True


def _send_confirmation(row, start_date, kind, tz_name):
    payload = signing.dumps({'d': start_date.isoformat(), 'k': kind, 'z': tz_name}, salt=SIGNING_SALT)
    confirm = _url('accounts:counter_email_confirm', row.token, query=f'?c={payload}')
    plain = (
        f'Tap to confirm your {kind} milestone emails:\n{confirm}\n\n'
        "We'll email you on each milestone day, and nothing else.\n"
        "If you didn't ask for this, ignore this email and you won't hear from us.\n\n"
        '— MyRecoveryPal'
    )
    html = (
        f'<p>Confirm your {kind} milestone emails:</p>'
        f'<p><a href="{confirm}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">Yes, email me my milestones</a></p>'
        "<p style=\"color:#666;font-size:13px;\">We'll email you on each milestone day, and nothing "
        "else. If you didn't ask for this, ignore this email and you won't hear from us.</p>"
    )
    try:
        ok, _ = send_email(subject='Confirm your milestone emails', plain_message=plain,
                           html_message=html, recipient_email=row.email)
    except Exception:
        logger.exception('Failed to send counter-email confirmation %s', row.pk)
        return False
    return ok


def _send_milestone(row, days, label):
    medallion = _url('core:sobriety_medallion_maker',
                     query=f'?days={days}&utm_source=email&utm_medium=email&utm_campaign=counter_milestone')
    signup = _url('accounts:register',
                  query=f'?sobriety_date={row.start_date.isoformat()}'
                        '&utm_source=email&utm_medium=email&utm_campaign=counter_milestone')
    unsubscribe = _url('accounts:counter_email_stop', row.token)
    plain = (
        f"Today you're {label} {row.kind} ({days:,} days). That took something. Well done.\n\n"
        f'Make your {label} medallion (free): {medallion}\n\n'
        f'Want a counter that keeps counting, a daily check-in and people who get it? '
        f'Save your date to a free account: {signup}\n\n'
        f'Stop these emails: {unsubscribe}'
    )
    html = (
        f"<p style=\"font-size:18px;\"><strong>Today you're {label} {row.kind}.</strong></p>"
        f'<p>{days:,} days. That took something. Well done.</p>'
        f'<p><a href="{medallion}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:600;">Make my {label} medallion</a></p>'
        f'<p style="color:#444;">Want a counter that keeps counting, a daily check-in and people '
        f'who get it? <a href="{signup}">Save your date to a free account</a>.</p>'
        f'<p style="color:#999;font-size:12px;"><a href="{unsubscribe}">Stop these emails</a></p>'
    )
    return send_email(subject=f"{label.capitalize()} {row.kind} today", plain_message=plain,
                      html_message=html, recipient_email=row.email)


def send_due(now=None):
    """Hourly: email everyone whose milestone is today, from 9 AM their time.
    Returns how many were sent."""
    now = now or timezone.now()
    CounterEmail.objects.filter(
        confirmed_at__isnull=True, created_at__lt=now - PURGE_UNCONFIRMED_AFTER).delete()

    sent = 0
    for row in CounterEmail.objects.filter(confirmed_at__isnull=False):
        local = now.astimezone(_zone(row.timezone))
        if local.hour < SEND_LOCAL_HOUR:
            continue
        milestone = milestone_for(row.start_date, local.date())
        if not milestone or milestone[0] == row.last_sent_days:
            continue
        days, label = milestone
        # Members get their own milestone emails; don't send both.
        if not User.objects.filter(email__iexact=row.email).exists():
            try:
                ok, _ = _send_milestone(row, days, label)
            except Exception:
                logger.exception('Failed to send counter milestone %s', row.pk)
                continue
            if not ok:
                continue  # try again next hour
            sent += 1
        row.last_sent_days = days
        row.save(update_fields=['last_sent_days'])
    return sent


def _back_to(kind):
    return redirect(KINDS.get(kind, KINDS['sober']))


@require_POST
def signup(request):
    """Form post from a calculator. Answers JSON to fetch(), else redirects back."""
    kind = request.POST.get('kind') if request.POST.get('kind') in KINDS else 'sober'
    ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def answer(ok, text):
        if ajax:
            return JsonResponse({'ok': ok, 'message': text}, status=200 if ok else 400)
        (messages.success if ok else messages.error)(request, text)
        return _back_to(kind)

    if request.POST.get('website'):  # honeypot: people never see this field
        return answer(True, SIGNUP_MESSAGE)
    email = (request.POST.get('email') or '').strip()
    try:
        validate_email(email)
    except ValidationError:
        return answer(False, 'Please enter a valid email address.')
    start = CustomUserCreationForm.parse_carried_date(request.POST.get('start_date'))
    if not start:
        return answer(False, 'Enter your date in the calculator first.')
    if not request_emails(email, start, kind, request.POST.get('timezone') or ''):
        return answer(False, "We couldn't send your confirmation email. Please try again in a minute.")
    return answer(True, SIGNUP_MESSAGE)


def _read_link(request):
    """The (date, kind, time zone) a confirmation link was issued for, or None."""
    try:
        data = signing.loads(request.GET.get('c') or '', salt=SIGNING_SALT,
                             max_age=LINK_MAX_AGE.total_seconds())
        start = CustomUserCreationForm.parse_carried_date(data['d'])
        kind = data['k']
    except (signing.BadSignature, KeyError, TypeError):
        return None
    if not start or kind not in KINDS:
        return None
    return start, kind, str(data.get('z') or '')[:64]


@require_http_methods(['GET', 'POST'])
def confirm(request, token):
    """GET shows a button (mail scanners prefetch links, and a prefetch must
    not opt anyone in); POST applies the link's date and confirms."""
    row = CounterEmail.objects.filter(token=token).first()
    link = _read_link(request) if row else None
    if not link:
        messages.error(request, 'That link has expired. Enter your date and email again.')
        return _back_to('sober')
    start, kind, tz_name = link
    if request.method == 'GET':
        return render(request, 'accounts/counter_email_confirm.html',
                      {'start': start, 'kind': kind})
    if (row.start_date, row.kind) != (start, kind):
        row.last_sent_days = None
    was_confirmed = bool(row.confirmed_at)
    row.start_date, row.kind, row.timezone = start, kind, tz_name
    row.confirmed_at = row.confirmed_at or timezone.now()
    row.save()
    if not was_confirmed:
        queue_ga_event(request, 'calculator_email_confirmed', kind=kind)
    messages.success(request, "You're set. We'll email you on each milestone day.")
    return _back_to(kind)


@require_http_methods(['GET', 'POST'])
def stop(request, token):
    """GET shows a button (mail scanners prefetch links); POST deletes the row."""
    row = CounterEmail.objects.filter(token=token).first()
    if request.method == 'POST':
        if row:
            row.delete()
        return render(request, 'accounts/counter_email_stop.html', {'done': True})
    return render(request, 'accounts/counter_email_stop.html', {'done': row is None})
