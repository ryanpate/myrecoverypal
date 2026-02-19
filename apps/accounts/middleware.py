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

    def __call__(self, request):
        # Close stale connections before processing
        close_old_connections()

        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        If a database connection dies mid-request, close all connections
        so the next request starts fresh.
        """
        if isinstance(exception, (OperationalError, InterfaceError)):
            logger.warning(f"Database connection error during request: {exception}")
            for conn in connections.all():
                conn.close()
        return None

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