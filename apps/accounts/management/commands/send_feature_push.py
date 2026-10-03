"""
Send the one-off "guided audio is here" push notification to app users.

Leads with help, not a sale: the free craving audio. Tapping it opens the
audio library. Targets active members with an active device token who allow
notifications (email_notifications, the existing push preference), haven't
had this push (AnnouncementDelivery with KEY), and for whom it's daytime:
only between 9 AM and 8 PM in each member's own time zone (User.timezone).
Anyone outside that window is skipped and picked up by a later run, so run
it a couple of times across the day to reach everyone.

Dry-run by default. Run in-container via railway ssh:
    python manage.py send_feature_push                      # dry-run
    python manage.py send_feature_push --test USERNAME      # push to one member's devices
    python manage.py send_feature_push --commit             # send
"""
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from apps.accounts.models import AnnouncementDelivery, DeviceToken, User
from apps.accounts.push_notifications import send_push_to_user

KEY = 'library-push-2026-10'
TITLE = 'Guided audio is here 🎧'
BODY = 'When a craving hits, press play. Urge surfing, breathing and grounding, free for everyone.'
SEND_HOURS = range(9, 20)  # local 9:00-19:59


def deep_link():
    return (reverse('resources:audio')
            + '?utm_source=push&utm_medium=push&utm_campaign=library-2026-10')


def local_hour(user, now=None):
    try:
        tz = ZoneInfo(user.timezone) if getattr(user, 'timezone', '') else ZoneInfo('America/New_York')
    except Exception:
        tz = ZoneInfo('America/New_York')
    return (now or datetime.now(tz)).astimezone(tz).hour


class Command(BaseCommand):
    help = 'Send the "guided audio is here" push to members with the app installed.'

    def add_arguments(self, parser):
        parser.add_argument('--test', metavar='USERNAME', help="Push to one member's devices and exit.")
        parser.add_argument('--commit', action='store_true', help='Actually send (default is dry-run).')
        parser.add_argument('--any-hour', action='store_true', help='Ignore the 9 AM-8 PM local-time window.')
        parser.add_argument('--sleep', type=float, default=0.2)

    def handle(self, *args, **opts):
        if opts['test']:
            user = User.objects.filter(username=opts['test']).first()
            if not user:
                raise CommandError(f"No member called {opts['test']}")
            results = send_push_to_user(user, TITLE, BODY, {'url': deep_link(), 'type': 'announcement'})
            self.stdout.write(self.style.SUCCESS(f'Test push to {user.username}: {results} (not recorded)'))
            return

        already = AnnouncementDelivery.objects.filter(key=KEY).values_list('user_id', flat=True)
        with_device = DeviceToken.objects.filter(active=True).values_list('user_id', flat=True)
        candidates = list(User.objects.filter(is_active=True, email_notifications=True, id__in=with_device)
                          .exclude(id__in=already).order_by('id'))
        now = datetime.now(ZoneInfo('UTC'))
        due = [u for u in candidates if opts['any_hour'] or local_hour(u, now) in SEND_HOURS]
        later = len(candidates) - len(due)
        self.stdout.write(f"With the app: {len(candidates)}  |  Daytime now: {len(due)}  |  "
                          f"Outside 9 AM-8 PM (next run): {later}  |  "
                          f"Mode: {'COMMIT' if opts['commit'] else 'DRY-RUN'}")
        if not opts['commit']:
            for u in due[:25]:
                self.stdout.write(f'  would push -> {u.username}')
            self.stdout.write('Dry-run complete. Re-run with --commit to send.')
            return

        sent = failed = 0
        for u in due:
            try:
                results = send_push_to_user(u, TITLE, BODY, {'url': deep_link(), 'type': 'announcement'})
                if sum(r['sent'] for r in results.values()):
                    AnnouncementDelivery.objects.get_or_create(user=u, key=KEY)
                    sent += 1
                else:
                    failed += 1  # nothing delivered: leave unrecorded so a later run retries
            except Exception as exc:
                failed += 1
                self.stderr.write(f'  FAILED {u.username}: {exc}')
            time.sleep(opts['sleep'])
        self.stdout.write(self.style.SUCCESS(f'Done. Delivered to {sent}, failed {failed}, '
                                             f'waiting for daytime {later}.'))
