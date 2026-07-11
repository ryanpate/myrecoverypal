"""Tests for the online-meeting sync service.

Feeds are exercised through local JSON files (sync_source accepts a file
path), so no HTTP mocking is needed except for the all-sources-failed case.
"""
import json
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.support_services.meeting_sync import sync_all, sync_source
from apps.support_services.models import Meeting

User = get_user_model()


def feed_file(meetings):
    """Write a TSML-shaped feed to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False)
    json.dump(meetings, f)
    f.close()
    return f.name


ONLINE_MEETING = {
    "name": "Morning Serenity",
    "slug": "morning-serenity",
    "day": 1,
    "time": "07:00",
    "end_time": "08:00",
    "attendance_option": "online",
    "conference_url": "https://zoom.us/j/123",
    "types": ["O", "D"],
    "group": "Serenity Group",
    "notes": "Passcode 1234",
}

IN_PERSON_MEETING = {
    "name": "Downtown Noon",
    "slug": "downtown-noon",
    "day": 2,
    "time": "12:00",
    "attendance_option": "in_person",
}


class SyncSourceTests(TestCase):
    def test_creates_online_meetings_with_namespaced_slug(self):
        path = feed_file([ONLINE_MEETING, IN_PERSON_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.attendance_option, "online")
        self.assertEqual(m.conference_url, "https://zoom.us/j/123")
        self.assertTrue(m.is_approved)
        self.assertTrue(m.is_active)
        # In-person meetings from the feed are never imported.
        self.assertEqual(Meeting.objects.count(), 1)

    def test_updates_existing_meeting_by_slug(self):
        path = feed_file([ONLINE_MEETING])
        sync_source("test", path)

        changed = dict(ONLINE_MEETING, name="Morning Serenity (Renamed)")
        result = sync_source("test", feed_file([changed]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.name, "Morning Serenity (Renamed)")

    def test_deactivates_meetings_missing_from_feed(self):
        other = dict(ONLINE_MEETING, name="Evening Hope",
                     slug="evening-hope")
        sync_source("test", feed_file([ONLINE_MEETING, other]))

        result = sync_source("test", feed_file([ONLINE_MEETING]))

        self.assertEqual(result["deactivated"], 1)
        self.assertFalse(
            Meeting.objects.get(slug="online-test-evening-hope").is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

        # A third sync with the same feed must not re-count the
        # already-deactivated meeting.
        result = sync_source("test", feed_file([ONLINE_MEETING]))
        self.assertEqual(result["deactivated"], 0)

    def test_reactivates_meeting_that_returns_to_feed(self):
        sync_source("test", feed_file([ONLINE_MEETING]))
        sync_source("test", feed_file([]))
        self.assertFalse(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

        sync_source("test", feed_file([ONLINE_MEETING]))
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

    def test_never_touches_community_submitted_meetings(self):
        user = User.objects.create_user(
            username="member", password="x")
        # A community meeting whose slug happens to match the namespace.
        community = Meeting.objects.create(
            name="Online Test Serenity",
            slug="online-test-serenity",
            submitted_by=user,
            is_approved=True,
            is_active=True,
        )
        sync_source("test", feed_file([ONLINE_MEETING]))

        community.refresh_from_db()
        self.assertTrue(community.is_active)

    def test_default_timezone_applied_when_feed_omits_it(self):
        path = feed_file([ONLINE_MEETING])  # no "timezone" key
        sync_source("test", path, default_tz="America/Los_Angeles")
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.timezone, "America/Los_Angeles")

    def test_skips_meetings_without_a_name(self):
        nameless = dict(ONLINE_MEETING, name="  ")
        result = sync_source("test", feed_file([nameless]))
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(Meeting.objects.count(), 0)


class SyncAllTests(TestCase):
    def test_failed_source_is_isolated_and_skips_deactivation(self):
        good = {"key": "good",
                "url": feed_file([ONLINE_MEETING]),
                "timezone": "America/Chicago"}
        # First run seeds a meeting under the "bad" namespace.
        sync_source("bad", feed_file(
            [dict(ONLINE_MEETING, slug="bad-meeting")]))
        bad = {"key": "bad", "url": "/nonexistent/feed.json",
               "timezone": "America/Chicago"}

        results = sync_all([good, bad])

        self.assertIsNone(results["bad"])
        self.assertEqual(results["good"]["created"], 1)
        # The bad source's existing meeting survives its feed being down.
        self.assertTrue(
            Meeting.objects.get(
                slug="online-bad-bad-meeting").is_active)
        # Legacy cleanup is skipped on partial failure.
        self.assertNotIn("legacy_deactivated", results)

    def test_all_sources_failed_raises(self):
        bad = {"key": "bad", "url": "/nonexistent/feed.json",
               "timezone": "America/Chicago"}
        with self.assertRaises(RuntimeError):
            sync_all([bad])

    def test_empty_sources_list_is_a_noop(self):
        sync_source("test", feed_file([ONLINE_MEETING]))

        results = sync_all([])

        self.assertEqual(results, {})
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

    def test_legacy_bare_prefix_rows_deactivated_when_all_succeed(self):
        # Row from the old single-source seed: bare "online-" prefix,
        # no source key, no submitter.
        legacy = Meeting.objects.create(
            name="Old Seattle Import",
            slug="online-old-seattle-import",
            is_approved=True,
            is_active=True,
        )
        good = {"key": "test",
                "url": feed_file([ONLINE_MEETING]),
                "timezone": "America/Chicago"}

        results = sync_all([good])

        # "online-old-..." does not match "online-test-", so it is legacy.
        self.assertEqual(results["legacy_deactivated"], 1)
        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)
