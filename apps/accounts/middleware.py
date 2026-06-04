import logging
import time
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
    2. Mid-request drops (during processing): retried up to MAX_RETRIES times with
       backoff. Railway's proxy can drop multiple consecutive connections during
       stress, so a single retry isn't enough to keep the UX seamless.

    Mid-request retry can't rely on catching the exception in __call__: Django wraps
    every middleware's get_response in convert_exception_to_response, so a view or
    template that raises OperationalError/InterfaceError (e.g. a lazy
    `user.subscription` query during template render) is turned into a 500 *response*
    before it ever propagates back to this middleware. Instead, process_exception —
    which Django invokes *before* that conversion — records the drop on the request,
    and __call__ checks that flag after get_response returns to decide whether to retry.

    Safe with ATOMIC_REQUESTS=True: when a connection dies mid-view, the COMMIT
    was never sent, so the transaction is implicitly rolled back at the DB level.
    Retrying the view replays the same logic against a fresh connection.
    """

    # Total attempts = 1 initial + len(BACKOFF_DELAYS) retries
    BACKOFF_DELAYS = (0.1, 0.3, 0.7)

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

        total_attempts = 1 + len(self.BACKOFF_DELAYS)
        for attempt in range(total_attempts):
            # Reset the per-attempt drop flag; process_exception sets it if the
            # downstream view/template hits a dead connection.
            request._db_connection_dropped = None
            response = None
            try:
                response = self.get_response(request)
            except (OperationalError, InterfaceError) as e:
                # Defensive: some response paths (streaming, etc.) can still let the
                # error propagate as an exception rather than going through
                # process_exception. Treat it the same way.
                self._close_all_connections()
                dropped = e
            else:
                # Normal path: Django already converted any view/template DB error
                # into the response and called process_exception (below), which
                # records the drop on the request.
                dropped = getattr(request, '_db_connection_dropped', None)
                if dropped is None:
                    return response

            if attempt < len(self.BACKOFF_DELAYS):
                delay = self.BACKOFF_DELAYS[attempt]
                logger.warning(
                    "Database connection lost mid-request (attempt %d/%d): %s. Retrying in %.2fs",
                    attempt + 1, total_attempts, dropped, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Database connection lost after %d attempts, giving up: %s",
                    total_attempts, dropped,
                )
                if response is not None:
                    # The 500 response Django already built for this request.
                    return response
                raise dropped

    def process_exception(self, request, exception):
        """
        If a database connection dies mid-request, record it on the request so
        __call__ can retry, and close all connections so the retry (and the next
        request) starts fresh.
        """
        if isinstance(exception, (OperationalError, InterfaceError)):
            logger.warning("Database connection error during request: %s", exception)
            request._db_connection_dropped = exception
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