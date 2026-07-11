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


import json

from django.test import override_settings
from django.urls import reverse

from apps.accounts.plan_forms import RelapsePreventionPlanForm


class PlanFormContactsTests(TestCase):
    def _form(self, contacts_json):
        return RelapsePreventionPlanForm(data={
            "triggers": "", "warning_signs": "", "coping_strategies": "",
            "reasons": "", "emergency_steps": "", "halt_notes": "",
            "support_contacts": contacts_json,
        })

    def test_valid_rows_kept_and_trimmed(self):
        form = self._form(json.dumps([
            {"name": "  Sam ", "phone": " 555-0100", "relationship": "sponsor"},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["support_contacts"], [
            {"name": "Sam", "phone": "555-0100", "relationship": "sponsor"},
        ])

    def test_empty_rows_dropped_and_unknown_keys_stripped(self):
        form = self._form(json.dumps([
            {"name": "", "phone": "", "relationship": ""},
            {"name": "Ana", "phone": "", "relationship": "", "evil": "x"},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["support_contacts"], [
            {"name": "Ana", "phone": "", "relationship": ""},
        ])

    def test_more_than_ten_rows_rejected(self):
        rows = [{"name": f"P{i}", "phone": "", "relationship": ""}
                for i in range(11)]
        form = self._form(json.dumps(rows))
        self.assertFalse(form.is_valid())
        self.assertIn("support_contacts", form.errors)

    def test_non_list_rejected(self):
        form = self._form(json.dumps({"name": "not-a-list"}))
        self.assertFalse(form.is_valid())

    def test_values_capped_at_100_chars(self):
        form = self._form(json.dumps([
            {"name": "x" * 300, "phone": "", "relationship": ""},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            len(form.cleaned_data["support_contacts"][0]["name"]), 100)

    def test_null_values_become_empty_strings(self):
        form = self._form(json.dumps([
            {"name": "Ana", "phone": None, "relationship": None},
        ]))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["support_contacts"], [
            {"name": "Ana", "phone": "", "relationship": ""},
        ])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PlanBuilderViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="builder", password="x")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("accounts:relapse_plan"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])

    def test_get_creates_empty_plan_and_renders_sections(self):
        resp = self.client.get(reverse("accounts:relapse_plan"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            RelapsePreventionPlan.objects.filter(user=self.user).exists())
        for label in ("triggers", "warning_signs", "coping_strategies",
                      "reasons", "emergency_steps", "halt_notes"):
            self.assertContains(resp, f'name="{label}"')

    def test_post_saves_and_reload_shows_content(self):
        resp = self.client.post(reverse("accounts:relapse_plan"), {
            "triggers": "Payday fridays",
            "warning_signs": "Skipping meetings",
            "coping_strategies": "Call Sam; go for a run",
            "reasons": "My kids",
            "emergency_steps": "Call 988 or my sponsor",
            "halt_notes": "Tiredness hits hardest",
            "support_contacts": json.dumps([
                {"name": "Sam", "phone": "555-0100",
                 "relationship": "sponsor"},
            ]),
        })
        self.assertRedirects(resp, reverse("accounts:relapse_plan"),
                             fetch_redirect_response=False)
        plan = RelapsePreventionPlan.objects.get(user=self.user)
        self.assertEqual(plan.filled_section_count, 7)
        follow = self.client.get(reverse("accounts:relapse_plan"))
        self.assertContains(follow, "Payday fridays")
        self.assertContains(follow, "7 of 7")

    def test_eleven_contacts_shows_visible_error(self):
        rows = [{"name": f"P{i}", "phone": "", "relationship": ""}
                for i in range(11)]
        resp = self.client.post(reverse("accounts:relapse_plan"), {
            "triggers": "x", "warning_signs": "", "coping_strategies": "",
            "reasons": "", "emergency_steps": "", "halt_notes": "",
            "support_contacts": json.dumps(rows),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "10 contacts or fewer")
        from apps.accounts.models import RelapsePreventionPlan
        plan = RelapsePreventionPlan.objects.get(user=self.user)
        self.assertEqual(plan.support_contacts, [])


from unittest import skipUnless
from unittest.mock import patch

try:
    import weasyprint  # noqa: F401
    HAS_WEASYPRINT = True
except Exception:
    HAS_WEASYPRINT = False


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PlanPdfGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pdfu", password="x")
        self.client.force_login(self.user)

    def test_free_user_redirected_to_pricing(self):
        self.user.subscription.tier = 'free'
        self.user.subscription.save()
        resp = self.client.get(reverse("accounts:relapse_plan_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:pricing"), resp["Location"])

    def test_premium_user_gets_pdf_response(self):
        # New users default to a premium trial (signal), which is_premium().
        with patch("apps.accounts.plan_views.render_plan_pdf",
                   return_value=b"%PDF-fake") as mock_render:
            resp = self.client.get(reverse("accounts:relapse_plan_pdf"))
        mock_render.assert_called_once_with(self.user)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("relapse-prevention-plan.pdf",
                      resp["Content-Disposition"])

    @skipUnless(HAS_WEASYPRINT, "WeasyPrint not available in this env")
    def test_real_render_produces_pdf_bytes(self):
        from apps.accounts.plan_service import render_plan_pdf
        RelapsePreventionPlan.objects.create(
            user=self.user, triggers="Payday fridays",
            support_contacts=[{"name": "Sam", "phone": "555-0100",
                               "relationship": "sponsor"}])
        pdf = render_plan_pdf(self.user)
        self.assertTrue(pdf.startswith(b"%PDF"))
