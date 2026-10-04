"""The library section of the weekly digest (resources/digest.py)."""
import shutil
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.tasks import send_weekly_digests
from resources.digest import library_block
from resources.models import ProgramDayCompletion, ProgramEnrollment
from resources.reflections import reflection_for_date
from resources.test_audio import make_track
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()
SEND = 'apps.accounts.tasks.send_email'
SITE = 'https://www.myrecoverypal.com'


def run_digests():
    return send_weekly_digests.si().apply().result if hasattr(send_weekly_digests, 'si') else send_weekly_digests()


@override_settings(SITE_URL=SITE)
class LibraryBlockTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.user = User.objects.create_user('dg', 'dg@example.com', 'pw12345!')
        make_free(self.user)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def test_reflection_with_card_and_utm(self):
        day = date(2026, 10, 4)
        b = library_block(self.user, SITE, today=day)
        r = reflection_for_date(day)
        self.assertEqual(b['reflection']['title'], r.title)
        self.assertTrue(b['reflection']['card_url'].endswith(f'/resources/reflections/{r.slug}/card.png?format=og'))
        self.assertIn('utm_campaign=weekly_library', b['reflection']['url'])
        self.assertNotIn('session', b)  # no audio generated yet
        self.assertNotIn('program', b)

    def test_session_rotates_weekly_and_marks_locked(self):
        make_track('urge-surfing', free=True, category='cravings')
        paid = make_track('body-scan')
        paid.preview.save('p.mp3', paid.audio.file, save=True)
        picks = {library_block(self.user, SITE, today=date(2026, 10, 4) + timedelta(weeks=w))['session']['title']
                 for w in range(4)}
        self.assertEqual(len(picks), 2)
        for w in range(4):
            s = library_block(self.user, SITE, today=date(2026, 10, 4) + timedelta(weeks=w))['session']
            if s['title'] == 'Body-Scan':
                self.assertTrue(s['locked'] and s['preview'])
            else:
                self.assertFalse(s['locked'])
        make_premium(self.user)
        for w in range(4):
            self.assertFalse(library_block(self.user, SITE, today=date(2026, 10, 4) + timedelta(weeks=w))['session']['locked'])

    def test_open_program_lesson(self):
        e = ProgramEnrollment.objects.create(user=self.user, program_slug='first-30-days')
        ProgramDayCompletion.objects.create(enrollment=e, day=1, completed_on=date(2026, 10, 1))
        b = library_block(self.user, SITE, today=date(2026, 10, 4))
        self.assertEqual(b['program']['day'], 2)
        self.assertEqual(b['program']['title'], e.program.title)
        self.assertEqual(b['program']['lesson'], e.program.lesson(2).title)


@override_settings(SITE_URL=SITE)
class DigestSendingTests(TestCase):
    def member(self, name, last_login_days_ago):
        u = User.objects.create_user(name, f'{name}@example.com', 'pw12345!')
        last = None if last_login_days_ago is None else timezone.now() - timedelta(days=last_login_days_ago)
        User.objects.filter(pk=u.pk).update(last_login=last)
        return u

    @patch(SEND, return_value=(True, None))
    def test_quiet_but_recent_member_gets_library_digest(self, send):
        self.member('recent', 10)
        self.member('dormant', 200)
        self.member('never', None)
        run_digests()
        recipients = [c.kwargs['recipient_email'] for c in send.call_args_list]
        self.assertEqual(recipients, ['recent@example.com'])
        html = send.call_args.kwargs['html_message']
        self.assertIn("This week's reflection", html)
        self.assertIn('/card.png?format=og', html)

    @patch(SEND, return_value=(True, None))
    def test_opted_out_never_gets_it(self, send):
        u = self.member('optout', 1)
        User.objects.filter(pk=u.pk).update(email_notifications=False)
        run_digests()
        send.assert_not_called()
