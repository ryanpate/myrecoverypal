"""{% program_progress_card %}: "continue your program" card for the progress home."""
from django import template

from resources.program_service import active_enrollment, get_progress
from resources.programs import get_program

register = template.Library()

# Members this early in recovery (or with no sobriety date) are invited to
# start First 30 Days when they aren't enrolled in anything.
INVITE_MAX_DAYS_SOBER = 30


@register.inclusion_tag('resources/programs/_progress_card.html', takes_context=True)
def program_progress_card(context):
    user = context.get('user')
    if not getattr(user, 'is_authenticated', False):
        return {'show': False}
    enrollment = active_enrollment(user)
    if enrollment is not None:
        return {'show': True, 'program': enrollment.program,
                'progress': get_progress(enrollment, user)}
    if user.sobriety_date is None or user.get_days_sober() <= INVITE_MAX_DAYS_SOBER:
        from resources.models import ProgramEnrollment
        if not ProgramEnrollment.objects.filter(user=user).exists():
            return {'show': True, 'program': get_program('first-30-days'), 'progress': None}
    return {'show': False}
