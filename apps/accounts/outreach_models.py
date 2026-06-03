# apps/accounts/outreach_models.py
"""Cold-outreach (B2B email) suppression list.

Recipients of facility cold-outreach are NOT registered users, so we can't use
the User.marketing_emails_enabled flag. This model is a standalone suppression
list keyed by email address. Check it before sending any cold-outreach batch.
"""
from django.db import models


class ColdOutreachSuppression(models.Model):
    """An email address that has opted out of cold-outreach (facility) emails."""

    SOURCE_CHOICES = [
        ('sober_living', 'Sober Living'),
        ('rehab', 'Rehab / Treatment Center'),
        ('court_liaison', 'Court / Probation Liaison'),
        ('other', 'Other'),
    ]

    email = models.EmailField(unique=True, db_index=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, blank=True,
        help_text='Which outreach list this address came from, if known.',
    )
    unsubscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-unsubscribed_at']
        verbose_name = 'Cold-outreach opt-out'
        verbose_name_plural = 'Cold-outreach opt-outs'

    def __str__(self):
        return self.email
