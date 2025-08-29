# recovery_hub/urls.py (or your main urls.py)

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
    # Add other app URLs as needed
]

# Serve media files and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    # Note: Django automatically serves static files in DEBUG mode from STATICFILES_DIRS
    # But if you need to explicitly add it:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT)
