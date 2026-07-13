"""Tests for video posts in the social feed."""
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import SocialPost

User = get_user_model()


def small_mp4(name='clip.mp4', content_type='video/mp4', size=1024):
    return SimpleUploadedFile(name, b'\x00' * size, content_type=content_type)


class FakeFile:
    """Stub with just the attributes validate_video reads (avoids allocating 50MB)."""
    def __init__(self, name='clip.mp4', size=1024, content_type='video/mp4'):
        self.name = name
        self.size = size
        self.content_type = content_type


class ValidateVideoTests(TestCase):
    def test_valid_mp4(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(FakeFile())
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_valid_mov_and_webm(self):
        from apps.accounts.image_utils import validate_video
        self.assertTrue(validate_video(FakeFile('a.mov', content_type='video/quicktime'))[0])
        self.assertTrue(validate_video(FakeFile('a.webm', content_type='video/webm'))[0])

    def test_oversized_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(FakeFile(size=51 * 1024 * 1024))
        self.assertFalse(is_valid)
        self.assertIn('50MB', error)

    def test_disallowed_type_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(
            FakeFile('a.avi', content_type='video/x-msvideo'))
        self.assertFalse(is_valid)

    def test_no_file_rejected(self):
        from apps.accounts.image_utils import validate_video
        is_valid, error = validate_video(None)
        self.assertFalse(is_valid)


class SocialPostVideoFieldTests(TestCase):
    def test_post_accepts_video_file(self):
        user = User.objects.create_user(username='vid', password='x')
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            post = SocialPost.objects.create(
                author=user, content='clip', video=small_mp4())
            self.assertTrue(post.video.name.startswith('social_posts/videos/'))
            self.assertTrue(post.video.url)


@override_settings(
    SECURE_SSL_REDIRECT=False,
    ALLOWED_HOSTS=['testserver'],
    MIDDLEWARE=[
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ]
)
class CreateVideoPostViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='poster', password='x')
        self.client.force_login(self.user)
        self.url = reverse('accounts:create_social_post')

    def test_create_post_with_video(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            resp = self.client.post(self.url, {'content': 'my clip', 'video': small_mp4()})
            data = resp.json()
            self.assertTrue(data['success'])
            self.assertTrue(data['post']['video_url'])
            post = SocialPost.objects.get(author=self.user)
            self.assertTrue(post.video)

    def test_video_only_post_allowed(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            resp = self.client.post(self.url, {'video': small_mp4()})
            self.assertTrue(resp.json()['success'])

    def test_oversized_video_rejected(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            big = small_mp4(size=51 * 1024 * 1024)
            resp = self.client.post(self.url, {'content': 'x', 'video': big})
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(SocialPost.objects.count(), 0)

    def test_bad_video_type_rejected(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            bad = small_mp4(name='clip.avi', content_type='video/x-msvideo')
            resp = self.client.post(self.url, {'content': 'x', 'video': bad})
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(SocialPost.objects.count(), 0)

    def test_image_and_video_together_rejected(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            import io
            from PIL import Image
            buf = io.BytesIO()
            Image.new('RGB', (10, 10)).save(buf, format='JPEG')
            img = SimpleUploadedFile('a.jpg', buf.getvalue(), content_type='image/jpeg')
            resp = self.client.post(
                self.url, {'content': 'x', 'image': img, 'video': small_mp4()})
            self.assertEqual(resp.status_code, 400)
            self.assertIn('not both', resp.json()['error'])

    def test_feed_api_includes_video_url(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            SocialPost.objects.create(author=self.user, content='clip', video=small_mp4())
            resp = self.client.get(reverse('accounts:social_feed_posts_api'))
            posts = resp.json()['posts']
            self.assertTrue(posts[0]['video_url'])
