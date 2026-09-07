"""Populate is_personal_story so the blog can be demoted from search.

The field has existed since the first migration but was never set — all 73
published posts carried the default False, so it could not be used to tell
keyword articles from personal narratives.

Marks every post True except the six that target real keywords. Reversible:
the backwards pass clears the flag rather than guessing.
"""
from django.db import migrations

SEO_INDEXED_SLUGS = [
    'dopamine-detox-addiction-recovery',
    'high-functioning-alcoholic-signs-help',
    'how-long-does-alcohol-withdrawal-last',
    'how-to-stop-drinking-alcohol-guide',
    'signs-of-alcoholism-self-assessment',
    'what-is-sober-curious-guide',
]


def mark_personal_stories(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    Post.objects.exclude(slug__in=SEO_INDEXED_SLUGS).update(is_personal_story=True)
    Post.objects.filter(slug__in=SEO_INDEXED_SLUGS).update(is_personal_story=False)


def clear_personal_stories(apps, schema_editor):
    Post = apps.get_model('blog', 'Post')
    Post.objects.update(is_personal_story=False)


class Migration(migrations.Migration):
    dependencies = [('blog', '0004_fix_empty_slugs')]
    operations = [
        migrations.RunPython(mark_personal_stories, clear_personal_stories),
    ]
