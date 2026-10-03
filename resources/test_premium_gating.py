"""Regression tests for resource access levels.

The old check was `not hasattr(request.user, 'has_premium')`, which is
always true, and it redirected to a `store:premium` URL that doesn't exist.
Any resource marked premium therefore 500'd for everyone, paying members
included.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from resources.access import can_access_resource, user_has_premium
from resources.models import Resource, ResourceCategory

User = get_user_model()


def make_premium(user):
    user.subscription.tier = 'premium'
    user.subscription.status = 'active'
    user.subscription.save()


def make_free(user):
    user.subscription.tier = 'free'
    user.subscription.save()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PremiumResourceGatingTests(TestCase):
    def setUp(self):
        cat = ResourceCategory.objects.create(name='Tools', description='x')
        self.resource = Resource.objects.create(
            title='Deep Dive Guide', category=cat, description='Preview text.',
            content='<p>SECRET-PREMIUM-BODY</p>', access_level='premium',
            interaction_type='hybrid', interactive_component='DailyRecoveryChecklist',
        )
        self.user = User.objects.create_user(username='gate', password='x')

    def test_helpers(self):
        make_free(self.user)
        self.assertFalse(user_has_premium(self.user))
        self.assertFalse(can_access_resource(self.user, self.resource))
        make_premium(self.user)
        self.assertTrue(user_has_premium(self.user))
        self.assertTrue(can_access_resource(self.user, self.resource))

    def test_court_tier_counts_as_premium(self):
        self.user.subscription.tier = 'court'
        self.user.subscription.status = 'active'
        self.user.subscription.save()
        self.assertTrue(user_has_premium(self.user))

    def test_detail_shows_preview_not_content_to_free_user(self):
        make_free(self.user)
        self.client.force_login(self.user)
        resp = self.client.get(self.resource.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Preview text.')
        self.assertContains(resp, 'This resource is part of Premium')
        self.assertNotContains(resp, 'SECRET-PREMIUM-BODY')

    def test_detail_shows_preview_to_anonymous(self):
        resp = self.client.get(self.resource.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'SECRET-PREMIUM-BODY')

    def test_detail_shows_content_to_premium_user(self):
        make_premium(self.user)
        self.client.force_login(self.user)
        resp = self.client.get(self.resource.get_absolute_url())
        self.assertContains(resp, 'SECRET-PREMIUM-BODY')
        self.assertNotContains(resp, 'This resource is part of Premium')

    def test_free_user_interactive_and_download_redirect_to_pricing(self):
        make_free(self.user)
        self.client.force_login(self.user)
        for name in ('resources:interactive', 'resources:download'):
            resp = self.client.get(reverse(name, args=[self.resource.slug]))
            self.assertEqual(resp.status_code, 302, name)
            self.assertIn(reverse('accounts:pricing'), resp['Location'], name)

    def test_premium_user_reaches_interactive_view(self):
        make_premium(self.user)
        self.client.force_login(self.user)
        resp = self.client.get(reverse('resources:interactive', args=[self.resource.slug]))
        self.assertEqual(resp.status_code, 200)

    def test_free_user_cannot_save_progress(self):
        make_free(self.user)
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse('resources:save_progress', args=[self.resource.slug]),
            data='{"completed_items": 1, "total_items": 2}',
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 403)

    def test_free_resource_still_open_to_everyone(self):
        self.resource.access_level = 'free'
        self.resource.save()
        resp = self.client.get(self.resource.get_absolute_url())
        self.assertContains(resp, 'SECRET-PREMIUM-BODY')
