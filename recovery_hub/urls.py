# recovery_hub/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls', namespace='core')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('blog/', include('apps.blog.urls', namespace='blog')),
    path('journal/', include('apps.journal.urls', namespace='journal')),
    path('resources/', include('resources.urls', namespace='resources')),
    path('newsletter/', include('apps.newsletter.urls', namespace='newsletter')),
    path('store/', include('apps.store.urls', namespace='store')),
    path('support/', include('apps.support_services.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
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

# Handler pages for errors (optional but recommended)
#handler404 = 'apps.core.views.custom_404'
#handler500 = 'apps.core.views.custom_500'
#handler403 = 'apps.core.views.custom_403'
#handler400 = 'apps.core.views.custom_400'
