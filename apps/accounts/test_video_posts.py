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
