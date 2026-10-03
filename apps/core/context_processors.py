# apps/core/context_processors.py
"""
SEO Context Processor for MyRecoveryPal
Add this file to apps/core/context_processors.py
"""

from django.conf import settings

def seo_defaults(request):
    """
    Provides default SEO values that can be overridden in individual templates.
    Usage in templates: {{ seo_title }}, {{ seo_description }}, etc.
    """
    
    # Get current URL for canonical and Open Graph — force www for consistency
    current_url = request.build_absolute_uri()
    current_url = current_url.replace('://myrecoverypal.com', '://www.myrecoverypal.com')
    
    # Default values
    default_title = "MyRecoveryPal - Your Recovery Support Community"
    default_description = "Free recovery community. Track milestones, connect with peers, journal your journey, access resources. Join MyRecoveryPal today."
    default_keywords = "recovery support, addiction recovery, sobriety tracker, recovery community, peer support, recovery journal, milestone tracking, sobriety app, recovery resources, mental health support"
    default_image = request.build_absolute_uri(settings.STATIC_URL + 'images/og-image.png')
    
    # Trial expiry banner data (for authenticated users with expiring trials)
    trial_ending_soon = False
    trial_days_left = None
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            sub = getattr(request.user, 'subscription', None)
            # Only no-card signup trials: someone with a Stripe subscription has
            # already subscribed and must not be told to "Keep Premium".
            if sub and sub.is_trialing() and sub.trial_end and not sub.stripe_subscription_id:
                from django.utils import timezone as tz
                delta = sub.trial_end - tz.now()
                if delta.days <= 2:
                    trial_ending_soon = True
                    trial_days_left = max(0, delta.days)
        except Exception:
            pass

    return {
        'seo_title': default_title,
        'seo_description': default_description,
        'seo_keywords': default_keywords,
        'seo_image': default_image,
        'seo_url': current_url,
        'site_name': 'MyRecoveryPal',
        'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
        'twitter_site': '@myrecoverypal',
        'twitter_creator': '@myrecoverypal',
        'REVENUECAT_IOS_API_KEY': getattr(settings, 'REVENUECAT_IOS_API_KEY', ''),
        'trial_ending_soon': trial_ending_soon,
        'trial_days_left': trial_days_left,
    }


def ga_events(request):
    """Hand any server-queued GA4 events to base.html.

    Popping here is what makes them fire once: the next render clears the
    session queue. See apps/core/analytics.py.
    """
    from apps.core.analytics import pop_ga_events
    return {'ga_events': pop_ga_events(request)}


# Bump when there's something new to announce: everyone who dismissed the
# previous version sees the new one once (localStorage key in _whats_new.html).
WHATS_NEW_VERSION = '2026-10-library'
# Calm "home" pages only. Never on crisis, SOS, Anchor, check-in, checkout,
# onboarding or auth pages, where an interruption would get in the way.
WHATS_NEW_PAGES = {'accounts:progress', 'accounts:social_feed', 'resources:list'}


def whats_new(request):
    """Decide whether base.html may offer the one-time "What's new" popup.

    Only logged-in members, only on WHATS_NEW_PAGES, and not in someone's
    first day (onboarding already introduces everything). Whether this
    browser has already seen this version is checked client-side.
    """
    user = getattr(request, 'user', None)
    match = getattr(request, 'resolver_match', None)
    if not (user and user.is_authenticated and match and match.view_name in WHATS_NEW_PAGES):
        return {}
    from datetime import timedelta
    from django.utils import timezone
    joined = getattr(user, 'date_joined', None)
    if joined and timezone.now() - joined < timedelta(days=1):
        return {}
    sub = getattr(user, 'subscription', None)
    if sub and sub.is_supporter():
        return {}  # family members: these are tools for the person in recovery
    return {'show_whats_new': True, 'whats_new_version': WHATS_NEW_VERSION}
