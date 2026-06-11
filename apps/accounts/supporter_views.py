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


@login_required
def supporter_renew(request):
    """Landing for supporters without an active subscription."""
    return render(request, 'accounts/supporter/renew.html')


@login_required
def manage_links(request):
    links = SupporterLink.objects.filter(member=request.user).exclude(
        status__in=['revoked', 'declined']
    ).select_related('supporter')
    return render(request, 'accounts/supporter/manage_links.html', {'links': links})


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
