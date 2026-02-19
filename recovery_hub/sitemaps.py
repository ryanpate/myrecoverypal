# recovery_hub/sitemaps.py
"""
Sitemap configuration for MyRecoveryPal
This creates a dynamic sitemap.xml that updates automatically
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from apps.blog.models import Post  # Assuming you have a Post model
# from resources.models import Resource  # Uncomment if you have resources
# from apps.journal.models import JournalEntry  # Don't include private entries


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    protocol = 'https'
    changefreq = 'weekly'

    def items(self):
        # List all your public static pages with priorities
        return [
            # Home page - highest priority
            ('core:index', 1.0),

            # Blog listing
            ('blog:post_list', 0.9),

            # HIGH PRIORITY: SEO Landing Pages (high-value keywords)
            ('core:sobriety_calculator', 0.95),  # Interactive tool - highest engagement
            ('core:sobriety_counter_app', 0.9),  # "sobriety counter app" keyword
            ('core:sober_grid_alternative', 0.9),  # "sober grid alternative" keyword
            ('core:alcohol_recovery_app', 0.85),  # "alcohol recovery app" keyword
            ('core:drug_addiction_recovery_app', 0.85),  # "drug addiction app" keyword
            ('core:free_aa_app', 0.85),  # "free AA app" keyword
            ('core:opioid_recovery_app', 0.85),  # "opioid recovery app" keyword
            ('core:gambling_addiction_app', 0.85),  # "gambling addiction app" keyword
            ('core:mental_health_recovery_app', 0.85),  # "mental health recovery app" keyword
            ('core:ai_recovery_coach', 0.9),  # "AI recovery coach" keyword

            # Core pages
            ('core:demo', 0.8),  # Demo/tour page
            ('core:about', 0.8),  # About page
            ('core:crisis', 0.8),  # Crisis resources

            # Community pages
            ('core:contact', 0.7),  # Contact page
            ('core:success_stories', 0.7),  # Success stories
            ('core:team', 0.6),  # Team page
            ('core:guidelines', 0.6),  # Community guidelines

            # Account pages
            ('accounts:login', 0.5),  # Login
            ('accounts:register', 0.6),  # Signup

            # Legal pages
            ('core:privacy', 0.5),  # Privacy policy
            ('core:terms', 0.5),  # Terms of service
            ('core:cookies', 0.4),  # Cookie policy

            # Store
            ('store:product_list', 0.5),  # Store
        ]

    def location(self, item):
        url_name, priority = item
        return reverse(url_name)

    def priority(self, item):
        url_name, priority = item
        return priority

    def get_urls(self, page=1, site=None, protocol=None):
        # Override to use the correct domain from settings
        from django.contrib.sites.models import Site
        if site is None:
            # Use the domain from settings instead of database
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    protocol = 'https'
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Return published blog posts only, ordered by most recent
        return Post.objects.filter(status='published').order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at

    def location(self, obj):
        return obj.get_absolute_url()

    def priority(self, obj):
        # Higher priority for recent posts
        import datetime
        from django.utils import timezone

        age_days = (timezone.now() - obj.published_at).days
        if age_days < 7:
            return 0.9  # Very recent posts
        elif age_days < 30:
            return 0.8  # Recent posts
        else:
            return 0.7  # Older posts

    def get_urls(self, page=1, site=None, protocol=None):
        # Override to use the correct domain from settings
        from django.contrib.sites.models import Site
        if site is None:
            # Use the domain from settings instead of database
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')


# Uncomment if you have resources and want them in sitemap
# class ResourceSitemap(Sitemap):
#     """Sitemap for resources"""
#     changefreq = "monthly"
#     priority = 0.6
#
#     def items(self):
#         # Return only public resources
#         return Resource.objects.filter(is_public=True)
#
#     def lastmod(self, obj):
#         return obj.updated_at
#
#     def location(self, obj):
#         return obj.get_absolute_url()


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
    # 'resources': ResourceSitemap,  # Uncomment if needed
}
