"""Manually trigger the daily blog digest email.

Usage:
    python manage.py send_blog_digest           # run synchronously, bypass idempotency cache
    python manage.py send_blog_digest --dry-run # render email for first recipient and print HTML; send nothing
"""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone


class Command(BaseCommand):
    help = "Send the daily blog digest now (bypasses the idempotency cache) or preview with --dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Render the email for the first eligible recipient and print to stdout. No emails sent, no cache writes.',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self._dry_run()
            return

        # Clear today's idempotency key so the task actually runs.
        today_key = f"blog_digest_sent_{timezone.now().date().isoformat()}"
        cache.delete(today_key)
        self.stdout.write(f"Cleared cache key {today_key}, running task...")

        from apps.blog.tasks import send_daily_blog_digest
        send_daily_blog_digest()
        self.stdout.write(self.style.SUCCESS("send_daily_blog_digest completed."))

    def _dry_run(self):
        from apps.blog.models import Post
        from apps.accounts.models import User

        window_start = timezone.now() - timedelta(hours=24)
        posts = list(
            Post.objects
            .filter(status='published', published_at__gte=window_start)
            .select_related('author')
            .order_by('-published_at')
        )
        if not posts:
            self.stdout.write(self.style.WARNING(
                "No posts in last 24h. Task would log and exit with no email sent."
            ))
            return

        author_ids = {p.author_id for p in posts}
        recipient = (
            User.objects
            .filter(is_active=True, email_notifications=True)
            .exclude(email='')
            .exclude(pk__in=author_ids)
            .first()
        )
        if recipient is None:
            self.stdout.write(self.style.WARNING(
                "No eligible recipients. Task would log and exit with no email sent."
            ))
            return

        site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')
        html = render_to_string('emails/blog_daily_digest.html', {
            'user': recipient,
            'posts': posts,
            'site_url': site_url,
            'unsubscribe_url': f"{site_url}/accounts/edit-profile/#email-prefs",
            'current_year': timezone.now().year,
        })
        self.stdout.write(f"--- Would send to: {recipient.email} ---")
        self.stdout.write(f"--- Posts in digest: {len(posts)} ---")
        for p in posts:
            self.stdout.write(f"  · {p.title} (by {p.author.username}, {p.published_at})")
        self.stdout.write("\n--- Rendered HTML (first 2000 chars) ---")
        self.stdout.write(html[:2000])
