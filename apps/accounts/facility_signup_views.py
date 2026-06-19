"""Self-serve facility onboarding: public signup + email verification."""
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.email_service import send_email
from apps.accounts.facility_forms import FacilitySignupForm
from apps.accounts.facility_models import Facility, FacilityStaff

User = get_user_model()


def _unique_facility_slug(name):
    base = slugify(name) or 'facility'
    slug, i = base, 2
    while Facility.objects.filter(slug=slug).exists():
        slug = f'{base}-{i}'
        i += 1
    return slug


def _unique_username(email):
    base = email.split('@')[0] or 'staff'
    username, i = base, 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{i}'
        i += 1
    return username


def facility_signup(request):
    if request.method != 'POST':
        return render(request, 'accounts/facility/signup.html',
                      {'form': FacilitySignupForm()})

    form = FacilitySignupForm(request.POST)
    if not form.is_valid():
        return render(request, 'accounts/facility/signup.html', {'form': form})

    data = form.cleaned_data
    token = secrets.token_urlsafe(32)
    with transaction.atomic():
        user = User.objects.create_user(
            username=_unique_username(data['email']),
            email=data['email'], password=data['password'])
        if data.get('contact_name'):
            user.first_name = data['contact_name'][:150]
            user.save(update_fields=['first_name'])
        facility = Facility.objects.create(
            name=data['facility_name'],
            slug=_unique_facility_slug(data['facility_name']),
            status='pending', activation_token=token)
        FacilityStaff.objects.create(
            facility=facility, user=user, role='admin')

    verify_url = request.build_absolute_uri(
        reverse('accounts:facility_verify_email', args=[token]))
    send_email(
        subject=f'Verify your facility — {facility.name}',
        plain_message=f'Verify your MyRecoveryPal facility account: {verify_url}',
        html_message=render_to_string('emails/facility_verify_email.html',
                                      {'facility': facility, 'verify_url': verify_url}),
        recipient_email=user.email)
    send_email(
        subject=f'New facility signup: {facility.name}',
        plain_message=f'New facility "{facility.name}" signed up ({user.email}).',
        html_message=render_to_string('emails/facility_signup_notify.html',
                                      {'facility': facility, 'contact_email': user.email}),
        recipient_email=getattr(settings, 'FACILITY_SIGNUP_NOTIFY_EMAIL',
                                settings.DEFAULT_FROM_EMAIL))

    return render(request, 'accounts/facility/signup_done.html',
                  {'email': user.email})


def facility_verify_email(request, token):
    facility = (Facility.objects
                .filter(activation_token=token)
                .exclude(activation_token='')
                .first())
    if not facility:
        return render(request, 'accounts/facility/verify_invalid.html')

    facility.status = 'active'
    facility.email_verified_at = timezone.now()
    facility.activation_token = ''
    facility.save(update_fields=['status', 'email_verified_at', 'activation_token'])

    staff = (FacilityStaff.objects
             .filter(facility=facility, role='admin')
             .select_related('user').first())
    if staff:
        login(request, staff.user,
              backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f'{facility.name} is verified and active.')
    return redirect('accounts:facility_dashboard')
