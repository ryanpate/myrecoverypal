# Generated manually - mark existing users as onboarded

from django.db import migrations


def mark_existing_users_onboarded(apps, schema_editor):
    """Mark all existing users as having completed onboarding."""
    User = apps.get_model('accounts', 'User')
    User.objects.all().update(has_completed_onboarding=True)


def reverse_mark_users(apps, schema_editor):
    """Reverse: mark all users as not having completed onboarding."""
    User = apps.get_model('accounts', 'User')
    User.objects.all().update(has_completed_onboarding=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_has_completed_onboarding'),
    ]

    operations = [
        migrations.RunPython(mark_existing_users_onboarded, reverse_mark_users),
    ]
