"""Tests for the relapse prevention plan: model, form, builder, PDF gate."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import RelapsePreventionPlan

User = get_user_model()


class PlanModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="p1", password="x")

    def test_empty_plan_counts_zero(self):
        plan = RelapsePreventionPlan.objects.create(user=self.user)
        self.assertEqual(plan.filled_section_count, 0)

    def test_partial_plan_counts_filled_sections(self):
        plan = RelapsePreventionPlan.objects.create(
            user=self.user,
            triggers="Payday fridays",
            reasons="My kids",
            halt_notes="   ",  # whitespace only — not counted
        )
        self.assertEqual(plan.filled_section_count, 2)

    def test_contacts_count_as_a_section(self):
        plan = RelapsePreventionPlan.objects.create(
            user=self.user,
            support_contacts=[{"name": "Sam", "phone": "555-0100",
                               "relationship": "sponsor"}],
        )
        self.assertEqual(plan.filled_section_count, 1)

    def test_one_plan_per_user(self):
        RelapsePreventionPlan.objects.create(user=self.user)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            RelapsePreventionPlan.objects.create(user=self.user)
