"""Shareable reflection cards, and free guided audio after a struggling check-in."""
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import DailyCheckIn
from resources.reflection_cards import FORMATS, opening_line, render_card
from resources.reflections import REFLECTIONS, todays_reflection
from resources.test_audio import make_track
from resources.test_premium_gating import make_free

User = get_user_model()


class CardRenderTests(TestCase):
    def test_every_reading_renders_in_every_format(self):
        from io import BytesIO
        from PIL import Image
        for r in REFLECTIONS[:5] + [max(REFLECTIONS, key=lambda x: len(x.title))]:
            for fmt, size in FORMATS.items():
                img = Image.open(BytesIO(render_card(r, fmt)))
                self.assertEqual(img.size, size, (r.slug, fmt))

    def test_opening_line_is_public_text(self):
        for r in REFLECTIONS:
            line = opening_line(r).rstrip('…')
            self.assertTrue(r.paragraphs[0].startswith(line.split('…')[0][:40]), r.slug)
            self.assertLessEqual(len(opening_line(r)), 211)
            self.assertNotIn(r.prompt, opening_line(r))  # the prompt stays on the page


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CardViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_card_png_public_and_cached(self):
        r = todays_reflection()
        url = reverse('resources:reflection_card', args=[r.slug])
        resp = self.client.get(url)
        self.assertEqual(resp['Content-Type'], 'image/png')
        self.assertIn('max-age', resp['Cache-Control'])
        self.assertTrue(resp.content.startswith(b'\x89PNG'))
        story = self.client.get(url + '?format=story&download=1')
        self.assertIn('attachment', story['Content-Disposition'])
        self.assertIn('-story.png', story['Content-Disposition'])
        self.assertEqual(self.client.get(url + '?format=bogus').status_code, 200)
        self.assertEqual(self.client.get(reverse('resources:reflection_card', args=['nope'])).status_code, 404)

    def test_pages_use_card_as_link_preview_and_offer_share(self):
        r = todays_reflection()
        og = f"{reverse('resources:reflection_card', args=[r.slug])}?format=og"
        for url in (reverse('resources:reflections'), reverse('resources:reflection_detail', args=[r.slug])):
            resp = self.client.get(url)
            self.assertContains(resp, f'<meta property="og:image" content="https://www.myrecoverypal.com{og}">')
            self.assertContains(resp, 'rf-share-btn')


def checkin(user, mood, craving):
    return DailyCheckIn.objects.create(user=user, mood=mood, craving_level=craving, energy_level=3)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupportAudioTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        make_track('urge-surfing', free=True, category='cravings')
        make_track('grounding-5-4-3-2-1', free=True, category='calm')
        self.user = User.objects.create_user('sa', 'sa@example.com', 'pw12345!')
        make_free(self.user)
        self.client.force_login(self.user)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def confirm(self, c):
        return self.client.get(reverse('accounts:checkin_confirmation') + f'?checkin={c.id}')

    def test_craving_gets_urge_surfing(self):
        resp = self.confirm(checkin(self.user, mood=3, craving=4))
        self.assertContains(resp, reverse('resources:audio_play', args=['urge-surfing']))
        self.assertContains(resp, 'free')

    def test_low_mood_gets_grounding(self):
        resp = self.confirm(checkin(self.user, mood=1, craving=0))
        self.assertContains(resp, reverse('resources:audio_play', args=['grounding-5-4-3-2-1']))

    def test_calm_checkin_offers_nothing(self):
        resp = self.confirm(checkin(self.user, mood=5, craving=0))
        self.assertNotContains(resp, 'support-audio')

    def test_free_member_can_actually_play_it(self):
        resp = self.client.get(reverse('resources:audio_play', args=['urge-surfing']))
        self.assertIn('/audio/urge-surfing-', resp['Location'])

    def test_never_offers_a_premium_track(self):
        from resources.models import AudioTrack
        AudioTrack.objects.filter(slug='urge-surfing').update(is_free=False)
        resp = self.confirm(checkin(self.user, mood=3, craving=4))
        self.assertNotContains(resp, 'support-audio')

    def test_ajax_checkin_returns_audio(self):
        resp = self.client.post(reverse('accounts:quick_checkin'), {'mood': 3, 'craving_level': 4, 'energy_level': 3})
        data = resp.json()
        self.assertTrue(data['needs_support'])
        self.assertEqual(data['support_audio']['slug'], 'urge-surfing')
        self.assertEqual(data['support_audio']['play_url'], reverse('resources:audio_play', args=['urge-surfing']))

    def test_ajax_calm_checkin_no_audio(self):
        resp = self.client.post(reverse('accounts:quick_checkin'), {'mood': 5, 'craving_level': 0, 'energy_level': 3})
        self.assertIsNone(resp.json()['support_audio'])
