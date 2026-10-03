"""Tests for the audio library: MP3 stitching, scripts, generation and views."""
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from resources import audio_mp3
from resources.audio_scripts import (
    CATEGORIES, REFLECTION_SLUG_PREFIX, SESSIONS, P, all_scripts, spoken_characters, transcript,
)
from resources.models import AudioTrack
from resources.reflections import REFLECTIONS, todays_reflection
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()

# MPEG-1 Layer III, 64 kbps, 44.1 kHz, mono: 208-byte frames.
HEADER = bytes([0xFF, 0xFB, 0x50, 0xC0])
FRAME_LEN = 144 * 64000 // 44100


def fake_mp3(frames=10, id3=True):
    frame = HEADER + bytes([0x11]) * (FRAME_LEN - 4)
    tag = b'ID3\x04\x00\x00\x00\x00\x00\x0a' + b'\x00' * 10 if id3 else b''
    return tag + frame * frames


def info_frame():
    # Xing header sits after the 17-byte mono side info.
    body = bytearray(FRAME_LEN - 4)
    body[17:21] = b'Xing'
    return HEADER + bytes(body)


class Mp3StitchTests(TestCase):
    def test_parse_header(self):
        info = audio_mp3.parse_header(HEADER)
        self.assertEqual((info['bitrate'], info['sample_rate'], info['length']), (64000, 44100, FRAME_LEN))
        self.assertTrue(info['mono'])
        self.assertIsNone(audio_mp3.parse_header(b'\x00\x00\x00\x00'))

    def test_strips_id3_and_info_frames(self):
        data = fake_mp3(3) + b''
        data = data[:20] + info_frame() + data[20:]
        frames = audio_mp3.audio_frames(data)
        self.assertEqual(len(frames), 3)

    def test_stitch_inserts_silence_and_reports_duration(self):
        mp3, seconds = audio_mp3.stitch([fake_mp3(10), 2.0, fake_mp3(5)])
        frame_s = 1152 / 44100
        silent = round(2.0 / frame_s)
        self.assertEqual(len(mp3), (15 + silent) * FRAME_LEN)
        self.assertAlmostEqual(seconds, (15 + silent) * frame_s, places=6)
        self.assertNotIn(b'ID3', mp3)
        # Silent frames share the speech frames' header (constant bitrate).
        self.assertEqual(mp3[10 * FRAME_LEN:10 * FRAME_LEN + 4], HEADER)

    def test_stitch_needs_audio(self):
        with self.assertRaises(audio_mp3.MP3Error):
            audio_mp3.stitch([1.0, b'not audio'])


class AudioScriptTests(TestCase):
    def test_slugs_unique_categories_known(self):
        slugs = [s[0] for s in all_scripts()]
        self.assertEqual(len(slugs), len(set(slugs)))
        for s in all_scripts():
            self.assertIn(s[2], CATEGORIES, s[0])

    def test_craving_tools_are_free(self):
        free = {s.slug for s in SESSIONS if s.free}
        self.assertTrue({'urge-surfing', 'breathing-4-7-8', 'grounding-5-4-3-2-1', 'craving-reset'} <= free)
        for s in SESSIONS:
            if s.category == 'cravings':
                self.assertTrue(s.free, s.slug)

    def test_every_reflection_has_a_narration(self):
        narrated = {s[6] for s in all_scripts() if s[6]}
        self.assertEqual(narrated, {r.slug for r in REFLECTIONS})

    def test_parts_are_text_or_pause(self):
        for slug, *_rest in all_scripts():
            parts = _rest[4]
            self.assertTrue(parts, slug)
            for p in parts:
                self.assertTrue(isinstance(p, P) or (isinstance(p, str) and p.strip()), slug)
            self.assertIsInstance(parts[0], str, slug)

    def test_only_approved_numbers(self):
        import re
        for slug, *_rest in all_scripts():
            text = transcript(_rest[4])
            for digits in re.findall(r'\d[\d -]{2,}\d', text):
                self.assertIn(digits.replace(' ', ''), {'988', '911'}, slug)

    def test_character_count(self):
        self.assertEqual(spoken_characters(['ab', P(1), 'cde']), 5)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class GenerateAudioCommandTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.env = patch.dict('os.environ', {'ELEVENLABS_API_KEY': 'k', 'ELEVENLABS_VOICE_ID': 'v'})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def run_cmd(self, *args):
        out = StringIO()
        call_command('generate_audio', *args, stdout=out)
        return out.getvalue()

    def test_requires_key(self):
        with patch.dict('os.environ', {'ELEVENLABS_API_KEY': ''}):
            with self.assertRaises(CommandError):
                self.run_cmd('--only', 'urge-surfing')

    def test_dry_run_makes_no_calls(self):
        with patch('resources.management.commands.generate_audio.synthesize') as synth:
            out = self.run_cmd('--dry-run')
        synth.assert_not_called()
        self.assertIn('would generate  urge-surfing', out)
        self.assertFalse(AudioTrack.objects.exists())

    def test_generates_then_skips_unchanged(self):
        with patch('resources.management.commands.generate_audio.synthesize',
                   return_value=fake_mp3(4)) as synth:
            self.run_cmd('--only', 'urge-surfing')
            calls = synth.call_count
            track = AudioTrack.objects.get(slug='urge-surfing')
            self.assertTrue(track.is_free)
            self.assertGreater(track.duration_seconds, 60)  # pauses stitched in
            self.assertTrue(track.audio.name.startswith('audio/urge-surfing-'))
            # neighbouring text is passed for consistent intonation
            first = synth.call_args_list[0]
            self.assertEqual(first.args[2], '')
            self.assertTrue(first.args[3])
            self.run_cmd('--only', 'urge-surfing')
            self.assertEqual(synth.call_count, calls)
            self.run_cmd('--only', 'urge-surfing', '--force')
            self.assertEqual(synth.call_count, calls * 2)

    def test_reflection_track_links_to_reading(self):
        r = REFLECTIONS[0]
        with patch('resources.management.commands.generate_audio.synthesize', return_value=fake_mp3(2)):
            self.run_cmd('--only', REFLECTION_SLUG_PREFIX + r.slug)
        track = AudioTrack.objects.get(slug=REFLECTION_SLUG_PREFIX + r.slug)
        self.assertEqual(track.reflection_slug, r.slug)
        self.assertFalse(track.is_free)

    def test_removed_scripts_deactivated(self):
        AudioTrack.objects.create(slug='old-session', title='Old', category='calm')
        with patch('resources.management.commands.generate_audio.synthesize', return_value=fake_mp3(2)):
            self.run_cmd('--sessions-only')
        self.assertFalse(AudioTrack.objects.get(slug='old-session').is_active)


def make_track(slug, free=False, reflection_slug='', category='calm'):
    t = AudioTrack(slug=slug, title=slug.title(), category=category, is_free=free,
                   reflection_slug=reflection_slug, transcript='Hello there.', duration_seconds=300)
    t.audio.save(f'{slug}.mp3', ContentFile(fake_mp3(2)), save=False)
    t.save()
    return t


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class AudioViewTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.free = make_track('urge-surfing', free=True, category='cravings')
        self.paid = make_track('body-scan')
        today = todays_reflection()
        other = next(r for r in REFLECTIONS if r != today)
        self.today_track = make_track(REFLECTION_SLUG_PREFIX + today.slug, reflection_slug=today.slug,
                                      category='reflections')
        self.other_track = make_track(REFLECTION_SLUG_PREFIX + other.slug, reflection_slug=other.slug,
                                      category='reflections')
        self.other = other
        self.user = User.objects.create_user('listener', 'l@example.com', 'pw12345!')

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def play(self, track):
        return self.client.get(reverse('resources:audio_play', args=[track.slug]))

    def test_index_lists_tracks_with_locks(self):
        resp = self.client.get(reverse('resources:audio'))
        self.assertContains(resp, 'Urge-Surfing')
        self.assertContains(resp, '🔒')
        self.assertContains(resp, '☀ Today:')

    def test_empty_library(self):
        AudioTrack.objects.all().delete()
        resp = self.client.get(reverse('resources:audio'))
        self.assertContains(resp, 'being recorded')

    def test_free_track_plays_for_anonymous(self):
        resp = self.play(self.free)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/audio/urge-surfing-', resp['Location'])
        detail = self.client.get(reverse('resources:audio_detail', args=[self.free.slug]))
        self.assertContains(detail, reverse('resources:audio_play', args=[self.free.slug]))
        self.assertNotContains(detail, self.free.audio.url)

    def test_todays_reflection_free_others_premium(self):
        self.client.force_login(self.user)
        make_free(self.user)
        self.assertIn('/audio/', self.play(self.today_track)['Location'])
        self.assertEqual(self.play(self.other_track)['Location'], reverse('accounts:pricing'))
        self.assertEqual(self.play(self.paid)['Location'], reverse('accounts:pricing'))
        detail = self.client.get(reverse('resources:audio_detail', args=[self.paid.slug]))
        self.assertContains(detail, 'Listen with Premium')
        self.assertNotContains(detail, 'Hello there.')

    def test_anonymous_locked_goes_to_login(self):
        self.assertIn(reverse('accounts:login'), self.play(self.paid)['Location'])

    def test_premium_plays_everything(self):
        self.client.force_login(self.user)
        make_premium(self.user)
        for t in (self.paid, self.other_track):
            self.assertIn('/audio/', self.play(t)['Location'])

    def test_inactive_track_404(self):
        AudioTrack.objects.filter(pk=self.paid.pk).update(is_active=False)
        self.assertEqual(self.play(self.paid).status_code, 404)

    def test_reflection_listen_uses_recording(self):
        resp = self.client.get(reverse('resources:reflections'))
        self.assertContains(resp, reverse('resources:audio_play', args=[self.today_track.slug]))
        # Locked reading: no narration offered
        resp = self.client.get(reverse('resources:reflection_detail', args=[self.other.slug]))
        self.assertNotContains(resp, reverse('resources:audio_play', args=[self.other_track.slug]))

    def test_hub_promo_and_sos(self):
        self.assertContains(self.client.get(reverse('resources:list')), 'Guided Audio')
        self.assertContains(self.client.get(reverse('core:craving_sos')),
                            reverse('resources:audio_detail', args=[self.free.slug]))
        AudioTrack.objects.all().delete()
        self.assertNotContains(self.client.get(reverse('resources:list')), 'New: Guided Audio')
        self.assertNotContains(self.client.get(reverse('core:craving_sos')), 'sos-audio')

    def test_sitemap_includes_sessions_not_narrations(self):
        resp = self.client.get('/sitemap.xml')
        if resp.status_code == 200 and b'sitemapindex' in resp.content:
            resp = self.client.get('/sitemap-audio.xml')
        body = resp.content.decode()
        self.assertIn(reverse('resources:audio_detail', args=[self.free.slug]), body)
        self.assertNotIn(self.today_track.slug, body)
