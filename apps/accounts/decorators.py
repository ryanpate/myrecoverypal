# apps/accounts/decorators.py
"""
Feature gating decorators for premium features
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def premium_required(view_func):
    """
    Decorator that requires Premium or Pro subscription
    Redirects to upgrade page if user doesn't have premium access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')

        # Check if user has subscription
        if not hasattr(request.user, 'subscription'):
            messages.warning(
                request,
                'This feature requires a Premium subscription. Upgrade now to unlock!'
            )
            return redirect('accounts:pricing')

        # Check if subscription is premium or pro
        if not request.user.subscription.is_premium():
            messages.warning(
                request,
                'This feature requires a Premium subscription. Upgrade now to unlock!'
            )
            return redirect('accounts:pricing')

        return view_func(request, *args, **kwargs)

    return wrapper


def court_required(view_func):
    """
    Decorator that requires Court Compliance subscription.
    Redirects to upgrade page if user doesn't have court access.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')

        if not hasattr(request.user, 'subscription'):
            messages.warning(
                request,
                'Court Compliance reporting requires the Court Compliance subscription.'
            )
            return redirect('accounts:pricing')

        if not request.user.subscription.is_court():
            messages.warning(
                request,
                'Court Compliance reporting requires the Court Compliance subscription.'
            )
            return redirect('accounts:pricing')

        return view_func(request, *args, **kwargs)

    return wrapper


def facility_staff_required(view_func):
    """Requires the user to be staff of an active facility.
    Attaches request.facility_staff and request.facility."""
    from apps.accounts.facility_models import FacilityStaff

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')
        staff = (FacilityStaff.objects
                 .select_related('facility')
                 .filter(user=request.user, facility__status='active')
                 .first())
        if not staff:
            messages.warning(request, 'You do not have a facility dashboard.')
            return redirect('accounts:progress')
        request.facility_staff = staff
        request.facility = staff.facility
        return view_func(request, *args, **kwargs)
    return wrapper


def supporter_required(view_func):
    """Requires an active Supporter subscription. Lapsed/absent -> renew page."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access this feature.')
            return redirect('accounts:login')
        sub = getattr(request.user, 'subscription', None)
        if sub is None or not sub.is_supporter():
            messages.warning(
                request,
                'Viewing a loved one’s progress requires an active Supporter subscription.'
            )
            return redirect('accounts:supporter_renew')
        return view_func(request, *args, **kwargs)
    return wrapper


def check_feature_limit(feature_name, limit_attr):
    """
    Decorator factory for checking feature usage limits
    Usage: @check_feature_limit('groups', 'max_groups')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Premium/Pro users have no limits
            if hasattr(request.user, 'subscription') and request.user.subscription.is_premium():
                return view_func(request, *args, **kwargs)

            # Check limit for free users
            limits = {
                'max_groups': 5,
                'max_private_groups': 0,
            }

            limit = limits.get(limit_attr, float('inf'))

            # Get current count based on feature
            if feature_name == 'groups':
                count = request.user.get_joined_groups().count()
            else:
                count = 0

            if count >= limit:
                messages.warning(
                    request,
                    f'You\'ve reached the free tier limit of {limit} {feature_name}. '
                    f'Upgrade to Premium for unlimited access!'
                )
                return redirect('accounts:pricing')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
