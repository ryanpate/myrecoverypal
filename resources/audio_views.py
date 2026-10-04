"""Views for the audio library (guided sessions + reflection narrations).

Access (see resources/audio_scripts.py):
  * free sessions (craving and calm tools) are open to everyone, logged in
    or not: safety tools are never paywalled;
  * a reflection narration is free on the day it is today's reflection;
  * everything else is Premium.

The MP3 itself lives at an unguessable storage URL. The page never prints
it: the player points at `audio_play`, which checks access and redirects.
A redirect URL that someone copies would keep working; that's an accepted
tradeoff for short meditations (signed URLs would break iOS background
playback when they expire mid-session).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .access import user_has_premium
from .audio_scripts import CATEGORIES
from .models import AudioTrack
from .reflections import todays_reflection


def active_tracks():
    return AudioTrack.objects.filter(is_active=True).exclude(audio='')


def can_listen(user, track):
    if track.is_free:
        return True
    if track.reflection_slug and track.reflection_slug == todays_reflection().slug:
        return True
    return user_has_premium(user)


def track_for_reflection(reflection):
    """The active narration of `reflection`, or None."""
    return active_tracks().filter(reflection_slug=reflection.slug).first()


def _track_or_404(slug):
    track = active_tracks().filter(slug=slug).first()
    if track is None:
        raise Http404('No such audio session')
    return track


def audio_index(request):
    tracks = list(active_tracks())
    has_premium = user_has_premium(request.user)
    today_slug = todays_reflection().slug
    groups = []
    for key, label in CATEGORIES.items():
        items = [t for t in tracks if t.category == key]
        if key == 'reflections':
            # Today's narration first; the rest are a Premium library.
            items.sort(key=lambda t: (t.reflection_slug != today_slug, t.title))
        if items:
            groups.append((key, label, [(t, can_listen(request.user, t)) for t in items]))
    return render(request, 'resources/audio/index.html', {
        'groups': groups,
        'has_premium': has_premium,
        'today_slug': today_slug,
    })


def hour_label(h):
    return f"{(h % 12) or 12} {'AM' if h < 12 else 'PM'}"


def _reminder_context(user, track):
    """Context for the "Make it a habit" card on remindable sessions."""
    from .tasks import AUDIO_REMINDERS, REMINDER_HOURS
    if not user.is_authenticated or track.slug not in AUDIO_REMINDERS:
        return {}
    from apps.accounts.models import DeviceToken
    from .models import AudioReminder
    reminder = AudioReminder.objects.filter(user=user, track_slug=track.slug).first()
    hour = reminder.hour if reminder else AUDIO_REMINDERS[track.slug]['hour']
    return {'reminder': {
        'on': bool(reminder and reminder.enabled),
        'hour': hour,
        'label': hour_label(hour),
        'hours': [(h, hour_label(h)) for h in REMINDER_HOURS],
        'has_app': DeviceToken.objects.filter(user=user, active=True).exists(),
    }}


@login_required
@require_POST
def audio_reminder(request, slug):
    """Turn the daily reminder for a session on (at an hour) or off."""
    from .models import AudioReminder
    from .tasks import AUDIO_REMINDERS, REMINDER_HOURS
    track = _track_or_404(slug)
    if slug not in AUDIO_REMINDERS:
        raise Http404('No reminders for this session')
    if request.POST.get('action') == 'off':
        AudioReminder.objects.filter(user=request.user, track_slug=slug).update(enabled=False)
        messages.info(request, 'Reminder turned off.')
    else:
        try:
            hour = int(request.POST.get('hour', AUDIO_REMINDERS[slug]['hour']))
        except (TypeError, ValueError):
            hour = AUDIO_REMINDERS[slug]['hour']
        if hour not in REMINDER_HOURS:
            hour = AUDIO_REMINDERS[slug]['hour']
        AudioReminder.objects.update_or_create(
            user=request.user, track_slug=slug,
            defaults={'hour': hour, 'enabled': True, 'last_sent_on': None})
        messages.success(request, f'Done. We\'ll remind you every day at {hour_label(hour)}, your time.')
    return redirect('resources:audio_detail', slug=track.slug)


def audio_detail(request, slug):
    track = _track_or_404(slug)
    allowed = can_listen(request.user, track)
    related = [t for t in active_tracks().filter(category=track.category).exclude(pk=track.pk)
               if t.category != 'reflections'][:4]
    return render(request, 'resources/audio/detail.html', {
        'track': track,
        'allowed': allowed,
        'category_label': CATEGORIES.get(track.category, ''),
        'has_premium': user_has_premium(request.user),
        'related': related,
        'is_today': bool(track.reflection_slug) and track.reflection_slug == todays_reflection().slug,
        **_reminder_context(request.user, track),
    })


@never_cache
def audio_preview(request, slug):
    """The free opening of a Premium session. Public, like the description."""
    track = _track_or_404(slug)
    if not track.preview:
        raise Http404('No preview for this session')
    return redirect(track.preview.url)


@never_cache
def audio_play(request, slug):
    track = _track_or_404(slug)
    if not can_listen(request.user, track):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login')}?next={reverse('resources:audio_detail', args=[slug])}")
        messages.info(request, 'The full audio library is part of Premium.')
        return redirect('accounts:pricing')
    return redirect(track.audio.url)


# Struggling check-in -> one-tap guided audio (always a FREE session: someone
# mid-craving is never shown a paywall). Craving -> urge surfing; low mood
# without a craving -> grounding.
SUPPORT_AUDIO_CRAVING = 'urge-surfing'
SUPPORT_AUDIO_LOW_MOOD = 'grounding-5-4-3-2-1'


def support_audio_for(checkin):
    """A free AudioTrack to offer after `checkin`, or None."""
    if checkin is None or not checkin.needs_support():
        return None
    slug = SUPPORT_AUDIO_CRAVING if checkin.craving_level >= 3 else SUPPORT_AUDIO_LOW_MOOD
    return active_tracks().filter(slug=slug, is_free=True).first()


def support_audio_payload(checkin):
    """JSON-ready version of support_audio_for, for the AJAX check-in."""
    track = support_audio_for(checkin)
    if track is None:
        return None
    return {
        'slug': track.slug,
        'title': track.title,
        'minutes': track.minutes,
        'play_url': reverse('resources:audio_play', args=[track.slug]),
        'detail_url': reverse('resources:audio_detail', args=[track.slug]),
        'reason': 'craving' if checkin.craving_level >= 3 else 'low_mood',
    }

