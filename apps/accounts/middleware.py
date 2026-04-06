import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections, OperationalError, InterfaceError

User = get_user_model()
logger = logging.getLogger(__name__)


class DatabaseConnectionMiddleware:
    """
    Middleware to handle Railway PostgreSQL proxy connection issues.

    Handles two failure modes:
    1. Stale connections (pre-request): validated via health check before each request
    2. Mid-request drops (during processing): caught via process_exception, connection
       is closed so the next request gets a fresh one
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def _close_all_connections(self):
        """Force-close all database connections so Django opens fresh ones."""
        for conn in connections.all():
            try:
                conn.close()
            except Exception:
                pass
            # If conn.close() failed to clear the underlying connection
            # (e.g. psycopg2 raises on an already-dead socket), null it out
            # so Django doesn't try to reuse it.
            if conn.connection is not None:
                try:
                    conn.connection.close()
                except Exception:
                    pass
                conn.connection = None

    def __call__(self, request):
        # Validate existing connections — closes those past conn_max_age
        close_old_connections()

        # Proactively verify the default connection is alive.
        # Railway's proxy can kill idle connections before conn_max_age expires.
        try:
            connection.ensure_connection()
        except (OperationalError, InterfaceError):
            logger.warning("Stale database connection detected pre-request, reconnecting")
            self._close_all_connections()

        try:
            response = self.get_response(request)
        except (OperationalError, InterfaceError) as e:
            # Connection died mid-request — close all and retry once
            logger.warning("Database connection lost mid-request (%s), retrying", e)
            self._close_all_connections()
            response = self.get_response(request)

        return response

    def process_exception(self, request, exception):
        """
        If a database connection dies mid-request, close all connections
        so the next request starts fresh.
        """
        if isinstance(exception, (OperationalError, InterfaceError)):
            logger.warning("Database connection error during request: %s", exception)
            self._close_all_connections()
        return None

class NoCacheHTMLMiddleware:
    """
    Set Cache-Control: no-cache on HTML responses so WKWebView
    (Capacitor iOS) always fetches fresh pages from the server.
    Static assets are unaffected (served by WhiteNoise with 1-year cache).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        if 'text/html' in content_type:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response


class SEONoIndexMiddleware:
    """
    Add X-Robots-Tag: noindex on pages that should not be indexed:
    - Login/register with ?next= parameters (creates infinite URL variants)
    - Any /accounts/ page behind auth (dashboard, profile, etc.)
    - Blog tag/category pages (thin listing pages, 81 in GSC "not indexed")
    - Any blog URL with ?filter= or ?page= params (near-duplicate content)
    - Support service filter pages
    Only affects crawlers — transparent to users.
    """
    NOINDEX_PREFIXES = (
        '/accounts/dashboard',
        '/accounts/edit-profile',
        '/accounts/messages',
        '/accounts/notifications',
        '/accounts/milestones',
        '/accounts/social-feed',
        '/accounts/progress',
        '/accounts/recovery-coach',
        '/accounts/subscription',
        '/journal/',
        '/admin/',
        '/blog/tag/',         # Thin tag listing pages (24 base + 73 filter variants)
        '/blog/category/',    # Thin category listing pages (7 base + 8 filter variants)
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path

        # Noindex login/register with ?next= query params
        if path in ('/accounts/login/', '/accounts/register/') and request.GET.get('next'):
            response['X-Robots-Tag'] = 'noindex, nofollow'
            return response

        # Noindex blog/support pages with filter/page query params
        if (path.startswith('/blog/') or path.startswith('/support/')) and (
            request.GET.get('filter') or request.GET.get('page') or request.GET.get('type')
        ):
            response['X-Robots-Tag'] = 'noindex, nofollow'
            return response

        # Noindex pages matching prefix list
        for prefix in self.NOINDEX_PREFIXES:
            if path.startswith(prefix):
                response['X-Robots-Tag'] = 'noindex, nofollow'
                return response

        return response


class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated:
            # Update last activity every 2 minutes to avoid too many DB writes
            if not request.user.last_activity or \
               (timezone.now() - request.user.last_activity).seconds > 120:
                User.objects.filter(id=request.user.id).update(
                    last_activity=timezone.now()
                )
        
        return response