"""Tests for the Craving SOS coach trigger: exemption + session view."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.coach_service import can_send_message, get_message_count_today
from apps.accounts.models import CoachMessage, RecoveryCoachSession

User = get_user_model()


class SosExemptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sos", password="x")
        # Ensure user is free (not premium)
        if hasattr(self.user, 'subscription'):
            self.user.subscription.tier = 'free'
            self.user.subscription.save()

    def _spam_routine_messages(self, n):
        session = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual')
        for _ in range(n):
            CoachMessage.objects.create(
                session=session, role='user', content='hi')

    def test_sos_session_never_limited_for_free_user(self):
        self._spam_routine_messages(3)  # free daily limit exhausted
        sos = RecoveryCoachSession.objects.create(
            user=self.user, trigger='sos')
        allowed, reason = can_send_message(self.user, session=sos)
        self.assertTrue(allowed)
        self.assertIsNone(reason)

    def test_sos_messages_do_not_count_toward_daily_total(self):
        sos = RecoveryCoachSession.objects.create(
            user=self.user, trigger='sos')
        for _ in range(5):
            CoachMessage.objects.create(
                session=sos, role='user', content='wave')
        self.assertEqual(get_message_count_today(self.user), 0)

    def test_routine_session_still_limited(self):
        self._spam_routine_messages(3)
        manual = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual')
        allowed, reason = can_send_message(self.user, session=manual)
        self.assertFalse(allowed)
        self.assertEqual(reason, "upgrade_required")


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CoachStartSosViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sos2", password="x")
        self.client.force_login(self.user)

    def test_creates_sos_session_with_static_opener(self):
        resp = self.client.get(reverse("accounts:coach_start_sos"))
        self.assertRedirects(
            resp, reverse("accounts:recovery_coach"),
            fetch_redirect_response=False)
        session = RecoveryCoachSession.objects.get(
            user=self.user, trigger='sos')
        self.assertTrue(session.is_active)
        opener = session.messages.get()
        self.assertEqual(opener.role, 'assistant')
        self.assertIn("Cravings", opener.content)

    def test_reuses_todays_sos_session(self):
        self.client.get(reverse("accounts:coach_start_sos"))
        self.client.get(reverse("accounts:coach_start_sos"))
        self.assertEqual(
            RecoveryCoachSession.objects.filter(
                user=self.user, trigger='sos').count(), 1)

    def test_deactivates_other_active_sessions(self):
        other = RecoveryCoachSession.objects.create(
            user=self.user, trigger='manual', is_active=True)
        self.client.get(reverse("accounts:coach_start_sos"))
        other.refresh_from_db()
        self.assertFalse(other.is_active)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("accounts:coach_start_sos"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp["Location"])
