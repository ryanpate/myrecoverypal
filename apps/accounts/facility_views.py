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

    if facility.status != 'active':
        messages.error(request, 'This facility is not currently accepting new members.')
        return redirect('accounts:progress')

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


# --- Staff views ---

from apps.accounts.decorators import facility_staff_required
from apps.accounts import facility_service as fs

RISK_ORDER = {fs.RISK_AT_RISK: 0, fs.RISK_WATCH: 1, fs.RISK_OK: 2}


@facility_staff_required
def facility_dashboard(request):
    facility = request.facility
    rows = []
    for m in fs.visible_memberships(facility):
        risk = fs.compute_member_risk(m)
        rows.append({'membership': m, 'risk': risk})
    rows.sort(key=lambda r: RISK_ORDER[r['risk']['risk_level']])
    return render(request, 'accounts/facility/dashboard.html', {
        'facility': facility,
        'summary': fs.cohort_summary(facility),
        'rows': rows,
    })


@facility_staff_required
def facility_roster(request):
    facility = request.facility
    members = facility.memberships.select_related('user').order_by('-created_at')
    invites = facility.invites.order_by('-created_at')
    return render(request, 'accounts/facility/roster.html', {
        'facility': facility, 'members': members, 'invites': invites,
    })


@facility_staff_required
def facility_member_detail(request, membership_id):
    # tenant isolation + consent gate enforced in the queryset
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, facility=request.facility,
        status='active', consent_granted_at__isnull=False)
    return render(request, 'accounts/facility/member_detail.html', {
        'facility': request.facility,
        'membership': membership,
        'risk': fs.compute_member_risk(membership),
    })


@facility_staff_required
@require_POST
def facility_generate_invite(request):
    FacilityInvite.objects.create(
        facility=request.facility, code=FacilityInvite.generate_code(),
        created_by=request.user)
    messages.success(request, 'New invite link created.')
    return redirect('accounts:facility_roster')


@facility_staff_required
@require_POST
def facility_revoke_member(request, membership_id):
    membership = get_object_or_404(
        FacilityMembership, id=membership_id, facility=request.facility)
    membership.status = 'revoked'
    membership.left_at = timezone.now()
    membership.save(update_fields=['status', 'left_at'])
    messages.success(request, 'Member removed from your cohort.')
    return redirect('accounts:facility_roster')
