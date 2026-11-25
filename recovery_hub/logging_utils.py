"""Logging helpers used by settings.LOGGING (web and celery-worker).

Railway marks every line written to stderr as level "error", so routine
records go to stdout and only ERROR and above go to stderr. Every line is
also passed through ``mask_emails`` so an address that reaches a log message
or a traceback comes out as r***@gmail.com.
"""
import logging
import re

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)')


def mask_emails(text):
    return EMAIL_RE.sub(r'\1***@\2', text)


class RedactingFormatter(logging.Formatter):
    """Formats the whole record (message, args, traceback), then masks emails."""

    def format(self, record):
        return mask_emails(super().format(record))


class BelowErrorFilter(logging.Filter):
    """Lets through DEBUG to WARNING, so ERROR+ is left to the stderr handler."""

    def filter(self, record):
        return record.levelno < logging.ERROR
