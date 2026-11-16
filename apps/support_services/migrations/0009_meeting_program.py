"""Add Meeting.program and mark every existing feed import as AA.

Until now every feed was an AA intergroup, so imported rows (no submitter,
"mtg-"/"online-" slug) are all AA. NA imports arrive with program='NA'.
"""
from django.db import migrations, models
from django.db.models import Q


def backfill(apps, schema_editor):
    Meeting = apps.get_model('support_services', 'Meeting')
    Meeting.objects.filter(
        Q(slug__startswith='mtg-') | Q(slug__startswith='online-'),
        submitted_by__isnull=True,
    ).update(program='AA')


class Migration(migrations.Migration):
    dependencies = [
        ('support_services', '0008_backfill_meeting_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='program',
            field=models.CharField(blank=True, db_index=True, max_length=10),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
