# apps/accounts/tests_security_followup.py
"""Regression tests for the remaining 2026-09-30 audit items."""
import http.server
import io
import os
import threading
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Milestone, SocialPost

User = get_user_model()

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


def _user(name, **extra):
    return User.objects.create_user(
        username=name, email=f'{name}@example.com', password='pw-12345-xyz', **extra)


class _RecordingHandler(http.server.BaseHTTPRequestHandler):
    hits = []

    def do_GET(self):
        type(self).hits.append(self.path)
        body = b'<html><head><title>internal admin</title></head></html>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@override_settings(**_TEST_SETTINGS)
class LinkPreviewSsrfTests(TestCase):
    """The preview fetcher must never talk to non-public addresses, however
    the URL is spelled (the old check was a hostname string blocklist)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = http.server.HTTPServer(('127.0.0.1', 0), _RecordingHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        super().tearDownClass()

    def setUp(self):
        _RecordingHandler.hits.clear()
        self.client.force_login(_user('previewer'))

    def _preview(self, url):
        return self.client.get(reverse('accounts:link_preview_api'), {'url': url})

    def test_internal_address_in_alternate_spellings_is_never_requested(self):
        for host in ('2130706433', '0x7f000001', '127.1', '[::ffff:127.0.0.1]'):
            resp = self._preview(f'http://{host}:{self.port}/secret')
            self.assertNotEqual(resp.status_code, 200, host)
            self.assertNotIn('internal admin', resp.content.decode(), host)
        self.assertEqual(_RecordingHandler.hits, [])

    def test_hostname_resolving_to_internal_address_is_never_requested(self):
        import socket
        real = socket.getaddrinfo

        def fake(host, *args, **kwargs):
            if host == 'innocent.example':
                host = '127.0.0.1'
            return real(host, *args, **kwargs)

        with patch('socket.getaddrinfo', side_effect=fake):
            resp = self._preview(f'http://innocent.example:{self.port}/secret')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(_RecordingHandler.hits, [])


@override_settings(**_TEST_SETTINGS)
class PaymentSuccessOwnershipTests(TestCase):
    """A Checkout Session id must only upgrade the account that paid."""

    def _stripe_objects(self, customer):
        session = MagicMock(customer=customer, subscription='sub_123')
        stripe_sub = MagicMock(id='sub_123', status='active')
        stripe_sub.__getitem__.side_effect = lambda k: {
            'items': {'data': [{'price': {'id': 'price_x'}}]}}[k]
        return session, stripe_sub

    def _visit(self, user, customer):
        session, stripe_sub = self._stripe_objects(customer)
        self.client.force_login(user)
        with patch('apps.accounts.payment_views.stripe.checkout.Session.retrieve', return_value=session), \
                patch('apps.accounts.payment_views.stripe.Subscription.retrieve', return_value=stripe_sub), \
                patch('apps.accounts.payment_views._subscription_period', return_value=(None, None)):
            return self.client.get(reverse('accounts:payment_success'), {'session_id': 'cs_test_1'})

    def test_someone_elses_checkout_session_does_not_upgrade_me(self):
        freeloader = _user('freeloader2')
        sub = freeloader.subscription
        sub.stripe_customer_id = 'cus_freeloader'
        sub.save()
        self._visit(freeloader, customer='cus_payer')
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'free')
        self.assertIsNone(sub.stripe_subscription_id)

    def test_my_own_checkout_session_upgrades_me(self):
        payer = _user('payer')
        sub = payer.subscription
        sub.stripe_customer_id = 'cus_payer'
        sub.save()
        self._visit(payer, customer='cus_payer')
        sub.refresh_from_db()
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.stripe_subscription_id, 'sub_123')


@override_settings(**_TEST_SETTINGS)
class ProfilePrivacyTests(TestCase):
    def setUp(self):
        self.viewer = _user('viewer1')
        self.sober_date = date.today() - timedelta(days=4321)

    def test_days_sober_hidden_in_community_when_sobriety_date_is_private(self):
        _user('hiddendays', sobriety_date=self.sober_date, show_sobriety_date=False)
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse('accounts:community'))
        self.assertContains(resp, 'hiddendays')
        self.assertNotContains(resp, '4321')

    def test_days_sober_shown_in_community_when_sobriety_date_is_public(self):
        _user('showndays', sobriety_date=self.sober_date, show_sobriety_date=True)
        self.client.force_login(self.viewer)
        self.assertContains(self.client.get(reverse('accounts:community')), '4321')

    def test_days_sober_hidden_in_followers_list_when_private(self):
        hidden = _user('hiddendays2', sobriety_date=self.sober_date, show_sobriety_date=False)
        hidden.follow_user(self.viewer)
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse('accounts:followers_list', args=['viewer1']))
        self.assertContains(resp, 'hiddendays2')
        self.assertNotContains(resp, '4321')

    def test_private_profile_requires_login(self):
        """Profiles are private by default (is_profile_public=False): a
        logged-out visitor must not see who is a member of a recovery site."""
        _user('privateperson2', first_name='Zelda', is_profile_public=False)
        resp = self.client.get(reverse('accounts:profile', args=['privateperson2']))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

    def test_public_profile_still_visible_to_anonymous_visitors(self):
        _user('publicperson', is_profile_public=True)
        resp = self.client.get(reverse('accounts:profile', args=['publicperson']))
        self.assertEqual(resp.status_code, 200)

    def test_private_profile_still_viewable_by_logged_in_members(self):
        _user('privateperson4', is_profile_public=False)
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse('accounts:profile', args=['privateperson4']))
        self.assertEqual(resp.status_code, 200)

    def test_milestones_hidden_on_profile_when_sobriety_date_is_private(self):
        owner = _user('milestoneowner', sobriety_date=self.sober_date, show_sobriety_date=False,
                      is_profile_public=True)
        Milestone.objects.create(user=owner, title='Zebra Milestone Title', days_sober=90)
        self.client.force_login(self.viewer)
        resp = self.client.get(reverse('accounts:profile', args=['milestoneowner']))
        self.assertNotContains(resp, 'Zebra Milestone Title')
        self.client.force_login(owner)
        resp = self.client.get(reverse('accounts:profile', args=['milestoneowner']))
        self.assertContains(resp, 'Zebra Milestone Title')


@override_settings(**_TEST_SETTINGS)
class PasswordResetAndAllauthTests(TestCase):
    def setUp(self):
        caches['rate_limiting'].clear()

    def test_password_reset_requests_are_rate_limited(self):
        url = reverse('accounts:password_reset')
        with patch('apps.accounts.email_service.send_email', return_value=(True, None)):
            codes = [self.client.post(url, {'email': 'nobody@example.com'}).status_code
                     for _ in range(6)]
        self.assertEqual(codes[:5], [302] * 5)
        self.assertEqual(codes[5], 403)

    def test_unused_allauth_views_are_not_exposed(self):
        for path in ('/accounts/password/reset/', '/accounts/email/', '/accounts/password/change/'):
            self.assertEqual(self.client.get(path).status_code, 404, path)


@override_settings(**_TEST_SETTINGS)
class AdminMaintenanceEndpointTests(TestCase):
    """Maintenance views used to accept ?key=<ADMIN_SECRET_KEY> over GET,
    which leaks the key into access logs. Staff login only."""

    def test_secret_key_in_query_string_no_longer_authorizes(self):
        with patch.dict(os.environ, {'ADMIN_SECRET_KEY': 'topsecret'}):
            for url in (reverse('accounts:fix_avatar_urls'),
                        reverse('accounts:setup_review_account'),
                        reverse('blog:create_seo_posts'),
                        reverse('blog:backfill_blog_push', args=['some-slug'])):
                with patch('django.core.management.call_command') as call:
                    resp = self.client.get(url, {'key': 'topsecret'})
                self.assertIn(resp.status_code, (302, 403), url)
                call.assert_not_called()

    def test_staff_can_still_use_them(self):
        staff = _user('staffer', is_staff=True, is_superuser=True)
        self.client.force_login(staff)
        resp = self.client.get(reverse('accounts:fix_avatar_urls'))
        self.assertEqual(resp.status_code, 200)


class FacilityUsernameTests(TestCase):
    def test_username_from_email_contains_only_safe_characters(self):
        from apps.accounts.facility_signup_views import _unique_username
        username = _unique_username('"\');alert(1);//a/b<x>"@evil.com')
        self.assertRegex(username, r'^[A-Za-z0-9_.-]+$')

    def test_ordinary_email_keeps_its_local_part(self):
        from apps.accounts.facility_signup_views import _unique_username
        self.assertEqual(_unique_username('jane.doe@clinic.org'), 'jane.doe')


@override_settings(**_TEST_SETTINGS)
class UploadValidationTests(TestCase):
    def _fake_image(self):
        return SimpleUploadedFile('x.png', b'<html>not an image</html>', content_type='image/png')

    def test_validate_image_rejects_non_image_bytes_with_image_mime_type(self):
        from apps.accounts.image_utils import validate_image
        ok, _ = validate_image(self._fake_image())
        self.assertFalse(ok)

    def test_validate_image_accepts_a_real_image(self):
        from PIL import Image
        from apps.accounts.image_utils import validate_image
        buf = io.BytesIO()
        Image.new('RGB', (4, 4), 'red').save(buf, format='PNG')
        ok, err = validate_image(SimpleUploadedFile('ok.png', buf.getvalue(), content_type='image/png'))
        self.assertTrue(ok, err)

    def test_onboarding_pledge_photo_must_be_an_image(self):
        user = _user('onboarder')
        self.client.force_login(user)
        self.client.post(reverse('accounts:onboarding') + '?step=3',
                         {'step': '3', 'pledge_reason': 'family', 'pledge_photo': self._fake_image()})
        user.refresh_from_db()
        self.assertFalse(user.pledge_photo)


@override_settings(**_TEST_SETTINGS)
class FeedAndNotificationApiTests(TestCase):
    def test_anonymous_feed_api_returns_no_more_than_the_public_teaser(self):
        author = _user('poster')
        for i in range(8):
            SocialPost.objects.create(author=author, content=f'post {i}', visibility='public')
        data = self.client.get(reverse('accounts:social_feed_posts_api')).json()
        self.assertLessEqual(len(data['posts']), 3)
        page2 = self.client.get(reverse('accounts:social_feed_posts_api'), {'page': 2}).json()
        self.assertLessEqual(len(page2['posts']), 3)
        self.assertFalse(data.get('has_next', False))

    def test_unread_only_notifications_filter_does_not_error(self):
        self.client.force_login(_user('notified'))
        resp = self.client.get(reverse('accounts:notifications_api'), {'unread_only': 'true'})
        self.assertEqual(resp.status_code, 200)
