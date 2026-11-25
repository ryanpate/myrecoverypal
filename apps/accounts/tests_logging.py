"""Log output from tasks: right level on the right stream, no email addresses.

Railway labels every stderr line "error", so routine records must reach
stdout and only ERROR+ stderr. Every line is masked by RedactingFormatter.
"""
import io
import logging
import re
from contextlib import contextmanager
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from recovery_hub.logging_utils import mask_emails

EMAIL = re.compile(r'[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9-]+\.[A-Za-z]{2,}')


@contextmanager
def captured_root_streams():
    """Point the configured root handlers (from settings.LOGGING) at buffers."""
    out, err = io.StringIO(), io.StringIO()
    handlers = [h for h in logging.getLogger().handlers if isinstance(h, logging.StreamHandler)]
    old = [(h, h.stream) for h in handlers]
    for h in handlers:
        h.setStream(err if h.level >= logging.ERROR else out)
    try:
        yield out, err
    finally:
        for h, stream in old:
            h.setStream(stream)


class MaskEmailsTests(TestCase):
    def test_masks_local_part_keeps_first_letter_and_domain(self):
        self.assertEqual(mask_emails('sent to ryan.pate@gmail.com ok'), 'sent to r***@gmail.com ok')

    def test_leaves_celery_hostnames_and_redis_urls_alone(self):
        for text in ('celery@20c0982ad61d ready.', 'redis://default:**@redis.railway.internal:6379//'):
            self.assertEqual(mask_emails(text), text)


class TaskLogOutputTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='logtester', email='logtester@gmail.com', password='x')

    def _run_welcome(self, send_result):
        from apps.accounts.tasks import send_welcome_email_day_1
        with mock.patch('apps.accounts.tasks.send_email', return_value=send_result), \
                captured_root_streams() as (out, err):
            send_welcome_email_day_1.apply(args=[self.user.pk])
        return out.getvalue(), err.getvalue()

    def test_routine_task_log_is_info_on_stdout_with_no_email(self):
        out, err = self._run_welcome((True, None))
        self.assertIn(f'Welcome email Day 1 sent to user {self.user.pk}', out)
        self.assertTrue(out.startswith('INFO'), out)
        self.assertEqual(err, '')
        self.assertIsNone(EMAIL.search(out), out)

    def test_failure_is_error_on_stderr_and_an_echoed_address_is_masked(self):
        # Provider errors often echo the recipient back.
        out, err = self._run_welcome((False, 'Resend 422: invalid to logtester@gmail.com'))
        self.assertIn('ERROR', err)
        self.assertIn('l***@gmail.com', err)
        self.assertIsNone(EMAIL.search(out + err), out + err)

    def test_celery_keeps_the_django_logging_config(self):
        self.assertFalse(settings.CELERY_WORKER_HIJACK_ROOT_LOGGER)
