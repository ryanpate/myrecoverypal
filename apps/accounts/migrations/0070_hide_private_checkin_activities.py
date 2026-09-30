from django.db import migrations
from django.db.models import Q


def hide_private_activities(apps, schema_editor):
    """Unshared check-ins and logged slips were written with the model
    default is_public=True, which exposed them on followers' dashboards.
    Shared check-ins ("<name> checked in") and pledges stay public."""
    ActivityFeed = apps.get_model('accounts', 'ActivityFeed')
    ActivityFeed.objects.filter(
        Q(title__startswith='Daily Check-in:') | Q(title='Logged a slip'),
        activity_type='check_in_posted',
        is_public=True,
    ).update(is_public=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0069_supporter_family_invite'),
    ]

    operations = [
        migrations.RunPython(hide_private_activities, migrations.RunPython.noop),
    ]
