"""Which one-off announcement emails each member has received.

One row per (user, key), so `send_feature_announcement` never emails anyone
twice and a new announcement only needs a new key, not a new User column.
"""
from django.conf import settings
from django.db import models


class AnnouncementDelivery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='announcement_deliveries')
    key = models.CharField(max_length=60)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'key')

    def __str__(self):
        return f'{self.key} -> {self.user_id}'
