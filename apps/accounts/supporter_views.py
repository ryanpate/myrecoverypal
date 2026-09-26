"""Views for the family / supporter dashboard."""
import secrets
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from apps.accounts.supporter_models import SupporterLink, PRESET_CHOICES
from apps.accounts.supporter_forms import SupporterInviteForm, PresetForm
from apps.accounts.decorators import supporter_required
from apps.accounts import supporter_service
from apps.accounts.email_service import send_email


@login_required
def supporter_renew(request):
    """Landing for supporters without an active subscription."""
    return render(request, 'accounts/supporter/renew.html')


@login_required
def manage_links(request):
    links = SupporterLink.objects.filter(member=request.user).exclude(
        status__in=['revoked', 'declined']
    ).select_related('supporter')
    supporting = SupporterLink.objects.filter(supporter=request.user).exclude(
        status__in=['revoked', 'declined']
    ).select_related('member')
    return render(request, 'accounts/supporter/manage_links.html', {
        'links': links, 'supporting': supporting,
    })


@login_required
def supporter_invite(request):
    if request.method == 'POST':
        form = SupporterInviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['invite_email']
            existing = SupporterLink.objects.filter(
                member=request.user, invite_email=email, status='pending'
            ).exists()
            if existing:
                messages.info(request, 'You already have a pending invite to that email.')
                return redirect('accounts:supporter_manage')
            SupporterLink.objects.create(
                member=request.user,
                initiated_by='member',
                preset=form.cleaned_data['preset'],
                invite_email=email,
                invite_token=secrets.token_urlsafe(32),
                status='pending',
            )
            messages.success(request, 'Invite link created.')
            return redirect('accounts:supporter_manage')
    else:
        form = SupporterInviteForm()
    return render(request, 'accounts/supporter/invite.html', {'form': form})


@login_required
@require_POST
def supporter_set_preset(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user)
    form = PresetForm(request.POST)
    if form.is_valid():
        link.set_preset(form.cleaned_data['preset'])
        messages.success(request, 'Sharing level updated.')
    else:
        messages.error(request, 'That sharing level is not valid.')
    return redirect('accounts:supporter_manage')


@login_required
@require_POST
def supporter_revoke(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user)
    link.revoke()
    messages.success(request, 'Access revoked.')
    return redirect('accounts:supporter_manage')


@login_required
@supporter_required
def supporter_dashboard(request, link_id):
    link = get_object_or_404(
        SupporterLink, id=link_id, supporter=request.user, status='active'
    )
    dashboard = supporter_service.get_dashboard_data(link)
    return render(request, 'accounts/supporter/dashboard.html',
                  {'link': link, 'dashboard': dashboard})


@login_required
@supporter_required
@require_POST
def supporter_encourage(request, link_id):
    link = get_object_or_404(SupporterLink, id=link_id, supporter=request.user, status='active')
    if supporter_service.send_encouragement(link, request.POST.get('key', '')):
        messages.success(request, 'Sent. 💛')
    return redirect('accounts:supporter_dashboard', link_id=link.id)


@login_required
def supporter_accept(request, token):
    """A supporter (Path A) accepts an email invite, binding their account.

    GET renders a confirm page (the email link is a GET); POST binds.
    Bearer-token model: possession of the 256-bit token is the credential and
    it is delivered only to the invited email. We do NOT hard-match
    request.user.email to invite_email — accepted tradeoff for MVP; revisit
    before scaling the data-richer 'close' preset.
    """
    link = get_object_or_404(SupporterLink, invite_token=token, status='pending')
    if request.method == 'POST':
        # Guard the (member, supporter) unique constraint, which spans ALL
        # statuses: if any link already exists for this pair (active, paused,
        # revoked, or declined), binding here would raise IntegrityError.
        if SupporterLink.objects.filter(
            member=link.member, supporter=request.user
        ).exists():
            messages.info(request, 'You already have a connection with this person.')
            return redirect('accounts:social_feed')
        link.supporter = request.user
        link.status = 'active'   # member already set preset = consent on invite
        if not link.consented_at:
            link.consented_at = timezone.now()
        link.save(update_fields=['supporter', 'status', 'consented_at', 'updated_at'])
        messages.success(request, 'You are now connected.')
        return redirect('accounts:supporter_dashboard', link_id=link.id)
    return render(request, 'accounts/supporter/accept.html', {'link': link})


@login_required
def supporter_consent(request, link_id):
    """Member (Path B) reviews a supporter-initiated request and accepts/declines."""
    link = get_object_or_404(SupporterLink, id=link_id, member=request.user, status='pending')
    if request.method == 'POST':
        if request.POST.get('decision') == 'accept':
            # Clamp to a valid preset so a crafted POST can't reach the model's
            # ValidationError path (which would 500).
            preset = request.POST.get('preset', 'standard')
            if preset not in {c[0] for c in PRESET_CHOICES}:
                preset = 'standard'
            link.consent(preset=preset)
            messages.success(request, 'Connected. You control what they see and can pause anytime.')
        else:
            link.decline()
        return redirect('accounts:supporter_manage')
    return render(request, 'accounts/supporter/consent.html', {'link': link})


@login_required
@require_POST
def request_support(request):
    notified = supporter_service.record_support_request(request.user)
    if notified:
        messages.success(
            request,
            "Your close supporters have been notified. You're not alone. "
            "If you're in crisis, call or text 988.",
        )
    else:
        messages.info(
            request,
            "You don't have a close supporter set up yet. You're not alone — "
            "if you're in crisis, call or text 988, or reach out in the community.",
        )
    nxt = request.POST.get('next')
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(nxt)
    return redirect('accounts:social_feed')



# --- Family-started support (supporter-initiated) ----------------------------
#
# A family member invites the person in recovery. Nothing is shared until that
# person accepts and picks a sharing level; the family member pays for
# Supporter only after acceptance. Privacy rule: never reveal whether an email
# already has an account — every invite behaves identically.

MAX_FAMILY_INVITES_PER_DAY = 5


def _asker_name(user):
    return (user.first_name or '').strip() or 'Someone who cares about you'


@login_required
def supporter_invite_member(request):
    from datetime import timedelta
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    from django.urls import reverse

    context = {}
    if request.method == 'POST':
        name = (request.POST.get('loved_one_name') or '').strip()[:60]
        email = (request.POST.get('email') or '').strip().lower()
        note = (request.POST.get('note') or '').strip()[:500]
        recent = SupporterLink.objects.filter(
            supporter=request.user, initiated_by='supporter',
            created_at__gte=timezone.now() - timedelta(days=1)).count()
        error = None
        if not name:
            error = 'Tell us what you call them, so the invite feels personal.'
        elif email:
            try:
                validate_email(email)
            except ValidationError:
                error = 'That email address doesn’t look right.'
        if not error and recent >= MAX_FAMILY_INVITES_PER_DAY:
            error = 'You’ve sent the most invites allowed today. Try again tomorrow.'
        if error:
            context.update(error=error, form={'loved_one_name': name, 'email': email, 'note': note})
        else:
            link = SupporterLink.objects.create(
                supporter=request.user, initiated_by='supporter', status='pending',
                invite_token=secrets.token_urlsafe(32), invite_email=email,
                loved_one_name=name, invite_note=note,
            )
            accept_url = request.build_absolute_uri(
                reverse('accounts:supporter_member_accept', args=[link.invite_token]))
            if email:
                _email_invite(request.user, link, accept_url)
            context.update(link=link, accept_url=accept_url, emailed=bool(email))
    return render(request, 'accounts/supporter/invite_member.html', context)


def _email_invite(supporter, link, accept_url):
    asker = _asker_name(supporter)
    note_plain = f'\n\n"{link.invite_note}"\n' if link.invite_note else ''
    plain = (
        f'{asker} would like to support your recovery on MyRecoveryPal.{note_plain}\n\n'
        'You decide what they see (just your day count and milestones, or a little more), '
        'and you can pause or stop sharing at any time. Nothing is shared unless you accept.\n\n'
        f'See the request: {accept_url}\n\n'
        "If you don't recognise this, ignore it and nothing will be shared."
    )
    from django.utils.html import escape
    note_html = (f'<blockquote style="border-left:3px solid #52b788;padding-left:12px;color:#444;">'
                 f'{escape(link.invite_note)}</blockquote>') if link.invite_note else ''
    html = (
        f'<p><strong>{escape(asker)}</strong> would like to support your recovery on MyRecoveryPal.</p>'
        f'{note_html}'
        '<p>You decide what they see, and you can pause or stop sharing at any time. '
        'Nothing is shared unless you accept.</p>'
        f'<p><a href="{accept_url}" style="background:#1e4d8b;color:#fff;padding:12px 20px;'
        'border-radius:8px;text-decoration:none;font-weight:600;">See the request</a></p>'
        "<p style=\"color:#888;font-size:12px;\">If you don't recognise this, ignore it and nothing will be shared.</p>"
    )
    try:
        send_email(subject=f'{asker} would like to support your recovery',
                   plain_message=plain, html_message=html, recipient_email=link.invite_email)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Family invite email failed for link %s', link.pk)


@login_required
def supporter_member_accept(request, token):
    """The person in recovery reviews a family-started request and accepts or declines."""
    link = get_object_or_404(SupporterLink, invite_token=token, status='pending',
                             initiated_by='supporter', member__isnull=True)
    if link.supporter_id == request.user.id:
        messages.info(request, 'This invite is for your loved one. Share the link with them.')
        return redirect('accounts:supporter_manage')

    if request.method == 'POST':
        if request.POST.get('decision') != 'accept':
            link.decline()
            messages.info(request, 'Declined. Nothing has been shared.')
            return redirect('accounts:progress')
        if SupporterLink.objects.filter(member=request.user, supporter=link.supporter).exists():
            messages.info(request, 'You already have a connection with this person.')
            return redirect('accounts:supporter_manage')
        preset = request.POST.get('preset', 'standard')
        if preset not in {c[0] for c in PRESET_CHOICES}:
            preset = 'standard'
        link.member = request.user
        link.save(update_fields=['member', 'updated_at'])
        link.consent(preset=preset)
        _email_family_accepted(link)
        messages.success(request, 'Connected. You control what they see and can pause anytime.')
        return redirect('accounts:supporter_manage')

    return render(request, 'accounts/supporter/consent.html', {
        'link': link, 'asker_name': _asker_name(link.supporter),
    })


def _email_family_accepted(link):
    from django.conf import settings
    from django.urls import reverse
    name = link.loved_one_name or 'Your loved one'
    url = settings.SITE_URL.rstrip('/') + reverse('accounts:supporter_dashboard', args=[link.id])
    plain = (f'{name} accepted your invitation to support them on MyRecoveryPal.\n\n'
             f'See how they\'re doing: {url}\n\n— MyRecoveryPal')
    from django.utils.html import escape
    html = (f'<p><strong>{escape(name)}</strong> accepted your invitation to support them.</p>'
            f'<p><a href="{url}">See how they\'re doing</a></p>')
    try:
        send_email(subject=f'{name} accepted your support', plain_message=plain,
                   html_message=html, recipient_email=link.supporter.email)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Family accepted email failed for link %s', link.pk)
