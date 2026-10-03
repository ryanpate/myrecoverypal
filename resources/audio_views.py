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
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

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
