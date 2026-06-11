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
