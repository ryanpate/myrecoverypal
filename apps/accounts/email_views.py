# apps/accounts/email_views.py
"""Email-related views (unsubscribe, etc.)."""
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404
from django.shortcuts import render

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

    return render(request, 'accounts/email_unsubscribed.html', {'user': user})
