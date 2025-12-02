# apps/accounts/payment_models.py
"""
Payment and subscription models for MyRecoveryPal
Handles Stripe subscriptions, transactions, and billing
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

# Founding member limit - first N users get premium free
FOUNDING_MEMBER_LIMIT = 200


class Subscription(models.Model):
    """
    User subscription model
    Tracks Premium and Pro tier subscriptions
    """
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('pro', 'Professional'),
    ]

    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
        ('incomplete', 'Incomplete'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default='free'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    billing_period = models.CharField(
        max_length=10,
        choices=BILLING_PERIOD_CHOICES,
        null=True,
        blank=True
    )

    # Stripe IDs
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)

    # Billing dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Founding member status
    is_founding_member = models.BooleanField(
        default=False,
        help_text="Early adopter with lifetime premium access"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['stripe_customer_id']),
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_tier_display()} ({self.status})"

    def is_active(self):
        """Check if subscription is active"""
        return self.status in ['active', 'trialing']

    def is_premium(self):
        """Check if user has Premium tier or higher (includes founding members)"""
        if self.is_founding_member:
            return True
        return self.tier in ['premium', 'pro'] and self.is_active()

    def is_pro(self):
        """Check if user has Pro tier"""
        return self.tier == 'pro' and self.is_active()

    def is_trialing(self):
        """Check if user is in trial period"""
        return self.status == 'trialing' and self.trial_end and self.trial_end > timezone.now()

    def days_until_renewal(self):
        """Days until next billing cycle"""
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(0, delta.days)
        return None

    def can_upgrade(self):
        """Check if user can upgrade their subscription"""
        if self.tier == 'free':
            return True
        if self.tier == 'premium' and self.is_active():
            return True  # Can upgrade to Pro
        return False

    def can_downgrade(self):
        """Check if user can downgrade their subscription"""
        return self.tier in ['premium', 'pro'] and self.is_active()

    @classmethod
    def get_founding_member_count(cls):
        """Get the number of founding members"""
        try:
            return cls.objects.filter(is_founding_member=True).count()
        except Exception:
            # Column may not exist yet (pre-migration)
            return 0

    @classmethod
    def get_founding_member_spots_remaining(cls):
        """Get the number of founding member spots remaining"""
        try:
            count = cls.get_founding_member_count()
            return max(0, FOUNDING_MEMBER_LIMIT - count)
        except Exception:
            # Column may not exist yet (pre-migration)
            return FOUNDING_MEMBER_LIMIT

    @classmethod
    def founding_member_spots_available(cls):
        """Check if founding member spots are still available"""
        try:
            return cls.get_founding_member_spots_remaining() > 0
        except Exception:
            # Column may not exist yet (pre-migration)
            return True


class Transaction(models.Model):
    """
    Payment transaction model
    Tracks all payment attempts and completions
    """
    TRANSACTION_TYPE_CHOICES = [
        ('subscription', 'Subscription Payment'),
        ('one_time', 'One-time Payment'),
        ('refund', 'Refund'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default='subscription'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    # Stripe IDs
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)

    # Description
    description = models.TextField(blank=True)

    # Payment method (last 4 digits)
    payment_method_last4 = models.CharField(max_length=4, blank=True)
    payment_method_brand = models.CharField(max_length=20, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.status})"

    def is_successful(self):
        """Check if transaction was successful"""
        return self.status == 'succeeded'


class PaymentMethod(models.Model):
    """
    Stored payment methods (cards)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )

    stripe_payment_method_id = models.CharField(max_length=255, unique=True)

    # Card details
    card_brand = models.CharField(max_length=20, blank=True)  # visa, mastercard, etc.
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.card_brand} ****{self.card_last4}"

    def save(self, *args, **kwargs):
        # If this is set as default, unset all other payment methods
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    Invoice model for record keeping
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('void', 'Void'),
        ('uncollectible', 'Uncollectible'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )

    stripe_invoice_id = models.CharField(max_length=255, unique=True)
    stripe_invoice_pdf = models.URLField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Amounts
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='USD')

    # Dates
    invoice_date = models.DateTimeField()
    due_date = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Description
    description = models.TextField(blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['user', '-invoice_date']),
            models.Index(fields=['stripe_invoice_id']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.user.username}"

    def is_paid(self):
        """Check if invoice is paid"""
        return self.status == 'paid'


class SubscriptionPlan(models.Model):
    """
    Available subscription plans
    """
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=10, choices=Subscription.TIER_CHOICES)
    billing_period = models.CharField(max_length=10, choices=Subscription.BILLING_PERIOD_CHOICES)

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    # Stripe ID
    stripe_price_id = models.CharField(max_length=255, blank=True)
    stripe_product_id = models.CharField(max_length=255, blank=True)

    # Features (JSON field for flexibility)
    features = models.JSONField(default=list, blank=True)

    # Display
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscription_plans'
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        ordering = ['sort_order', 'tier', 'billing_period']
        unique_together = ['tier', 'billing_period']

    def __str__(self):
        return f"{self.name} - ${self.price}/{self.billing_period}"

    def get_monthly_equivalent(self):
        """Get monthly price equivalent for comparison"""
        if self.billing_period == 'monthly':
            return self.price
        elif self.billing_period == 'yearly':
            return self.price / 12
        return self.price
