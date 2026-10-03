"""Tests for the daily reflection library."""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.journal.models import JournalEntry
from resources.models import ReflectionFavorite
from resources.reflections import (
    REFLECTIONS, THEMES, by_theme, reflection_for_date, todays_reflection,
)
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()


def other_than_today():
    today = todays_reflection()
    return next(r for r in REFLECTIONS if r != today)


class ReflectionContentTests(TestCase):
    def test_slugs_unique_and_not_reserved(self):
        slugs = [r.slug for r in REFLECTIONS]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertNotIn('favorites', slugs)

    def test_every_reading_well_formed(self):
        for r in REFLECTIONS:
            self.assertIn(r.theme, THEMES, r.slug)
            self.assertGreaterEqual(len(r.paragraphs), 2, r.slug)
            self.assertTrue(r.prompt.endswith('?'), r.slug)

    def test_every_theme_has_readings(self):
        for key, label, items in by_theme():
            self.assertTrue(items, key)

    def test_rotation_is_deterministic_and_cycles(self):
        d = date(2026, 10, 3)
        self.assertEqual(reflection_for_date(d), reflection_for_date(d))
        picks = {reflection_for_date(d + timedelta(days=i)).slug for i in range(len(REFLECTIONS))}
        self.assertEqual(len(picks), len(REFLECTIONS))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReflectionPublicTests(TestCase):
    def test_index_shows_todays_reading_in_full(self):
        today = todays_reflection()
        resp = self.client.get(reverse('resources:reflections'))
        self.assertEqual(resp.status_code, 200)
        for p in today.paragraphs:
            self.assertContains(resp, p.split('.')[0][:40].replace('"', '&quot;').replace("'", '&#x27;'))
        self.assertContains(resp, 'Open the whole library with Premium')

    def test_todays_detail_is_full_for_anonymous(self):
        today = todays_reflection()
        resp = self.client.get(reverse('resources:reflection_detail', args=[today.slug]))
        self.assertContains(resp, 'rf-prompt')
        self.assertNotContains(resp, 'Read the rest with Premium')

    def test_other_detail_is_preview_for_anonymous(self):
        r = other_than_today()
        resp = self.client.get(reverse('resources:reflection_detail', args=[r.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Read the rest with Premium')
        self.assertNotContains(resp, 'rf-prompt')

    def test_every_detail_page_renders(self):
        for r in REFLECTIONS:
            resp = self.client.get(reverse('resources:reflection_detail', args=[r.slug]))
            self.assertEqual(resp.status_code, 200, r.slug)

    def test_unknown_404s(self):
        resp = self.client.get(reverse('resources:reflection_detail', args=['nope']))
        self.assertEqual(resp.status_code, 404)

    def test_sitemap_and_hub_link(self):
        resp = self.client.get(reverse('resources:list'))
        self.assertContains(resp, reverse('resources:reflections'))
        resp = self.client.get('/sitemap.xml')
        if b'sitemapindex' in resp.content:
            resp = self.client.get('/sitemap-reflections.xml')
        self.assertContains(resp, reverse('resources:reflection_detail', args=[REFLECTIONS[0].slug]))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReflectionMemberTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rf', email='rf@example.com', password='x')
        self.client.force_login(self.user)

    def test_premium_reads_any_reading_in_full(self):
        make_premium(self.user)
        r = other_than_today()
        resp = self.client.get(reverse('resources:reflection_detail', args=[r.slug]))
        self.assertContains(resp, 'rf-prompt')
        self.assertContains(resp, 'Save to favorites')

    def test_free_member_sees_preview_and_no_favorite_button(self):
        make_free(self.user)
        r = other_than_today()
        resp = self.client.get(reverse('resources:reflection_detail', args=[r.slug]))
        self.assertContains(resp, 'Read the rest with Premium')
        self.assertNotContains(resp, 'Save to favorites')

    def test_favorite_toggle_premium(self):
        make_premium(self.user)
        r = other_than_today()
        url = reverse('resources:reflection_favorite', args=[r.slug])
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.json(), {'favorite': True})
        self.assertTrue(ReflectionFavorite.objects.filter(user=self.user, reflection_slug=r.slug).exists())
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse('resources:reflection_detail', args=[r.slug]),
                             fetch_redirect_response=False)
        self.assertFalse(ReflectionFavorite.objects.exists())

    def test_favorite_requires_premium_and_post(self):
        make_free(self.user)
        r = other_than_today()
        url = reverse('resources:reflection_favorite', args=[r.slug])
        resp = self.client.post(url)
        self.assertIn(reverse('accounts:pricing'), resp['Location'])
        self.assertFalse(ReflectionFavorite.objects.exists())
        make_premium(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_favorites_page_lists_only_mine(self):
        other = User.objects.create_user(username='o2', email='o2@example.com', password='x')
        ReflectionFavorite.objects.create(user=self.user, reflection_slug=REFLECTIONS[0].slug)
        ReflectionFavorite.objects.create(user=other, reflection_slug=REFLECTIONS[1].slug)
        ReflectionFavorite.objects.create(user=self.user, reflection_slug='retired-slug')
        resp = self.client.get(reverse('resources:reflection_favorites'))
        self.assertContains(resp, REFLECTIONS[0].title)
        self.assertNotContains(resp, REFLECTIONS[1].title)

    def test_free_member_can_journal_on_todays_reading(self):
        make_free(self.user)
        today = todays_reflection()
        url = reverse('resources:reflection_journal', args=[today.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'Reflection: {today.title}')
        resp = self.client.post(url, {'title': f'Reflection: {today.title}', 'content': 'My answer'})
        entry = JournalEntry.objects.get(user=self.user)
        self.assertRedirects(resp, reverse('journal:entry_detail', args=[entry.pk]),
                             fetch_redirect_response=False)

    def test_free_member_cannot_journal_on_archive(self):
        make_free(self.user)
        r = other_than_today()
        resp = self.client.get(reverse('resources:reflection_journal', args=[r.slug]))
        self.assertIn(reverse('accounts:pricing'), resp['Location'])

    def test_premium_member_can_journal_on_archive(self):
        make_premium(self.user)
        r = other_than_today()
        resp = self.client.get(reverse('resources:reflection_journal', args=[r.slug]))
        self.assertContains(resp, r.prompt.replace("'", '&#x27;').replace('"', '&quot;'))

    def test_journal_title_does_not_trip_daily_thought_guard(self):
        """reflect_today treats titles starting "Daily Reflection" as today's entry."""
        make_premium(self.user)
        r = other_than_today()
        self.client.post(reverse('resources:reflection_journal', args=[r.slug]),
                         {'title': f'Reflection: {r.title}', 'content': 'x'})
        resp = self.client.get(reverse('journal:reflect_today'))
        self.assertEqual(resp.status_code, 200)

    def test_rotation_follows_local_date(self):
        with patch('resources.reflections.timezone.localdate', return_value=date(2026, 1, 1)):
            self.assertEqual(todays_reflection(), reflection_for_date(date(2026, 1, 1)))
