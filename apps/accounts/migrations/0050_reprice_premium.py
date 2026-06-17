"""
Phase 2 reprice: Premium $4.99/$29.99 -> $9.99/$59.99.

The new LIVE Stripe prices were created up front (lookup_keys premium_monthly /
premium_yearly) and verified before this migration was written; this only
re-points the SubscriptionPlan rows + display price. Old prices stay active in
Stripe so any in-flight checkout isn't broken. Ships in lockstep with the
pricing copy change so nothing displays a stale price.
"""
from decimal import Decimal

from django.db import migrations

NEW_MONTHLY_PRICE_ID = 'price_1TiiVi6oOlORkbTypCuNQUwO'  # $9.99/month
NEW_YEARLY_PRICE_ID = 'price_1TiiVi6oOlORkbTySfY8eTF7'   # $59.99/year

OLD_MONTHLY_PRICE_ID = 'price_1T7NmL6oOlORkbTyymje0SAM'  # $4.99/month
OLD_YEARLY_PRICE_ID = 'price_1T7NmM6oOlORkbTydJQkQgFf'   # $29.99/year


def _set(apps, monthly_price, monthly_id, yearly_price, yearly_id):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(tier='premium', billing_period='monthly').update(
        price=monthly_price, stripe_price_id=monthly_id)
    SubscriptionPlan.objects.filter(tier='premium', billing_period='yearly').update(
        price=yearly_price, stripe_price_id=yearly_id)


def forwards(apps, schema_editor):
    _set(apps, Decimal('9.99'), NEW_MONTHLY_PRICE_ID, Decimal('59.99'), NEW_YEARLY_PRICE_ID)


def backwards(apps, schema_editor):
    _set(apps, Decimal('4.99'), OLD_MONTHLY_PRICE_ID, Decimal('29.99'), OLD_YEARLY_PRICE_ID)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0049_subscription_winback_sent_at'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
