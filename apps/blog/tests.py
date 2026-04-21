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
