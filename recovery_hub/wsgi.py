"""
WSGI config for recovery_hub project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'recovery_hub.settings.production')

application = get_wsgi_application()
