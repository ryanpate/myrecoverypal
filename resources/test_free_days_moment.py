"""The upgrade moment right after a program's last free lesson."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from resources.models import ProgramEnrollment
from resources.programs import get_program
from resources.test_premium_gating import make_free, make_premium
from resources.test_programs import finish_days

User = get_user_model()
P = get_program('first-30-days')
FAMILY = get_program('family-and-friends')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FreeDaysDoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('fd', 'fd@example.com', 'pw12345!')
        self.client.force_login(self.user)

    def complete_last_free_day(self, program):
        e = ProgramEnrollment.objects.create(user=self.user, program_slug=program.slug)
        finish_days(e, program.free_days - 1)
        resp = self.client.post(reverse('resources:program_complete', args=[program.slug, program.free_days]))
        return self.client.get(resp['Location'])

    def test_free_member_sees_milestone_with_next_lesson(self):
        make_free(self.user)
        resp = self.complete_last_free_day(P)
        self.assertContains(resp, f'You finished the free week of {P.title}')
        nxt = P.lesson(P.free_days + 1)
        self.assertContains(resp, nxt.title.replace("'", '&#x27;'))
        self.assertContains(resp, f'{P.length - P.free_days} lessons left')
        self.assertContains(resp, 'data-promo="program_free_days_done"')
        self.assertContains(resp, f'href="{reverse("accounts:pricing")}"')
        import re
        self.assertIsNone(re.search(r'\$\d', resp.content.decode()))  # no web price (App Store 3.1)

    def test_trial_wording_only_when_eligible(self):
        make_free(self.user)
        sub = self.user.subscription
        eligible = sub.card_trial_eligible()
        resp = self.complete_last_free_day(P)
        self.assertEqual('try Premium free for 7 days' in resp.content.decode(), eligible)

    def test_premium_member_gets_normal_celebration(self):
        make_premium(self.user)
        resp = self.complete_last_free_day(P)
        self.assertNotContains(resp, 'pg-milestone')
        self.assertContains(resp, f'Day {P.free_days} complete')

    def test_not_shown_on_earlier_days_or_revisits(self):
        make_free(self.user)
        e = ProgramEnrollment.objects.create(user=self.user, program_slug=P.slug)
        resp = self.client.post(reverse('resources:program_complete', args=[P.slug, 1]))
        self.assertNotContains(self.client.get(resp['Location']), 'pg-milestone')
        e.completions.all().delete()
        finish_days(e, P.free_days)
        url = reverse('resources:program_day', args=[P.slug, P.free_days])
        self.assertNotContains(self.client.get(url), 'pg-milestone')  # no ?done=1

    def test_family_course_points_to_supporter_seat(self):
        make_free(self.user)
        resp = self.complete_last_free_day(FAMILY)
        self.assertContains(resp, 'Keep going with a Supporter seat')
        self.assertContains(resp, reverse('accounts:supporter_renew'))
        self.assertContains(resp, f'free {FAMILY.free_days} days')
