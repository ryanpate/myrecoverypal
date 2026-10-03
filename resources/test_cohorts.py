"""Tests for program cohorts (resources/cohorts.py)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import GroupMembership, Notification, RecoveryGroup
from resources.cohorts import (
    JOIN_WINDOW_DAYS, MAX_MEMBERS, SMALL_COHORT_MAX_AGE_DAYS, SMALL_COHORT_SIZE, join_cohort,
)
from resources.models import ProgramCohort, ProgramEnrollment

User = get_user_model()
SLUG = 'first-30-days'


class CohortTestMixin:
    n = 0

    def enrolled(self):
        CohortTestMixin.n += 1
        u = User.objects.create_user(
            username=f'c{self.n}', email=f'c{self.n}@example.com', password='x')
        return ProgramEnrollment.objects.create(user=u, program_slug=SLUG)

    def age(self, cohort, days):
        ProgramCohort.objects.filter(pk=cohort.pk).update(
            created_at=timezone.now() - timedelta(days=days))
        cohort.refresh_from_db()

    def fill(self, cohort, size):
        while cohort.group.memberships.filter(status='active').count() < size:
            e = self.enrolled()
            GroupMembership.objects.create(user=e.user, group=cohort.group, status='active')


class RollingRuleTests(CohortTestMixin, TestCase):
    def test_first_member_creates_secret_group(self):
        e = self.enrolled()
        cohort = join_cohort(e)
        group = cohort.group
        self.assertEqual(group.privacy_level, 'secret')
        self.assertEqual(group.max_members, MAX_MEMBERS)
        self.assertIn('First 30 Days cohort', group.name)
        self.assertTrue(GroupMembership.objects.filter(user=e.user, group=group, status='active').exists())
        e.refresh_from_db()
        self.assertEqual(e.cohort, cohort)

    def test_second_member_within_week_joins_same_cohort_and_members_are_told(self):
        a, b = self.enrolled(), self.enrolled()
        c1 = join_cohort(a)
        self.age(c1, JOIN_WINDOW_DAYS - 1)
        self.assertEqual(join_cohort(b), c1)
        n = Notification.objects.get(recipient=a.user)
        self.assertIn('cohort', n.title)
        self.assertEqual(n.link, f'/accounts/groups/{c1.group_id}/')
        self.assertFalse(Notification.objects.filter(recipient=b.user).exists())

    def test_small_cohort_stays_open_up_to_three_weeks(self):
        c1 = join_cohort(self.enrolled())
        self.age(c1, JOIN_WINDOW_DAYS + 3)
        self.assertEqual(join_cohort(self.enrolled()), c1)
        self.age(c1, SMALL_COHORT_MAX_AGE_DAYS + 1)
        self.assertNotEqual(join_cohort(self.enrolled()), c1)

    def test_established_cohort_closes_after_a_week(self):
        c1 = join_cohort(self.enrolled())
        self.fill(c1, SMALL_COHORT_SIZE)
        self.age(c1, JOIN_WINDOW_DAYS + 1)
        self.assertNotEqual(join_cohort(self.enrolled()), c1)

    def test_full_cohort_opens_a_new_one(self):
        c1 = join_cohort(self.enrolled())
        self.fill(c1, MAX_MEMBERS)
        self.assertNotEqual(join_cohort(self.enrolled()), c1)

    def test_idempotent(self):
        e = self.enrolled()
        c1 = join_cohort(e)
        self.assertEqual(join_cohort(e), c1)
        self.assertEqual(ProgramCohort.objects.count(), 1)
        self.assertEqual(GroupMembership.objects.filter(user=e.user).count(), 1)

    def test_rejoin_after_leaving_returns_to_same_cohort(self):
        e = self.enrolled()
        c1 = join_cohort(e)
        GroupMembership.objects.filter(user=e.user, group=c1.group).update(status='left')
        self.age(c1, 60)  # long closed to newcomers
        self.assertEqual(join_cohort(e), c1)
        self.assertEqual(GroupMembership.objects.get(user=e.user, group=c1.group).status, 'active')

    def test_ban_is_never_undone(self):
        e = self.enrolled()
        c1 = join_cohort(e)
        GroupMembership.objects.filter(user=e.user, group=c1.group).update(status='banned')
        self.assertIsNone(join_cohort(e))
        self.assertEqual(GroupMembership.objects.get(user=e.user, group=c1.group).status, 'banned')

    def test_archived_cohort_is_not_reused(self):
        c1 = join_cohort(self.enrolled())
        RecoveryGroup.objects.filter(pk=c1.group_id).update(is_active=False)
        self.assertNotEqual(join_cohort(self.enrolled()), c1)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CohortViewTests(CohortTestMixin, TestCase):
    def setUp(self):
        self.e = self.enrolled()
        self.client.force_login(self.e.user)
        self.join_url = reverse('resources:program_cohort_join', args=[SLUG])

    def test_program_page_offers_join_then_shows_cohort(self):
        detail = reverse('resources:program_detail', args=[SLUG])
        self.assertContains(self.client.get(detail), 'Join cohort')
        resp = self.client.post(self.join_url)
        cohort = ProgramCohort.objects.get()
        self.assertRedirects(resp, reverse('accounts:group_detail', args=[cohort.group_id]),
                             fetch_redirect_response=False)
        resp = self.client.get(detail)
        self.assertContains(resp, 'Your cohort: 1 member')
        self.assertNotContains(resp, 'Join cohort')

    def test_lesson_page_links_to_cohort(self):
        self.assertContains(self.client.get(reverse('resources:program_day', args=[SLUG, 1])),
                            'Join cohort')
        self.client.post(self.join_url)
        resp = self.client.get(reverse('resources:program_day', args=[SLUG, 1]))
        self.assertContains(resp, "Talk about today's lesson with your cohort")

    def test_join_requires_enrollment_and_post(self):
        other = User.objects.create_user(username='noenroll', email='n@example.com', password='x')
        self.client.force_login(other)
        resp = self.client.post(self.join_url)
        self.assertRedirects(resp, reverse('resources:program_detail', args=[SLUG]),
                             fetch_redirect_response=False)
        self.assertFalse(ProgramCohort.objects.exists())
        self.assertEqual(self.client.get(self.join_url).status_code, 405)

    def test_group_page_shows_cohort_card_not_creator(self):
        self.client.post(self.join_url)
        cohort = ProgramCohort.objects.get()
        resp = self.client.get(reverse('accounts:group_detail', args=[cohort.group_id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'First 30 Days cohort')
        self.assertNotContains(resp, 'Group Creator')

    def test_cohort_hidden_from_non_members(self):
        self.client.post(self.join_url)
        cohort = ProgramCohort.objects.get()
        outsider = User.objects.create_user(username='out', email='out@example.com', password='x')
        self.client.force_login(outsider)
        resp = self.client.get(reverse('accounts:group_detail', args=[cohort.group_id]))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.get(reverse('accounts:groups_list'))
        self.assertNotContains(resp, cohort.group.name)

    def test_banned_member_sees_no_join_card(self):
        self.client.post(self.join_url)
        cohort = ProgramCohort.objects.get()
        GroupMembership.objects.filter(user=self.e.user).update(status='banned')
        resp = self.client.get(reverse('resources:program_detail', args=[SLUG]))
        self.assertNotContains(resp, 'Join cohort')
        resp = self.client.post(self.join_url)
        self.assertRedirects(resp, reverse('resources:program_detail', args=[SLUG]),
                             fetch_redirect_response=False)
        self.assertEqual(GroupMembership.objects.get(user=self.e.user, group=cohort.group).status, 'banned')

    def test_ordinary_groups_still_show_creator(self):
        g = RecoveryGroup.objects.create(name='Plain', description='x', group_type='interest',
                                         privacy_level='public', creator=self.e.user)
        resp = self.client.get(reverse('accounts:group_detail', args=[g.id]))
        self.assertContains(resp, 'Group Creator')
