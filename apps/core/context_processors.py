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
            if sub and sub.is_trialing() and sub.trial_end:
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
        'twitter_site': '@myrecoverypal',
        'twitter_creator': '@myrecoverypal',
        'REVENUECAT_IOS_API_KEY': getattr(settings, 'REVENUECAT_IOS_API_KEY', ''),
        'trial_ending_soon': trial_ending_soon,
        'trial_days_left': trial_days_left,
    }