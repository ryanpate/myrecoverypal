# apps/accounts/rate_limiting.py
"""
Rate limiting middleware for MyRecoveryPal
Protects against brute force attacks and API abuse
"""
from django.core.cache import caches
from django.http import HttpResponseForbidden
from django.utils import timezone
import hashlib
import logging

logger = logging.getLogger(__name__)

# Use dedicated rate_limiting cache to avoid Redis dependency
# Falls back to default cache if rate_limiting cache not configured
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
        # Skip rate limiting for admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)

        # Different limits for different endpoints
        if request.path.startswith('/accounts/login/'):
            if not self.check_rate_limit(ip, 'login', max_requests=5, window=300):  # 5 per 5 min
                return HttpResponseForbidden('Too many login attempts. Please try again in 5 minutes.')

        elif request.path.startswith('/accounts/register/'):
            if not self.check_rate_limit(ip, 'register', max_requests=3, window=3600):  # 3 per hour
                return HttpResponseForbidden('Too many registration attempts. Please try again later.')

        elif request.path.startswith('/api/'):
            if not self.check_rate_limit(ip, 'api', max_requests=100, window=60):  # 100 per minute
                return HttpResponseForbidden('API rate limit exceeded. Please slow down.')

        return self.get_response(request)

    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

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
            # Use dedicated rate limiting cache (local memory, not Redis)
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
