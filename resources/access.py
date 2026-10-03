"""Access checks for resources and worksheets.

One place that knows how `Resource.access_level` maps onto the user's
subscription, so the list, detail, interactive and download views all agree.
"""


def user_has_premium(user):
    """True when the user has an active Premium (or Court, a superset) tier."""
    if not getattr(user, 'is_authenticated', False):
        return False
    # The reverse one-to-one raises RelatedObjectDoesNotExist (an
    # AttributeError subclass) when no row exists, so getattr's default
    # covers users created before subscriptions were auto-provisioned.
    sub = getattr(user, 'subscription', None)
    return bool(sub and sub.is_premium())


def user_has_supporter_access(user):
    """True for a paid Supporter subscription, or the Supporter seat that a
    loved one's Premium plan includes (SupporterLink.is_included_seat)."""
    if not getattr(user, 'is_authenticated', False):
        return False
    sub = getattr(user, 'subscription', None)
    if sub and sub.is_supporter():
        return True
    from apps.accounts.supporter_models import SupporterLink
    links = SupporterLink.objects.filter(supporter=user, status='active').select_related('member')
    return any(link.is_included_seat() for link in links)


def has_program_access(user, program):
    """Whether `user` can open `program` lessons beyond its free days."""
    if user_has_premium(user):
        return True
    if program.access == 'family':
        return user_has_supporter_access(user)
    return False


def can_access_resource(user, resource):
    """Whether `user` may use the full content of `resource`."""
    if resource.access_level == 'registered':
        return bool(getattr(user, 'is_authenticated', False))
    if resource.access_level == 'premium':
        return user_has_premium(user)
    return True
