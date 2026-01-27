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
    
    # Get current URL for canonical and Open Graph
    current_url = request.build_absolute_uri()
    
    # Default values
    default_title = "MyRecoveryPal - Your Recovery Support Community"
    default_description = "Free recovery community. Track milestones, connect with peers, journal your journey, access resources. Join MyRecoveryPal today."
    default_keywords = "recovery support, addiction recovery, sobriety tracker, recovery community, peer support, recovery journal, milestone tracking, sobriety app, recovery resources, mental health support"
    default_image = request.build_absolute_uri(settings.STATIC_URL + 'images/og-image.png')
    
    return {
        'seo_title': default_title,
        'seo_description': default_description,
        'seo_keywords': default_keywords,
        'seo_image': default_image,
        'seo_url': current_url,
        'site_name': 'MyRecoveryPal',
        'twitter_site': '@myrecoverypal',  # Update with your Twitter handle
        'twitter_creator': '@myrecoverypal',  # Update with your Twitter handle
    }