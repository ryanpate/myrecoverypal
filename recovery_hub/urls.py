# recovery_hub/urls.py (or your main urls.py)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('blog/', include('apps.blog.urls')),
    path('journal/', include('apps.journal.urls')),
    path('resources/', include('resources.urls')),  # Add this line
    path('newsletter/', include('apps.newsletter.urls')),
    path('store/', include('apps.store.urls')),
    # Add other app URLs as needed
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
