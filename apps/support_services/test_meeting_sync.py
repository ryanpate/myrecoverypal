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
    _attendance_option,
    _map,
    _split_address,
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

FULL_IN_PERSON_MEETING = {
    "name": "Downtown Noon",
    "slug": "downtown-noon",
    "day": 2,
    "time": "12:00",
    "end_time": "13:00",
    "attendance_option": "in_person",
    "location": "First Methodist Church",
    "formatted_address": "123 Main St, Houston, TX 77002, USA",
    "address": "123 Main St",
    "city": "Houston",
    "state": "TX",
    "postal_code": "77002",
    "country": "US",
    "latitude": "29.76043200",
    "longitude": "-95.36980300",
    "region": "Downtown",
    "website": "https://aahouston.org/",
    "types": ["O", "D"],
}

HYBRID_MEETING = {
    "name": "Bridge Group",
    "slug": "bridge-group",
    "day": 3,
    "time": "18:00",
    "attendance_option": "hybrid",
    "conference_url": "https://zoom.us/j/999",
    "location": "Community Hall",
    "formatted_address": "9 Oak Ave, Seattle, WA",
    "city": "Seattle",
    "state": "WA",
}


class SyncSourceTests(TestCase):
    def test_creates_meetings_with_namespaced_slug(self):
        path = feed_file([ONLINE_MEETING, IN_PERSON_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 2)
        m = Meeting.objects.get(slug="mtg-test-morning-serenity")
        self.assertEqual(m.attendance_option, "online")
        self.assertEqual(m.conference_url, "https://zoom.us/j/123")
        self.assertTrue(m.is_approved)
        self.assertTrue(m.is_active)
        # In-person meetings are imported too, as of the 2026-09 expansion.
        self.assertEqual(Meeting.objects.count(), 2)
        self.assertEqual(
            Meeting.objects.get(slug="mtg-test-downtown-noon").attendance_option,
            "in_person",
        )

    def test_updates_existing_meeting_by_slug(self):
        path = feed_file([ONLINE_MEETING])
        sync_source("test", path)

        changed = dict(ONLINE_MEETING, name="Morning Serenity (Renamed)")
        result = sync_source("test", feed_file([changed]))

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        m = Meeting.objects.get(slug="mtg-test-morning-serenity")
        self.assertEqual(m.name, "Morning Serenity (Renamed)")

    def test_deactivates_meetings_missing_from_feed(self):
        other = dict(ONLINE_MEETING, name="Evening Hope",
                     slug="evening-hope")
        sync_source("test", feed_file([ONLINE_MEETING, other]))

        result = sync_source("test", feed_file([ONLINE_MEETING]))

        self.assertEqual(result["deactivated"], 1)
        self.assertFalse(
            Meeting.objects.get(slug="mtg-test-evening-hope").is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="mtg-test-morning-serenity").is_active)

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
                slug="mtg-test-morning-serenity").is_active)

        sync_source("test", feed_file([ONLINE_MEETING]))
        self.assertTrue(
            Meeting.objects.get(
                slug="mtg-test-morning-serenity").is_active)

    def test_empty_feed_skips_deactivation(self):
        sync_source("test", feed_file([ONLINE_MEETING]))

        result = sync_source("test", feed_file([]))

        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(
            Meeting.objects.get(
                slug="mtg-test-morning-serenity").is_active)

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
        m = Meeting.objects.get(slug="mtg-test-morning-serenity")
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
                slug="mtg-houston-morning-serenity").exists())

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
                slug="mtg-houston-morning-serenity").is_active)


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
                slug="mtg-bad-bad-meeting").is_active)
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
                slug="mtg-test-morning-serenity").is_active)

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

        # "online-old-..." matches neither "mtg-test-" nor
        # "online-test-", so it is legacy.
        self.assertEqual(results["legacy_deactivated"], 1)
        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertTrue(
            Meeting.objects.get(
                slug="mtg-test-morning-serenity").is_active)


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
                slug="mtg-cli-morning-serenity").exists())
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


class AttendanceOptionDerivationTests(TestCase):
    """Older TSML feeds omit attendance_option; derive it from the payload."""

    def test_explicit_value_is_trusted(self):
        self.assertEqual(
            _attendance_option({"attendance_option": "hybrid"}), "hybrid")

    def test_conference_url_and_address_is_hybrid(self):
        self.assertEqual(
            _attendance_option({
                "conference_url": "https://zoom.us/j/1",
                "formatted_address": "123 Main St, Houston, TX",
            }),
            "hybrid",
        )

    def test_conference_url_only_is_online(self):
        self.assertEqual(
            _attendance_option({"conference_url": "https://zoom.us/j/1"}),
            "online",
        )

    def test_address_only_is_in_person(self):
        self.assertEqual(
            _attendance_option({"formatted_address": "123 Main St"}),
            "in_person",
        )

    def test_bare_address_field_counts_as_a_location(self):
        self.assertEqual(_attendance_option({"address": "123 Main St"}), "in_person")

    def test_no_signal_at_all_is_in_person(self):
        self.assertEqual(_attendance_option({}), "in_person")

    def test_unrecognised_explicit_value_is_derived_instead(self):
        self.assertEqual(
            _attendance_option({
                "attendance_option": "hybrid_but_typoed",
                "conference_url": "https://zoom.us/j/1",
            }),
            "online",
        )


class MapAddressFieldsTests(TestCase):
    def test_in_person_meeting_carries_its_address(self):
        d = _map(FULL_IN_PERSON_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "in_person")
        self.assertEqual(d["location"], "First Methodist Church")
        self.assertEqual(d["formatted_address"], "123 Main St, Houston, TX 77002, USA")
        self.assertEqual(d["address"], "123 Main St")
        self.assertEqual(d["city"], "Houston")
        self.assertEqual(d["state"], "TX")
        self.assertEqual(d["postal_code"], "77002")
        self.assertEqual(d["region"], "Downtown")
        self.assertEqual(d["website"], "https://aahouston.org/")
        self.assertEqual(str(d["latitude"]), "29.76043200")

    def test_in_person_meeting_has_no_conference_url(self):
        d = _map(FULL_IN_PERSON_MEETING, True, "America/Chicago")
        self.assertEqual(d["conference_url"], "")

    def test_hybrid_meeting_carries_both_address_and_join_link(self):
        d = _map(HYBRID_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "hybrid")
        self.assertEqual(d["conference_url"], "https://zoom.us/j/999")
        self.assertEqual(d["city"], "Seattle")

    def test_online_meeting_keeps_its_placeholder_location(self):
        """Online meetings must not look like somewhere you travel to."""
        d = _map(ONLINE_MEETING, True, "America/Chicago")
        self.assertEqual(d["attendance_option"], "online")
        self.assertEqual(d["location"], "Online Meeting")
        self.assertEqual(d["formatted_address"], "")
        self.assertEqual(d["city"], "")

    def test_state_is_truncated_to_the_column_width(self):
        """Meeting.state is CharField(max_length=2); some feeds send
        full state names, which would raise DataError on Postgres."""
        d = _map({**FULL_IN_PERSON_MEETING, "state": "Texas"}, True, "UTC")
        self.assertEqual(d["state"], "Te")

    def test_missing_coordinates_become_none_not_empty_string(self):
        d = _map(HYBRID_MEETING, True, "America/Chicago")
        self.assertIsNone(d["latitude"])
        self.assertIsNone(d["longitude"])

    def test_meeting_without_a_name_is_still_skipped(self):
        self.assertIsNone(_map({"city": "Houston"}, True, "UTC"))


class ImportsAllAttendanceTypesTests(TestCase):
    def test_in_person_meetings_are_imported(self):
        path = feed_file([ONLINE_MEETING, FULL_IN_PERSON_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 2)
        self.assertEqual(Meeting.objects.count(), 2)
        m = Meeting.objects.get(slug="mtg-test-downtown-noon")
        self.assertEqual(m.attendance_option, "in_person")
        self.assertEqual(m.city, "Houston")
        self.assertEqual(m.state, "TX")

    def test_new_online_meetings_use_the_mtg_prefix(self):
        path = feed_file([ONLINE_MEETING])
        sync_source("test", path)
        self.assertTrue(
            Meeting.objects.filter(slug="mtg-test-morning-serenity").exists())

    def test_existing_online_row_is_updated_in_place_not_duplicated(self):
        """The 1,565 legacy `online-` rows must keep their indexed URLs."""
        Meeting.objects.create(
            slug="online-test-morning-serenity",
            name="Morning Serenity",
            attendance_option="online",
            conference_url="https://zoom.us/j/OLD",
            is_approved=True, is_active=True,
        )
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(Meeting.objects.count(), 1)
        m = Meeting.objects.get(slug="online-test-morning-serenity")
        self.assertEqual(m.conference_url, "https://zoom.us/j/123")

    def test_online_meeting_that_becomes_hybrid_keeps_its_url(self):
        Meeting.objects.create(
            slug="online-test-bridge-group",
            name="Bridge Group",
            attendance_option="online",
            conference_url="https://zoom.us/j/999",
            is_approved=True, is_active=True,
        )
        path = feed_file([HYBRID_MEETING])
        sync_source("test", path)

        self.assertEqual(Meeting.objects.count(), 1)
        m = Meeting.objects.get(slug="online-test-bridge-group")
        self.assertEqual(m.attendance_option, "hybrid")
        self.assertEqual(m.city, "Seattle")

    def test_deactivation_covers_both_prefixes(self):
        Meeting.objects.create(
            slug="online-test-gone-legacy", name="Gone Legacy",
            is_approved=True, is_active=True)
        Meeting.objects.create(
            slug="mtg-test-gone-new", name="Gone New",
            is_approved=True, is_active=True)
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["deactivated"], 2)
        self.assertFalse(Meeting.objects.get(slug="online-test-gone-legacy").is_active)
        self.assertFalse(Meeting.objects.get(slug="mtg-test-gone-new").is_active)

    def test_community_submissions_are_never_deactivated(self):
        user = User.objects.create_user("c", "c@example.com", "pw")
        Meeting.objects.create(
            slug="mtg-test-community-run", name="Community Run",
            submitted_by=user, is_approved=True, is_active=True)
        path = feed_file([ONLINE_MEETING])
        result = sync_source("test", path)

        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(Meeting.objects.get(slug="mtg-test-community-run").is_active)

    def test_empty_feed_still_skips_deactivation(self):
        Meeting.objects.create(
            slug="mtg-test-survivor", name="Survivor",
            is_approved=True, is_active=True)
        result = sync_source("test", feed_file([]))

        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(Meeting.objects.get(slug="mtg-test-survivor").is_active)

    def test_meetings_without_a_name_are_skipped_not_imported(self):
        path = feed_file([ONLINE_MEETING, {"slug": "nameless", "day": 1}])
        result = sync_source("test", path)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["skipped"], 1)

    def test_feed_of_only_unusable_rows_does_not_deactivate(self):
        """A feed that returns rows but none we can map must not wipe the
        source — same protection as an empty feed."""
        Meeting.objects.create(
            slug="mtg-test-survivor", name="Survivor",
            is_approved=True, is_active=True)
        path = feed_file([{"slug": "nameless", "day": 1}, {"day": 2}])
        result = sync_source("test", path)

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["skipped"], 2)
        self.assertEqual(result["deactivated"], 0)
        self.assertTrue(Meeting.objects.get(slug="mtg-test-survivor").is_active)


class SplitAddressTests(TestCase):
    """Real TSML feeds send only `formatted_address` — no discrete city or
    state. Without parsing it, every in-person meeting has an empty city,
    which breaks both the SEO title and any future city hub page."""

    def test_full_us_address_with_country(self):
        self.assertEqual(
            _split_address("2111 Webster St, League City, TX 77573, USA"),
            {"address": "2111 Webster St", "city": "League City",
             "state": "TX", "postal_code": "77573"},
        )

    def test_address_without_country(self):
        self.assertEqual(
            _split_address("9 Oak Ave, Seattle, WA 98101"),
            {"address": "9 Oak Ave", "city": "Seattle",
             "state": "WA", "postal_code": "98101"},
        )

    def test_address_without_postal_code(self):
        self.assertEqual(
            _split_address("9 Oak Ave, Seattle, WA"),
            {"address": "9 Oak Ave", "city": "Seattle",
             "state": "WA", "postal_code": ""},
        )

    def test_multi_part_street_is_kept_whole(self):
        self.assertEqual(
            _split_address("First Church, 100 Main St, Houston, TX 77002, USA"),
            {"address": "First Church, 100 Main St", "city": "Houston",
             "state": "TX", "postal_code": "77002"},
        )

    def test_zip_plus_four(self):
        self.assertEqual(
            _split_address("1 A St, Austin, TX 78701-1234, USA")["postal_code"],
            "78701-1234",
        )

    def test_lowercase_state_is_upcased(self):
        self.assertEqual(
            _split_address("1 A St, Austin, tx 78701")["state"], "TX")

    def test_unparseable_address_yields_empty_fields(self):
        self.assertEqual(
            _split_address("Somewhere vague"),
            {"address": "", "city": "", "state": "", "postal_code": ""},
        )

    def test_empty_input_yields_empty_fields(self):
        self.assertEqual(
            _split_address(""),
            {"address": "", "city": "", "state": "", "postal_code": ""},
        )

    def test_non_us_address_is_not_forced_into_state(self):
        """A trailing token that is not a 2-letter state must not become one."""
        self.assertEqual(
            _split_address("12 Rue Cler, Paris, France")["state"], "")


class MapParsesFormattedAddressTests(TestCase):
    REAL_FEED_ROW = {
        "name": "Daily Bread Group",
        "slug": "daily-bread-group",
        "day": 1,
        "time": "06:00",
        "attendance_option": "in_person",
        "location": "Bay Area Club",
        "formatted_address": "2111 Webster St, League City, TX 77573, USA",
        "latitude": 29.5119506,
        "longitude": -95.0725082,
        "region": "Clear Lake - Galveston",
    }

    def test_city_and_state_are_derived_from_formatted_address(self):
        d = _map(self.REAL_FEED_ROW, True, "America/Chicago")
        self.assertEqual(d["city"], "League City")
        self.assertEqual(d["state"], "TX")
        self.assertEqual(d["postal_code"], "77573")
        self.assertEqual(d["address"], "2111 Webster St")

    def test_explicit_feed_fields_win_over_the_parsed_address(self):
        row = dict(self.REAL_FEED_ROW, city="Webster", state="TX")
        d = _map(row, True, "America/Chicago")
        self.assertEqual(d["city"], "Webster")

    def test_float_coordinates_survive(self):
        d = _map(self.REAL_FEED_ROW, True, "America/Chicago")
        self.assertEqual(str(d["latitude"]), "29.5119506")
        self.assertEqual(str(d["longitude"]), "-95.0725082")


class SyncQueryCountTests(TestCase):
    """The importer must not scale queries with feed size.

    _resolve_slug checked both slug namespaces with one .exists() query per
    meeting. At ~6,500 meetings that was ~13,000 extra round trips, and the
    first production sync took 33 minutes. Phase 3 multiplies the feed count,
    so this has to be flat before more feeds are added.
    """

    def _feed(self, n):
        return feed_file([
            dict(ONLINE_MEETING, name=f'Group {i}', slug=f'group-{i}')
            for i in range(n)
        ])

    def test_slug_resolution_does_not_scale_with_feed_size(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as small:
            sync_source('qa', self._feed(2))
        with CaptureQueriesContext(connection) as large:
            sync_source('qb', self._feed(12))

        # One write per meeting, nothing else. Was ~8 queries/meeting when
        # _resolve_slug queried per row and update_or_create paid a SELECT
        # plus savepoints on top; now ~1.02.
        extra = len(large.captured_queries) - len(small.captured_queries)
        self.assertLessEqual(
            extra, 10 + 3,
            f'query count grew by {extra} for 10 extra meetings — '
            f'expected ~10 (one write each), so lookups are per-row again')

    def test_existing_rows_are_still_matched_in_one_pass(self):
        """The prefetch must not break in-place updates of legacy slugs."""
        Meeting.objects.create(
            slug='online-qc-group-0', name='Group 0',
            attendance_option='online', conference_url='https://zoom.us/j/OLD',
            is_approved=True, is_active=True)
        result = sync_source('qc', self._feed(3))

        self.assertEqual(result['created'], 2)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(
            Meeting.objects.get(slug='online-qc-group-0').conference_url,
            'https://zoom.us/j/123')


class UpdatedAtFreshnessTests(TestCase):
    """updated_at is rendered as "Last verified" on in-person meeting pages.

    QuerySet.update() bypasses save(), so auto_now would never fire and every
    in-person listing would show a frozen verification date — a stale address
    presented as current.
    """

    def test_resyncing_advances_updated_at(self):
        from datetime import timedelta
        from django.utils import timezone as tz

        path = feed_file([ONLINE_MEETING])
        sync_source('fresh', path)
        m = Meeting.objects.get(slug='mtg-fresh-morning-serenity')
        Meeting.objects.filter(pk=m.pk).update(
            updated_at=tz.now() - timedelta(days=30))
        stale = Meeting.objects.get(pk=m.pk).updated_at

        sync_source('fresh', path)

        self.assertGreater(Meeting.objects.get(pk=m.pk).updated_at, stale)
