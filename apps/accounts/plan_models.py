"""Relapse prevention plan — a private, guided safety worksheet.

One plan per member. Content is private like the journal: it must never be
rendered in feeds, activity streams, or any other member's view. The plan
itself is always free; only the PDF export is premium (plan_views.py).
"""
from django.conf import settings
from django.db import models


class RelapsePreventionPlan(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='relapse_plan',
    )

    triggers = models.TextField(
        blank=True, help_text="People, places, feelings that put you at risk")
    warning_signs = models.TextField(
        blank=True, help_text="Early signs you're drifting toward a slip")
    coping_strategies = models.TextField(
        blank=True, help_text="What actually works when a craving hits")
    reasons = models.TextField(
        blank=True, help_text="Your reasons for recovery")
    emergency_steps = models.TextField(
        blank=True, help_text="Exact steps if a slip happens or feels close")
    halt_notes = models.TextField(
        blank=True,
        help_text="HALT: how hunger, anger, loneliness, tiredness show up for you")

    # List of {"name": str, "phone": str, "relationship": str}
    support_contacts = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    SECTION_FIELDS = (
        'triggers', 'warning_signs', 'coping_strategies',
        'reasons', 'emergency_steps', 'halt_notes',
    )

    def __str__(self):
        return f"Relapse prevention plan — {self.user.username}"

    @property
    def filled_section_count(self):
        """0..7 — the six text sections plus the contacts list."""
        filled = sum(
            1 for f in self.SECTION_FIELDS if getattr(self, f).strip())
        if self.support_contacts:
            filled += 1
        return filled
