"""PDF rendering and Anchor hand-off for recovery worksheets.

WeasyPrint is imported lazily so this module loads in environments without
the native Pango libraries (same pattern as apps/accounts/plan_service.py).
"""
import hashlib
from io import BytesIO

from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone

from .worksheets import answers_as_text, build_sections

# Anchor's history window is ~10-40 messages; keep the opener well short of
# swamping it.
COACH_OPENER_MAX_CHARS = 4000
BLANK_PDF_CACHE_SECONDS = 60 * 60 * 24 * 7


def _pdf_from_html(html_str):
    from weasyprint import HTML

    buf = BytesIO()
    HTML(string=html_str).write_pdf(target=buf)
    return buf.getvalue()


def _render_html(worksheet, data=None, user=None):
    return render_to_string('resources/worksheets/pdf.html', {
        'worksheet': worksheet,
        'sections': build_sections(worksheet, data),
        'filled': data is not None,
        'owner': user,
        'generated': timezone.now(),
        'scale_points': range(11),
    })


def render_blank_pdf(worksheet):
    """Blank, printable worksheet. Public, so cached by rendered content."""
    html_str = _render_html(worksheet)
    key = 'worksheet-blank-pdf:' + hashlib.sha256(html_str.encode()).hexdigest()
    pdf = cache.get(key)
    if pdf is None:
        pdf = _pdf_from_html(html_str)
        cache.set(key, pdf, BLANK_PDF_CACHE_SECONDS)
    return pdf


def render_entry_pdf(entry):
    """A saved entry with the owner's answers filled in (Premium)."""
    return _pdf_from_html(_render_html(entry.worksheet, entry.data, entry.user))


def start_coach_session(entry):
    """Open an Anchor session seeded with this worksheet's answers.

    The opener is static (no API call), and the answers sit in the session
    history, so Anchor sees them on the user's first reply.
    """
    from apps.accounts.models import CoachMessage, RecoveryCoachSession

    worksheet = entry.worksheet
    answers = answers_as_text(worksheet, entry.data)
    if len(answers) > COACH_OPENER_MAX_CHARS:
        answers = answers[:COACH_OPENER_MAX_CHARS].rstrip() + '\n[...]'

    RecoveryCoachSession.objects.filter(
        user=entry.user, is_active=True).update(is_active=False)
    session = RecoveryCoachSession.objects.create(
        user=entry.user, is_active=True,
        title=f'Worksheet: {worksheet.title}'[:200],
    )
    CoachMessage.objects.create(
        session=session, role='assistant',
        content=(
            f"Thanks for sharing your {worksheet.title} worksheet with me. "
            f"Here's what you wrote:\n\n{answers}\n\n"
            "What stood out to you most while you were filling it in?"
        ),
    )
    return session
