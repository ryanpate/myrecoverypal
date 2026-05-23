"""Rename `pro` tier to `court` and update any existing rows."""
from django.db import migrations, models


def rename_pro_to_court(apps, schema_editor):
    Subscription = apps.get_model('accounts', 'Subscription')
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    Subscription.objects.filter(tier='pro').update(tier='court')
    SubscriptionPlan.objects.filter(tier='pro').update(tier='court')


def reverse_rename(apps, schema_editor):
    Subscription = apps.get_model('accounts', 'Subscription')
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    Subscription.objects.filter(tier='court').update(tier='pro')
    SubscriptionPlan.objects.filter(tier='court').update(tier='pro')


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0033_seed_lovedone60'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='tier',
            field=models.CharField(
                choices=[('free', 'Free'), ('premium', 'Premium'), ('court', 'Court Compliance')],
                default='free', max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='tier',
            field=models.CharField(
                choices=[('free', 'Free'), ('premium', 'Premium'), ('court', 'Court Compliance')],
                max_length=10,
            ),
        ),
        migrations.RunPython(rename_pro_to_court, reverse_rename),
    ]
