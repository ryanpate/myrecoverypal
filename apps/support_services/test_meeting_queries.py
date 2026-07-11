"""Tests for meetings-starting-soon.

'Now' is frozen by patching the datetime symbol inside meeting_queries with
a subclass whose now() returns a fixed moment: Wednesday 2026-07-08 22:00
America/Chicago (day index 3 in the Meeting model's 0=Sunday scheme).
"""
from datetime import datetime, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase

from apps.support_services.meeting_queries import starting_soon
from apps.support_services.models import Meeting

FIXED_NOW = datetime(2026, 7, 8, 22, 0, tzinfo=ZoneInfo("America/Chicago"))


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW.astimezone(tz) if tz else FIXED_NOW.replace(tzinfo=None)


def make_meeting(slug, day, t, tz="America/Chicago", **kw):
    defaults = dict(
        name=slug, slug=slug, day=day, time=t, timezone=tz,
        attendance_option="online", conference_url="https://zoom.us/j/1",
        is_active=True, is_approved=True,
    )
    defaults.update(kw)
    return Meeting.objects.create(**defaults)


@patch("apps.support_services.meeting_queries.datetime", FixedDatetime)
class StartingSoonTests(TestCase):
    # Fixed now: Wed 22:00 Chicago. Window (3h): 22:00 Wed .. 01:00 Thu.
    # Meeting day indexes: Wed=3, Thu=4.

    def test_meeting_within_window_included_with_minutes_until(self):
        make_meeting("in-window", day=3, t=time(22, 30))
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["in-window"])
        self.assertEqual(result[0].minutes_until, 30)

    def test_meeting_already_started_excluded(self):
        make_meeting("past", day=3, t=time(21, 0))
        self.assertEqual(starting_soon(), [])

    def test_meeting_beyond_window_excluded(self):
        make_meeting("too-late", day=4, t=time(2, 0))  # Thu 02:00, window ends 01:00
        self.assertEqual(starting_soon(), [])

    def test_midnight_spillover_included(self):
        make_meeting("after-midnight", day=4, t=time(0, 30))  # Thu 00:30
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["after-midnight"])
        self.assertEqual(result[0].minutes_until, 150)

    def test_cross_zone_ordering(self):
        # 22:00 Chicago == 23:00 New York.
        make_meeting("chicago-2300", day=3, t=time(23, 0))                      # 60 min out
        make_meeting("ny-2330", day=3, t=time(23, 30), tz="America/New_York")   # 30 min out
        result = starting_soon()
        self.assertEqual([m.slug for m in result], ["ny-2330", "chicago-2300"])

    def test_inactive_in_person_and_unscheduled_excluded(self):
        make_meeting("inactive", day=3, t=time(22, 30), is_active=False)
        make_meeting("in-person", day=3, t=time(22, 30),
                     attendance_option="in_person")
        make_meeting("no-time", day=3, t=None)
        self.assertEqual(starting_soon(), [])

    def test_limit_applies_after_sorting(self):
        for i in range(8):
            make_meeting(f"m-{i}", day=3, t=time(22, 10 + i))
        result = starting_soon(limit=3)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].minutes_until, 10)

    def test_invalid_timezone_skipped_not_crashing(self):
        make_meeting("bad-tz", day=3, t=time(22, 30), tz="Not/AZone")
        make_meeting("good", day=3, t=time(22, 30))
        self.assertEqual([m.slug for m in starting_soon()], ["good"])
