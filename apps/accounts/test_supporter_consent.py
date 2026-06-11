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
