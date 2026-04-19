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

        # Clear the completion marker so the task doesn't short-circuit on
        # the idempotency check. This is an explicit recovery flow: the
        # operator is declaring that pushes were not delivered for this post
        # and should be sent now.
        if post.push_fanout_completed_at is not None:
            self.stdout.write(
                f"Clearing push_fanout_completed_at "
                f"(was {post.push_fanout_completed_at.isoformat()}) "
                f"to force re-send."
            )
            Post.objects.filter(pk=post_id).update(push_fanout_completed_at=None)

        from apps.blog.tasks import fanout_blog_push_notifications

        if run_sync:
            self.stdout.write(f"Running fan-out inline for post {post_id}...")
            result = fanout_blog_push_notifications.apply(args=[post_id])
            if result.failed():
                raise CommandError(f"Fan-out failed: {result.result}")
            self.stdout.write(self.style.SUCCESS("Done."))
            return

        self.stdout.write(f"Enqueuing fan-out for post {post_id}...")
        try:
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
        except Exception as e:
            # Broker (Redis) unavailable or misconfigured. Surface a helpful
            # error instead of letting the traceback propagate to Sentry —
            # this is an expected failure mode during recovery flows (the
            # whole reason this command exists is to recover from exactly
            # this kind of outage).
            raise CommandError(
                f"Could not enqueue task: {e}. The beat reconciliation task "
                f"will retry this post every 15 minutes once the broker is "
                f"back. To force immediate delivery, re-run with --sync "
                f"(runs inline, no broker needed)."
            )
        self.stdout.write(self.style.SUCCESS(
            f"Enqueued. Worker will process shortly. "
            f"If Redis is still down, re-run with --sync."
        ))
