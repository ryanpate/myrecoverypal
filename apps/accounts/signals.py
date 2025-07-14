from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from .models import User

@receiver(user_logged_in)
def update_last_seen(sender, user, request, **kwargs):
    """Update the last_seen timestamp when user logs in"""
    User.objects.filter(id=user.id).update(last_seen=timezone.now())