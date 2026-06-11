# apps/accounts/email_views.py
"""Email-related views (unsubscribe, etc.)."""
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from .outreach_models import ColdOutreachSuppression

User = get_user_model()


def unsubscribe_marketing(request, token):
    """One-click unsubscribe from marketing emails.

    Token format: signing.dumps({'user_id': X, 'kind': 'marketing'}).
    No expiry — once unsubscribed, the user can re-enable via their profile.
    """
    try:
        data = signing.loads(token)
    except signing.BadSignature:
        raise Http404('Invalid unsubscribe token')

    if data.get('kind') != 'marketing':
        raise Http404('Unknown unsubscribe kind')

    try:
        user = User.objects.get(pk=data['user_id'])
    except (User.DoesNotExist, KeyError):
        raise Http404('User not found')

    user.marketing_emails_enabled = False
    user.save(update_fields=['marketing_emails_enabled'])

    # Note: don't pass {'user': user} — that would shadow request.user in
    # base.html and make the anonymous visitor render the authenticated nav,
    # which evaluates user.subscription.is_court and triggers a DB query.
    return render(request, 'accounts/email_unsubscribed.html')


@csrf_protect
def cold_outreach_unsubscribe(request):
    """Opt-out page for facility cold-outreach emails.

    GET  — show the form (email pre-filled from ?email= if present).
    POST — record the address on the suppression list and confirm.

    Recipients aren't registered users, so this is keyed purely by email.
    Suppressing an address is always safe (it only stops sends), so no
    signed token is required.
    """
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'accounts/cold_outreach_unsubscribe.html', {
                'email': email,
                'error': 'Please enter a valid email address.',
            })

        ColdOutreachSuppression.objects.get_or_create(email=email)
        return render(request, 'accounts/cold_outreach_unsubscribe.html', {
            'email': email,
            'done': True,
        })

    prefill = (request.GET.get('email') or '').strip()
    return render(request, 'accounts/cold_outreach_unsubscribe.html', {
        'email': prefill,
    })
