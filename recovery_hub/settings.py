"""
Django settings for recovery_hub project.
"""
import ssl
from celery.schedules import crontab
import os
from pathlib import Path
import dj_database_url
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.up.railway.app',  # Railway subdomain
    'myrecoverypal.com',
    'www.myrecoverypal.com',
    '.myrecoverypal.com',
]

CSRF_TRUSTED_ORIGINS = [
    'https://*.up.railway.app',
    'https://myrecoverypal.com',
    'https://www.myrecoverypal.com',
]

# Add any additional hosts from environment
extra_hosts = os.environ.get('ALLOWED_HOSTS', '')
if extra_hosts:
    ALLOWED_HOSTS.extend([h.strip()
                         for h in extra_hosts.split(',') if h.strip()])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',  # Add before django.contrib.staticfiles
    'django.contrib.staticfiles',
    'cloudinary',  # Add after staticfiles
    'django.contrib.sites',
    'django.contrib.humanize',

    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework',
    'corsheaders',
    'storages',

    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.blog',
    'resources',  # FIXED: Changed from 'apps.resources' to 'resources'
    'apps.journal',
    'apps.store',
    'apps.newsletter',
    'apps.support_services',
    'django.contrib.sitemaps',
    'django_summernote',

    # PWA Support (optional - install with: pip install django-pwa)
    # 'pwa',
]

# Add debug toolbar in development
if DEBUG:
    try:
        import debug_toolbar
        import django_extensions
        INSTALLED_APPS += ['debug_toolbar', 'django_extensions']
    except ImportError:
        pass  # These packages might not be installed

SITE_ID = 1
SITE_DOMAIN = 'www.myrecoverypal.com'
SITE_URL = f'https://{SITE_DOMAIN}'

# SEO Defaults
SEO_DEFAULT_TITLE = "MyRecoveryPal - Your Recovery Support Community"
SEO_DEFAULT_DESCRIPTION = "Join MyRecoveryPal, a supportive community for individuals in recovery. Track milestones, connect with peers, journal your journey, and access recovery resources."
SEO_DEFAULT_KEYWORDS = "recovery support, addiction recovery, sobriety tracker, recovery community, peer support"

# Social Media
TWITTER_HANDLE = "@myrecoverypal"
FACEBOOK_PAGE = "https://www.facebook.com/myrecoverypal"
INSTAGRAM_HANDLE = "@myrecoverypal"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise for static files
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# Add debug toolbar middleware in development
if DEBUG:
    try:
        import debug_toolbar
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1']
    except ImportError:
        pass

ROOT_URLCONF = 'recovery_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Add PWA context processor if using django-pwa
                # 'pwa.context_processors.pwa',
            ],
        },
    },
]

WSGI_APPLICATION = 'recovery_hub.wsgi.application'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')

# Only configure database if DATABASE_URL exists
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,  # Added connection health checks
        )
    }
    # Add optimizations for PostgreSQL
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
    }
    # Enable atomic requests for better transaction handling
    DATABASES['default']['ATOMIC_REQUESTS'] = True
else:
    # Use SQLite as fallback (for build phase and local dev)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Login URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:dashboard'
LOGOUT_REDIRECT_URL = 'core:index'

# Django-allauth settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
# Set to 'mandatory' when email is configured
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_USERNAME_REQUIRED = False

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# FIXED: Ensure STATICFILES_DIRS points to the correct location
if os.path.exists(BASE_DIR / 'static'):
    STATICFILES_DIRS = [
        BASE_DIR / 'static',
    ]
else:
    STATICFILES_DIRS = []

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# WhiteNoise for serving static files - Fixed to avoid DRF issues
# Changed from CompressedManifestStaticFilesStorage
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'

# WhiteNoise settings
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

# Only set WHITENOISE_ROOT if the directory exists
if os.path.exists(BASE_DIR / 'root_files'):
    WHITENOISE_ROOT = BASE_DIR / 'root_files'

# Disable these for now to avoid issues
WHITENOISE_KEEP_ONLY_HASHED_FILES = False
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp',
                                       'zip', 'gz', 'tgz', 'bz2', 'tbz', 'xz', 'br', 'swf', 'flv', 'woff', 'woff2']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Cloudinary configuration - Simplified to avoid signature issues
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
    'SECURE': True,  # Use HTTPS
}

# CKEditor Configuration
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 400,
        'width': '100%',
        'toolbar_Custom': [
            {'name': 'document', 'items': [
                'Source', '-', 'Save', 'Preview', 'Print']},
            {'name': 'clipboard', 'items': [
                'Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': [
                'Find', 'Replace', '-', 'SelectAll']},
            {'name': 'basicstyles', 'items': [
                'Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-',
                                            'Blockquote', 'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': [
                'Image', 'Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            {'name': 'styles', 'items': [
                'Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks']},
        ],
        'extraPlugins': ','.join([
            'uploadimage',
            'div',
            'autolink',
            'autoembed',
            'embedsemantic',
            'autogrow',
            'widget',
            'lineutils',
            'clipboard',
            'dialog',
            'dialogui',
            'elementspath',
            'pastefromword',
        ]),
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'autoParagraph': False,
        'enterMode': 2,  # ENTER_BR
    }
}

# Allow iframe and other HTML elements for Medium embeds
CKEDITOR_ALLOW_NONIMAGE_FILES = True

SUMMERNOTE_CONFIG = {
    'summernote': {
        'width': '100%',
        'height': '400',
        'toolbar': [
            ['style', ['style']],
            ['font', ['bold', 'underline', 'italic', 'clear']],
            ['fontname', ['fontname']],
            ['fontsize', ['fontsize']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['height', ['height']],
            ['table', ['table']],
            ['insert', ['link', 'picture', 'video', 'hr']],
            ['view', ['fullscreen', 'codeview', 'help']],
            ['misc', ['undo', 'redo']],
        ],
        'styleTags': ['p', 'blockquote', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
        'fontNames': ['Arial', 'Georgia', 'Times New Roman', 'Verdana'],
        'codemirror': {
            'mode': 'htmlmixed',
            'lineNumbers': True,
            'theme': 'monokai',
        },
        'cleaner': {
            'notTimeOut': 2400,
            'action': 'paste',
            'keepHtml': True,
            'keepClasses': True,
            'badTags': ['script', 'applet'],
            'badAttributes': ['onclick', 'onerror'],
        },
    }
}

# Only use Cloudinary if credentials are provided
if os.environ.get('CLOUDINARY_CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

    # Simplified configuration to avoid signature errors
    CLOUDINARY_STORAGE.update({
        'FOLDER': 'myrecoverypal',  # Simple folder without subfolders
        'OVERWRITE': True,  # Overwrite files with same name
        'RESOURCE_TYPE': 'auto',  # Auto-detect resource type
    })

    # Initialize cloudinary
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
        secure=True
    )

# Session configuration for better performance
SESSION_SAVE_EVERY_REQUEST = False if not DEBUG else True

# ========================================
# PWA (Progressive Web App) Settings
# ========================================

PWA_APP_NAME = 'MyRecoveryPal'
PWA_APP_DESCRIPTION = "Your Journey to Recovery Starts Here"
PWA_APP_THEME_COLOR = '#1e4d8b'
PWA_APP_BACKGROUND_COLOR = '#f8f9fa'
PWA_APP_DISPLAY = 'standalone'
PWA_APP_SCOPE = '/'
PWA_APP_ORIENTATION = 'any'
PWA_APP_START_URL = '/'
PWA_APP_STATUS_BAR_COLOR = 'default'
PWA_APP_ICONS = [
    {
        'src': '/static/images/icon-192.png',
        'sizes': '192x192',
        'type': 'image/png',
        'purpose': 'any maskable'
    },
    {
        'src': '/static/images/icon-512.png',
        'sizes': '512x512',
        'type': 'image/png',
        'purpose': 'any maskable'
    }
]
PWA_APP_ICONS_APPLE = [
    {
        'src': '/static/images/icon-180.png',
        'sizes': '180x180'
    }
]
PWA_APP_SPLASH_SCREEN = [
    {
        'src': '/static/images/splash-640x1136.png',
        'media': '(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)'
    }
]
PWA_APP_DIR = 'ltr'
PWA_APP_LANG = 'en-US'
PWA_APP_SHORTCUTS = [
    {
        "name": "Daily Journal",
        "url": "/journal/",
        "description": "Write in your recovery journal",
        "icon": "/static/images/journal-icon.png"
    },
    {
        "name": "Find Meetings",
        "url": "/support/meetings/",
        "description": "Find recovery meetings near you",
        "icon": "/static/images/meeting-icon.png"
    },
    {
        "name": "Crisis Help",
        "url": "/support/crisis/",
        "description": "Get immediate crisis support",
        "icon": "/static/images/crisis-icon.png"
    }
]
PWA_APP_SCREENSHOTS = [
    {
        'src': '/static/images/screenshot1.png',
        'type': 'image/png',
        'sizes': '540x720'
    },
    {
        'src': '/static/images/screenshot2.png',
        'type': 'image/png',
        'sizes': '540x720'
    }
]
PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'static', 'service-worker.js')
PWA_APP_DEBUG_MODE = DEBUG

# ========================================
# Mobile App Configuration
# ========================================

# Mobile-specific settings
MOBILE_APP_IOS_APP_ID = 'com.myrecoverypal.app'
MOBILE_APP_ANDROID_APP_ID = 'com.myrecoverypal.app'
MOBILE_APP_APPLE_MOBILE_WEB_APP_CAPABLE = True
MOBILE_APP_APPLE_MOBILE_WEB_APP_STATUS_BAR_STYLE = 'default'
MOBILE_APP_APPLE_MOBILE_WEB_APP_TITLE = 'RecoveryPal'

# Apple Smart App Banner (for promoting iOS app if you have one)
# MOBILE_APP_IOS_APP_STORE_ID = 'your-app-store-id'

# Android App Links
# MOBILE_APP_ANDROID_PACKAGE = 'com.myrecoverypal.app'
# MOBILE_APP_ANDROID_APP_NAME = 'MyRecoveryPal'

# ========================================
# Email Configuration - Flexible for Any Provider
# ========================================

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')  # ✅ From env
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))  # ✅ From env
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'  # ✅ From env
EMAIL_USE_SSL = os.environ.get(
    'EMAIL_USE_SSL', 'False') == 'True'  # ✅ From env
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'apikey')  # ✅ From env
EMAIL_HOST_PASSWORD = os.environ.get(
    'EMAIL_HOST_PASSWORD', '')  # ✅ Correct var name
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'MyRecoveryPal <noreply@myrecoverypal.com>'
)  # ✅ From env
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', DEFAULT_FROM_EMAIL)  # ✅ From env

# Email timeout settings
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '30'))

# Site URL for email links - FIXED
SITE_URL = os.environ.get('SITE_URL', 'https://myrecoverypal.com')  # ✅ Fixed!

# Email debug settings (only in development)
if DEBUG:
    # Uncomment below to print emails to console instead of sending (for testing)
    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    pass

# Fail silently in development, raise errors in production
EMAIL_FAIL_SILENTLY = DEBUG

# SSL Configuration for Email

# Try to use certifi for certificate verification
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
except ImportError:
    pass  # certifi not installed, will use system certificates

# ========================================
# CORS and CSRF Settings
# ========================================

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://myrecoverypal.com',
    'https://www.myrecoverypal.com',
]

if DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:8000',
        'http://localhost:3000',
        'http://127.0.0.1:8000',
        'http://127.0.0.1:3000',
    ])

# Allow CORS for PWA to work properly
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

# CSRF settings (already defined at top, but adding extras here)
# Parse additional CSRF origins from environment
extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if extra_csrf:
    CSRF_TRUSTED_ORIGINS.extend([o.strip()
                                for o in extra_csrf.split(',') if o.strip()])

# ========================================
# Security Settings
# ========================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Additional security headers for mobile apps
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    SECURE_REFERRER_POLICY = 'same-origin'

# Content Security Policy (CSP) for PWA
# Only enable if you need strict CSP (may break some features)
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", 'cdn.jsdelivr.net', 'kit.fontawesome.com')
# CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", 'cdn.jsdelivr.net', 'fonts.googleapis.com')
# CSP_FONT_SRC = ("'self'", 'fonts.gstatic.com', 'kit.fontawesome.com')
# CSP_IMG_SRC = ("'self'", 'data:', 'https:')
# CSP_CONNECT_SRC = ("'self'",)
# CSP_FRAME_ANCESTORS = ("'none'",)
# CSP_BASE_URI = ("'self'",)
# CSP_FORM_ACTION = ("'self'",)

# ========================================
# Cache Configuration
# ========================================

# Redis/Celery Configuration (if using Railway Redis)
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {'max_connections': 50},
            }
        }
    }

    # Add PWA cache configuration
    CACHES['pwa_cache'] = {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'pwa',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
else:
    # Fallback to local memory cache if Redis not available
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        },
        'pwa_cache': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'pwa-cache',
        }
    }

# ========================================
# Celery Settings
# ========================================

CELERY_BEAT_SCHEDULE = {
    'send-scheduled-newsletters': {
        'task': 'apps.newsletter.tasks.send_scheduled_newsletters',
        'schedule': crontab(minute='*/15'),  # Check every 15 minutes
    },
}

# ========================================
# API Keys and External Services
# ========================================

# API Keys from environment
GOOGLE_API_KEY = os.environ.get(
    'GOOGLE_API_KEY', 'AIzaSyAKFMk5grddW39DgsQ9NZ0CI62emQaleys')
MAPBOX_API_KEY = os.environ.get(
    'MAPBOX_API_KEY', 'pk.eyJ1IjoicnlhbnBhdGUxIiwiYSI6ImNtZXd6cTQ1ejB4ajgyam9uZzNxazhvanMifQ.9oqD8jZ6rrhEjQtnO6TsgA')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')

# Push Notification Services (optional)
# FCM_SERVER_KEY = os.environ.get('FCM_SERVER_KEY', '')
# APNS_CERTIFICATE = os.environ.get('APNS_CERTIFICATE', '')

# ========================================
# Django REST Framework Configuration
# ========================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,

    # Mobile app optimizations
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}

# ========================================
# Logging Configuration
# ========================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',  # Changed to verbose for better debugging
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'mail_handler': {  # NEW: Dedicated handler for email logs
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if os.path.exists(BASE_DIR / 'logs') else ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.core.mail': {  # NEW: Email-specific logger
            'handlers': ['console', 'mail_handler'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps.accounts': {  # NEW: Your accounts app logger
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
if not os.path.exists(BASE_DIR / 'logs'):
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)
# Create logs directory if it doesn't exist
if not os.path.exists(BASE_DIR / 'logs'):
    os.makedirs(BASE_DIR / 'logs', exist_ok=True)
