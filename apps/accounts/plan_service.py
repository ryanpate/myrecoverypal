"""PDF rendering for the relapse prevention plan (premium export).

WeasyPrint is imported lazily so this module (and everything importing it)
loads fine in environments without the native Pango libraries — same
pattern as court_service.py.
"""
from io import BytesIO

from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.plan_models import RelapsePreventionPlan


def render_plan_pdf(user) -> bytes:
    from weasyprint import HTML

    plan, _ = RelapsePreventionPlan.objects.get_or_create(user=user)
    html_str = render_to_string('accounts/relapse_plan_pdf.html', {
        'plan_user': user,
        'plan': plan,
        'generated': timezone.now(),
    })
    buf = BytesIO()
    HTML(string=html_str).write_pdf(target=buf)
    return buf.getvalue()
