"""Seed Court Compliance SubscriptionPlan rows with live Stripe Price IDs.

Stripe Product + Prices were created via Stripe API on 2026-05-24:
- Product:       prod_UZin13sVWUI2b0  (MyRecoveryPal Court Compliance)
- Monthly price: price_1TaZME6oOlORkbTyZKsevLhS  ($19.99/mo)
- Yearly price:  price_1TaZMF6oOlORkbTyQ7oXCvxp  ($179/yr)

Stripe Price IDs are public identifiers (not secrets) and safe to commit.
"""
from decimal import Decimal

from django.db import migrations


PRODUCT_ID = "prod_UZin13sVWUI2b0"
MONTHLY_PRICE_ID = "price_1TaZME6oOlORkbTyZKsevLhS"
YEARLY_PRICE_ID = "price_1TaZMF6oOlORkbTyQ7oXCvxp"

COURT_FEATURES = [
    "Everything in Premium",
    "Log AA, NA, SMART, & secular meeting attendance",
    "Court-acceptable PDF reports with tamper-evident fingerprint",
    "Email reports directly to your probation officer",
    "Public verification URL — courts can confirm document integrity",
    "Compliance dashboard with weekly progress",
    "Unlimited reports + attendance logs",
]


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")

    SubscriptionPlan.objects.update_or_create(
        tier="court",
        billing_period="monthly",
        defaults={
            "name": "Court Compliance — Monthly",
            "price": Decimal("19.99"),
            "currency": "USD",
            "stripe_product_id": PRODUCT_ID,
            "stripe_price_id": MONTHLY_PRICE_ID,
            "features": COURT_FEATURES,
            "description": (
                "Court-acceptable PDF attendance reports with tamper-evident "
                "fingerprint, email-to-PO, and compliance dashboard. Includes "
                "all Premium features."
            ),
            "is_active": True,
            "sort_order": 30,
        },
    )

    SubscriptionPlan.objects.update_or_create(
        tier="court",
        billing_period="yearly",
        defaults={
            "name": "Court Compliance — Annual",
            "price": Decimal("179.00"),
            "currency": "USD",
            "stripe_product_id": PRODUCT_ID,
            "stripe_price_id": YEARLY_PRICE_ID,
            "features": COURT_FEATURES,
            "description": (
                "Save 25% vs monthly. Court-acceptable PDF attendance reports "
                "with tamper-evident fingerprint, email-to-PO, and compliance "
                "dashboard. Includes all Premium features."
            ),
            "is_active": True,
            "sort_order": 31,
        },
    )


def unseed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(
        tier="court", stripe_price_id__in=[MONTHLY_PRICE_ID, YEARLY_PRICE_ID]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0035_court_compliance_models"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
