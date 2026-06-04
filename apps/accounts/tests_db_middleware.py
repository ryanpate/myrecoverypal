# apps/accounts/tests_db_middleware.py
"""Tests for DatabaseConnectionMiddleware mid-request retry.

Django wraps each middleware's get_response with convert_exception_to_response,
so a view/template that raises InterfaceError is turned into a 500 *response*
before it reaches the middleware __call__ — it never propagates as an exception.
The middleware therefore cannot rely on catching the exception in __call__; it
must detect the failure another way (a flag set by process_exception) and retry.
"""
from unittest import mock

from django.db import InterfaceError
from django.http import HttpResponse
from django.test import SimpleTestCase

from apps.accounts.middleware import DatabaseConnectionMiddleware


class _Request:
    """Minimal stand-in for an HttpRequest (middleware never touches the DB on it)."""


class DatabaseConnectionRetryTest(SimpleTestCase):
    @mock.patch.object(DatabaseConnectionMiddleware, '_close_all_connections')
    @mock.patch('apps.accounts.middleware.connection')
    @mock.patch('apps.accounts.middleware.close_old_connections')
    @mock.patch('time.sleep', return_value=None)
    def test_retries_after_mid_request_connection_drop(
        self, _sleep, _close_old, _conn, _close_all
    ):
        calls = {'n': 0}
        mw_holder = {}

        def downstream(request):
            """Emulate Django: view raises -> process_exception called -> 500 response."""
            calls['n'] += 1
            try:
                if calls['n'] == 1:
                    # First render hits a dead connection (e.g. lazy user.subscription query)
                    raise InterfaceError('connection already closed')
                return HttpResponse('OK', status=200)
            except Exception as exc:
                mw_holder['mw'].process_exception(request, exc)
                return HttpResponse('Server Error', status=500)

        mw = DatabaseConnectionMiddleware(downstream)
        mw_holder['mw'] = mw

        response = mw(_Request())

        self.assertEqual(calls['n'], 2, "view should be retried once after the drop")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')

    @mock.patch.object(DatabaseConnectionMiddleware, '_close_all_connections')
    @mock.patch('apps.accounts.middleware.connection')
    @mock.patch('apps.accounts.middleware.close_old_connections')
    def test_healthy_request_is_not_retried(self, _close_old, _conn, _close_all):
        calls = {'n': 0}

        def good_view(request):
            calls['n'] += 1
            return HttpResponse('OK', status=200)

        mw = DatabaseConnectionMiddleware(good_view)
        response = mw(_Request())

        self.assertEqual(calls['n'], 1, "a healthy request must not be retried")
        self.assertEqual(response.status_code, 200)

    @mock.patch.object(DatabaseConnectionMiddleware, '_close_all_connections')
    @mock.patch('apps.accounts.middleware.connection')
    @mock.patch('apps.accounts.middleware.close_old_connections')
    @mock.patch('time.sleep', return_value=None)
    def test_persistent_drop_returns_500_after_giving_up(
        self, _sleep, _close_old, _conn, _close_all
    ):
        calls = {'n': 0}
        mw_holder = {}

        def always_dead(request):
            calls['n'] += 1
            try:
                raise InterfaceError('connection already closed')
            except Exception as exc:
                mw_holder['mw'].process_exception(request, exc)
                return HttpResponse('Server Error', status=500)

        mw = DatabaseConnectionMiddleware(always_dead)
        mw_holder['mw'] = mw

        response = mw(_Request())

        # 1 initial + 3 retries
        self.assertEqual(calls['n'], 1 + len(DatabaseConnectionMiddleware.BACKOFF_DELAYS))
        self.assertEqual(response.status_code, 500)
