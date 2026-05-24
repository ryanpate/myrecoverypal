# apps/accounts/court_views.py
"""Court Compliance views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.court_models import (
    CourtReport, CourtReportProfile, MeetingAttendance,
)


def verify_court_report(request, hash_value):
    """
    Public endpoint — court / probation officer pastes a hash and we confirm
    that hash matches a real report. We do NOT leak any personal info.
    """
    if len(hash_value) == 64:
        report = CourtReport.objects.filter(pdf_hash=hash_value).first()
    elif len(hash_value) >= 8:
        report = CourtReport.objects.filter(pdf_hash__startswith=hash_value).first()
    else:
        report = None

    if not report:
        raise Http404('Unknown court report fingerprint')

    return render(request, 'court/verify.html', {
        'report': report,
        'verified_at': timezone.now(),
    })
