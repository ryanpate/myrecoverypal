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


def can_access_resource(user, resource):
    """Whether `user` may use the full content of `resource`."""
    if resource.access_level == 'registered':
        return bool(getattr(user, 'is_authenticated', False))
    if resource.access_level == 'premium':
        return user_has_premium(user)
    return True
