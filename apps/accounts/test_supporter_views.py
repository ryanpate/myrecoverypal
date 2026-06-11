from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from apps.accounts.decorators import supporter_required

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
