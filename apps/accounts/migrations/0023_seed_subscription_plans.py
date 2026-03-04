"""
Seed SubscriptionPlan records with Stripe price IDs.

Product: MyRecoveryPal Premium (prod_U5YubDoBSimGpa)
Monthly: price_1T7NmL6oOlORkbTyymje0SAM ($4.99/mo)
Yearly:  price_1T7NmM6oOlORkbTydJQkQgFf ($29.99/yr)
"""
from django.db import migrations


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')

    # Clear any stale plans first
    SubscriptionPlan.objects.all().delete()

    SubscriptionPlan.objects.create(
        name='Premium Monthly',
        tier='premium',
        billing_period='monthly',
        price=4.99,
        currency='USD',
        stripe_price_id='price_1T7NmL6oOlORkbTyymje0SAM',
        stripe_product_id='prod_U5YubDoBSimGpa',
        features=[
            'AI Recovery Coach (20 msgs/day)',
            'Unlimited groups & private groups',
            'Unlimited journal & export',
            '90-day analytics & charts',
            'Premium badge',
        ],
        description='Full access to all MyRecoveryPal Premium features, billed monthly.',
        is_active=True,
        sort_order=1,
    )

    SubscriptionPlan.objects.create(
        name='Premium Yearly',
        tier='premium',
        billing_period='yearly',
        price=29.99,
        currency='USD',
        stripe_price_id='price_1T7NmM6oOlORkbTydJQkQgFf',
        stripe_product_id='prod_U5YubDoBSimGpa',
        features=[
            'AI Recovery Coach (20 msgs/day)',
            'Unlimited groups & private groups',
            'Unlimited journal & export',
            '90-day analytics & charts',
            'Premium badge',
            'Save 50% vs monthly',
        ],
        description='Full access to all MyRecoveryPal Premium features, billed yearly. Save 50%!',
        is_active=True,
        sort_order=2,
    )


def reverse_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('accounts', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(
        stripe_product_id='prod_U5YubDoBSimGpa'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_fix_checkin_utc_dates'),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_plans),
    ]
