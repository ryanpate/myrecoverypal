"""
Treatment-center aftercare models. A Facility (org) monitors its alumni's
post-discharge engagement. Alumni opt in via FacilityInvite; FacilityMembership
is the consent record. See docs/superpowers/specs/2026-06-17-treatment-center-aftercare-design.md
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class Facility(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('active', 'Active'), ('paused', 'Paused')]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    monthly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text='Record-keeping only; billing is handled offline.')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Self-serve signup: random token for the email-verification link, cleared
    # once used. Default status stays 'active' so create_facility/admin are
    # unaffected; only self-serve signups set status='pending'.
    activation_token = models.CharField(
        max_length=64, blank=True, default='', db_index=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'facilities'
        verbose_name_plural = 'facilities'

    def __str__(self):
        return self.name


class FacilityStaff(models.Model):
    ROLE_CHOICES = [('admin', 'Admin'), ('coordinator', 'Coordinator')]

    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='staff')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='facility_staff_roles')
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='coordinator')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_staff'
        unique_together = ('facility', 'user')

    def __str__(self):
        return f'{self.user} @ {self.facility} ({self.role})'


class FacilityMembership(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'), ('active', 'Active'),
        ('revoked', 'Revoked'), ('left', 'Left'),
    ]

    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='facility_memberships')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='invited')
    consent_granted_at = models.DateTimeField(null=True, blank=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    # Drives the "newly at-risk" weekly digest: stamped when included as at-risk,
    # cleared when the member returns to ok.
    risk_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_memberships'
        unique_together = ('facility', 'user')

    def __str__(self):
        return f'{self.user} @ {self.facility} ({self.status})'

    @property
    def is_visible_to_staff(self):
        return self.status == 'active' and self.consent_granted_at is not None


class FacilityInvite(models.Model):
    facility = models.ForeignKey(
        Facility, on_delete=models.CASCADE, related_name='invites')
    code = models.CharField(max_length=40, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_facility_invites')
    uses = models.IntegerField(default=0)
    max_uses = models.IntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'facility_invites'

    def __str__(self):
        return f'{self.code} ({self.facility})'

    @staticmethod
    def generate_code():
        return secrets.token_urlsafe(12)

    def is_valid(self):
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        return True
