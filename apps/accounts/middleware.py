import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import connection, OperationalError, InterfaceError

User = get_user_model()
logger = logging.getLogger(__name__)


class DatabaseConnectionMiddleware:
    """
    Middleware to ensure database connections are healthy before processing requests.

    This fixes "connection already closed" errors that occur when Railway's PostgreSQL
    proxy terminates idle connections, but Django still holds a reference to them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the connection is usable before processing the request
        self._ensure_connection()

        response = self.get_response(request)
        return response

    def _ensure_connection(self):
        """
        Verify the database connection is alive, close it if stale.
        Django will automatically create a new connection when needed.
        """
        try:
            # Try a simple query to test the connection
            connection.ensure_connection()
            if connection.connection is not None:
                connection.connection.cursor().execute('SELECT 1')
        except (OperationalError, InterfaceError) as e:
            # Connection is dead, close it so Django creates a fresh one
            logger.warning(f"Stale database connection detected, closing: {e}")
            connection.close()

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