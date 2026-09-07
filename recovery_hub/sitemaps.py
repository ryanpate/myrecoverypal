# recovery_hub/sitemaps.py
"""
Sitemap configuration for MyRecoveryPal
This creates a dynamic sitemap.xml that updates automatically
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from apps.blog.models import Post  # Assuming you have a Post model
from apps.store.models import Category as StoreCategory
from resources.models import Resource
from apps.support_services.models import Meeting
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

            # Resources hub pages (individual resources covered by ResourceSitemap)
            ('resources:list', 0.7),
            ('resources:educational_resources', 0.6),

            # HIGH PRIORITY: SEO Landing Pages (high-value keywords)
            ('core:sobriety_calculator', 0.95),  # Interactive tool - highest engagement
            ('core:clean_time_calculator', 0.95),  # "clean time calculator" — NA/drug-recovery tool, weak SERP competition
            ('accounts:milestone_badge_creator', 0.95),  # Free interactive medallion creator
            ('core:sobriety_medallion_maker', 0.95),  # "sobriety medallion"/"AA chip generator" — top click driver in GSC
            ('core:sober_grid_alternative', 0.9),  # "sober grid alternative" keyword
            ('core:support_a_loved_one', 0.9),  # "support a loved one in recovery" — Supporter tier landing
            ('core:alcohol_recovery_app', 0.85),  # "alcohol recovery app" keyword
            ('core:drug_addiction_recovery_app', 0.85),  # "drug addiction app" keyword
            # sobriety_counter_app, free_aa_app, mental_health_recovery_app,
            # opioid_recovery_app and gambling_addiction_app are intentionally
            # excluded: all five 301 to consolidated pages, and GSC flags
            # redirecting sitemap URLs ("Page with redirect", validation failed).
            # SitemapNoRedirectTests guards this — a sitemap entry must return 200.
            ('core:ai_recovery_coach', 0.9),  # "AI recovery coach" keyword
            ('core:court_ordered_meeting_tracker', 0.9),  # "court ordered AA app" — Court Compliance tier landing
            ('core:online_aa_meetings', 0.9),  # "online AA meetings" — live meeting directory
            ('support_services:meeting_list', 0.9),  # Meeting directory hub (detail pages: MeetingSitemap)
            ('core:craving_sos', 0.9),  # "how to stop cravings" — interactive SOS toolbox
            ('core:relapse_prevention_plan', 0.9),  # "relapse prevention plan template" — guided builder landing
            ('core:for_probation_officers', 0.7),  # PO verification guide / outreach one-pager

            # Pricing (paid tier discovery)
            ('accounts:pricing', 0.75),

            # Core pages
            ('core:demo', 0.8),  # Demo/tour page
            ('core:about', 0.8),  # About page
            ('core:crisis', 0.8),  # Crisis resources
            ('store:product_list', 0.7),  # Recovery Shop (journals/apparel)

            # Community pages
            ('core:contact', 0.7),  # Contact page
            ('core:success_stories', 0.7),  # Success stories
            ('core:team', 0.6),  # Team page
            ('core:guidelines', 0.6),  # Community guidelines

            # Account pages (login intentionally excluded — auth page, no search value)
            ('accounts:register', 0.6),  # Signup

            # Legal pages
            ('core:privacy', 0.5),  # Privacy policy
            ('core:terms', 0.5),  # Terms of service
            ('core:cookies', 0.4),  # Cookie policy
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


class StoreCategorySitemap(Sitemap):
    """Sitemap for Recovery Shop category filter pages (?category=slug)."""
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.65  # Just under the main /store/ page (0.7).

    def items(self):
        return list(
            StoreCategory.objects.filter(products__is_active=True).distinct()
        )

    def location(self, obj):
        return f"{reverse('store:product_list')}?category={obj.slug}"

    def get_urls(self, page=1, site=None, protocol=None):
        from django.contrib.sites.models import Site
        if site is None:
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')


class ResourceSitemap(Sitemap):
    """Sitemap for resources"""
    protocol = 'https'
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Resource.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class MeetingSitemap(Sitemap):
    """Sitemap for individual recovery meeting pages.

    ~1,565 approved meetings. These were never submitted to Google, which
    is why /support/meetings/ and its detail pages sat in "Crawled -
    currently not indexed" despite being the highest-engagement section
    of the site.
    """
    protocol = 'https'
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Meeting.objects.filter(
            is_approved=True, is_active=True
        ).order_by('pk')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()

    def get_urls(self, page=1, site=None, protocol=None):
        from django.contrib.sites.models import Site
        if site is None:
            site = Site(domain=settings.SITE_DOMAIN, name=settings.SITE_DOMAIN)
        return super().get_urls(page=page, site=site, protocol='https')


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogPostSitemap,
    'store_categories': StoreCategorySitemap,
    'resources': ResourceSitemap,
    'meetings': MeetingSitemap,
}
