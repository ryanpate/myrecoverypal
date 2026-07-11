"""Lookups for the shared daily-thought / daily-reading card.

Used by both the social feed and the progress home so the two surfaces
always agree on the day's content.
"""
from django.utils import timezone

from apps.accounts.models import DailyRecoveryThought


def get_daily_thought():
    """Today's DailyRecoveryThought, or None.

    Uses timezone.now().date() (server/UTC date), matching how the 6 AM UTC
    publish_daily_thought task keys the row — a per-user localdate lookup
    could miss the row entirely near midnight.
    """
    return DailyRecoveryThought.objects.filter(
        date=timezone.now().date()
    ).first()


def get_daily_reading():
    """Deterministic daily pick from published blog posts, or None.

    Same post for every user all day; cycles the whole archive as the
    ordinal advances. No state, no task, no model.
    """
    from apps.blog.models import Post

    posts = Post.objects.filter(status='published').order_by('id')
    count = posts.count()
    if not count:
        return None
    try:
        return posts[timezone.now().date().toordinal() % count]
    except IndexError:
        # A post was deleted between count() and the indexed fetch.
        return None
