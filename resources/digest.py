"""The library section of the Sunday weekly digest email
(apps/accounts/tasks.py::send_weekly_digests).

Three short blocks that bring members back to the library each week:
  * this week's reflection (the one that's today's, free today), shown with
    its share card image;
  * a guided session for the week, rotating weekly through the sessions
    (locked Premium ones point to their free preview);
  * the member's open program lesson, if they're partway through one.
"""
from django.urls import reverse
from django.utils import timezone

UTM = '?utm_source=email&utm_medium=digest&utm_campaign=weekly_library'


def library_block(user, site_url, today=None):
    from .audio_views import active_tracks, can_listen
    from .models import ProgramEnrollment
    from .program_service import get_progress
    from .reflections import reflection_for_date

    today = today or timezone.localdate()
    site_url = site_url.rstrip('/')
    reflection = reflection_for_date(today)
    block = {
        'reflection': {
            'title': reflection.title,
            'preview': reflection.preview,
            'url': f"{site_url}{reverse('resources:reflection_detail', args=[reflection.slug])}{UTM}",
            'card_url': f"{site_url}{reverse('resources:reflection_card', args=[reflection.slug])}?format=og",
        },
        'library_url': f"{site_url}{reverse('resources:list')}{UTM}",
    }

    sessions = list(active_tracks().filter(reflection_slug='').order_by('slug'))
    if sessions:
        track = sessions[today.isocalendar()[1] % len(sessions)]
        locked = not can_listen(user, track)
        block['session'] = {
            'title': track.title,
            'minutes': track.minutes,
            'description': track.description,
            'url': f"{site_url}{reverse('resources:audio_detail', args=[track.slug])}{UTM}",
            'locked': locked,
            'preview': locked and bool(track.preview),
        }

    for enrollment in ProgramEnrollment.objects.filter(user=user, completed_at__isnull=True).order_by('-started_at'):
        program = enrollment.program
        if program is None:
            continue
        progress = get_progress(enrollment, user, today)
        if progress.next_status in ('current', 'waiting', 'premium'):
            lesson = program.lesson(progress.next_day)
            block['program'] = {
                'title': program.title,
                'day': progress.next_day,
                'length': program.length,
                'lesson': lesson.title if lesson else '',
                'url': f"{site_url}{reverse('resources:program_detail', args=[program.slug])}{UTM}",
            }
            break
    return block
