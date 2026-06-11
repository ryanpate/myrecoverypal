"""Views for the family / supporter dashboard."""
import secrets
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from apps.accounts.supporter_models import SupporterLink
from apps.accounts.supporter_forms import SupporterInviteForm, PresetForm


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
