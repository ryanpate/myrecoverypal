"""Views for the family / supporter dashboard."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def supporter_renew(request):
    """Landing for supporters without an active subscription."""
    return render(request, 'accounts/supporter/renew.html')
