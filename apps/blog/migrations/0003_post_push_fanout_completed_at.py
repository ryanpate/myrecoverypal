from django.db import migrations, models


def backfill_completed_at(apps, schema_editor):
    """Treat already-published posts as having their fan-out done.

    Without this, deploying the new beat retry task would fire off push
    notifications for every historical blog post the next time beat runs.
    """
    Post = apps.get_model('blog', 'Post')
    Post.objects.filter(
        status='published',
        published_at__isnull=False,
        push_fanout_completed_at__isnull=True,
    ).update(push_fanout_completed_at=models.F('published_at'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_alter_post_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='push_fanout_completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_completed_at, noop),
    ]
