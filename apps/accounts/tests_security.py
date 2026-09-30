# apps/accounts/tests_security.py
"""Regression tests for the 2026-09-30 security audit (accounts app)."""
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import (
    ActivityFeed, GroupMembership, RecoveryGroup,
)

User = get_user_model()

_TEST_SETTINGS = {
    'PREPEND_WWW': False,
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
}


def _user(name):
    return User.objects.create_user(
        username=name, email=f'{name}@example.com', password='pw-12345-xyz')


@override_settings(**_TEST_SETTINGS)
class PrivateActivityVisibilityTests(TestCase):
    """Check-ins the user chose not to share, and logged slips, must never
    reach a follower's dashboard."""

    def setUp(self):
        self.owner = _user('owner')
        self.follower = _user('follower')
        self.follower.follow_user(self.owner)

    def _follower_dashboard(self):
        self.client.force_login(self.follower)
        resp = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_unshared_quick_checkin_hidden_from_follower(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('accounts:quick_checkin'), {
            'mood': '2', 'gratitude': 'secretgratitudetext', 'is_shared': 'false'})
        self.assertNotIn('secretgratitudetext', self._follower_dashboard())

    def test_unshared_daily_checkin_hidden_from_follower(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('accounts:daily_checkin'), {
            'mood': '2', 'craving_level': '3', 'energy_level': '2',
            'gratitude': 'secretgratitudetext'})
        self.assertTrue(ActivityFeed.objects.filter(
            user=self.owner, title__startswith='Daily Check-in').exists())
        self.assertNotIn('secretgratitudetext', self._follower_dashboard())

    def test_logged_slip_hidden_from_follower(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('accounts:log_slip'), {
            'slip_date': timezone.localdate().isoformat(),
            'substance': '', 'trigger': '', 'notes': ''})
        self.assertTrue(ActivityFeed.objects.filter(
            user=self.owner, title='Logged a slip').exists())
        self.assertNotIn('Logged a slip', self._follower_dashboard())

    def test_owner_still_sees_own_private_checkin(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('accounts:quick_checkin'), {
            'mood': '2', 'gratitude': 'secretgratitudetext', 'is_shared': 'false'})
        resp = self.client.get(reverse('accounts:dashboard'))
        self.assertContains(resp, 'secretgratitudetext')

    def test_cannot_like_or_comment_on_someone_elses_private_activity(self):
        activity = ActivityFeed.objects.create(
            user=self.owner, activity_type='check_in_posted',
            title='Logged a slip', is_public=False)
        self.client.force_login(self.follower)
        like = self.client.post(reverse('accounts:like_activity', args=[activity.id]))
        comment = self.client.post(
            reverse('accounts:comment_on_activity', args=[activity.id]), {'comment': 'hi'})
        self.assertEqual(like.status_code, 404)
        self.assertEqual(comment.status_code, 404)
        self.assertEqual(activity.likes.count(), 0)
        self.assertEqual(activity.comments.count(), 0)

    def test_can_still_like_public_activity(self):
        activity = ActivityFeed.objects.create(
            user=self.owner, activity_type='milestone_created',
            title='30 days', is_public=True)
        self.client.force_login(self.follower)
        resp = self.client.post(reverse('accounts:like_activity', args=[activity.id]))
        self.assertTrue(resp.json()['liked'])


@override_settings(**_TEST_SETTINGS)
class SecretGroupTests(TestCase):
    """'Secret – invitation only' groups are reachable only via invite link."""

    def setUp(self):
        self.creator = _user('creator')
        self.outsider = _user('outsider')
        self.group = RecoveryGroup.objects.create(
            name='Hidden Circle Zeta', description='d', group_type='interest',
            privacy_level='secret', creator=self.creator)
        GroupMembership.objects.create(
            user=self.creator, group=self.group, status='admin',
            joined_date=timezone.now().date())

    def test_outsider_cannot_join_secret_group_directly(self):
        self.client.force_login(self.outsider)
        resp = self.client.post(reverse('accounts:join_group', args=[self.group.id]))
        self.assertFalse(resp.json()['success'])
        self.assertFalse(GroupMembership.objects.filter(
            user=self.outsider, group=self.group).exists())

    def test_secret_group_not_listed_for_outsider(self):
        self.client.force_login(self.outsider)
        resp = self.client.get(reverse('accounts:groups_list'))
        self.assertNotContains(resp, 'Hidden Circle Zeta')

    def test_secret_group_listed_for_member(self):
        self.client.force_login(self.creator)
        resp = self.client.get(reverse('accounts:groups_list'))
        self.assertContains(resp, 'Hidden Circle Zeta')

    def test_secret_group_detail_404_for_outsider(self):
        self.client.force_login(self.outsider)
        resp = self.client.get(reverse('accounts:group_detail', args=[self.group.id]))
        self.assertEqual(resp.status_code, 404)

    def test_secret_group_detail_visible_to_member(self):
        self.client.force_login(self.creator)
        resp = self.client.get(reverse('accounts:group_detail', args=[self.group.id]))
        self.assertEqual(resp.status_code, 200)

    def test_public_group_still_joinable(self):
        public = RecoveryGroup.objects.create(
            name='Open', description='d', group_type='interest',
            privacy_level='public', creator=self.creator)
        self.client.force_login(self.outsider)
        resp = self.client.post(reverse('accounts:join_group', args=[public.id]))
        self.assertTrue(resp.json()['success'])


def _rc_subscriber(expires, product='com.myrecoverypal.premium.monthly',
                   original_id='$RCAnonymousID:abc'):
    return {
        'original_app_user_id': original_id,
        'entitlements': {'premium': {
            'expires_date': expires, 'product_identifier': product,
            'purchase_date': '2026-09-01T00:00:00Z'}},
    }


@override_settings(**_TEST_SETTINGS)
class IosSyncVerificationTests(TestCase):
    """The sync endpoint must take the entitlement from RevenueCat, never
    from the JSON the client sends."""

    FETCH = 'apps.accounts.payment_views._fetch_revenuecat_subscriber'

    def setUp(self):
        self.user = _user('iosuser')
        self.client.force_login(self.user)

    def _sync(self, **body):
        return self.client.post(
            reverse('accounts:ios_subscription_sync'),
            data=json.dumps(body), content_type='application/json')

    def _future(self):
        return (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

    def test_client_claim_without_app_user_id_grants_nothing(self):
        resp = self._sync(is_premium=True, product_id='court')
        self.assertEqual(resp.status_code, 400)
        self.user.subscription.refresh_from_db()
        self.assertEqual(self.user.subscription.tier, 'free')

    def test_claim_rejected_when_revenuecat_has_no_entitlement(self):
        with patch(self.FETCH, return_value={
                'original_app_user_id': 'x', 'entitlements': {}}):
            self._sync(is_premium=True, product_id='court', app_user_id='x')
        self.user.subscription.refresh_from_db()
        self.assertEqual(self.user.subscription.tier, 'free')
        self.assertFalse(self.user.subscription.is_premium())

    def test_claim_rejected_when_entitlement_expired(self):
        with patch(self.FETCH, return_value=_rc_subscriber('2020-01-01T00:00:00Z')):
            self._sync(is_premium=True, app_user_id='x')
        self.user.subscription.refresh_from_db()
        self.assertFalse(self.user.subscription.is_premium())

    def test_verified_entitlement_grants_premium_with_revenuecat_expiry(self):
        expires = self._future()
        with patch(self.FETCH, return_value=_rc_subscriber(expires)) as fetch:
            resp = self._sync(
                is_premium=True, app_user_id='$RCAnonymousID:abc',
                product_id='court', expires_date='2099-01-01T00:00:00Z')
        fetch.assert_called_once_with('$RCAnonymousID:abc')
        self.assertEqual(resp.json()['status'], 'ok')
        sub = self.user.subscription
        sub.refresh_from_db()
        # Tier and expiry come from RevenueCat, not the client's "court"/2099.
        self.assertEqual(sub.tier, 'premium')
        self.assertEqual(sub.subscription_source, 'apple')
        self.assertEqual(sub.current_period_end.strftime('%Y-%m-%dT%H:%M:%SZ'), expires)
        self.assertTrue(sub.is_premium())

    def test_verification_outage_changes_nothing(self):
        with patch(self.FETCH, return_value=None):
            resp = self._sync(is_premium=True, app_user_id='x')
        self.assertEqual(resp.status_code, 503)
        self.user.subscription.refresh_from_db()
        self.assertEqual(self.user.subscription.tier, 'free')

    def test_one_purchase_cannot_upgrade_a_second_account(self):
        with patch(self.FETCH, return_value=_rc_subscriber(self._future())):
            self._sync(is_premium=True, app_user_id='$RCAnonymousID:abc')
            other = _user('freeloader')
            self.client.force_login(other)
            resp = self._sync(is_premium=True, app_user_id='$RCAnonymousID:abc')
        self.assertEqual(resp.status_code, 409)
        other.subscription.refresh_from_db()
        self.assertEqual(other.subscription.tier, 'free')


@override_settings(**_TEST_SETTINGS)
class LinkPreviewImageTests(TestCase):
    """og:image comes from an attacker-controlled page and is placed in an
    <img src>; only plain http(s) URLs may be returned."""

    def _preview(self, og_image):
        html = (f'<html><head><title>T</title>'
                f'<meta property="og:image" content="{og_image}"></head></html>')
        resp_obj = MagicMock()
        resp_obj.headers = {'Content-Type': 'text/html'}
        resp_obj.read.return_value = html.encode()
        resp_obj.__enter__.return_value = resp_obj
        self.client.force_login(_user('viewer'))
        with patch('apps.accounts.safe_fetch.open_public_url', return_value=resp_obj):
            return self.client.get(
                reverse('accounts:link_preview_api'), {'url': 'https://evil.example/p'}).json()

    def test_attribute_breaking_image_is_dropped(self):
        data = self._preview('x&quot; onerror=&quot;alert(1)')
        self.assertEqual(data['image'], '')

    def test_non_http_image_is_dropped(self):
        self.assertEqual(self._preview('javascript:alert(1)')['image'], '')

    def test_normal_image_url_is_kept(self):
        data = self._preview('https://cdn.example.com/a.png?x=1&amp;y=2')
        self.assertEqual(data['image'], 'https://cdn.example.com/a.png?x=1&y=2')


class PrivateActivityBackfillTests(TestCase):
    """Rows written before the fix carried the model default is_public=True."""

    def test_backfill_hides_existing_private_checkins_and_slips_only(self):
        from importlib import import_module
        from django.apps import apps as django_apps
        migration = import_module(
            'apps.accounts.migrations.0070_hide_private_checkin_activities')
        owner = _user('legacy')
        mk = lambda title: ActivityFeed.objects.create(
            user=owner, activity_type='check_in_posted', title=title, is_public=True)
        private_checkin = mk('Daily Check-in: Struggling')
        slip = mk('Logged a slip')
        shared = mk('legacy checked in')
        pledge = mk("legacy took today's pledge")

        migration.hide_private_activities(django_apps, None)

        for row in (private_checkin, slip, shared, pledge):
            row.refresh_from_db()
        self.assertFalse(private_checkin.is_public)
        self.assertFalse(slip.is_public)
        self.assertTrue(shared.is_public)
        self.assertTrue(pledge.is_public)
