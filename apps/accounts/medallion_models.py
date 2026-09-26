"""Medallion purchases: the HD Medallion Pack and printed Printify keepsakes."""
import secrets

from django.conf import settings
from django.db import models


def _new_token():
    return secrets.token_urlsafe(24)


class MedallionDesign(models.Model):
    """A medallion design frozen at purchase, so what's delivered matches what was bought.

    Buyers may be anonymous (most medallion traffic arrives from search), so the
    unguessable `token` is the credential for the buyer's page.
    """
    token = models.CharField(max_length=64, unique=True, default=_new_token)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    email = models.EmailField(blank=True)
    amount_cents = models.PositiveIntegerField(default=0)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    receipt_emailed = models.BooleanField(default=False)

    # Badge parameters (same meaning as SavedBadge).
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
        abstract = True
        ordering = ['-created_at']

    def badge_kwargs(self):
        return {
            'style': self.style, 'name': self.name, 'time_format': self.time_format,
            'font_size': self.font_size, 'color': self.color, 'outline': self.outline,
        }


class MedallionPackPurchase(MedallionDesign):
    """A paid (or Premium-included) unlock of one medallion design's HD pack."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='medallion_pack_purchases',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta(MedallionDesign.Meta):
        pass

    def __str__(self):
        return f'Medallion pack #{self.pk} ({self.days}d {self.style}, {self.status})'


class KeepsakeOrder(MedallionDesign):
    """A printed keepsake (mug, sticker) fulfilled automatically through Printify."""
    PRODUCT_CHOICES = [('mug', 'Mug'), ('sticker', 'Sticker')]
    STATUS_CHOICES = [
        ('pending', 'Awaiting payment'),
        ('paid', 'Paid'),
        ('submitted', 'Sent to printer'),
        ('in_production', 'In production'),
        ('shipped', 'Shipped'),
        ('failed', 'Needs attention'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='keepsake_orders',
    )
    product = models.CharField(max_length=20, choices=PRODUCT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_name = models.CharField(max_length=200, blank=True)
    shipping_phone = models.CharField(max_length=40, blank=True)
    shipping_address = models.JSONField(default=dict, blank=True)  # Stripe address shape
    printify_order_id = models.CharField(max_length=64, blank=True, db_index=True)
    tracking_url = models.URLField(max_length=500, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    carrier = models.CharField(max_length=50, blank=True)
    last_error = models.TextField(blank=True)
    shipped_emailed = models.BooleanField(default=False)

    class Meta(MedallionDesign.Meta):
        pass

    def __str__(self):
        return f'Keepsake #{self.pk} {self.product} ({self.status})'
