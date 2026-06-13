"""Cross-linking between recovery resources and blog posts.

Resources and blog posts use separate taxonomies, so we bridge them with an
explicit category map. This keeps internal links topical and works at any scale
(no per-item curation) as new posts/resources are added. Model imports are lazy
inside the helpers to avoid an import cycle between the two apps.
"""

# Resource category slug -> blog category names whose posts are topically related.
RESOURCE_TO_BLOG_CATEGORIES = {
    'educational': ['Education & Awareness', 'Recovery Fundamentals'],
    'support': ['Support Systems', 'Community Voices', 'Personal Journey'],
    'tools': ['Coping Strategies', 'Resources & Tools', 'Life Skills', 'Relapse Prevention'],
    'wellness': ['Mental Health & Wellness', 'Daily Living'],
    'family': ['Family & Relationships'],
    'professional': ['Education & Awareness', 'Mental Health & Wellness', 'Special Populations'],
    'crisis': ['Mental Health & Wellness'],
}

# Blog category name -> resource category slugs whose resources are relevant.
BLOG_TO_RESOURCE_CATEGORIES = {
    'Education & Awareness': ['educational', 'professional'],
    'Recovery Fundamentals': ['educational', 'tools'],
    'Support Systems': ['support'],
    'Community Voices': ['support'],
    'Personal Journey': ['support', 'wellness'],
    'Coping Strategies': ['tools', 'wellness'],
    'Resources & Tools': ['tools'],
    'Life Skills': ['tools', 'wellness'],
    'Mental Health & Wellness': ['wellness', 'professional'],
    'Daily Living': ['wellness', 'tools'],
    'Family & Relationships': ['family'],
    'Relapse Prevention': ['tools'],
    'Special Populations': ['professional'],
    'Inspiration & Motivation': ['support', 'wellness'],
}


def related_blog_posts(resource, limit=3):
    """Published blog posts topically related to a resource (by category map)."""
    from apps.blog.models import Post

    cat_names = RESOURCE_TO_BLOG_CATEGORIES.get(resource.category.slug, [])
    if not cat_names:
        return Post.objects.none()
    return (
        Post.objects.filter(status='published', category__name__in=cat_names)
        .select_related('author', 'category')
        .order_by('-published_at')[:limit]
    )


def related_resources_for_post(post, limit=3):
    """Active resources relevant to a blog post (by category map).

    Falls back to featured resources when the post's blog category isn't mapped,
    so every post still surfaces a few useful tools.
    """
    from resources.models import Resource

    slugs = BLOG_TO_RESOURCE_CATEGORIES.get(post.category.name, []) if post.category else []
    qs = Resource.objects.filter(is_active=True).select_related('category', 'resource_type')
    if slugs:
        qs = qs.filter(category__slug__in=slugs)
    return qs.order_by('-featured', '-created_at')[:limit]
