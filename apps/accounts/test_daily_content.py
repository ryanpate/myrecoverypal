"""Tests for the daily thought/reading lookups."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.daily_content import get_daily_reading, get_daily_thought
from apps.accounts.models import DailyRecoveryThought
from apps.blog.models import Post
from django.contrib.auth import get_user_model

User = get_user_model()


class DailyThoughtTests(TestCase):
    def test_returns_todays_thought(self):
        today = timezone.now().date()
        thought = DailyRecoveryThought.objects.create(
            quote="One day at a time.", date=today)
        DailyRecoveryThought.objects.create(
            quote="Yesterday's.", date=today - timedelta(days=1))
        self.assertEqual(get_daily_thought(), thought)

    def test_returns_none_when_no_thought_today(self):
        self.assertIsNone(get_daily_thought())


class DailyReadingTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="author", password="x")
        self.posts = [
            Post.objects.create(
                title=f"Post {i}", slug=f"post-{i}",
                author=author, content="body", status="published",
            )
            for i in range(3)
        ]
        Post.objects.create(
            title="Draft", slug="draft", author=author,
            content="body", status="draft",
        )

    def test_deterministic_for_a_day_and_skips_drafts(self):
        first = get_daily_reading()
        second = get_daily_reading()
        self.assertEqual(first, second)
        self.assertIn(first, self.posts)  # never the draft

    def test_rotates_across_days(self):
        today = timezone.now().date()
        expected_index = today.toordinal() % 3
        self.assertEqual(get_daily_reading(), self.posts[expected_index])

    def test_none_when_no_published_posts(self):
        Post.objects.all().delete()
        self.assertIsNone(get_daily_reading())
