"""Tests for scheduled posts in the social feed."""
from datetime import timedelta, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    ActivityFeed, Notification, PostReaction, SocialPost, SocialPostComment,
)

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ScheduledPostTestCase(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', email='author@example.com', password='x')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='x')
        self.feed_url = reverse('accounts:social_feed')
        self.api_url = reverse('accounts:social_feed_posts_api')

    def schedule(self, content='Queued for later', hours=2, **kwargs):
        return SocialPost.objects.create(
            author=self.author, content=content,
            scheduled_at=timezone.now() + timedelta(hours=hours), **kwargs)

    def api_contents(self):
        return [p['content'] for p in self.client.get(self.api_url).json()['posts']]


class ScheduledPostVisibilityTests(ScheduledPostTestCase):
    def test_hidden_from_other_members_until_its_time(self):
        self.schedule()
        self.client.force_login(self.other)

        self.assertNotContains(self.client.get(self.feed_url), 'Queued for later')
        self.assertNotIn('Queued for later', self.api_contents())
        self.assertNotContains(
            self.client.get(reverse('accounts:dashboard')), 'Queued for later')

    def test_hidden_from_logged_out_visitors(self):
        self.schedule()
        self.assertNotContains(self.client.get(self.feed_url), 'Queued for later')
        self.assertNotIn('Queued for later', self.api_contents())

    def test_author_sees_it_in_the_scheduled_list_only(self):
        post = self.schedule()
        self.client.force_login(self.author)
        resp = self.client.get(self.feed_url)

        self.assertEqual(list(resp.context['scheduled_posts']), [post])
        self.assertContains(resp, 'id="scheduledPosts"')
        self.assertContains(resp, 'Queued for later')
        # Not in the feed itself, for the author either
        self.assertNotIn(post, list(resp.context['posts']))
        self.assertNotIn('Queued for later', self.api_contents())

    def test_other_members_get_no_scheduled_list(self):
        self.schedule()
        self.client.force_login(self.other)
        resp = self.client.get(self.feed_url)
        self.assertEqual(list(resp.context['scheduled_posts']), [])
        self.assertNotContains(resp, 'id="scheduledPosts"')

    def test_appears_for_everyone_once_the_time_passes(self):
        post = self.schedule(hours=2)
        later = timezone.now() + timedelta(hours=3)
        self.client.force_login(self.other)

        with mock.patch('django.utils.timezone.now', return_value=later):
            self.assertContains(self.client.get(self.feed_url), 'Queued for later')
            self.assertIn('Queued for later', self.api_contents())

            self.client.force_login(self.author)
            resp = self.client.get(self.feed_url)
            self.assertIn(post, list(resp.context['posts']))
            self.assertEqual(list(resp.context['scheduled_posts']), [])

    def test_sorted_by_publish_time_not_created_time(self):
        now = timezone.now()
        # Written yesterday, went live a minute ago
        scheduled = SocialPost.objects.create(
            author=self.author, content='scheduled',
            scheduled_at=now - timedelta(minutes=1))
        SocialPost.objects.filter(pk=scheduled.pk).update(
            created_at=now - timedelta(days=1))
        # Posted an hour ago, after the scheduled one was written
        older = SocialPost.objects.create(author=self.other, content='hour ago')
        SocialPost.objects.filter(pk=older.pk).update(
            created_at=now - timedelta(hours=1))
        newest = SocialPost.objects.create(author=self.other, content='just now')

        self.client.force_login(self.other)
        resp = self.client.get(self.feed_url)
        self.assertEqual(
            [p.pk for p in resp.context['posts']],
            [newest.pk, scheduled.pk, older.pk])
        self.assertEqual(self.api_contents(), ['just now', 'scheduled', 'hour ago'])

    def test_posts_without_a_time_are_published_right_away(self):
        SocialPost.objects.create(author=self.author, content='Right now')
        self.client.force_login(self.other)
        self.assertContains(self.client.get(self.feed_url), 'Right now')

    def test_not_counted_before_it_is_live(self):
        self.schedule()
        self.assertEqual(SocialPost.objects.live().count(), 0)
        self.assertEqual(SocialPost.objects.scheduled().count(), 1)


class ScheduledPostNoEarlyActivityTests(ScheduledPostTestCase):
    def test_scheduling_fires_no_notifications(self):
        self.client.force_login(self.author)
        when = (timezone.now() + timedelta(days=1)).isoformat()
        activities_before = ActivityFeed.objects.count()
        with mock.patch(
                'apps.accounts.push_notifications.PushNotificationService._send_push') as push:
            resp = self.client.post(
                reverse('accounts:create_social_post'),
                {'content': 'Tomorrow', 'scheduled_at': when})
        self.assertEqual(resp.status_code, 200)
        push.assert_not_called()
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(ActivityFeed.objects.count(), activities_before)

    def test_nobody_can_react_or_comment_before_it_is_live(self):
        post = self.schedule()
        for user in (self.other, self.author):
            self.client.force_login(user)
            react = self.client.post(
                reverse('accounts:react_to_post', args=[post.id]),
                {'reaction_type': 'like'})
            like = self.client.post(reverse('accounts:like_social_post', args=[post.id]))
            comment = self.client.post(
                reverse('accounts:comment_social_post', args=[post.id]),
                {'content': 'early'})
            self.assertEqual(
                [react.status_code, like.status_code, comment.status_code],
                [404, 404, 404])

        self.assertEqual(PostReaction.objects.count(), 0)
        self.assertEqual(SocialPostComment.objects.count(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_reactions_notify_once_it_is_live(self):
        post = self.schedule(hours=2)
        self.client.force_login(self.other)
        later = timezone.now() + timedelta(hours=3)
        with mock.patch('django.utils.timezone.now', return_value=later):
            resp = self.client.post(
                reverse('accounts:react_to_post', args=[post.id]),
                {'reaction_type': 'like'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Notification.objects.filter(recipient=self.author).count(), 1)

    def test_weekly_digest_query_skips_scheduled_posts(self):
        self.schedule(visibility='public')
        week_ago = timezone.now() - timedelta(days=7)
        self.assertFalse(
            SocialPost.objects.live().filter(live_at__gte=week_ago).exists())


class CreateScheduledPostTests(ScheduledPostTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.author)
        self.url = reverse('accounts:create_social_post')

    def test_local_time_with_offset_is_stored_as_utc(self):
        when = (timezone.now() + timedelta(days=2)).replace(microsecond=0)
        # What a browser five hours behind UTC would mean by the same instant
        local = when.astimezone(timezone.get_fixed_timezone(-300))
        resp = self.client.post(
            self.url, {'content': 'Later', 'scheduled_at': local.isoformat()})

        self.assertEqual(resp.status_code, 200)
        post = SocialPost.objects.get()
        self.assertEqual(post.scheduled_at, when)
        self.assertTrue(post.is_scheduled)
        self.assertIsNotNone(resp.json()['post']['scheduled_at'])

    def test_browser_utc_string_is_accepted(self):
        when = (timezone.now() + timedelta(days=2)).replace(microsecond=0)
        # The shape of Date.prototype.toISOString()
        js_iso = when.astimezone(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        resp = self.client.post(self.url, {'content': 'Later', 'scheduled_at': js_iso})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(SocialPost.objects.get().scheduled_at, when)

    def test_time_without_an_offset_is_read_as_utc(self):
        when = (timezone.now() + timedelta(days=2)).replace(microsecond=0)
        naive = when.astimezone(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        resp = self.client.post(self.url, {'content': 'Later', 'scheduled_at': naive})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(SocialPost.objects.get().scheduled_at, when)

    def test_no_time_posts_immediately(self):
        resp = self.client.post(self.url, {'content': 'Now'})
        self.assertEqual(resp.status_code, 200)
        post = SocialPost.objects.get()
        self.assertIsNone(post.scheduled_at)
        self.assertFalse(post.is_scheduled)

    def test_past_time_rejected(self):
        past = (timezone.now() - timedelta(minutes=5)).isoformat()
        resp = self.client.post(self.url, {'content': 'Oops', 'scheduled_at': past})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SocialPost.objects.count(), 0)

    def test_garbage_time_rejected(self):
        resp = self.client.post(self.url, {'content': 'Oops', 'scheduled_at': 'soon'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(SocialPost.objects.count(), 0)

    def test_composer_has_the_schedule_picker(self):
        resp = self.client.get(self.feed_url)
        self.assertContains(resp, 'id="schedule-input"')
        self.assertContains(resp, 'type="datetime-local"')


class ManageScheduledPostTests(ScheduledPostTestCase):
    def reschedule_url(self, post):
        return reverse('accounts:reschedule_social_post', args=[post.id])

    def test_author_can_reschedule(self):
        post = self.schedule(hours=2)
        new_time = (timezone.now() + timedelta(days=3)).replace(microsecond=0)
        self.client.force_login(self.author)
        resp = self.client.post(
            self.reschedule_url(post), {'scheduled_at': new_time.isoformat()})
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.scheduled_at, new_time)

    def test_reschedule_to_the_past_rejected(self):
        post = self.schedule(hours=2)
        original = post.scheduled_at
        self.client.force_login(self.author)
        resp = self.client.post(
            self.reschedule_url(post),
            {'scheduled_at': (timezone.now() - timedelta(hours=1)).isoformat()})
        self.assertEqual(resp.status_code, 400)
        post.refresh_from_db()
        self.assertEqual(post.scheduled_at, original)

    def test_post_now_publishes_and_stamps_the_publish_time(self):
        post = self.schedule(hours=2)
        self.client.force_login(self.author)
        resp = self.client.post(self.reschedule_url(post), {'publish_now': '1'})
        self.assertEqual(resp.status_code, 200)
        post.refresh_from_db()
        self.assertFalse(post.is_scheduled)
        self.assertEqual(SocialPost.objects.live().count(), 1)

    def test_other_members_cannot_reschedule_edit_or_delete(self):
        post = self.schedule()
        self.client.force_login(self.other)
        new_time = (timezone.now() + timedelta(days=3)).isoformat()

        resched = self.client.post(self.reschedule_url(post), {'scheduled_at': new_time})
        now = self.client.post(self.reschedule_url(post), {'publish_now': '1'})
        edit = self.client.post(
            reverse('accounts:edit_social_post', args=[post.id]), {'content': 'hijack'})
        delete = self.client.post(reverse('accounts:delete_social_post', args=[post.id]))

        self.assertEqual(resched.status_code, 404)
        self.assertEqual(now.status_code, 404)
        self.assertEqual(edit.status_code, 403)
        self.assertNotEqual(delete.json().get('success'), True)
        post.refresh_from_db()
        self.assertEqual(post.content, 'Queued for later')
        self.assertTrue(post.is_scheduled)

    def test_a_live_post_cannot_be_rescheduled(self):
        post = SocialPost.objects.create(author=self.author, content='Already out')
        self.client.force_login(self.author)
        resp = self.client.post(
            self.reschedule_url(post),
            {'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat()})
        self.assertEqual(resp.status_code, 404)
        post.refresh_from_db()
        self.assertIsNone(post.scheduled_at)

    def test_author_can_edit_and_delete(self):
        post = self.schedule()
        self.client.force_login(self.author)
        edit = self.client.post(
            reverse('accounts:edit_social_post', args=[post.id]), {'content': 'Reworded'})
        self.assertEqual(edit.status_code, 200)
        post.refresh_from_db()
        self.assertEqual(post.content, 'Reworded')
        self.assertTrue(post.is_scheduled)

        delete = self.client.post(reverse('accounts:delete_social_post', args=[post.id]))
        self.assertTrue(delete.json()['success'])
        self.assertFalse(SocialPost.objects.filter(pk=post.pk).exists())


@override_settings(OFFICIAL_POST_USERNAME='myrecoverypal')
class PostAsOfficialAccountTests(ScheduledPostTestCase):
    def setUp(self):
        super().setUp()
        self.official = User.objects.create_user(username='myrecoverypal', email='myrecoverypal@example.com', password='x')
        self.staff = User.objects.create_user(username='admin', email='admin@example.com', password='x', is_staff=True)
        self.url = reverse('accounts:create_social_post')
        self.when = (timezone.now() + timedelta(days=1)).isoformat()

    def test_staff_can_schedule_as_the_official_account(self):
        self.client.force_login(self.staff)
        resp = self.client.post(self.url, {
            'content': 'From the team', 'post_as': 'official', 'scheduled_at': self.when})
        self.assertEqual(resp.status_code, 200)
        post = SocialPost.objects.get()
        self.assertEqual(post.author, self.official)

        # Staff manage it from their own Scheduled list
        feed = self.client.get(self.feed_url)
        self.assertEqual(list(feed.context['scheduled_posts']), [post])
        self.assertContains(feed, 'id="post-as-select"')
        delete = self.client.post(reverse('accounts:delete_social_post', args=[post.id]))
        self.assertTrue(delete.json()['success'])

    def test_members_cannot_post_as_the_official_account(self):
        self.client.force_login(self.other)
        resp = self.client.post(self.url, {'content': 'Fake', 'post_as': 'official'})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(SocialPost.objects.count(), 0)
        self.assertNotContains(self.client.get(self.feed_url), 'id="post-as-select"')

    def test_members_do_not_see_the_official_queue(self):
        SocialPost.objects.create(
            author=self.official, content='From the team',
            scheduled_at=timezone.now() + timedelta(days=1))
        self.client.force_login(self.other)
        resp = self.client.get(self.feed_url)
        self.assertEqual(list(resp.context['scheduled_posts']), [])
        self.assertNotContains(resp, 'From the team')

    @override_settings(OFFICIAL_POST_USERNAME='')
    def test_off_when_no_official_account_is_configured(self):
        self.client.force_login(self.staff)
        resp = self.client.post(self.url, {'content': 'x', 'post_as': 'official'})
        self.assertEqual(resp.status_code, 403)
        self.assertNotContains(self.client.get(self.feed_url), 'id="post-as-select"')
