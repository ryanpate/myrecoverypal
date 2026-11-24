"""Remove "Court-acceptable" from stored SubscriptionPlan text.

Migration 0036 seeded the Court plans with "Court-acceptable PDF reports"
in their description and feature list. We cannot know what a given court
accepts, so the pages now say "verifiable" and tell the reader to check
with their probation officer; the stored plan text has to match.
"""
import re

from django.db import migrations

CLAIM = re.compile(r"court-acceptable pdf", re.IGNORECASE)


def reword(text):
    return CLAIM.sub("Verifiable PDF", text)


def reword_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("accounts", "SubscriptionPlan")
    for plan in SubscriptionPlan.objects.all():
        description = reword(plan.description or "")
        features = [reword(f) if isinstance(f, str) else f for f in (plan.features or [])]
        if description != (plan.description or "") or features != (plan.features or []):
            plan.description = description
            plan.features = features
            plan.save(update_fields=["description", "features"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0080_social_post_scheduled_at"),
    ]

    operations = [
        migrations.RunPython(reword_plans, migrations.RunPython.noop),
    ]
