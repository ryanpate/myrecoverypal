"""Family-started support: a loved one invites the person in recovery, who consents.

Consent stays with the person in recovery: nothing is shared until they accept
and choose a sharing level. The family member pays for Supporter only after
acceptance.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


def _user(username, **kw):
    return User.objects.create_user(username=username, email=f'{username}@example.com',
                                    password='pw', **kw)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class ForFamiliesPageTest(TestCase):

    def test_landing_page_explains_consent_and_links_to_invite(self):
        resp = self.client.get(reverse('core:support_a_loved_one'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '<h1')
        self.assertContains(resp, 'consent')
        self.assertContains(resp, reverse('accounts:supporter_invite_member'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FamilyInviteTest(TestCase):

    def setUp(self):
        self.parent = _user('parent', first_name='Maria')
        self.client.login(username='parent', password='pw')
        self.url = reverse('accounts:supporter_invite_member')

    @patch('apps.accounts.supporter_views.send_email')
    def test_invite_creates_pending_supporter_initiated_link_and_emails_it(self, send):
        resp = self.client.post(self.url, {'loved_one_name': 'Alex', 'email': 'alex@example.com',
                                           'note': 'We love you.'})
        link = SupporterLink.objects.get()
        self.assertEqual((link.initiated_by, link.supporter, link.member, link.status),
                         ('supporter', self.parent, None, 'pending'))
        self.assertTrue(link.invite_token)
        accept_url = reverse('accounts:supporter_member_accept', args=[link.invite_token])
        self.assertContains(resp, accept_url)          # shareable link shown to the parent
        self.assertEqual(send.call_count, 1)
        self.assertIn(accept_url, send.call_args.kwargs['plain_message'])
        self.assertIn('We love you.', send.call_args.kwargs['plain_message'])

    @patch('apps.accounts.supporter_views.send_email')
    def test_email_is_optional(self, send):
        self.client.post(self.url, {'loved_one_name': 'Alex'})
        self.assertEqual(SupporterLink.objects.count(), 1)
        send.assert_not_called()

    @patch('apps.accounts.supporter_views.send_email')
    def test_response_never_reveals_whether_email_has_an_account(self, send):
        _user('alex')  # alex@example.com exists
        existing = self.client.post(self.url, {'loved_one_name': 'A', 'email': 'alex@example.com'})
        unknown = self.client.post(self.url, {'loved_one_name': 'B', 'email': 'nobody@example.com'})
        for resp in (existing, unknown):
            self.assertNotContains(resp, 'already has an account')
            self.assertNotContains(resp, 'alex@example.com has')
        self.assertEqual(send.call_count, 2)

    @patch('apps.accounts.supporter_views.send_email')
    def test_daily_invite_cap(self, send):
        from apps.accounts.supporter_views import MAX_FAMILY_INVITES_PER_DAY
        for i in range(MAX_FAMILY_INVITES_PER_DAY + 2):
            self.client.post(self.url, {'loved_one_name': f'P{i}', 'email': f'p{i}@example.com'})
        self.assertEqual(SupporterLink.objects.count(), MAX_FAMILY_INVITES_PER_DAY)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MemberAcceptTest(TestCase):

    def setUp(self):
        self.parent = _user('parent2', first_name='Maria')
        self.link = SupporterLink.objects.create(
            supporter=self.parent, initiated_by='supporter', status='pending',
            invite_token='tok-123', invite_email='alex@example.com')
        self.url = reverse('accounts:supporter_member_accept', args=['tok-123'])

    def test_requires_login_and_returns_after_signup(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(self.url, resp.url)

    def test_member_sees_who_is_asking_and_sharing_choices(self):
        _user('alex')
        self.client.login(username='alex', password='pw')
        resp = self.client.get(self.url)
        self.assertContains(resp, 'Maria')
        self.assertContains(resp, 'name="preset"')

    @patch('apps.accounts.supporter_views.send_email')
    def test_accept_binds_member_with_chosen_preset_and_tells_the_family(self, send):
        alex = _user('alex')
        self.client.login(username='alex', password='pw')
        self.client.post(self.url, {'decision': 'accept', 'preset': 'cheerleader'})
        self.link.refresh_from_db()
        self.assertEqual((self.link.member, self.link.status, self.link.preset),
                         (alex, 'active', 'cheerleader'))
        self.assertIsNotNone(self.link.consented_at)
        self.assertEqual(send.call_args.kwargs['recipient_email'], 'parent2@example.com')

    def test_decline_shares_nothing(self):
        _user('alex')
        self.client.login(username='alex', password='pw')
        self.client.post(self.url, {'decision': 'decline'})
        self.link.refresh_from_db()
        self.assertEqual((self.link.status, self.link.member), ('declined', None))

    def test_family_member_cannot_accept_their_own_invite(self):
        self.client.login(username='parent2', password='pw')
        self.client.post(self.url, {'decision': 'accept', 'preset': 'close'})
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'pending')

    def test_existing_connection_does_not_crash(self):
        alex = _user('alex')
        SupporterLink.objects.create(member=alex, supporter=self.parent, initiated_by='member',
                                     status='active')
        self.client.login(username='alex', password='pw')
        resp = self.client.post(self.url, {'decision': 'accept', 'preset': 'standard'})
        self.assertEqual(resp.status_code, 302)
        self.link.refresh_from_db()
        self.assertEqual(self.link.status, 'pending')

    def test_family_sees_pending_invite_on_manage_page(self):
        self.client.login(username='parent2', password='pw')
        resp = self.client.get(reverse('accounts:supporter_manage'))
        self.assertContains(resp, 'Waiting for')
