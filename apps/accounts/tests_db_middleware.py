# apps/accounts/tests_db_middleware.py
"""Tests for DatabaseConnectionMiddleware mid-request retry.

Django wraps each middleware's get_response with convert_exception_to_response,
so a view/template that raises InterfaceError is turned into a 500 *response*
before it reaches the middleware __call__ — it never propagates as an exception.
The middleware therefore cannot rely on catching the exception in __call__; it
must detect the failure another way (a flag set by process_exception) and retry.
"""
import logging
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import InterfaceError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase

from apps.accounts.middleware import DatabaseConnectionMiddleware
from apps.accounts.views import social_feed_view


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


class SocialFeedDropIsNotLoggedTest(TestCase):
    """
    A mid-request connection drop must reach Sentry only as an *exception* event.

    settings._drop_recovered_db_drops filters those out by inspecting
    hint['exc_info'], which only exists for exception events. A view that logs
    its own `logger.error("...")` produces a *message* event with no exc_info,
    so the filter can't see it and the retried-and-recovered request still
    creates a Sentry issue (PYTHON-DJANGO-52).
    """

    def test_connection_drop_propagates_without_an_error_log(self):
        User = get_user_model()
        user = User.objects.create_user(username='feeduser', password='x')

        request = RequestFactory().get('/accounts/social-feed/')
        request.user = user

        records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Capture()
        view_logger = logging.getLogger('apps.accounts.views')
        view_logger.addHandler(handler)
        try:
            with mock.patch.object(
                User, 'get_following', side_effect=InterfaceError('cursor already closed')
            ):
                with self.assertRaises(InterfaceError):
                    social_feed_view(request)
        finally:
            view_logger.removeHandler(handler)

        self.assertEqual(
            [r.getMessage() for r in records if r.levelno >= logging.ERROR],
            [],
            "the view must not log the drop itself — that bypasses the Sentry filter",
        )


class RawPsycopg2DropIsRetriedTest(SimpleTestCase):
    """
    sentry-sdk's SQL instrumentation (CursorWrapper.execute -> _set_db_data ->
    connection.get_dsn_parameters()) runs outside Django's wrap_database_errors,
    so a mid-query drop there raises a *raw* psycopg2.InterfaceError that Django
    never translates. It isn't a django.db.InterfaceError, so it used to bypass
    the retry entirely and 500 the user (PYTHON-DJANGO-51: /accounts/progress/
    returned 500 at 06:25:24 with no retry logged, while a django.db-flavoured
    drop on /support/meetings/ one millisecond earlier retried and served 200).
    """

    @mock.patch.object(DatabaseConnectionMiddleware, '_close_all_connections')
    @mock.patch('apps.accounts.middleware.connection')
    @mock.patch('apps.accounts.middleware.close_old_connections')
    @mock.patch('time.sleep', return_value=None)
    def test_raw_psycopg2_interface_error_is_retried(
        self, _sleep, _close_old, _conn, _close_all
    ):
        import psycopg2

        self.assertNotIsInstance(
            psycopg2.InterfaceError('connection already closed'), InterfaceError,
            "precondition: the raw driver error is not a django.db.InterfaceError",
        )

        calls = {'n': 0}
        mw_holder = {}

        def downstream(request):
            calls['n'] += 1
            try:
                if calls['n'] == 1:
                    raise psycopg2.InterfaceError('connection already closed')
                return HttpResponse('OK', status=200)
            except Exception as exc:
                mw_holder['mw'].process_exception(request, exc)
                return HttpResponse('Server Error', status=500)

        mw = DatabaseConnectionMiddleware(downstream)
        mw_holder['mw'] = mw

        response = mw(_Request())

        self.assertEqual(calls['n'], 2, "a raw psycopg2 drop must be retried too")
        self.assertEqual(response.status_code, 200)
