"""Tests for guided day-by-day programs."""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.journal.models import JournalEntry
from resources.models import ProgramDayCompletion, ProgramEnrollment
from resources.program_service import complete_day, get_progress
from resources.programs import FREE_DAYS, PROGRAMS, get_program
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()
P = get_program('first-30-days')


def finish_days(enrollment, days, start=date(2026, 1, 1)):
    """Mark days 1..days complete on consecutive past dates."""
    for d in range(1, days + 1):
        ProgramDayCompletion.objects.create(
            enrollment=enrollment, day=d, completed_on=start + timedelta(days=d - 1))


class ProgramContentTests(TestCase):
    def test_first_30_days_has_30_lessons_numbered(self):
        self.assertEqual(P.length, 30)
        self.assertEqual([l.day for l in P.lessons], list(range(1, 31)))

    def test_every_action_url_reverses(self):
        for program in PROGRAMS:
            for lesson in program.lessons:
                if lesson.action:
                    try:
                        reverse(lesson.action.url_name, args=lesson.action.args)
                    except NoReverseMatch:
                        self.fail(f'{program.slug} day {lesson.day}: {lesson.action.url_name}')

    def test_lessons_well_formed(self):
        for lesson in P.lessons:
            self.assertGreaterEqual(len(lesson.paragraphs), 2, lesson.day)
            self.assertTrue(lesson.prompt.endswith('?'), lesson.day)

    def test_week_titles(self):
        self.assertTrue(P.week_title(1).startswith('Week 1'))
        self.assertTrue(P.week_title(8).startswith('Week 2'))
        self.assertTrue(P.week_title(30).startswith('Days 29-30'))


class PacingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pace', email='pace@example.com', password='x')
        make_premium(self.user)
        self.enrollment = ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        self.today = date(2026, 3, 10)

    def test_day_one_open_on_enrollment(self):
        p = get_progress(self.enrollment, self.user, self.today)
        self.assertEqual((p.next_day, p.next_status), (1, 'current'))
        self.assertEqual(p.status(2), 'locked')

    def test_one_lesson_per_day(self):
        self.assertTrue(complete_day(self.enrollment, self.user, 1, self.today))
        p = get_progress(self.enrollment, self.user, self.today)
        self.assertEqual((p.next_day, p.next_status), (2, 'waiting'))
        self.assertFalse(complete_day(self.enrollment, self.user, 2, self.today))
        tomorrow = self.today + timedelta(days=1)
        self.assertEqual(get_progress(self.enrollment, self.user, tomorrow).next_status, 'current')
        self.assertTrue(complete_day(self.enrollment, self.user, 2, tomorrow))

    def test_missed_days_resume_where_left_off(self):
        complete_day(self.enrollment, self.user, 1, self.today)
        later = self.today + timedelta(days=12)
        p = get_progress(self.enrollment, self.user, later)
        self.assertEqual((p.next_day, p.next_status), (2, 'current'))

    def test_cannot_skip_ahead(self):
        self.assertFalse(complete_day(self.enrollment, self.user, 3, self.today))
        self.assertFalse(ProgramDayCompletion.objects.exists())

    def test_free_member_stops_after_free_days(self):
        make_free(self.user)
        finish_days(self.enrollment, FREE_DAYS)
        p = get_progress(self.enrollment, self.user, self.today)
        self.assertEqual((p.next_day, p.next_status), (FREE_DAYS + 1, 'premium'))
        self.assertTrue(p.can_read(1))
        self.assertFalse(p.can_read(FREE_DAYS + 1))
        self.assertFalse(complete_day(self.enrollment, self.user, FREE_DAYS + 1, self.today))

    def test_finishing_marks_enrollment_complete(self):
        finish_days(self.enrollment, P.length - 1)
        self.assertTrue(complete_day(self.enrollment, self.user, P.length, self.today))
        self.enrollment.refresh_from_db()
        self.assertIsNotNone(self.enrollment.completed_at)
        p = get_progress(self.enrollment, self.user, self.today)
        self.assertTrue(p.finished)
        self.assertEqual(p.percent, 100)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgramViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pv', email='pv@example.com', password='x')
        self.client.force_login(self.user)

    def test_index_and_overview_public(self):
        self.client.logout()
        resp = self.client.get(reverse('resources:programs'))
        self.assertContains(resp, P.title)
        resp = self.client.get(reverse('resources:program_detail', args=[P.slug]))
        self.assertContains(resp, 'Join free to start')
        self.assertContains(resp, P.lessons[0].title)
        self.assertContains(resp, P.lessons[-1].title)

    def test_lessons_need_login_and_enrollment(self):
        self.client.logout()
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 1]))
        self.assertIn('login', resp['Location'])
        self.client.force_login(self.user)
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 1]))
        self.assertRedirects(resp, reverse('resources:program_detail', args=[P.slug]),
                             fetch_redirect_response=False)

    def test_enroll_read_complete_flow(self):
        make_free(self.user)
        resp = self.client.post(reverse('resources:program_enroll', args=[P.slug]))
        self.assertRedirects(resp, reverse('resources:program_day', args=[P.slug, 1]),
                             fetch_redirect_response=False)
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 1]))
        self.assertContains(resp, P.lessons[0].paragraphs[0][:30])
        self.assertContains(resp, 'Mark Day 1 complete')
        self.assertContains(resp, reverse(P.lessons[0].action.url_name))
        resp = self.client.post(reverse('resources:program_complete', args=[P.slug, 1]))
        self.assertRedirects(resp, reverse('resources:program_day', args=[P.slug, 1]) + '?done=1',
                             fetch_redirect_response=False)
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 1]) + '?done=1')
        self.assertContains(resp, 'Day 1 complete')
        self.assertContains(resp, 'opens tomorrow')
        # Day 2 waits until tomorrow.
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 2]))
        self.assertRedirects(resp, reverse('resources:program_detail', args=[P.slug]),
                             fetch_redirect_response=False)

    def test_enroll_requires_post(self):
        resp = self.client.get(reverse('resources:program_enroll', args=[P.slug]))
        self.assertEqual(resp.status_code, 405)

    def test_free_member_sees_premium_lock_on_day_8(self):
        make_free(self.user)
        e = ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        finish_days(e, FREE_DAYS)
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, FREE_DAYS + 1]))
        self.assertContains(resp, 'Continue with Premium')
        self.assertNotContains(resp, P.lessons[FREE_DAYS].paragraphs[0][:30])
        resp = self.client.post(reverse('resources:program_complete', args=[P.slug, FREE_DAYS + 1]))
        self.assertIn(reverse('accounts:pricing'), resp['Location'])
        # Completed lessons stay readable.
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, 3]))
        self.assertContains(resp, P.lessons[2].paragraphs[0][:30])

    def test_premium_member_continues_past_free_days(self):
        make_premium(self.user)
        e = ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        finish_days(e, FREE_DAYS)
        resp = self.client.get(reverse('resources:program_day', args=[P.slug, FREE_DAYS + 1]))
        self.assertContains(resp, f'Mark Day {FREE_DAYS + 1} complete')

    def test_journal_from_lesson(self):
        ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        url = reverse('resources:program_journal', args=[P.slug, 1])
        resp = self.client.get(url)
        self.assertContains(resp, 'First 30 Days, Day 1')
        self.client.post(url, {'title': 'First 30 Days, Day 1: You started', 'content': 'Because.'})
        self.assertTrue(JournalEntry.objects.filter(user=self.user, content='Because.').exists())

    def test_restart(self):
        e = ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        finish_days(e, 3)
        self.client.post(reverse('resources:program_restart', args=[P.slug]))
        e2 = ProgramEnrollment.objects.get(user=self.user)
        self.assertFalse(e2.completions.exists())

    def test_progress_home_card(self):
        self.user.sobriety_date = timezone.localdate() - timedelta(days=5)
        self.user.save()
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'New: the First 30 Days program')
        ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'First 30 Days: Day 1 of 30')
        self.assertContains(resp, reverse('resources:program_day', args=[P.slug, 1]))

    def test_progress_home_card_hidden_for_long_term_members(self):
        self.user.sobriety_date = timezone.localdate() - timedelta(days=400)
        self.user.save()
        resp = self.client.get(reverse('accounts:progress'))
        self.assertNotContains(resp, 'First 30 Days')

    def test_unknown_program_and_day_404(self):
        self.assertEqual(self.client.get(reverse('resources:program_detail', args=['nope'])).status_code, 404)
        ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        self.assertEqual(self.client.get(reverse('resources:program_day', args=[P.slug, 99])).status_code, 404)

    def test_sitemap_and_hub(self):
        resp = self.client.get(reverse('resources:list'))
        self.assertContains(resp, reverse('resources:programs'))
        resp = self.client.get('/sitemap.xml')
        if b'sitemapindex' in resp.content:
            resp = self.client.get('/sitemap-programs.xml')
        self.assertContains(resp, reverse('resources:program_detail', args=[P.slug]))
