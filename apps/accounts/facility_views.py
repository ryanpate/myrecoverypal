"""Treatment-center aftercare views: enrollment/consent (client) + dashboard (staff)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.facility_models import (
    Facility, FacilityInvite, FacilityMembership,
)


@login_required
def facility_join(request, code):
    invite = get_object_or_404(FacilityInvite, code=code)
    facility = invite.facility

    membership = FacilityMembership.objects.filter(
        facility=facility, user=request.user).first()
    if membership and membership.status == 'active':
        messages.info(request, f'You are already sharing with {facility.name}.')
        return redirect('accounts:progress')

    if request.method == 'POST':
        if request.POST.get('consent') != 'on':
            messages.warning(request, 'You must consent in order to join.')
            return render(request, 'accounts/facility/join_consent.html',
                          {'facility': facility, 'code': code})
        if not invite.is_valid():
            messages.error(request, 'This invite link is no longer valid.')
            return redirect('accounts:progress')

        now = timezone.now()
        if membership is None:
            membership = FacilityMembership(facility=facility, user=request.user)
        membership.status = 'active'
        membership.consent_granted_at = now
        membership.enrolled_at = now
        membership.left_at = None
        membership.save()

        invite.uses += 1
        invite.save(update_fields=['uses'])

        messages.success(request, f'You are now connected with {facility.name}.')
        return redirect('accounts:progress')

    return render(request, 'accounts/facility/join_consent.html',
                  {'facility': facility, 'code': code})


@login_required
@require_POST
def facility_leave(request, membership_id):
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, user=request.user)
    membership.status = 'revoked'
    membership.left_at = timezone.now()
    membership.save(update_fields=['status', 'left_at'])
    messages.success(request, 'You have stopped sharing with your facility.')
    return redirect('accounts:progress')
