"""Voice the audio library with ElevenLabs and store the MP3s.

Usage (run where the audio should be stored, i.e. a Railway shell so files
land in Cloudinary):

    python manage.py generate_audio --dry-run        # what would change + character count
    python manage.py generate_audio                  # generate new or changed tracks
    python manage.py generate_audio --only urge-surfing --force
    python manage.py generate_audio --sessions-only  # skip the 30 reflection narrations
    python manage.py generate_audio --previews       # (re)build Premium previews only; no ElevenLabs

Needs ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (see resources/elevenlabs.py).
A track is only re-voiced when its script, voice, model or format changed,
so re-running is cheap. Tracks whose script was removed are deactivated.

Only one run at a time: a second run started while one is going (say, from
another SSH session) stops straight away instead of paying to voice the same
tracks twice. The lock is a Postgres advisory lock, so it covers every
container and is released automatically if a run dies.
"""
import hashlib
import json
from contextlib import contextmanager

from django.core.files.base import ContentFile
from django.db import connection
from django.core.management.base import BaseCommand, CommandError

from resources.audio_mp3 import preview as cut_preview, stitch
from resources.audio_scripts import all_scripts, spoken_characters, transcript
from resources.elevenlabs import VOICE_SETTINGS, ElevenLabsConfig, synthesize
from resources.models import AudioTrack


def content_hash(parts, config):
    payload = json.dumps({
        'parts': [p if isinstance(p, str) else {'pause': p.seconds} for p in parts],
        'voice': config.voice_id, 'model': config.model_id,
        'format': config.output_format, 'settings': VOICE_SETTINGS,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


# Arbitrary app-wide key for pg_try_advisory_lock ("audi").
LOCK_KEY = 0x61756469


def try_lock():
    """Take the run lock without waiting. True if taken. Without Postgres
    (local SQLite) there is nothing shared to lock, so always True."""
    if connection.vendor != 'postgresql':
        return True
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(%s)', [LOCK_KEY])
        return bool(cursor.fetchone()[0])


def unlock():
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s)', [LOCK_KEY])


@contextmanager
def single_run():
    if not try_lock():
        raise CommandError(
            'Another generate_audio run is already in progress, so this one stopped '
            'without voicing anything. Let it finish (check with: python manage.py shell '
            '-c "from resources.models import AudioTrack; print(AudioTrack.objects.count())"), '
            'then re-run to pick up anything left.')
    try:
        yield
    finally:
        unlock()


def wants_preview(track):
    """Premium guided sessions get a free preview. Free sessions don't need
    one, and reflection narrations are about a minute long already."""
    return not track.is_free and not track.reflection_slug


def save_preview(track, mp3):
    """Cut and store the preview for `track` from its full MP3 (or clear it)."""
    old = track.preview.name if track.preview else ''
    if wants_preview(track):
        data, seconds = cut_preview(mp3)
        track.preview.save(f'{track.slug}-preview.mp3', ContentFile(data), save=False)
        track.preview_seconds = round(seconds, 2)
    else:
        track.preview = ''
        track.preview_seconds = 0
    track.save(update_fields=['preview', 'preview_seconds'])
    if old and old != track.preview.name:
        try:
            track.preview.storage.delete(old)
        except Exception:  # best effort; a stale file is harmless
            pass


def read_audio(track, client=None):
    """Bytes of a stored track (Cloudinary URL or local file)."""
    url = track.audio.url
    if url.startswith('http'):
        import httpx
        resp = (client or httpx).get(url, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    with track.audio.open('rb') as f:
        return f.read()


def render(parts, config, client=None):
    """Synthesize each spoken part and stitch in the pauses. Returns (mp3, seconds)."""
    spoken = [i for i, p in enumerate(parts) if isinstance(p, str)]
    pieces = []
    for i, part in enumerate(parts):
        if isinstance(part, str):
            pos = spoken.index(i)
            prev_text = parts[spoken[pos - 1]] if pos > 0 else ''
            next_text = parts[spoken[pos + 1]] if pos + 1 < len(spoken) else ''
            pieces.append(synthesize(config, part, prev_text, next_text, client=client))
        else:
            pieces.append(part.seconds)
    return stitch(pieces)


class Command(BaseCommand):
    help = 'Generate audio-library MP3s with ElevenLabs (see resources/audio_scripts.py).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be generated and the character count. No API calls.')
        parser.add_argument('--force', action='store_true', help='Re-voice even unchanged tracks.')
        parser.add_argument('--only', nargs='+', default=None, help='Only these slugs.')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--sessions-only', action='store_true')
        group.add_argument('--reflections-only', action='store_true')
        parser.add_argument('--previews', action='store_true',
                            help='Only (re)build Premium previews from existing audio. No ElevenLabs calls.')

    def handle(self, *args, **opts):
        if opts['previews']:
            return self._previews(opts)
        config = ElevenLabsConfig()
        dry = opts['dry_run']
        if not dry and config.missing():
            raise CommandError(f"Set {', '.join(config.missing())} first.")
        if dry:
            return self._run(config, dry, opts)
        # Lock before planning, so the plan sees every track a previous run saved.
        with single_run():
            return self._run(config, dry, opts)

    def _run(self, config, dry, opts):
        scripts = all_scripts()
        live_slugs = {s[0] for s in scripts}
        if opts['only']:
            unknown = set(opts['only']) - live_slugs
            if unknown:
                raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
            scripts = [s for s in scripts if s[0] in opts['only']]
        if opts['sessions_only']:
            scripts = [s for s in scripts if not s[6]]
        if opts['reflections_only']:
            scripts = [s for s in scripts if s[6]]

        todo, chars = [], 0
        for slug, title, category, description, free, parts, reflection_slug in scripts:
            track = AudioTrack.objects.filter(slug=slug).first()
            digest = content_hash(parts, config)
            fields = {'title': title, 'category': category, 'description': description,
                      'is_free': free, 'reflection_slug': reflection_slug,
                      'transcript': transcript(parts), 'is_active': True}
            if track and track.audio and track.content_hash == digest and not opts['force']:
                # Unchanged audio: still sync wording/access in case those changed.
                if any(getattr(track, k) != v for k, v in fields.items()):
                    if not dry:
                        AudioTrack.objects.filter(pk=track.pk).update(**fields)
                    self.stdout.write(f'  metadata  {slug}')
                continue
            todo.append((slug, parts, digest, fields, track))
            chars += spoken_characters(parts)

        self.stdout.write(f'{len(todo)} track(s) to voice, {chars:,} characters.')
        if dry:
            for slug, *_ in todo:
                self.stdout.write(f'  would generate  {slug}')
            return

        import httpx
        with httpx.Client(timeout=120) as client:
            for slug, parts, digest, fields, track in todo:
                self.stdout.write(f'  generating  {slug} ...', ending='')
                self.stdout.flush()
                mp3, seconds = render(parts, config, client=client)
                # Re-read: the row may have been created since the plan was
                # made, so update it rather than insert a duplicate slug.
                track = AudioTrack.objects.filter(slug=slug).first()
                old_name = track.audio.name if track and track.audio else ''
                track = track or AudioTrack(slug=slug)
                for k, v in fields.items():
                    setattr(track, k, v)
                track.content_hash = digest
                track.voice_id = config.voice_id
                track.model_id = config.model_id
                track.duration_seconds = round(seconds, 2)
                track.audio.save(f'{slug}.mp3', ContentFile(mp3), save=False)
                track.save()
                save_preview(track, mp3)
                if old_name and old_name != track.audio.name:
                    try:
                        track.audio.storage.delete(old_name)
                    except Exception:  # best effort; a stale file is harmless
                        pass
                self.stdout.write(self.style.SUCCESS(f' {seconds / 60:.1f} min'))

        stale = AudioTrack.objects.exclude(slug__in=live_slugs).filter(is_active=True)
        if not opts['only'] and stale.exists():
            count = stale.update(is_active=False)
            self.stdout.write(f'Deactivated {count} track(s) whose script was removed.')
        self.stdout.write(self.style.SUCCESS('Done.'))

    def _previews(self, opts):
        tracks = AudioTrack.objects.filter(is_active=True).exclude(audio='')
        if opts['only']:
            tracks = tracks.filter(slug__in=opts['only'])
        todo = [t for t in tracks if wants_preview(t) or t.preview]
        self.stdout.write(f'{len(todo)} track(s) to check for previews.')
        if opts['dry_run']:
            for t in todo:
                self.stdout.write(f"  would {'build' if wants_preview(t) else 'clear'} preview  {t.slug}")
            return
        import httpx
        with httpx.Client() as client:
            for t in todo:
                save_preview(t, read_audio(t, client) if wants_preview(t) else b'')
                self.stdout.write(f'  preview  {t.slug}  {t.preview_seconds:.0f}s')
        self.stdout.write(self.style.SUCCESS('Done.'))

