"""
One-time data migration to fix DailyCheckIn dates stored as UTC instead of
the user's local date.

Problem: Server TIME_ZONE is UTC. A user checking in at 8 PM Central (CST/CDT)
would have created_at = 2 AM UTC the *next* day, and the date field was set to
that UTC date — one day ahead of their actual local date.

Fix: For check-ins where created_at falls between midnight and 8 AM UTC
(i.e., the user was likely in a US timezone checking in during the evening),
shift the date field back by one day. Skip any that would create a
unique_together conflict (user already has a check-in on the corrected date).
"""

from datetime import timedelta

from django.db import migrations


def fix_utc_dates(apps, schema_editor):
    DailyCheckIn = apps.get_model('accounts', 'DailyCheckIn')

    # Find check-ins created between midnight and 8 AM UTC
    # These are likely US evening check-ins stored with the wrong date
    candidates = DailyCheckIn.objects.filter(
        created_at__hour__lt=8
    )

    fixed = 0
    skipped = 0

    for checkin in candidates:
        corrected_date = checkin.date - timedelta(days=1)

        # Skip if there's already a check-in for this user on the corrected date
        conflict = DailyCheckIn.objects.filter(
            user_id=checkin.user_id,
            date=corrected_date,
        ).exclude(pk=checkin.pk).exists()

        if conflict:
            skipped += 1
            continue

        checkin.date = corrected_date
        checkin.save(update_fields=['date'])
        fixed += 1

    if fixed or skipped:
        print(f"\n  Fixed {fixed} check-in date(s), skipped {skipped} (conflict).")


def noop(apps, schema_editor):
    pass  # No reverse — dates can't be reliably reverted


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_add_linked_checkin_to_socialpost'),
    ]

    operations = [
        migrations.RunPython(fix_utc_dates, noop),
    ]
