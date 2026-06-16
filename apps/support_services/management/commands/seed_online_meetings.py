"""Seed the Meeting table with online recovery meetings from a public TSML feed.

Online meetings are location-independent: the conference URL works for anyone,
anywhere, and the source intergroup keeps those links current. We import only
the *online* subset of a real Meeting Guide / TSML feed so the local meeting
search returns accurate, joinable results instead of an empty list.

Usage:
    python manage.py seed_online_meetings                 # default source, auto-approved
    python manage.py seed_online_meetings --source <url>  # any TSML JSON feed
    python manage.py seed_online_meetings --limit 100     # cap rows (testing)
"""

from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.support_services.models import Meeting

# Seattle AA Intergroup publishes a large, well-maintained TSML feed with ~400
# online meetings spread across every day of the week. Online meetings are open
# to anyone regardless of location.
DEFAULT_SOURCE = "https://www.seattleaa.org/wp-admin/admin-ajax.php?action=meetings"

# Slug namespace so imported rows never collide with community-submitted meetings.
SLUG_PREFIX = "online"


class Command(BaseCommand):
    help = "Import online meetings from a TSML/Meeting Guide JSON feed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=str, default=DEFAULT_SOURCE,
            help="URL or local file path to a TSML/Meeting Guide JSON feed",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Maximum number of meetings to import (for testing)",
        )
        parser.add_argument(
            "--no-approve", action="store_true",
            help="Import as unapproved (default is auto-approved so they appear in search)",
        )

    def handle(self, *args, **options):
        source = options["source"]
        limit = options["limit"]
        approve = not options["no_approve"]

        data = self._load(source)
        meetings = data if isinstance(data, list) else data.get("meetings", [])

        online = [
            m for m in meetings
            if m.get("attendance_option") == "online" and m.get("conference_url")
        ]
        self.stdout.write(
            f"Feed: {len(meetings)} meetings total, {len(online)} online with a join link"
        )
        if limit:
            online = online[:limit]

        created = updated = skipped = 0
        for m in online:
            slug = self._slug(m)
            defaults = self._map(m, approve)
            if defaults is None:
                skipped += 1
                continue
            obj, was_created = Meeting.objects.update_or_create(
                slug=slug, defaults=defaults
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} created, {updated} updated, {skipped} skipped."
        ))

    def _load(self, source):
        if source.startswith("http"):
            resp = requests.get(source, headers={"User-Agent": "MyRecoveryPal/1.0"}, timeout=60)
            resp.raise_for_status()
            return resp.json()
        import json
        with open(source) as f:
            return json.load(f)

    def _slug(self, m):
        base = m.get("slug") or slugify(m.get("name", "meeting"))
        return f"{SLUG_PREFIX}-{base}"[:255]

    def _map(self, m, approve):
        name = (m.get("name") or "").strip()
        if not name:
            return None
        return {
            "name": name,
            "day": m.get("day"),
            "time": self._time(m.get("time")),
            "end_time": self._time(m.get("end_time")),
            "timezone": m.get("timezone") or "America/Chicago",
            "attendance_option": "online",
            "conference_url": m.get("conference_url") or "",
            "conference_phone": (m.get("conference_phone") or "")[:30],
            "types": m.get("types") or [],
            # Online meetings have no physical location; keep address fields blank
            # so users don't think they need to travel.
            "location": "Online Meeting",
            "group": (m.get("group") or "")[:255],
            "notes": m.get("notes") or "",  # join instructions / passwords live here
            "is_approved": approve,
            "is_active": True,
        }

    @staticmethod
    def _time(value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%H:%M").time()
        except (ValueError, TypeError):
            return None
