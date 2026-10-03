"""Voice the audio library with ElevenLabs and store the MP3s.

Usage (run where the audio should be stored, i.e. a Railway shell so files
land in Cloudinary):

    python manage.py generate_audio --dry-run        # what would change + character count
    python manage.py generate_audio                  # generate new or changed tracks
    python manage.py generate_audio --only urge-surfing --force
    python manage.py generate_audio --sessions-only  # skip the 30 reflection narrations

Needs ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID (see resources/elevenlabs.py).
A track is only re-voiced when its script, voice, model or format changed,
so re-running is cheap. Tracks whose script was removed are deactivated.
"""
import hashlib
import json

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from resources.audio_mp3 import stitch
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

    def handle(self, *args, **opts):
        config = ElevenLabsConfig()
        dry = opts['dry_run']
        if not dry and config.missing():
            raise CommandError(f"Set {', '.join(config.missing())} first.")

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
