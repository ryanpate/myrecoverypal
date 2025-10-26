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
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        # List all your public static pages
        return [
            'core:index',  # Home page
            'accounts:login',
            'accounts:signup',
            'blog:post_list',  # Blog listing
            # Add more static pages as needed
            # 'core:about',
            # 'core:contact',
            # 'core:privacy',
            # 'core:terms',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        # Return published blog posts only
        return Post.objects.filter(status='published').order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at

    def location(self, obj):
        return obj.get_absolute_url()


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
