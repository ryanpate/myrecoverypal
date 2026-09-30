# apps/accounts/rate_limiting.py
"""
Rate limiting middleware for MyRecoveryPal
Protects against brute force attacks and API abuse
"""
from django.core.cache import caches
from django.http import HttpResponseForbidden
from django.utils import timezone
import hashlib
import ipaddress
import logging

logger = logging.getLogger(__name__)

# https://www.cloudflare.com/ips/ — CF-Connecting-IP is only believed when the
# request actually arrived from one of these networks.
CLOUDFLARE_NETWORKS = [ipaddress.ip_network(net) for net in (
    '173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22',
    '141.101.64.0/18', '108.162.192.0/18', '190.93.240.0/20', '188.114.96.0/20',
    '197.234.240.0/22', '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13',
    '104.24.0.0/14', '172.64.0.0/13', '131.0.72.0/22',
    '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32', '2405:b500::/32',
    '2405:8100::/32', '2a06:98c0::/29', '2c0f:f248::/32',
)]


def _is_cloudflare(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in CLOUDFLARE_NETWORKS)


# Use the dedicated rate_limiting cache (Redis in production, so counters are
# shared by every gunicorn worker). Falls back to default cache if it is not
# configured.
def get_rate_limit_cache():
    """Get the rate limiting cache, falling back to default if not available."""
    try:
        return caches['rate_limiting']
    except Exception:
        return caches['default']


class RateLimitMiddleware:
    """
    Simple rate limiting middleware using Django cache
    Limits requests per IP address
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip rate limiting for static files
        if request.path.startswith('/static/'):
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)

        # Different limits for different endpoints. Login and registration
        # count submitted attempts (POST), not page views.
        if request.path.startswith(('/accounts/login/', '/admin/login/')):
            if request.method == 'POST' and not self.check_rate_limit(ip, 'login', max_requests=5, window=300):  # 5 per 5 min
                return HttpResponseForbidden('Too many login attempts. Please try again in 5 minutes.')

        elif request.path.startswith('/accounts/register/'):
            if request.method == 'POST' and not self.check_rate_limit(ip, 'register', max_requests=3, window=3600):  # 3 per hour
                return HttpResponseForbidden('Too many registration attempts. Please try again later.')

        elif request.path.startswith('/accounts/password-reset/'):
            if request.method == 'POST' and not self.check_rate_limit(ip, 'password_reset', max_requests=5, window=3600):  # 5 per hour
                return HttpResponseForbidden('Too many password reset requests. Please try again later.')

        elif request.path.startswith('/api/'):
            if not self.check_rate_limit(ip, 'api', max_requests=100, window=60):  # 100 per minute
                return HttpResponseForbidden('API rate limit exceeded. Please slow down.')

        return self.get_response(request)

    def get_client_ip(self, request):
        """Get client IP address from request.

        Railway's edge rewrites X-Forwarded-For so its first entry is the
        address that connected to Railway — normally a Cloudflare node, since
        the site is proxied. The visitor's own address is then in
        CF-Connecting-IP, which anyone can forge by skipping Cloudflare and
        hitting the origin directly, so it only counts when the peer really
        is Cloudflare.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            peer = x_forwarded_for.split(',')[0].strip()
        else:
            peer = request.META.get('REMOTE_ADDR')
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip and _is_cloudflare(peer):
            return cf_connecting_ip.strip()
        return peer

    def check_rate_limit(self, identifier, action, max_requests, window):
        """
        Check if rate limit is exceeded

        Args:
            identifier: Unique identifier (IP address)
            action: Type of action (login, register, api)
            max_requests: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            # Use dedicated rate limiting cache
            rate_cache = get_rate_limit_cache()
            cache_key = f'rate_limit:{action}:{hashlib.md5(identifier.encode()).hexdigest()}'

            # Get current count
            current = rate_cache.get(cache_key, 0)

            if current >= max_requests:
                return False

            # Increment counter
            if current == 0:
                # First request - set with expiry
                rate_cache.set(cache_key, 1, window)
            else:
                # Increment existing counter
                try:
                    rate_cache.incr(cache_key)
                except ValueError:
                    # Key expired between get and incr, reset it
                    rate_cache.set(cache_key, 1, window)

            return True
        except Exception as e:
            # If cache fails, allow the request through
            # This ensures the site stays functional even if cache backend is down
            logger.warning(f'Rate limiting cache error: {e}. Allowing request through.')
            return True
