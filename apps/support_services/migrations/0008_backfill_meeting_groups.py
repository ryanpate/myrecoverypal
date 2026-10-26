"""Backfill group_key and is_group_primary for every existing meeting (~23k rows)."""
from django.db import migrations


def backfill(apps, schema_editor):
    from apps.support_services.grouping import assign_primaries, meeting_group_key

    Meeting = apps.get_model('support_services', 'Meeting')
    batch = []
    for meeting in Meeting.objects.only(
            'pk', 'slug', 'name', 'attendance_option', 'formatted_address', 'address',
            'location', 'city', 'state', 'conference_url', 'submitted_by').iterator(chunk_size=2000):
        meeting.group_key = meeting_group_key(meeting)
        batch.append(meeting)
        if len(batch) >= 2000:
            Meeting.objects.bulk_update(batch, ['group_key'])
            batch = []
    if batch:
        Meeting.objects.bulk_update(batch, ['group_key'])
    assign_primaries(Meeting)


class Migration(migrations.Migration):
    dependencies = [
        ('support_services', '0007_meeting_group_key'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
