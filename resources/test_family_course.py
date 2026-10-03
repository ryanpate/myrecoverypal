"""Tests for the family & friends course and the family worksheets."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.supporter_models import SupporterLink
from resources.access import has_program_access, user_has_supporter_access
from resources.models import ProgramDayCompletion, ProgramEnrollment, WorksheetEntry
from resources.program_service import get_progress
from resources.programs import FAMILY_PROGRAMS, get_program
from resources.test_premium_gating import make_free, make_premium
from resources.test_program_tracks import PHONE_RE, all_text
from resources.worksheets import get_worksheet

User = get_user_model()
SLUG = 'family-and-friends'
FAMILY = get_program(SLUG)
ALLOWED_NUMBERS = {'988', '911', '1-800-662-4357', '1-800-799-7233'}


def make_supporter(user):
    user.subscription.tier = 'supporter'
    user.subscription.status = 'active'
    user.subscription.save()


def user(name):
    return User.objects.create_user(username=name, email=f'{name}@example.com', password='x')


class FamilyContentTests(TestCase):
    def test_shape(self):
        self.assertEqual(FAMILY_PROGRAMS, [FAMILY])
        self.assertEqual((FAMILY.kind, FAMILY.access, FAMILY.free_days, FAMILY.length),
                         ('family', 'family', 3, 14))
        for lesson in FAMILY.lessons:
            self.assertTrue(lesson.prompt.endswith('?'), lesson.day)
            if lesson.action:
                try:
                    reverse(lesson.action.url_name, args=lesson.action.args)
                except NoReverseMatch:
                    self.fail(f'day {lesson.day}: {lesson.action.url_name}')

    def test_only_approved_numbers_and_no_statistics(self):
        text = all_text(FAMILY)
        for number in PHONE_RE.findall(text):
            self.assertIn(number, ALLOWED_NUMBERS, number)
        self.assertNotIn('%', text)

    def test_safety_lesson(self):
        text = all_text(FAMILY).lower()
        for term in ('911', 'naloxone', '1-800-799-7233', 'overdose', '988'):
            self.assertIn(term, text)
        # Never steer families toward confrontations or ultimatums.
        self.assertNotIn('intervention', text)
        self.assertNotIn('ultimatum', text)

    def test_safety_lesson_is_free(self):
        """Never paywall safety: the safety lesson must be inside the free days."""
        safety = [l for l in FAMILY.lessons if '1-800-799-7233' in ' '.join(l.paragraphs)]
        self.assertTrue(safety)
        self.assertLessEqual(safety[0].day, FAMILY.free_days)

    def test_family_worksheets_registered(self):
        for slug in ('boundaries-plan', 'conversation-planner'):
            ws = get_worksheet(slug)
            self.assertEqual(ws.audience, 'family', slug)
            if ws.title_field:
                self.assertIn(ws.title_field, ws.fields_by_key)


class FamilyAccessTests(TestCase):
    def test_free_user_has_no_access(self):
        u = user('free')
        make_free(u)
        self.assertFalse(user_has_supporter_access(u))
        self.assertFalse(has_program_access(u, FAMILY))

    def test_paid_supporter_has_access_to_family_but_not_member_programs(self):
        u = user('sup')
        make_supporter(u)
        self.assertTrue(has_program_access(u, FAMILY))
        self.assertFalse(has_program_access(u, get_program('first-30-days')))

    def test_included_seat_from_premium_member(self):
        member, sup = user('member'), user('seat')
        make_premium(member)
        make_free(sup)
        SupporterLink.objects.create(member=member, supporter=sup, status='active',
                                     initiated_by='member', consented_at=timezone.now())
        self.assertTrue(has_program_access(sup, FAMILY))
        make_free(member)  # seat lapses with the member's Premium
        self.assertFalse(has_program_access(sup, FAMILY))

    def test_premium_user_has_access(self):
        u = user('prem')
        make_premium(u)
        self.assertTrue(has_program_access(u, FAMILY))

    def test_pacing_locks_day_4_for_free_user_only(self):
        for name, setup, expected in (('f', make_free, 'premium'), ('s', make_supporter, 'current')):
            u = user(name)
            setup(u)
            e = ProgramEnrollment.objects.create(user=u, program_slug=SLUG)
            for d in (1, 2, 3):
                ProgramDayCompletion.objects.create(enrollment=e, day=d, completed_on=date(2026, 1, d))
            self.assertEqual(get_progress(e, u, date(2026, 2, 1)).next_status, expected, name)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FamilyPageTests(TestCase):
    def setUp(self):
        self.u = user('fp')
        make_free(self.u)
        self.client.force_login(self.u)

    def test_overview_upsell_points_to_supporter_seat(self):
        resp = self.client.get(reverse('resources:program_detail', args=[SLUG]))
        self.assertContains(resp, 'Finish all 14 days with a Supporter seat')
        self.assertContains(resp, reverse('accounts:supporter_renew'))
        self.assertContains(resp, '1-800-799-7233')

    def test_day_4_lock_and_complete_redirect_to_supporter_page(self):
        e = ProgramEnrollment.objects.create(user=self.u, program_slug=SLUG)
        for d in (1, 2, 3):
            ProgramDayCompletion.objects.create(
                enrollment=e, day=d, completed_on=timezone.localdate() - timedelta(days=5 - d))
        resp = self.client.get(reverse('resources:program_day', args=[SLUG, 4]))
        self.assertContains(resp, 'Keep going with a Supporter seat')
        resp = self.client.post(reverse('resources:program_complete', args=[SLUG, 4]))
        self.assertIn(reverse('accounts:supporter_renew'), resp['Location'])

    def test_member_programs_still_upsell_premium(self):
        resp = self.client.get(reverse('resources:program_detail', args=['first-30-days']))
        self.assertContains(resp, 'Finish all 30 days with Premium')

    def test_index_and_worksheet_index_have_family_sections(self):
        resp = self.client.get(reverse('resources:programs'))
        self.assertContains(resp, 'For family &amp; friends')
        self.assertContains(resp, reverse('resources:program_detail', args=[SLUG]))
        resp = self.client.get(reverse('resources:worksheets'))
        self.assertContains(resp, reverse('resources:worksheet_detail', args=['boundaries-plan']))

    def test_landing_page_promotes_course(self):
        resp = self.client.get(reverse('core:support_a_loved_one'))
        self.assertContains(resp, reverse('resources:program_detail', args=[SLUG]))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FamilyWorksheetTests(TestCase):
    def setUp(self):
        self.u = user('fw')
        self.client.force_login(self.u)

    def test_supporter_can_save_family_worksheet_but_not_member_ones(self):
        make_supporter(self.u)
        resp = self.client.post(reverse('resources:worksheet_save', args=['boundaries-plan']),
                                {'situation': 'Lending money', 'boundary': "I won't give cash"})
        entry = WorksheetEntry.objects.get()
        self.assertRedirects(resp, entry.get_absolute_url(), fetch_redirect_response=False)
        resp = self.client.post(reverse('resources:worksheet_save', args=['urge-log']), {'when': 'now'})
        self.assertIn(reverse('accounts:pricing'), resp['Location'])
        self.assertEqual(WorksheetEntry.objects.count(), 1)

    def test_free_user_sent_to_supporter_page(self):
        make_free(self.u)
        resp = self.client.get(reverse('resources:worksheet_detail', args=['conversation-planner']))
        self.assertContains(resp, 'Save my answers (Supporter seat)')
        resp = self.client.post(reverse('resources:worksheet_save', args=['conversation-planner']),
                                {'goal': 'x'})
        self.assertIn(reverse('accounts:supporter_renew'), resp['Location'])
        self.assertFalse(WorksheetEntry.objects.exists())

    def test_no_anchor_for_family_worksheets(self):
        make_premium(self.u)
        entry = WorksheetEntry.objects.create(user=self.u, worksheet_slug='boundaries-plan',
                                              data={'situation': 'x'})
        resp = self.client.get(entry.get_absolute_url())
        self.assertNotContains(resp, 'Discuss with Anchor')
        resp = self.client.post(reverse('resources:worksheet_entry_coach', args=[entry.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_supporter_can_export_family_entry(self):
        make_supporter(self.u)
        entry = WorksheetEntry.objects.create(user=self.u, worksheet_slug='boundaries-plan',
                                              data={'situation': 'x'})
        from unittest.mock import patch
        with patch('resources.worksheet_service._pdf_from_html', return_value=b'%PDF-x'):
            resp = self.client.get(reverse('resources:worksheet_entry_pdf', args=[entry.pk]))
        self.assertEqual(resp.status_code, 200)
