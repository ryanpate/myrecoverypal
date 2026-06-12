from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def reset_trials(apps, schema_editor):
    """Give every in-trial subscription a fresh 14-day window from launch."""
    Subscription = apps.get_model('accounts', 'Subscription')
    Subscription.objects.filter(status='trialing').update(
        trial_end=timezone.now() + timedelta(days=14)
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0046_alter_subscription_status'),
    ]

    operations = [
        migrations.RunPython(reset_trials, noop_reverse),
    ]
