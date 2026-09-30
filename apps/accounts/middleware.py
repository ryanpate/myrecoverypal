import logging
import time
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.db import close_old_connections, connection, connections, OperationalError, InterfaceError

User = get_user_model()
logger = logging.getLogger(__name__)

# Django normally translates psycopg2 errors into django.db.* ones via
# wrap_database_errors. sentry-sdk's SQL instrumentation doesn't go through it:
# its CursorWrapper.execute calls _set_db_data() ->
# connection.get_dsn_parameters(), so a mid-query connection drop can surface as
# the *raw* psycopg2 error instead. That one isn't a django.db.InterfaceError, so
# it used to slip past the retry below and 500 the user (Sentry
# PYTHON-DJANGO-51, /accounts/progress/). Match both flavours.
DB_CONNECTION_ERRORS = (OperationalError, InterfaceError)
try:
    import psycopg2
except ImportError:  # sqlite (local dev / build phase)
    pass
else:
    DB_CONNECTION_ERRORS += (psycopg2.OperationalError, psycopg2.InterfaceError)


class HealthCheckMiddleware:
    """Answer Railway's deploy health check (GET /healthz/) before anything
    else runs. The probe is plain HTTP with Host: healthcheck.railway.app, so
    it has to bypass the HTTPS/www redirects and host validation. Without a
    health check Railway switches traffic to a new container as soon as it
    starts — while start.sh is still running migrations — and visitors get
    502s until gunicorn is up."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/healthz/':
            return HttpResponse('ok', content_type='text/plain')
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """Send a Content-Security-Policy header on every response.

    What it buys: scripts, styles, frames, fonts and XHR/fetch targets are
    limited to this site plus the third parties listed below; plugins
    (<object>/<embed>) and <base> hijacking are off; pages can't be framed;
    forms can only post here or on to Stripe.

    What it does NOT buy: protection against injected inline script. The
    templates rely on ~120 inline <script> blocks and ~190 inline on*=
    handlers, so script-src has to keep 'unsafe-inline'. Dropping it means
    moving those handlers into JS files and adding nonces — until then,
    output escaping remains the XSS defence and this header is a second layer.

    When a page starts loading something from a new host it must be added
    here, or browsers will block it (look for "Refused to load" in the
    console). CSP_REPORT_ONLY=true switches to report-only without a deploy.
    """

    DIRECTIVES = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'", "'unsafe-inline'",
            'https://www.googletagmanager.com',           # Google Analytics (gtag.js)
            'https://cdn.jsdelivr.net',                   # Bootstrap bundle, Chart.js
            'https://cdnjs.cloudflare.com',               # CodeMirror in the Summernote editor
            'https://js.stripe.com',                      # Stripe.js on the pricing page
            # Cloudflare Web Analytics beacon. Injected at Cloudflare's edge,
            # so it is in no template and only appears in production.
            'https://static.cloudflareinsights.com',
        ],
        'style-src': [
            "'self'", "'unsafe-inline'",
            'https://cdn.jsdelivr.net', 'https://cdnjs.cloudflare.com',
            'https://fonts.googleapis.com',
        ],
        'font-src': ["'self'", 'data:', 'https://fonts.gstatic.com', 'https://cdnjs.cloudflare.com'],
        # Link-preview cards show images from arbitrary sites; uploads preview as blob:
        'img-src': ["'self'", 'data:', 'blob:', 'https:', 'capacitor://localhost'],
        'media-src': ["'self'", 'blob:', 'https://res.cloudinary.com'],
        'connect-src': [
            "'self'", 'capacitor://localhost',
            'https://*.google-analytics.com', 'https://*.analytics.google.com',
            'https://*.googletagmanager.com', 'https://*.g.doubleclick.net',
            'https://*.google.com',
            'https://api.stripe.com',
            'https://cloudflareinsights.com',             # Cloudflare Web Analytics reports
        ],
        'frame-src': ["'self'", 'https://js.stripe.com', 'https://hooks.stripe.com'],
        'worker-src': ["'self'"],
        'manifest-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        # Checkout and billing-portal views answer a form POST with a redirect
        # to Stripe, and browsers apply form-action to that redirect.
        'form-action': ["'self'", 'https://checkout.stripe.com', 'https://billing.stripe.com'],
        'frame-ancestors': ["'none'"],
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.policy = self._build(self.DIRECTIVES)
        # The Summernote editor is an iframe embedded in our own blog/admin
        # forms, and django-summernote loads jQuery and Bootstrap 3 from CDNs
        # inside it. Those hosts are allowed for the editor pages only.
        editor_cdns = ['https://code.jquery.com', 'https://stackpath.bootstrapcdn.com']
        self.summernote_policy = self._build({
            **self.DIRECTIVES,
            'script-src': self.DIRECTIVES['script-src'] + editor_cdns,
            'style-src': self.DIRECTIVES['style-src'] + editor_cdns,
            'font-src': self.DIRECTIVES['font-src'] + editor_cdns,
            'frame-ancestors': ["'self'"],
        })

    @staticmethod
    def _build(directives):
        return '; '.join(f"{name} {' '.join(values)}" for name, values in directives.items())

    def __call__(self, request):
        response = self.get_response(request)
        header = ('Content-Security-Policy-Report-Only'
                  if getattr(settings, 'CSP_REPORT_ONLY', False)
                  else 'Content-Security-Policy')
        if header not in response:
            response[header] = (self.summernote_policy
                                if request.path.startswith('/summernote/')
                                else self.policy)
        return response


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
        except DB_CONNECTION_ERRORS:
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
            except DB_CONNECTION_ERRORS as e:
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
        if isinstance(exception, DB_CONNECTION_ERRORS):
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

        # Noindex blog/support pages with filter/page query params.
        # The meeting finder's own filters (day/city/state/q/attendance)
        # are included: /support/meetings/ is now in the sitemap, so its
        # filter permutations would otherwise become thin duplicates.
        if (path.startswith('/blog/') or path.startswith('/support/')) and any(
            request.GET.get(param) for param in (
                'filter', 'page', 'type',
                'day', 'city', 'state', 'q', 'attendance',
            )
        ):
            response['X-Robots-Tag'] = 'noindex, nofollow'
            return response

        # Noindex pages matching prefix list
        for prefix in self.NOINDEX_PREFIXES:
            if path.startswith(prefix):
                response['X-Robots-Tag'] = 'noindex, nofollow'
                return response

        return response


class UserTimezoneMiddleware:
    """Activate the authenticated user's stored IANA timezone so
    timezone.localdate() reflects their real local day (streaks/pledges)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz = getattr(getattr(request, 'user', None), 'timezone', '') or ''
        activated = False
        if tz:
            try:
                timezone.activate(tz)
                activated = True
            except Exception:
                timezone.deactivate()
        try:
            return self.get_response(request)
        finally:
            if activated:
                timezone.deactivate()


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