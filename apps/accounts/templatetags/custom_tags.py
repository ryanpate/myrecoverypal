from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def get_online_status(user):
    """
    Determine online status based on last_seen:
    - Online: Active within last 5 minutes
    - Recently Active: Active within last 30 minutes  
    - Offline: Inactive for 30+ minutes
    """
    if not user or not user.last_seen:
        return 'offline'
    
    now = timezone.now()
    time_diff = now - user.last_seen
    
    if time_diff < timedelta(minutes=5):
        return 'online'
    elif time_diff < timedelta(minutes=30):
        return 'recently-active'
    else:
        return 'offline'