"""
Family / Supporter dashboard models.

A SupporterLink connects a person in recovery (member) with a supporter
(family member / sponsor) who follows a curated, consent-controlled view of
the member's progress. The member always controls the preset and may pause or
revoke at any time. See docs/superpowers/specs/2026-06-11-family-supporter-dashboard-design.md
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

PRESET_CHOICES = [
    ('cheerleader', 'Cheerleader'),
    ('standard', 'Standard'),
    ('close', 'Close support'),
]

STATUS_CHOICES = [
    ('pending', 'Pending consent'),
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('revoked', 'Revoked'),
    ('declined', 'Declined'),
]

INITIATED_BY_CHOICES = [
    ('member', 'Member'),
    ('supporter', 'Supporter'),
]


class SupporterLink(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supporter_links',
        help_text='Person in recovery whose progress is shared.',
    )
    supporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supporting_links',
        help_text='Viewer; needs an active supporter subscription to see data.',
    )
    preset = models.CharField(max_length=12, choices=PRESET_CHOICES, default='standard')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    initiated_by = models.CharField(max_length=10, choices=INITIATED_BY_CHOICES)

    invite_email = models.EmailField(blank=True)
    invite_token = models.CharField(max_length=64, blank=True, db_index=True)

    inactivity_threshold_days = models.PositiveSmallIntegerField(default=3)
    last_inactivity_alert_sent = models.DateTimeField(null=True, blank=True)

    consented_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supporter_links'
        verbose_name = 'Supporter Link'
        verbose_name_plural = 'Supporter Links'
        constraints = [
            models.UniqueConstraint(fields=['member', 'supporter'], name='unique_member_supporter'),
        ]
        indexes = [
            models.Index(fields=['member', 'status']),
            models.Index(fields=['supporter', 'status']),
        ]

    def __str__(self):
        return f"{self.supporter} → {self.member} ({self.preset}/{self.status})"

    def clean(self):
        if self.member_id and self.member_id == self.supporter_id:
            raise ValidationError("A user cannot be their own supporter.")

    def is_live(self):
        """True when this link is actively sharing data."""
        return self.status == 'active'

    @staticmethod
    def _validate_preset(preset):
        valid = {c[0] for c in PRESET_CHOICES}
        if preset not in valid:
            raise ValidationError(f"Unknown preset: {preset!r}")

    def consent(self, preset=None):
        """Member grants consent (and optionally sets/changes the preset).

        Refuses to re-activate a terminal link: a revoked/declined link must
        be re-established as a new SupporterLink, never silently re-consented.
        """
        if self.status in ('revoked', 'declined'):
            raise ValidationError(
                "A revoked or declined link cannot be re-consented; create a new SupporterLink."
            )
        if preset is not None:
            self._validate_preset(preset)
            self.preset = preset
        self.status = 'active'
        if not self.consented_at:
            self.consented_at = timezone.now()
        self.save(update_fields=['preset', 'status', 'consented_at', 'updated_at'])

    def decline(self):
        self.status = 'declined'
        self.save(update_fields=['status', 'updated_at'])

    def pause(self):
        self.status = 'paused'
        self.save(update_fields=['status', 'updated_at'])

    def resume(self):
        """Resume a paused link. Only a paused link may resume — never un-revoke."""
        if self.status != 'paused':
            raise ValidationError("Only paused links can be resumed.")
        self.status = 'active'
        self.save(update_fields=['status', 'updated_at'])

    def revoke(self):
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        self.save(update_fields=['status', 'revoked_at', 'updated_at'])

    def set_preset(self, preset):
        """Member changes the sharing level on an existing link."""
        self._validate_preset(preset)
        self.preset = preset
        self.save(update_fields=['preset', 'updated_at'])
