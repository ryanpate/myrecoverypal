from django.core.management.base import BaseCommand, CommandError

from apps.blog.models import Post


class Command(BaseCommand):
    help = (
        "Re-run push notification fan-out for a published blog post. "
        "Use when the original fan-out was dropped (e.g. Redis was "
        "unavailable when the post was published)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'post_id',
            type=int,
            help='Primary key of the blog Post to fan out.',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Run the fan-out inline instead of enqueuing on Celery.',
        )

    def handle(self, *args, **options):
        post_id = options['post_id']
        run_sync = options['sync']

        try:
            post = Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            raise CommandError(f"Post {post_id} does not exist")

        if post.status != 'published':
            raise CommandError(
                f"Post {post_id} is not published (status={post.status})"
            )

        from apps.blog.tasks import fanout_blog_push_notifications

        if run_sync:
            self.stdout.write(f"Running fan-out inline for post {post_id}...")
            result = fanout_blog_push_notifications.apply(args=[post_id])
            if result.failed():
                raise CommandError(f"Fan-out failed: {result.result}")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        self.stdout.write(f"Enqueuing fan-out for post {post_id}...")
        fanout_blog_push_notifications.apply_async(
            args=[post_id],
            retry=True,
            retry_policy={
                'max_retries': 5,
                'interval_start': 1.0,
                'interval_step': 2.0,
                'interval_max': 5.0,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"Enqueued. Worker will process shortly. "
            f"If Redis is still down, re-run with --sync."
        ))
