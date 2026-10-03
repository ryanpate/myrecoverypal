"""Views for the daily reflection library.

Free for everyone: today's reading in full, plus the opening paragraph of
every other reading. Premium: every reading in full, favorites, and
"Reflect in journal" on any reading. Today's reading can be journaled by
any logged-in member, matching the free daily-thought card.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import premium_required

from .access import user_has_premium
from .audio_views import track_for_reflection
from .models import ReflectionFavorite
from .reflections import (
    RECENT_DAYS, THEMES, by_theme, get_reflection, reflection_for_date, todays_reflection,
)


def _reflection_or_404(slug):
    reflection = get_reflection(slug)
    if reflection is None:
        raise Http404('No such reflection')
    return reflection


def _favorite_slugs(user):
    if not user.is_authenticated:
        return set()
    return set(ReflectionFavorite.objects.filter(user=user)
               .values_list('reflection_slug', flat=True))


def can_read_full(user, reflection):
    return reflection == todays_reflection() or user_has_premium(user)


def reflection_index(request):
    today = timezone.localdate()
    has_premium = user_has_premium(request.user)
    recent = [(today - timedelta(days=i), reflection_for_date(today - timedelta(days=i)))
              for i in range(1, RECENT_DAYS + 1)]
    return render(request, 'resources/reflections/index.html', {
        'today': today,
        'todays': todays_reflection(),
        'audio_track': track_for_reflection(todays_reflection()),
        'themes': by_theme(),
        'recent': recent,
        'has_premium': has_premium,
        'favorite_slugs': _favorite_slugs(request.user),
    })


def reflection_detail(request, slug):
    reflection = _reflection_or_404(slug)
    is_today = reflection == todays_reflection()
    full_access = can_read_full(request.user, reflection)
    related = [r for _, _, rs in by_theme() for r in rs
               if r.theme == reflection.theme and r != reflection]
    return render(request, 'resources/reflections/detail.html', {
        'reflection': reflection,
        'is_today': is_today,
        'full_access': full_access,
        # Narration access matches reading access (today's, or Premium).
        'audio_track': track_for_reflection(reflection) if full_access else None,
        'has_premium': user_has_premium(request.user),
        'is_favorite': reflection.slug in _favorite_slugs(request.user),
        'related': related,
        'theme_label': THEMES[reflection.theme],
    })


@login_required
@premium_required
@require_POST
def reflection_favorite(request, slug):
    reflection = _reflection_or_404(slug)
    fav, created = ReflectionFavorite.objects.get_or_create(
        user=request.user, reflection_slug=reflection.slug)
    if not created:
        fav.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'favorite': created})
    return redirect('resources:reflection_detail', slug=slug)


@login_required
def reflection_journal(request, slug):
    """Journal entry pre-filled with a reading's prompt.

    POST delegates to the journal's own create_entry, so saving, streaks and
    the journal's own limits stay in one place.
    """
    reflection = _reflection_or_404(slug)
    if not can_read_full(request.user, reflection):
        messages.info(request, 'Journaling on any reading in the library is part of Premium.')
        return redirect('accounts:pricing')

    from apps.journal.views import create_entry
    if request.method == 'POST':
        return create_entry(request)

    from apps.journal.forms import JournalEntryForm
    # Deliberately not titled "Daily Reflection ...": the journal's
    # reflect_today view uses that prefix as its once-per-day guard.
    form = JournalEntryForm(initial={
        'title': f'Reflection: {reflection.title}',
        'content': f'{reflection.prompt}\n\n',
    })
    return render(request, 'journal/entry_form.html', {'form': form})


@login_required
def reflection_favorites(request):
    slugs = list(ReflectionFavorite.objects.filter(user=request.user)
                 .values_list('reflection_slug', flat=True))
    favorites = [r for r in (get_reflection(s) for s in slugs) if r is not None]
    return render(request, 'resources/reflections/favorites.html', {
        'favorites': favorites,
        'has_premium': user_has_premium(request.user),
    })
