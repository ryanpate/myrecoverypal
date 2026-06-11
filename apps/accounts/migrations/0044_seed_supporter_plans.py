"""Seed Supporter SubscriptionPlan rows.

Stripe Product + Prices will be created manually out-of-band before go-live.
stripe_price_id left blank here — wire in a follow-up migration once Stripe
prices are created.
"""
from decimal import Decimal

from django.db import migrations


SUPPORTER_FEATURES = [
    "Support a member's recovery journey",
    "See your member's check-in activity (with consent)",
    "Send encouragement messages",
    "One-tap encouragement reactions",
    "Be notified if your member goes quiet",
    "Supporter dashboard",
]


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")

    SubscriptionPlan.objects.update_or_create(
        tier="supporter",
        billing_period="monthly",
        defaults={
            "name": "Supporter",
            "price": Decimal("7.99"),
            "currency": "USD",
            "stripe_product_id": "",
            "stripe_price_id": "",
            "features": SUPPORTER_FEATURES,
            "description": (
                "Support someone in recovery. See their check-in activity, "
                "send encouragement, and get notified if they go quiet."
            ),
            "is_active": True,
            "sort_order": 40,
        },
    )

    SubscriptionPlan.objects.update_or_create(
        tier="supporter",
        billing_period="yearly",
        defaults={
            "name": "Supporter (Yearly)",
            "price": Decimal("79.00"),
            "currency": "USD",
            "stripe_product_id": "",
            "stripe_price_id": "",
            "features": SUPPORTER_FEATURES,
            "description": (
                "Save ~17% vs monthly. Support someone in recovery. "
                "See their check-in activity, send encouragement, and "
                "get notified if they go quiet."
            ),
            "is_active": True,
            "sort_order": 41,
        },
    )


def unseed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(tier="supporter").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0043_supporter_supporter_set_null"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
