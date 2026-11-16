"""Gift a year of Premium: bought once by anyone, redeemed by one member."""
from django.conf import settings
from django.db import models

from .medallion_models import _new_token


class PremiumGift(models.Model):
    """A prepaid year of Premium.

    The buyer needs no account (most are family, not members), so the
    unguessable `token` is the credential: whoever holds the link can redeem
    it, once.
    """
    STATUS_CHOICES = [
        ('pending', 'Awaiting payment'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    token = models.CharField(max_length=64, unique=True, default=_new_token)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    amount_cents = models.PositiveIntegerField()
    buyer_email = models.EmailField(blank=True)
    # Shown on the gift card. Both optional.
    from_name = models.CharField(max_length=40, blank=True)
    message = models.CharField(max_length=280, blank=True)

    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    receipt_emailed = models.BooleanField(default=False)

    redeemed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='premium_gifts',
    )
    redeemed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Premium gift #{self.pk} ({self.status}{", redeemed" if self.redeemed_at else ""})'

    @property
    def redeemable(self):
        return self.status == 'paid' and not self.redeemed_at
