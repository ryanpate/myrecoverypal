"""Tests for the daily-reflection journal flow."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought
from apps.journal.models import JournalEntry

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ReflectTodayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="r", email="r@example.com", password="x")
        self.client.force_login(self.user)
        self.thought = DailyRecoveryThought.objects.create(
            quote="Progress, not perfection.",
            author_attribution="",
            reflection_prompt="Where did you make progress today?",
            date=timezone.now().date(),
        )

    def test_get_prefills_title_and_content(self):
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Daily Reflection")
        self.assertContains(resp, "Progress, not perfection.")
        self.assertContains(resp, "Where did you make progress today?")

    def test_post_saves_private_entry_via_create_flow(self):
        resp = self.client.post(reverse("journal:reflect_today"), {
            "title": "Daily Reflection — test",
            "content": "My reflection.",
        })
        entry = JournalEntry.objects.get(user=self.user)
        self.assertRedirects(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}),
            fetch_redirect_response=False)
        self.assertEqual(entry.content, "My reflection.")

    def test_second_get_today_redirects_to_existing_entry(self):
        entry = JournalEntry.objects.create(
            user=self.user, title="Daily Reflection — earlier",
            content="done already",
        )
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertRedirects(
            resp, reverse("journal:entry_detail", kwargs={"pk": entry.pk}),
            fetch_redirect_response=False)

    def test_other_users_reflection_does_not_trigger_redirect(self):
        other = User.objects.create_user(username="o", email="o@example.com", password="x")
        JournalEntry.objects.create(
            user=other, title="Daily Reflection — theirs", content="x")
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)

    def test_works_without_a_daily_thought(self):
        self.thought.delete()
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Daily Reflection")

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("journal:reflect_today"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])
