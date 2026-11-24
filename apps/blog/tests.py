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
        args, kwargs = mock_cache.set.call_args
        # Key is the day-stamped idempotency marker (e.g. 'blog_digest_sent_2026-04-21')
        self.assertRegex(args[0], r'^blog_digest_sent_\d{4}-\d{2}-\d{2}$')
        # Value is True (marker only — we don't store data)
        self.assertIs(args[1], True)
        # TTL is 23 hours so the key naturally expires before the next day's run
        timeout = kwargs.get('timeout') if 'timeout' in kwargs else (args[2] if len(args) > 2 else None)
        self.assertEqual(timeout, 82800)

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


class SlugGenerationTest(TestCase):
    """A title that slugifies to '' (emoji/non-ASCII only) must never
    produce an empty slug — empty slugs make get_absolute_url raise
    NoReverseMatch (Sentry: blog/models.py get_absolute_url)."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='slugauthor', email='slugauthor@example.com', password='x',
        )
        from apps.blog.models import Category
        self.category = Category.objects.create(name='General')

    def test_model_save_emoji_title_gets_nonempty_slug(self):
        post = Post.objects.create(title="💪🙏", author=self.author, content="hi")
        self.assertTrue(post.slug)
        # Must not raise NoReverseMatch
        self.assertTrue(post.get_absolute_url())

    def test_form_save_emoji_title_gets_nonempty_slug(self):
        from apps.blog.forms import PostForm
        form = PostForm(data={
            'title': "💪🙏",
            'content': "hi",
            'status': 'draft',
            'category': self.category.pk,
        })
        self.assertTrue(form.is_valid(), form.errors)
        post = form.save(commit=False)
        self.assertTrue(post.slug)


class PostFormNewTagsTests(TestCase):
    """Typed-in tags must never crash a post save (Sentry: DataError "value
    too long for type character varying(50)" from PostForm.save)."""

    def setUp(self):
        self.author = User.objects.create_user(
            username='tagauthor', email='tagauthor@example.com', password='x',
        )
        from apps.blog.models import Category
        self.category = Category.objects.create(name='General')

    def _form(self, new_tags):
        from apps.blog.forms import PostForm
        form = PostForm(data={
            'title': 'A post', 'content': 'hi', 'status': 'draft',
            'category': self.category.pk, 'new_tags': new_tags,
        })
        form.instance.author = self.author
        return form

    def test_a_tag_over_50_characters_is_a_form_error_not_a_crash(self):
        form = self._form('recovery, ' + 'a sentence typed into the tag box by mistake ' * 2)
        self.assertFalse(form.is_valid())
        self.assertIn('50 characters', form.errors['new_tags'][0])

    def test_a_tag_that_slugifies_like_an_existing_one_reuses_it(self):
        from apps.blog.models import Tag
        Tag.objects.create(name='recovery', slug='recovery')
        form = self._form('Recovery!')
        self.assertTrue(form.is_valid(), form.errors)
        post = form.save()
        self.assertEqual([t.name for t in post.tags.all()], ['recovery'])
        self.assertEqual(Tag.objects.count(), 1)

    def test_a_tag_with_no_letters_is_skipped(self):
        from apps.blog.models import Tag
        form = self._form('💪, hope')
        self.assertTrue(form.is_valid(), form.errors)
        post = form.save()
        self.assertEqual([t.name for t in post.tags.all()], ['hope'])
        self.assertEqual(Tag.objects.count(), 1)

    def test_write_page_shows_the_tag_error_and_saves_nothing(self):
        from django.test import override_settings
        from django.urls import reverse
        self.client.force_login(self.author)
        with override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False):
            resp = self.client.post(reverse('blog:post_create'), {
                'title': 'A post', 'content': 'hi', 'status': 'draft',
                'category': self.category.pk, 'new_tags': 'x' * 51,
            })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Each tag can be up to 50 characters')
        self.assertFalse(Post.objects.filter(title='A post').exists())

    def test_typed_in_tags_stay_on_the_saved_post(self):
        form = self._form('hope, one day at a time')
        self.assertTrue(form.is_valid(), form.errors)
        post = form.save()
        self.assertEqual(sorted(t.name for t in post.tags.all()), ['hope', 'one day at a time'])
