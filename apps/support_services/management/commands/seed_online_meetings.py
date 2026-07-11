"""Sync online recovery meetings from configured TSML feeds.

The heavy lifting lives in apps.support_services.meeting_sync (shared with
the weekly Celery task). This command is the manual entry point.

Usage:
    python manage.py seed_online_meetings                     # all configured sources
    python manage.py seed_online_meetings --source <url> --key <key>   # one feed
    python manage.py seed_online_meetings --limit 100 --source <url> --key t  # testing
"""

from django.core.management.base import BaseCommand, CommandError

from apps.support_services.meeting_sync import sync_all, sync_source


class Command(BaseCommand):
    help = "Sync online meetings from TSML/Meeting Guide JSON feeds"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=str, default=None,
            help="URL or file path to a single feed (requires --key)",
        )
        parser.add_argument(
            "--key", type=str, default=None,
            help="Slug-namespace key for the single feed (with --source)",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Maximum meetings to import (single-source mode only)",
        )
        parser.add_argument(
            "--no-approve", action="store_true",
            help="Import as unapproved (default auto-approves)",
        )

    def handle(self, *args, **options):
        if options["source"]:
            if not options["key"]:
                raise CommandError("--source requires --key")
            results = {
                options["key"]: sync_source(
                    options["key"],
                    options["source"],
                    approve=not options["no_approve"],
                    limit=options["limit"],
                )
            }
        else:
            results = sync_all()

        for key, result in results.items():
            self.stdout.write(f"{key}: {result}")
        self.stdout.write(self.style.SUCCESS("Done."))
