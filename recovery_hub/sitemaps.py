# recovery_hub/sitemaps.py
"""
Sitemap configuration for MyRecoveryPal
This creates a dynamic sitemap.xml that updates automatically
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from apps.blog.models import Post  # Assuming you have a Post model
# from resources.models import Resource  # Uncomment if you have resources
# from apps.journal.models import JournalEntry  # Don't include private entries


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    changefreq = 'weekly'

    def items(self):
        # List all your public static pages with priorities
        return [
            ('core:index', 1.0),  # Home page - highest priority
            ('blog:post_list', 0.9),  # Blog listing
            ('core:about', 0.8),  # About page
            ('core:contact', 0.7),  # Contact page
            ('accounts:login', 0.6),  # Login
            ('accounts:signup', 0.6),  # Signup
            ('core:privacy', 0.5),  # Privacy policy
            ('core:terms', 0.5),  # Terms of service
            ('core:cookies', 0.4),  # Cookie policy
            ('core:guidelines', 0.6),  # Community guidelines
            ('core:success_stories', 0.7),  # Success stories
            ('core:team', 0.6),  # Team page
            ('core:crisis', 0.8),  # Crisis resources - important
            ('store:product_list', 0.5),  # Store
        ]

    def location(self, item):
        url_name, priority = item
        return reverse(url_name)

    def priority(self, item):
        url_name, priority = item
        return priority


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
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
