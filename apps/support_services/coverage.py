"""Recording searches the directory could not answer.

See CoverageRequest for why this exists and why no user is attached.
"""
import logging
import re

from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

# Long enough to be a real place name, short enough to reject junk. Bots
# were ~48% of GA4 traffic and must not be allowed to grow the table.
MIN_QUERY_LEN = 2
MAX_QUERY_LEN = 120

_ZIP_RE = re.compile(r'\b(\d{5})(?:-\d{4})?\b')

# Place names and meeting names use letters, digits, spaces and a little
# punctuation ("o'fallon mo", "omaha,ne", "10:10 meeting", "st. louis").
# Anything else, and any SQL fragment, is a vulnerability scanner: they made
# up 93 of the table's first 113 rows. (The ORM parameterises the search, so
# the probes are harmless; this just keeps them out of the demand ranking.)
_ALLOWED_RE = re.compile(r"^[\w\s,.'’#&/:-]+$")
_SQL_RE = re.compile(
    r"(--|/\*|\b(select|union|insert|update|delete|drop|sleep|benchmark|extractvalue|"
    r"updatexml|concat|waitfor|information_schema|order\s+by|null)\b)",
    re.IGNORECASE)


def is_plausible_query(query):
    """True if `query` could be a real place or meeting search."""
    normalised = (query or '').strip().lower()
    if not normalised or not _ALLOWED_RE.match(normalised) or _SQL_RE.search(normalised):
        return False
    compact = normalised.replace(' ', '').replace('-', '')
    if compact.isdigit() and len(compact) not in (5, 9):  # ZIP, ZIP+4 or a Zoom ID
        return False
    return True


def record_coverage_gap(query):
    """Note that `query` returned no meetings. Never raises."""
    try:
        normalised = (query or '').strip().lower()
        if not (MIN_QUERY_LEN <= len(normalised) <= MAX_QUERY_LEN):
            return
        if not is_plausible_query(normalised):
            return

        from apps.support_services.models import CoverageRequest

        zip_match = _ZIP_RE.search(normalised)
        postal_code = zip_match.group(1) if zip_match else ''

        updated = CoverageRequest.objects.filter(query=normalised).update(
            hits=F('hits') + 1, last_seen=timezone.now())
        if not updated:
            CoverageRequest.objects.create(
                query=normalised, postal_code=postal_code)
    except Exception:
        # Measuring the problem must never become the problem.
        logger.exception('Failed to record coverage gap for %r', query)
