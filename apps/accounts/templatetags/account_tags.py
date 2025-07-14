from django import template

register = template.Library()

@register.filter
def unread_messages_count(user):
    """Get count of unread messages for a user"""
    if user.is_authenticated:
        return user.received_messages.filter(is_read=False).count()
    return 0

@register.filter
def has_unread_messages(user):
    """Check if user has unread messages"""
    if user.is_authenticated:
        return user.received_messages.filter(is_read=False).exists()
    return False