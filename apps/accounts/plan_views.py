"""Views for the relapse prevention plan.

The plan itself is always free (never paywall a safety tool); only the PDF
export below is premium. Plan content is private — these views only ever
render the requesting user's own plan.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from apps.accounts.decorators import premium_required
from apps.accounts.plan_forms import RelapsePreventionPlanForm
from apps.accounts.plan_models import RelapsePreventionPlan


@login_required
def relapse_plan_view(request):
    plan, _ = RelapsePreventionPlan.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = RelapsePreventionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(
                request, 'Your relapse prevention plan has been saved.')
            return redirect('accounts:relapse_plan')
    else:
        form = RelapsePreventionPlanForm(instance=plan)

    sub = getattr(request.user, 'subscription', None)
    has_premium = bool(sub and sub.is_premium())
    return render(request, 'accounts/relapse_prevention_plan.html', {
        'form': form,
        'plan': plan,
        'has_premium': has_premium,
    })
