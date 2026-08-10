"""Tests for the online-meeting sync service.

Feeds are exercised through local JSON files (sync_source accepts a file
path), so no HTTP mocking is needed except for the all-sources-failed case.
"""
import json
import tempfile
from io import StringIO
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.support_services.meeting_sync import (
    FeedFetchError,
    sync_all,
    sync_source,
)
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
        other = dict(ONLINE_MEETING, name="Other Meeting", slug="other-meeting")
        sync_source("test", feed_file([ONLINE_MEETING]))
        sync_source("test", feed_file([other]))
        self.assertFalse(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

        sync_source("test", feed_file([ONLINE_MEETING]))
        self.assertTrue(
            Meeting.objects.get(
                slug="online-test-morning-serenity").is_active)

    def test_empty_feed_skips_deactivation(self):
        sync_source("test", feed_file([ONLINE_MEETING]))

        result = sync_source("test", feed_file([]))

        self.assertEqual(result["deactivated"], 0)
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


class FakeResponse:
    """Minimal stand-in for a requests Response."""

    def __init__(self, body, status=200, content_type="text/html"):
        self.text = body
        self.status_code = status
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"{self.status_code} Server Error", response=self)

    def json(self):
        return json.loads(self.text)


# What aahouston.org actually served when the weekly sync blew up: HTTP 200,
# but an HTML error page instead of the feed.
HTML_ERROR_PAGE = "<!DOCTYPE html><html><body>Service Unavailable</body></html>"
GOOD_FEED = json.dumps([ONLINE_MEETING])


@patch("apps.support_services.meeting_sync.time.sleep")
class LoadFeedTests(TestCase):
    """A 200 response whose body isn't JSON must not burn the whole sync."""

    def test_retries_and_succeeds_when_feed_briefly_returns_html(self, sleep):
        responses = [
            FakeResponse(HTML_ERROR_PAGE),
            FakeResponse(HTML_ERROR_PAGE),
            FakeResponse(GOOD_FEED, content_type="application/json"),
        ]
        with patch("apps.support_services.meeting_sync.requests.get",
                   side_effect=responses) as get:
            result = sync_source("houston", "https://aahouston.org/feed")

        self.assertEqual(get.call_count, 3)
        self.assertEqual(result["created"], 1)
        self.assertTrue(
            Meeting.objects.filter(
                slug="online-houston-morning-serenity").exists())

    def test_error_names_the_content_type_and_body_after_retries(self, sleep):
        with patch("apps.support_services.meeting_sync.requests.get",
                   return_value=FakeResponse(HTML_ERROR_PAGE)) as get:
            with self.assertRaises(FeedFetchError) as ctx:
                sync_source("houston", "https://aahouston.org/feed")

        self.assertEqual(get.call_count, 3)
        message = str(ctx.exception)
        # The whole point: Sentry must show what came back, not a bare
        # "Expecting value: line 1 column 1".
        self.assertIn("aahouston.org", message)
        self.assertIn("text/html", message)
        self.assertIn("Service Unavailable", message)

    def test_retries_on_connection_error(self, sleep):
        with patch(
            "apps.support_services.meeting_sync.requests.get",
            side_effect=[
                requests.ConnectionError("connection reset"),
                FakeResponse(GOOD_FEED, content_type="application/json"),
            ],
        ) as get:
            result = sync_source("houston", "https://aahouston.org/feed")

        self.assertEqual(get.call_count, 2)
        self.assertEqual(result["created"], 1)

    def test_rejects_json_that_is_not_a_list_or_object(self, sleep):
        # WordPress admin-ajax.php answers a request it can't route with a
        # bare "0" — valid JSON, useless feed.
        with patch("apps.support_services.meeting_sync.requests.get",
                   return_value=FakeResponse("0",
                                             content_type="application/json")):
            with self.assertRaises(FeedFetchError):
                sync_source("houston", "https://aahouston.org/feed")

    def test_local_file_feeds_are_not_retried(self, sleep):
        # File paths skip the HTTP path entirely; a missing file still fails
        # fast so sync_all can isolate it.
        with self.assertRaises(OSError):
            sync_source("test", "/nonexistent/feed.json")
        sleep.assert_not_called()

    def test_sync_all_isolates_a_feed_that_never_returns_json(self, sleep):
        sync_source("houston", feed_file([ONLINE_MEETING]))
        good = {"key": "good", "url": feed_file([
            dict(ONLINE_MEETING, slug="other")])}
        bad = {"key": "houston", "url": "https://aahouston.org/feed"}

        with patch("apps.support_services.meeting_sync.requests.get",
                   return_value=FakeResponse(HTML_ERROR_PAGE)):
            results = sync_all([good, bad])

        self.assertIsNone(results["houston"])
        # Houston's meetings survive its feed being broken.
        self.assertTrue(
            Meeting.objects.get(
                slug="online-houston-morning-serenity").is_active)


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


class SeedCommandTests(TestCase):
    def test_single_source_mode_with_key(self):
        out = StringIO()
        call_command(
            "seed_online_meetings",
            source=feed_file([ONLINE_MEETING]),
            key="cli",
            stdout=out,
        )
        self.assertTrue(
            Meeting.objects.filter(
                slug="online-cli-morning-serenity").exists())
        self.assertIn("Done.", out.getvalue())

    def test_no_args_syncs_all_configured_sources(self):
        with patch(
            "apps.support_services.management.commands."
            "seed_online_meetings.sync_all",
            return_value={"seattle": {"created": 5, "updated": 0,
                                      "skipped": 0, "deactivated": 0},
                          "legacy_deactivated": 0},
        ) as mock_sync:
            out = StringIO()
            call_command("seed_online_meetings", stdout=out)
        mock_sync.assert_called_once_with()
        self.assertIn("seattle", out.getvalue())


class RefreshTaskTests(TestCase):
    def test_task_calls_sync_all(self):
        with patch(
            "apps.support_services.tasks.sync_all",
            return_value={"seattle": {"created": 1, "updated": 0,
                                      "skipped": 0, "deactivated": 0}},
        ) as mock_sync:
            from apps.support_services.tasks import (
                refresh_online_meetings_task,
            )
            refresh_online_meetings_task.apply()
        mock_sync.assert_called_once_with()


class TimezoneDisplayTests(TestCase):
    def test_known_zone_returns_abbreviation(self):
        m = Meeting.objects.create(
            name="TZ Test", slug="tz-test",
            timezone="America/Los_Angeles",
        )
        # PST or PDT depending on date — both are acceptable.
        self.assertIn(m.timezone_display, ("PST", "PDT"))

    def test_unknown_zone_falls_back_to_raw_value(self):
        m = Meeting.objects.create(
            name="TZ Bad", slug="tz-bad", timezone="Not/AZone",
        )
        self.assertEqual(m.timezone_display, "Not/AZone")
