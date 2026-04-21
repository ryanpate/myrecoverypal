from django.test import TestCase

from apps.blog.tasks import _build_subject


class FakePost:
    def __init__(self, title):
        self.title = title


class BuildSubjectTest(TestCase):
    def test_single_post_uses_title(self):
        posts = [FakePost("Faith Didn't Come With the Lightning Bolt")]
        self.assertEqual(
            _build_subject(posts),
            "New on MyRecoveryPal: Faith Didn't Come With the Lightning Bolt",
        )

    def test_multiple_posts_uses_count(self):
        posts = [FakePost("a"), FakePost("b"), FakePost("c")]
        self.assertEqual(
            _build_subject(posts),
            "3 new posts on MyRecoveryPal today",
        )

    def test_two_posts(self):
        posts = [FakePost("a"), FakePost("b")]
        self.assertEqual(
            _build_subject(posts),
            "2 new posts on MyRecoveryPal today",
        )

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.tasks import send_daily_blog_digest

User = get_user_model()


class SendDailyBlogDigestTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username='author',
            email='author@example.com',
            password='x',
            email_notifications=True,
        )
        self.reader = User.objects.create_user(
            username='reader',
            email='reader@example.com',
            password='x',
            email_notifications=True,
        )
        self.optout = User.objects.create_user(
            username='optout',
            email='optout@example.com',
            password='x',
            email_notifications=False,
        )

    def _create_post(self, title="Post", hours_ago=1, author=None):
        """Helper: create a published post N hours ago."""
        post = Post.objects.create(
            title=title,
            content="body text for the post",
            excerpt="Short excerpt",
            status='published',
            author=author or self.author,
        )
        # Post.save() sets published_at; override for test timing.
        Post.objects.filter(pk=post.pk).update(
            published_at=timezone.now() - timedelta(hours=hours_ago)
        )
        post.refresh_from_db()
        return post

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_no_posts_in_window_sends_nothing(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        send_daily_blog_digest()
        mock_send.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_posts_older_than_24h_are_excluded(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        self._create_post(hours_ago=48)  # outside window
        send_daily_blog_digest()
        mock_send.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_author_is_excluded_from_recipients(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertNotIn('author@example.com', recipients)
        self.assertIn('reader@example.com', recipients)

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_users_with_email_notifications_off_excluded(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        recipients = [c.kwargs['recipient_email'] for c in mock_send.call_args_list]
        self.assertNotIn('optout@example.com', recipients)

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_idempotency_cache_hit_is_noop(self, mock_send, mock_cache):
        mock_cache.get.return_value = True  # already sent today
        self._create_post(author=self.author)
        send_daily_blog_digest()
        mock_send.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_successful_run_sets_cache(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        mock_send.return_value = (True, None)
        self._create_post(author=self.author)
        send_daily_blog_digest()
        mock_cache.set.assert_called_once()
        # First positional arg should be today's key
        args, _ = mock_cache.set.call_args
        self.assertTrue(args[0].startswith('blog_digest_sent_'))

    @patch('apps.blog.tasks.cache')
    @patch('apps.accounts.email_service.send_email')
    def test_per_user_failure_does_not_abort_batch(self, mock_send, mock_cache):
        mock_cache.get.return_value = None
        # First recipient raises, second succeeds
        mock_send.side_effect = [Exception("boom"), (True, None)]
        # Need 2 recipients (not including author): reader + one more
        extra = User.objects.create_user(
            username='extra', email='extra@example.com', password='x',
            email_notifications=True,
        )
        self._create_post(author=self.author)
        send_daily_blog_digest()
        # Both recipients attempted
        self.assertEqual(mock_send.call_count, 2)
        # Cache still set (run completed)
        mock_cache.set.assert_called_once()
