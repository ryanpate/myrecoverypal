"""Tests for the daily thought/reading card on the progress home."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought
from apps.journal.models import JournalEntry

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ProgressDailyThoughtTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="p", password="x", email="p@example.com")
        self.client.force_login(self.user)
        DailyRecoveryThought.objects.create(
            quote="Progress, not perfection.",
            reflection_prompt="Where did you make progress today?",
            date=timezone.now().date(),
        )

    def test_progress_home_shows_thought_and_reflect_button(self):
        resp = self.client.get(reverse("accounts:progress"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Progress, not perfection.")
        self.assertContains(resp, reverse("journal:reflect_today"))
        self.assertContains(resp, "Reflect in your journal")

    def test_button_switches_after_todays_reflection(self):
        entry = JournalEntry.objects.create(
            user=self.user, title="Daily Reflection — today", content="x")
        resp = self.client.get(reverse("accounts:progress"))
        self.assertContains(resp, "View today")
        self.assertContains(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}))

    def test_reading_link_renders_when_posts_exist(self):
        from apps.blog.models import Post
        author = User.objects.create_user(
            username="a2", password="x", email="a2@example.com")
        post = Post.objects.create(
            title="Daily Read", slug="daily-read", author=author,
            content="body", status="published")
        resp = self.client.get(reverse("accounts:progress"))
        self.assertContains(resp, "Daily Read")
        self.assertContains(resp, post.get_absolute_url())

    def test_no_reading_link_without_posts(self):
        resp = self.client.get(reverse("accounts:progress"))
        self.assertNotContains(resp, "Today&#x27;s reading")
        self.assertEqual(resp.status_code, 200)

    def test_social_feed_still_renders_with_partial(self):
        resp = self.client.get(reverse("accounts:social_feed"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Progress, not perfection.")
