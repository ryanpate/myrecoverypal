"""
Read back a user's Subscription row — for verifying an iOS IAP sandbox purchase
end to end (or any web checkout).

The RevenueCat UI confirms the *purchase*; this confirms the *backend sync*:
that capacitor-iap.js's POST to /accounts/api/ios-subscription/sync/ actually
flipped the row to tier='premium', status='active', subscription_source='apple'.

Run in a Railway shell (so it hits prod DB) right after the sandbox purchase:
    python manage.py show_subscription --email you@example.com
    python manage.py show_subscription --id 42

With no args it summarizes all non-free subscriptions (quick "did anyone pay?").
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.payment_models import Subscription

User = get_user_model()

FIELDS = (
    'tier', 'status', 'billing_period', 'subscription_source',
    'stripe_customer_id', 'stripe_subscription_id', 'stripe_price_id',
    'current_period_start', 'current_period_end', 'trial_end',
    'canceled_at', 'created_at', 'updated_at',
)


class Command(BaseCommand):
    help = "Show a user's Subscription row (verify iOS IAP / web checkout synced)."

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Look up the user by email.')
        parser.add_argument('--id', type=int, dest='user_id',
                            help='Look up the user by user ID.')

    def handle(self, *args, **opts):
        email, user_id = opts.get('email'), opts.get('user_id')

        if not email and not user_id:
            self._summary()
            return

        try:
            user = User.objects.get(email=email) if email else User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'No user found for {"email "+email if email else "id "+str(user_id)}')
        except User.MultipleObjectsReturned:
            raise CommandError(f'Multiple users share email {email}; use --id instead.')

        self.stdout.write(f'\nUser: {user.id}  {user.email}  (@{user.username})')

        sub = Subscription.objects.filter(user=user).first()
        if not sub:
            self.stdout.write(self.style.WARNING('  No Subscription row exists yet.'))
            return

        is_premium = sub.tier == 'premium' and sub.status in ('active', 'trialing')
        head = self.style.SUCCESS('  is_premium=True') if is_premium else self.style.WARNING('  is_premium=False')
        self.stdout.write(head)
        for f in FIELDS:
            self.stdout.write(f'    {f:22} {getattr(sub, f)}')

        # The exact end-to-end success shape after an iOS sandbox purchase.
        if sub.subscription_source == 'apple' and sub.tier == 'premium' and sub.status == 'active':
            self.stdout.write(self.style.SUCCESS('\n  ✓ iOS IAP synced correctly (apple / premium / active).'))

    def _summary(self):
        subs = (Subscription.objects.exclude(tier='free')
                .select_related('user').order_by('-updated_at'))
        self.stdout.write(f'\nNon-free subscriptions: {subs.count()}')
        for s in subs:
            self.stdout.write(
                f'  {s.user.email:35} {s.tier:9} {s.status:9} '
                f'{s.subscription_source:7} updated={s.updated_at:%Y-%m-%d %H:%M}'
            )
        if not subs:
            self.stdout.write(self.style.WARNING('  (none — no paid/trialing subscriptions yet)'))
