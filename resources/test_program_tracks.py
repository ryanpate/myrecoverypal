"""Tests for substance-specific program tracks and per-program free days."""
import re
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from resources.models import ProgramDayCompletion, ProgramEnrollment
from resources.program_service import get_progress
from resources.programs import PROGRAMS, TRACK_PROGRAMS, get_program
from resources.tasks import remind_enrollment
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()

ALLOWED_HELPLINES = {
    ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
    ('National Problem Gambling Helpline', '1-800-GAMBLER'),
    ('988 Suicide & Crisis Lifeline', '988'),
}
# Anything that looks like a phone number in lesson text must be one of these.
ALLOWED_NUMBERS = {'988', '911', '1-800-662-4357', '1-800-GAMBLER'}
PHONE_RE = re.compile(r'\b1-800-[A-Z0-9-]+\b|\b\d{3}-\d{3}-\d{4}\b|\b9[18][18]\b')


def all_text(program):
    parts = [program.title, program.summary, program.intro, program.audience, program.meta_description]
    for lesson in program.lessons:
        parts += [lesson.title, lesson.prompt, *lesson.paragraphs]
        if lesson.action:
            parts += [lesson.action.label, lesson.action.detail]
    return '\n'.join(parts)


class TrackContentTests(TestCase):
    def test_five_tracks(self):
        self.assertEqual(
            sorted(p.substance for p in TRACK_PROGRAMS),
            ['Alcohol', 'Cannabis', 'Gambling', 'Opioids', 'Stimulants'])

    def test_slugs_unique(self):
        slugs = [p.slug for p in PROGRAMS]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_track_shape(self):
        for p in TRACK_PROGRAMS:
            self.assertEqual(p.kind, 'track', p.slug)
            self.assertEqual(p.length, 14, p.slug)
            self.assertEqual(p.free_days, 3, p.slug)
            self.assertEqual(len(p.weeks), 2, p.slug)
            self.assertLessEqual(len(p.meta_description), 160, p.slug)
            self.assertGreaterEqual(sum(1 for l in p.lessons if l.action), 9, p.slug)
            for lesson in p.lessons:
                self.assertIn(len(lesson.paragraphs), (2, 3), f'{p.slug} day {lesson.day}')
                self.assertTrue(lesson.prompt.endswith('?'), f'{p.slug} day {lesson.day}')

    def test_actions_reverse(self):
        for p in TRACK_PROGRAMS:
            for lesson in p.lessons:
                if lesson.action:
                    try:
                        reverse(lesson.action.url_name, args=lesson.action.args)
                    except NoReverseMatch:
                        self.fail(f'{p.slug} day {lesson.day}: {lesson.action.url_name}')

    def test_helplines_only_from_allowed_list(self):
        for p in TRACK_PROGRAMS:
            self.assertTrue(p.helplines, p.slug)
            for row in p.helplines:
                self.assertIn(row, ALLOWED_HELPLINES, p.slug)

    def test_no_unapproved_phone_numbers_or_statistics(self):
        for p in TRACK_PROGRAMS:
            text = all_text(p)
            for number in PHONE_RE.findall(text):
                self.assertIn(number, ALLOWED_NUMBERS, f'{p.slug}: {number}')
            self.assertNotIn('%', text, p.slug)
            self.assertNotRegex(text.lower(), r'\bpercent\b', p.slug)

    def test_safety_messaging_present(self):
        text = {p.substance: all_text(p).lower() for p in TRACK_PROGRAMS}
        self.assertIn('seizure', text['Alcohol'])
        self.assertIn('doctor', text['Alcohol'])
        self.assertIn('naloxone', text['Opioids'])
        self.assertIn('overdose', text['Opioids'])
        self.assertIn('tolerance', text['Opioids'])
        self.assertIn('988', text['Stimulants'])
        self.assertIn('self-exclusion', text['Gambling'])

    def test_gambling_helpline_dials_digits(self):
        rows = get_program('gambling-14-days').helpline_rows
        self.assertIn(('National Problem Gambling Helpline', '1-800-GAMBLER', '18004262537'), rows)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class TrackPageTests(TestCase):
    def test_index_lists_core_and_tracks(self):
        resp = self.client.get(reverse('resources:programs'))
        self.assertContains(resp, 'Tracks by substance')
        for p in PROGRAMS:
            self.assertContains(resp, reverse('resources:program_detail', args=[p.slug]))

    def test_track_overview_shows_free_days_and_helplines(self):
        for p in TRACK_PROGRAMS:
            resp = self.client.get(reverse('resources:program_detail', args=[p.slug]))
            self.assertEqual(resp.status_code, 200, p.slug)
            self.assertContains(resp, 'First 3 days free')
            self.assertContains(resp, 'In an emergency, call')
            self.assertContains(resp, p.substance)

    def test_sitemap_lists_tracks(self):
        resp = self.client.get('/sitemap.xml')
        if b'sitemapindex' in resp.content:
            resp = self.client.get('/sitemap-programs.xml')
        for p in TRACK_PROGRAMS:
            self.assertContains(resp, reverse('resources:program_detail', args=[p.slug]))

    def test_every_track_lesson_renders(self):
        user = User.objects.create_user(username='tr', email='tr@example.com', password='x')
        make_premium(user)
        self.client.force_login(user)
        for p in TRACK_PROGRAMS:
            e = ProgramEnrollment.objects.create(user=user, program_slug=p.slug)
            for day in range(1, p.length + 1):
                resp = self.client.get(reverse('resources:program_day', args=[p.slug, day]))
                self.assertEqual(resp.status_code, 200, f'{p.slug} day {day}')
                ProgramDayCompletion.objects.create(
                    enrollment=e, day=day, completed_on=date(2026, 1, 1) + timedelta(days=day))


class TrackPacingTests(TestCase):
    def test_free_member_stops_after_three_days_on_a_track(self):
        user = User.objects.create_user(username='tf', email='tf@example.com', password='x')
        make_free(user)
        e = ProgramEnrollment.objects.create(user=user, program_slug='cannabis-14-days')
        for d in (1, 2, 3):
            ProgramDayCompletion.objects.create(enrollment=e, day=d, completed_on=date(2026, 1, d))
        p = get_progress(e, user, date(2026, 2, 1))
        self.assertEqual((p.next_day, p.next_status), (4, 'premium'))


@patch('apps.accounts.push_notifications.send_push_to_user', return_value={})
@patch('apps.accounts.email_service.send_email', return_value=(True, None))
class OneReminderPerDayTests(TestCase):
    def test_member_in_two_programs_gets_one_reminder(self, send_email, push):
        user = User.objects.create_user(username='two', email='two@example.com', password='x',
                                        timezone='America/New_York')
        make_premium(user)
        a = ProgramEnrollment.objects.create(user=user, program_slug='first-30-days')
        b = ProgramEnrollment.objects.create(user=user, program_slug='alcohol-14-days')
        nine = datetime.now(ZoneInfo('America/New_York')).replace(hour=9, minute=10)
        self.assertEqual(remind_enrollment(a, nine), {'push'})
        b.refresh_from_db()
        self.assertEqual(remind_enrollment(b, nine), set())
        # Next day the other program can go first.
        self.assertEqual(remind_enrollment(b, nine + timedelta(days=1)), {'push'})
