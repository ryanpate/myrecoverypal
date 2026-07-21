from django.db import migrations
from django.utils.text import slugify


def fix_empty_slugs(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    for post in Post.objects.filter(slug=''):
        base = slugify(post.title) or f"post-{post.pk}"
        slug = base
        counter = 1
        while Post.objects.filter(slug=slug).exclude(pk=post.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        post.slug = slug
        post.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_post_push_fanout_completed_at'),
    ]

    operations = [
        migrations.RunPython(fix_empty_slugs, migrations.RunPython.noop),
    ]
