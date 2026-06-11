from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from apps.accounts.decorators import supporter_required
from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


def _view(request):
    from django.http import HttpResponse
    return HttpResponse('ok')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterRequiredTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _prep(self, request):
        SessionMiddleware(lambda r: None).process_request(request)
        request.session.save()
        MessageMiddleware(lambda r: None).process_request(request)

    def test_redirects_without_supporter_sub(self):
        u = User.objects.create_user(username='plain', email='p@x.com', password='pw')
        # auto-created free subscription stays as-is (not a supporter)
        req = self.factory.get('/supporter/dashboard/')
        req.user = u
        self._prep(req)
        resp = supporter_required(_view)(req)
        self.assertEqual(resp.status_code, 302)

    def test_allows_active_supporter(self):
        u = User.objects.create_user(username='sup', email='s@x.com', password='pw')
        sub = u.subscription           # auto-created by signal
        sub.tier = 'supporter'
        sub.status = 'active'
        sub.save()
        req = self.factory.get('/supporter/dashboard/')
        req.user = u
        self._prep(req)
        resp = supporter_required(_view)(req)
        self.assertEqual(resp.status_code, 200)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MemberSharingTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mem', email='mem@x.com', password='pw')
        self.client.login(username='mem', password='pw')

    def test_member_can_invite_supporter_by_email(self):
        resp = self.client.post(reverse('accounts:supporter_invite'), {
            'invite_email': 'mom@example.com', 'preset': 'standard',
        })
        self.assertEqual(resp.status_code, 302)
        link = SupporterLink.objects.get(member=self.member)
        self.assertEqual(link.invite_email, 'mom@example.com')
        self.assertEqual(link.preset, 'standard')
        self.assertEqual(link.status, 'pending')
        self.assertEqual(link.initiated_by, 'member')
        self.assertTrue(link.invite_token)

    def test_duplicate_pending_invite_is_not_created(self):
        data = {'invite_email': 'dup@example.com', 'preset': 'standard'}
        self.client.post(reverse('accounts:supporter_invite'), data)
        self.client.post(reverse('accounts:supporter_invite'), data)
        count = SupporterLink.objects.filter(
            member=self.member, invite_email='dup@example.com', status='pending'
        ).count()
        self.assertEqual(count, 1)

    def test_member_can_change_preset(self):
        link = SupporterLink.objects.create(member=self.member,
            supporter=User.objects.create_user(username='x', email='x@x.com', password='pw'),
            initiated_by='member', status='active', preset='cheerleader')
        resp = self.client.post(reverse('accounts:supporter_set_preset', args=[link.id]),
                                {'preset': 'close'})
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.preset, 'close')

    def test_member_can_revoke(self):
        sup = User.objects.create_user(username='y', email='y@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='member', status='active', preset='standard')
        resp = self.client.post(reverse('accounts:supporter_revoke', args=[link.id]))
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.status, 'revoked')

    def test_cannot_touch_another_members_link(self):
        other = User.objects.create_user(username='other', email='o@x.com', password='pw')
        sup = User.objects.create_user(username='z', email='z@x.com', password='pw')
        link = SupporterLink.objects.create(member=other, supporter=sup,
            initiated_by='member', status='active', preset='standard')
        resp = self.client.post(reverse('accounts:supporter_revoke', args=[link.id]))
        self.assertEqual(resp.status_code, 404)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='dm', email='dm@x.com', password='pw')
        self.sup = User.objects.create_user(username='dsup', email='dsup@x.com', password='pw')
        s = self.sup.subscription
        s.tier = 'supporter'; s.status = 'active'; s.save()
        self.link = SupporterLink.objects.create(member=self.member, supporter=self.sup,
            initiated_by='member', status='active', preset='standard')

    def test_supporter_sees_dashboard(self):
        self.client.login(username='dsup', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('dashboard', resp.context)

    def test_non_owner_supporter_gets_404(self):
        intruder = User.objects.create_user(username='int', email='int@x.com', password='pw')
        s = intruder.subscription
        s.tier = 'supporter'; s.status = 'active'; s.save()
        self.client.login(username='int', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 404)

    def test_unsubscribed_supporter_redirected(self):
        s = self.sup.subscription
        s.status = 'canceled'; s.save()
        self.client.login(username='dsup', password='pw')
        resp = self.client.get(reverse('accounts:supporter_dashboard', args=[self.link.id]))
        self.assertEqual(resp.status_code, 302)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class InviteAcceptTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='mb', email='mb@x.com', password='pw')

    def test_supporter_accepts_email_invite_binds_account(self):
        link = SupporterLink.objects.create(member=self.member, initiated_by='member',
            preset='standard', invite_email='mom@x.com', invite_token='tok123', status='pending')
        mom = User.objects.create_user(username='mom', email='mom@x.com', password='pw')
        self.client.login(username='mom', password='pw')
        resp = self.client.post(reverse('accounts:supporter_accept', args=['tok123']))
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.supporter, mom)
        self.assertEqual(link.status, 'active')

    def test_member_consents_to_supporter_initiated_link(self):
        sup = User.objects.create_user(username='dad', email='dad@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='supporter', status='pending')
        self.client.login(username='mb', password='pw')
        resp = self.client.post(reverse('accounts:supporter_consent', args=[link.id]),
                                {'preset': 'close', 'decision': 'accept'})
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.status, 'active')
        self.assertEqual(link.preset, 'close')

    def test_member_declines_silently(self):
        sup = User.objects.create_user(username='dad2', email='dad2@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='supporter', status='pending')
        self.client.login(username='mb', password='pw')
        resp = self.client.post(reverse('accounts:supporter_consent', args=[link.id]),
                                {'decision': 'decline'})
        self.assertEqual(resp.status_code, 302)
        link.refresh_from_db()
        self.assertEqual(link.status, 'declined')

    def test_accept_get_renders_confirm_page(self):
        SupporterLink.objects.create(member=self.member, initiated_by='member',
            preset='standard', invite_email='aunt@x.com', invite_token='tokGET', status='pending')
        aunt = User.objects.create_user(username='aunt', email='aunt@x.com', password='pw')
        self.client.login(username='aunt', password='pw')
        resp = self.client.get(reverse('accounts:supporter_accept', args=['tokGET']))
        self.assertEqual(resp.status_code, 200)  # email link is a GET, must not 405

    def test_accept_when_already_supporting_does_not_500(self):
        sup = User.objects.create_user(username='sis', email='sis@x.com', password='pw')
        # existing active link to the same member
        SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='member', status='active', preset='standard')
        # a second pending invite the same user tries to accept
        SupporterLink.objects.create(member=self.member, initiated_by='member',
            preset='standard', invite_email='sis@x.com', invite_token='tokDUP', status='pending')
        self.client.login(username='sis', password='pw')
        resp = self.client.post(reverse('accounts:supporter_accept', args=['tokDUP']))
        self.assertEqual(resp.status_code, 302)  # handled gracefully, no IntegrityError 500
        self.assertEqual(SupporterLink.objects.filter(
            member=self.member, supporter=sup, status='active').count(), 1)

    def test_accept_after_revoke_does_not_500(self):
        # Re-invite after a revoke: the (member, supporter) pair already has a
        # revoked row; accepting a fresh invite must not hit the unique constraint.
        sup = User.objects.create_user(username='rex', email='rex@x.com', password='pw')
        SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='member', status='revoked', preset='standard')
        SupporterLink.objects.create(member=self.member, initiated_by='member',
            preset='standard', invite_email='rex@x.com', invite_token='tokREV', status='pending')
        self.client.login(username='rex', password='pw')
        resp = self.client.post(reverse('accounts:supporter_accept', args=['tokREV']))
        self.assertEqual(resp.status_code, 302)  # no IntegrityError 500


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RequestSupportViewTests(TestCase):
    def setUp(self):
        self.member = User.objects.create_user(username='rsm', email='rsm@x.com', password='pw')
        self.client.login(username='rsm', password='pw')

    def test_request_support_redirects(self):
        resp = self.client.post(reverse('accounts:supporter_request_support'))
        self.assertEqual(resp.status_code, 302)

    def test_request_support_ignores_external_next(self):
        resp = self.client.post(reverse('accounts:supporter_request_support'),
                                {'next': 'https://evil.example.com/'})
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.example.com', resp['Location'])


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class SupporterPageRenderTests(TestCase):
    """GET-render the redesigned supporter templates to catch template errors."""

    def setUp(self):
        self.member = User.objects.create_user(username='pm', email='pm@x.com', password='pw')
        self.client.login(username='pm', password='pw')

    def test_manage_empty_renders(self):
        resp = self.client.get(reverse('accounts:supporter_manage'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'My Support Circle')

    def test_manage_with_supporter_renders(self):
        sup = User.objects.create_user(username='pmsup', email='pmsup@x.com', password='pw')
        SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='member', status='active', preset='close')
        resp = self.client.get(reverse('accounts:supporter_manage'))
        self.assertEqual(resp.status_code, 200)

    def test_invite_page_renders(self):
        resp = self.client.get(reverse('accounts:supporter_invite'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Send invite')

    def test_consent_page_renders(self):
        sup = User.objects.create_user(username='pmsup2', email='pmsup2@x.com', password='pw')
        link = SupporterLink.objects.create(member=self.member, supporter=sup,
            initiated_by='supporter', status='pending')
        resp = self.client.get(reverse('accounts:supporter_consent', args=[link.id]))
        self.assertEqual(resp.status_code, 200)

    def test_renew_page_renders(self):
        resp = self.client.get(reverse('accounts:supporter_renew'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Become a Supporter')
