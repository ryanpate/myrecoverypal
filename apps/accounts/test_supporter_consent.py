from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterLinkModelTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='member', email='m@x.com', password='pw')
        self.supporter = User.objects.create_user(username='sup', email='s@x.com', password='pw')

    def test_defaults(self):
        link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='member', preset='standard'
        )
        self.assertEqual(link.status, 'pending')
        self.assertEqual(link.inactivity_threshold_days, 3)

    def test_cannot_support_self(self):
        link = SupporterLink(member=self.member, supporter=self.member, initiated_by='member')
        with self.assertRaises(ValidationError):
            link.full_clean()

    def test_unique_member_supporter(self):
        SupporterLink.objects.create(member=self.member, supporter=self.supporter, initiated_by='member')
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SupporterLink.objects.create(member=self.member, supporter=self.supporter, initiated_by='supporter')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterLinkTransitionTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='m2', email='m2@x.com', password='pw')
        self.supporter = User.objects.create_user(username='s2', email='s2@x.com', password='pw')
        self.link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='supporter', status='pending'
        )

    def test_member_consent_activates_and_sets_preset(self):
        self.link.consent(preset='close')
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'active')
        self.assertEqual(self.link.preset, 'close')
        self.assertIsNotNone(self.link.consented_at)

    def test_decline_is_terminal(self):
        self.link.decline()
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'declined')

    def test_pause_and_resume(self):
        self.link.consent(preset='standard')
        self.link.pause()
        self.assertEqual(self.link.status, 'paused')
        self.assertFalse(self.link.is_live())
        self.link.resume()
        self.assertEqual(self.link.status, 'active')
        self.assertTrue(self.link.is_live())

    def test_revoke_is_terminal_and_timestamped(self):
        self.link.consent(preset='standard')
        self.link.revoke()
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'revoked')
        self.assertIsNotNone(self.link.revoked_at)
        self.assertFalse(self.link.is_live())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterLinkGuardTests(TestCase):
    """Terminal-state and input guards (hardening from security review)."""

    def setUp(self):
        self.member = User.objects.create_user(username='m3', email='m3@x.com', password='pw')
        self.supporter = User.objects.create_user(username='s3', email='s3@x.com', password='pw')
        self.link = SupporterLink.objects.create(
            member=self.member, supporter=self.supporter, initiated_by='supporter', status='pending'
        )

    def test_consent_refuses_revoked_link(self):
        self.link.consent(preset='standard')
        self.link.revoke()
        with self.assertRaises(ValidationError):
            self.link.consent(preset='standard')

    def test_consent_refuses_declined_link(self):
        self.link.decline()
        with self.assertRaises(ValidationError):
            self.link.consent(preset='standard')

    def test_resume_only_from_paused(self):
        self.link.consent(preset='standard')
        self.link.revoke()
        with self.assertRaises(ValidationError):
            self.link.resume()
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'revoked')  # still revoked, not un-revoked

    def test_consent_rejects_unknown_preset(self):
        with self.assertRaises(ValidationError):
            self.link.consent(preset='everything')

    def test_set_preset_rejects_unknown_preset(self):
        self.link.consent(preset='standard')
        with self.assertRaises(ValidationError):
            self.link.set_preset('everything')
