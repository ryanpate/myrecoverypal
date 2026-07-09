# recovery_hub/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import RedirectView
from apps.core.views import robots_txt_view, ads_txt_view
from apps.accounts.court_views import verify_court_report
from apps.accounts.email_views import unsubscribe_marketing, cold_outreach_unsubscribe
from recovery_hub.sitemaps import sitemaps
from apps.accounts.admin_dashboard import engagement_dashboard, ab_test_results

urlpatterns = [
    # Redirects for common 404 sources (old URLs, common crawl patterns)
    path('accounts/signup/', RedirectView.as_view(pattern_name='accounts:register', permanent=True)),
    path('signup/', RedirectView.as_view(pattern_name='accounts:register', permanent=True)),
    path('register/', RedirectView.as_view(pattern_name='accounts:register', permanent=True)),
    path('login/', RedirectView.as_view(pattern_name='accounts:login', permanent=True)),
    path('feed/', RedirectView.as_view(pattern_name='accounts:social_feed', permanent=True)),
    path('dashboard/', RedirectView.as_view(pattern_name='accounts:dashboard', permanent=True)),
    path('profile/', RedirectView.as_view(pattern_name='accounts:dashboard', permanent=True)),
    # Short paths users/search engines might try
    path('community/', RedirectView.as_view(pattern_name='accounts:community', permanent=True)),
    path('groups/', RedirectView.as_view(pattern_name='accounts:groups', permanent=True)),
    path('meetings/', RedirectView.as_view(url='/support/meetings/', permanent=True)),
    path('coach/', RedirectView.as_view(pattern_name='accounts:recovery_coach', permanent=True)),
    path('ai-coach/', RedirectView.as_view(pattern_name='accounts:recovery_coach', permanent=True)),
    path('pricing/', RedirectView.as_view(pattern_name='accounts:pricing', permanent=True)),
    path('home/', RedirectView.as_view(url='/', permanent=True)),
    # 404s reported in Google Search Console (July 2026)
    path('pages/home/', RedirectView.as_view(url='/', permanent=True)),
    path('delete/', RedirectView.as_view(url='/', permanent=True)),
    path('edit/', RedirectView.as_view(url='/', permanent=True)),
    path('accounts/milestone/', RedirectView.as_view(url='/accounts/milestone-badge/', permanent=True)),
    # Short URL used in court-compliance outreach emails
    path('court-compliance/', RedirectView.as_view(pattern_name='core:court_ordered_meeting_tracker', permanent=True)),

    # Custom admin dashboards (must be before admin.site.urls)
    path('admin/dashboard/ab-tests/', ab_test_results, name='admin_ab_test_results'),
    path('admin/dashboard/', engagement_dashboard, name='admin_engagement_dashboard'),
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('blog/', include('apps.blog.urls', namespace='blog')),
    path('journal/', include('apps.journal.urls', namespace='journal')),
    path('resources/', include('resources.urls', namespace='resources')),
    path('newsletter/', include('apps.newsletter.urls', namespace='newsletter')),
    path('store/', include('apps.store.urls', namespace='store')),
    path('support/', include('apps.support_services.urls')),
    path('summernote/', include('django_summernote.urls')),
    # SEO files
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt_view, name='robots'),
    path('verify/court/<str:hash_value>/', verify_court_report, name='verify_court_report'),
    path('email/unsubscribe/<str:token>/', unsubscribe_marketing, name='unsubscribe_marketing'),
    path('email/cold-outreach-unsubscribe/', cold_outreach_unsubscribe, name='cold_outreach_unsubscribe'),
    path('ads.txt', ads_txt_view, name='ads'),
    # Add allauth URLs if using django-allauth
    path('accounts/', include('allauth.urls')),
]

# Debug toolbar URLs (only in development)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Serve media files and static files in development
if settings.DEBUG:
    # Media files (user uploads)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

    # Static files - simplified approach
    # Django automatically serves from STATICFILES_DIRS in DEBUG mode,
    # but we can be explicit for clarity
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)

# Handler pages for errors - custom error pages for better UX
handler404 = 'apps.core.views.custom_404'
handler500 = 'apps.core.views.custom_500'
handler403 = 'apps.core.views.custom_403'
handler400 = 'apps.core.views.custom_400'
