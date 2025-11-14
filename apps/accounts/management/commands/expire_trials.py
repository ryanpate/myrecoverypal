"""
Management command to expire trial subscriptions
Run this daily via cron or Railway scheduled tasks
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.payment_models import Subscription


class Command(BaseCommand):
    help = 'Expire trial subscriptions that have ended'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually expiring',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()

        # Find all trialing subscriptions with expired trial_end
        expired_trials = Subscription.objects.filter(
            status='trialing',
            trial_end__lte=now
        )

        count = expired_trials.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired trials found.'))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would expire {count} trial(s):')
            )
            for subscription in expired_trials:
                self.stdout.write(
                    f'  - User: {subscription.user.username} (trial ended: {subscription.trial_end})'
                )
        else:
            # Expire the trials by downgrading to free tier
            updated = expired_trials.update(
                tier='free',
                status='active',
                trial_end=None
            )

            self.stdout.write(
                self.style.SUCCESS(f'Successfully expired {updated} trial subscription(s)')
            )

            # Log each expired subscription
            for subscription in Subscription.objects.filter(
                id__in=expired_trials.values_list('id', flat=True)
            ):
                self.stdout.write(
                    f'  - Downgraded user {subscription.user.username} to free tier'
                )
