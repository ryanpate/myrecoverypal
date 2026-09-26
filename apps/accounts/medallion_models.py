"""One-time HD Medallion Pack purchases ($4.99, or included with Premium)."""
import secrets

from django.conf import settings
from django.db import models


def _new_token():
    return secrets.token_urlsafe(24)


class MedallionPackPurchase(models.Model):
    """A paid (or Premium-included) unlock of one medallion design's HD pack.

    Buyers may be anonymous — most medallion traffic arrives from search — so
    the unguessable `token` is the credential for the download page. The badge
    parameters are frozen at purchase so the pack always matches what was bought.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    token = models.CharField(max_length=64, unique=True, default=_new_token)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='medallion_pack_purchases',
    )
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    amount_cents = models.PositiveIntegerField(default=0)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    receipt_emailed = models.BooleanField(default=False)

    # Frozen badge parameters (same meaning as SavedBadge).
    days = models.PositiveIntegerField()
    style = models.CharField(max_length=30)
    name = models.CharField(max_length=30, blank=True)
    time_format = models.CharField(max_length=10, default='auto')
    font_size = models.PositiveIntegerField(default=110)
    color = models.CharField(max_length=10, default='white')
    outline = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Medallion pack #{self.pk} ({self.days}d {self.style}, {self.status})'

    def badge_kwargs(self):
        return {
            'style': self.style, 'name': self.name, 'time_format': self.time_format,
            'font_size': self.font_size, 'color': self.color, 'outline': self.outline,
        }
