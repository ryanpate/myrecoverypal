"""Tests for the interactive worksheet library."""
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import CoachMessage, RecoveryCoachSession
from resources.models import WorksheetEntry
from resources.test_premium_gating import make_free, make_premium
from resources.worksheets import (
    TEXT_MAX, TEXTAREA_MAX, WORKSHEETS, answers_as_text, clean_answers, get_worksheet,
)

User = get_user_model()

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except Exception:
    HAS_WEASYPRINT = False


class WorksheetDefinitionTests(TestCase):
    def test_slugs_unique_and_not_reserved(self):
        slugs = [w.slug for w in WORKSHEETS]
        self.assertEqual(len(slugs), len(set(slugs)))
        # These path segments are routed before worksheets/<slug>/.
        self.assertFalse({'mine', 'entry'} & set(slugs))

    def test_title_fields_exist(self):
        for w in WORKSHEETS:
            if w.title_field:
                self.assertIn(w.title_field, w.fields_by_key, w.slug)

    def test_field_types_known(self):
        for w in WORKSHEETS:
            for f in w.fields:
                self.assertIn(f.type, {'text', 'textarea', 'scale'}, f'{w.slug}.{f.key}')


class CleanAnswersTests(TestCase):
    def setUp(self):
        self.ws = get_worksheet('abc-thought-record')

    def test_strips_caps_clamps_and_ignores_unknown(self):
        data = clean_answers(self.ws, {
            'activating_event': '  ' + 'x' * (TEXT_MAX + 50) + ' ',
            'beliefs': 'y' * (TEXTAREA_MAX + 10),
            'emotion_before': '42',
            'craving_before': '-3',
            'emotion_after': 'lots',
            'consequences': '   ',
            'evil': 'ignored',
        })
        self.assertEqual(len(data['activating_event']), TEXT_MAX)
        self.assertEqual(len(data['beliefs']), TEXTAREA_MAX)
        self.assertEqual(data['emotion_before'], 10)
        self.assertEqual(data['craving_before'], 0)
        self.assertNotIn('emotion_after', data)
        self.assertNotIn('consequences', data)
        self.assertNotIn('evil', data)

    def test_all_blank_is_empty(self):
        self.assertEqual(clean_answers(self.ws, {'beliefs': ' '}), {})

    def test_answers_as_text(self):
        text = answers_as_text(self.ws, {'beliefs': 'I always mess up', 'emotion_before': 7})
        self.assertIn('I always mess up', text)
        self.assertIn('7/10', text)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WorksheetPublicPagesTests(TestCase):
    def test_index_lists_every_worksheet(self):
        resp = self.client.get(reverse('resources:worksheets'))
        self.assertEqual(resp.status_code, 200)
        for w in WORKSHEETS:
            self.assertContains(resp, reverse('resources:worksheet_detail', args=[w.slug]))

    def test_every_detail_page_renders_for_anonymous(self):
        for w in WORKSHEETS:
            resp = self.client.get(reverse('resources:worksheet_detail', args=[w.slug]))
            self.assertEqual(resp.status_code, 200, w.slug)
            self.assertContains(resp, 'Create an account to save')
            # Anonymous visitors get no posting form, so no CSRF token.
            self.assertNotContains(resp, 'csrfmiddlewaretoken')

    def test_unknown_worksheet_404s(self):
        resp = self.client.get(reverse('resources:worksheet_detail', args=['nope']))
        self.assertEqual(resp.status_code, 404)

    def test_blank_pdf_is_public(self):
        with patch('resources.worksheet_service._pdf_from_html', return_value=b'%PDF-fake') as m:
            cache.clear()
            resp = self.client.get(reverse('resources:worksheet_blank_pdf', args=['urge-log']))
            self.client.get(reverse('resources:worksheet_blank_pdf', args=['urge-log']))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('urge-log-worksheet.pdf', resp['Content-Disposition'])
        # Second request served from cache.
        self.assertEqual(m.call_count, 1)

    def test_resources_hub_links_to_worksheets(self):
        resp = self.client.get(reverse('resources:list'))
        self.assertContains(resp, reverse('resources:worksheets'))

    def test_sitemap_lists_worksheets(self):
        resp = self.client.get('/sitemap.xml')
        if resp.status_code == 200 and b'sitemapindex' in resp.content:
            resp = self.client.get('/sitemap-worksheets.xml')
        self.assertContains(resp, '/resources/worksheets/urge-log/')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WorksheetPremiumTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ws', email='ws@example.com', password='x')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='x')
        self.client.force_login(self.user)
        self.save_url = reverse('resources:worksheet_save', args=['urge-log'])

    def _entry(self, user=None, **data):
        return WorksheetEntry.objects.create(
            user=user or self.user, worksheet_slug='urge-log',
            data=data or {'when': 'Friday 6pm', 'intensity_start': 8})

    def test_free_user_sees_locked_save(self):
        make_free(self.user)
        resp = self.client.get(reverse('resources:worksheet_detail', args=['urge-log']))
        self.assertContains(resp, 'Save my answers (Premium)')
        self.assertContains(resp, 'Keep your answers with Premium')

    def test_free_user_cannot_save(self):
        make_free(self.user)
        resp = self.client.post(self.save_url, {'when': 'now'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:pricing'), resp['Location'])
        self.assertFalse(WorksheetEntry.objects.exists())

    def test_premium_user_saves_new_entry(self):
        make_premium(self.user)
        resp = self.client.post(self.save_url, {
            'when': 'Friday 6pm', 'trigger': 'Payday', 'intensity_start': '8', 'bogus': 'x'})
        entry = WorksheetEntry.objects.get()
        self.assertRedirects(resp, entry.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.data, {'when': 'Friday 6pm', 'trigger': 'Payday', 'intensity_start': 8})
        self.assertEqual(entry.label, 'Friday 6pm')

    def test_premium_blank_save_rejected(self):
        make_premium(self.user)
        resp = self.client.post(self.save_url, {'when': '  '})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(WorksheetEntry.objects.exists())

    def test_premium_user_edits_existing_entry(self):
        make_premium(self.user)
        entry = self._entry()
        self.client.post(self.save_url, {'entry_id': entry.pk, 'when': 'Saturday'})
        entry.refresh_from_db()
        self.assertEqual(entry.data, {'when': 'Saturday'})
        self.assertEqual(WorksheetEntry.objects.count(), 1)

    def test_cannot_edit_someone_elses_entry(self):
        make_premium(self.user)
        theirs = self._entry(user=self.other)
        resp = self.client.post(self.save_url, {'entry_id': theirs.pk, 'when': 'hijack'})
        self.assertEqual(resp.status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.data['when'], 'Friday 6pm')

    def test_entry_pages_are_private(self):
        make_premium(self.user)
        theirs = self._entry(user=self.other)
        for name, method in (('resources:worksheet_entry', 'get'),
                             ('resources:worksheet_entry_pdf', 'get'),
                             ('resources:worksheet_entry_coach', 'post'),
                             ('resources:worksheet_entry_delete', 'post')):
            resp = getattr(self.client, method)(reverse(name, args=[theirs.pk]))
            self.assertEqual(resp.status_code, 404, name)
        self.assertTrue(WorksheetEntry.objects.filter(pk=theirs.pk).exists())

    def test_entry_requires_login(self):
        entry = self._entry()
        self.client.logout()
        resp = self.client.get(entry.get_absolute_url())
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp['Location'])

    def test_premium_entry_page_is_editable(self):
        make_premium(self.user)
        entry = self._entry()
        resp = self.client.get(entry.get_absolute_url())
        self.assertContains(resp, 'Save changes')
        self.assertContains(resp, 'value="Friday 6pm"')
        self.assertContains(resp, 'Discuss with Anchor')
        self.assertContains(resp, 'noindex')

    def test_lapsed_user_can_read_and_delete_but_not_edit(self):
        entry = self._entry()
        make_free(self.user)
        resp = self.client.get(entry.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Friday 6pm')
        self.assertContains(resp, 'read-only')
        self.assertNotContains(resp, 'Save changes')
        resp = self.client.get(reverse('resources:worksheet_entry_pdf', args=[entry.pk]))
        self.assertIn(reverse('accounts:pricing'), resp['Location'])
        self.client.post(reverse('resources:worksheet_entry_delete', args=[entry.pk]))
        self.assertFalse(WorksheetEntry.objects.exists())

    def test_entry_pdf_for_premium(self):
        make_premium(self.user)
        entry = self._entry()
        with patch('resources.worksheet_service._pdf_from_html', return_value=b'%PDF-fake') as m:
            resp = self.client.get(reverse('resources:worksheet_entry_pdf', args=[entry.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'%PDF-fake')
        html = m.call_args[0][0]
        self.assertIn('Friday 6pm', html)

    def test_discuss_with_anchor_seeds_session(self):
        make_premium(self.user)
        old = RecoveryCoachSession.objects.create(user=self.user, is_active=True)
        entry = self._entry()
        resp = self.client.post(reverse('resources:worksheet_entry_coach', args=[entry.pk]))
        self.assertRedirects(resp, reverse('accounts:recovery_coach'), fetch_redirect_response=False)
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        session = RecoveryCoachSession.objects.get(user=self.user, is_active=True)
        self.assertEqual(session.title, 'Worksheet: Urge Log')
        msg = CoachMessage.objects.get(session=session)
        self.assertEqual(msg.role, 'assistant')
        self.assertIn('Friday 6pm', msg.content)
        self.assertIn('8/10', msg.content)

    def test_discuss_with_anchor_requires_post(self):
        make_premium(self.user)
        entry = self._entry()
        resp = self.client.get(reverse('resources:worksheet_entry_coach', args=[entry.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_my_worksheets_lists_only_mine(self):
        self._entry()
        self._entry(user=self.other, when='NOT-MINE')
        resp = self.client.get(reverse('resources:my_worksheets'))
        self.assertContains(resp, 'Friday 6pm')
        self.assertNotContains(resp, 'NOT-MINE')

    def test_index_shows_saved_counts(self):
        self._entry()
        self._entry()
        resp = self.client.get(reverse('resources:worksheets'))
        self.assertContains(resp, '2 saved')


@skipUnless(HAS_WEASYPRINT, 'WeasyPrint not available in this env')
class WorksheetRealPdfTests(TestCase):
    def test_every_blank_worksheet_renders(self):
        from resources.worksheet_service import render_blank_pdf
        cache.clear()
        for w in WORKSHEETS:
            pdf = render_blank_pdf(w)
            self.assertTrue(pdf.startswith(b'%PDF'), w.slug)
