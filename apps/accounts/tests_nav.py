# apps/accounts/tests_nav.py
"""Tests for the nav reorganization (top nav + dropdown + mobile slide-out + tab partials)."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MedallionsTabNavTest(TestCase):
    """Both medallions pages render the same tab navigation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='med_user', email='med@example.com', password='pw'
        )
        self.client.login(username='med_user', password='pw')

    def test_my_medallions_page_has_tab_nav(self):
        resp = self.client.get(reverse('accounts:my_medallions'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'medallions-tab-nav')
        self.assertContains(resp, 'My Medallions')
        self.assertContains(resp, 'Create New')

    def test_create_medallion_page_has_tab_nav(self):
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'medallions-tab-nav')
        self.assertContains(resp, 'My Medallions')
        self.assertContains(resp, 'Create New')

    def test_my_medallions_tab_marked_active_on_its_page(self):
        resp = self.client.get(reverse('accounts:my_medallions'))
        self.assertContains(resp, 'medallions-tab-nav__link--active')
        content = resp.content.decode('utf-8')
        active_idx = content.find('medallions-tab-nav__link--active')
        nearby = content[active_idx:active_idx + 400]
        self.assertIn('My Medallions', nearby)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CommunityTabNavTest(TestCase):
    """Both community and groups pages render the same tab navigation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='comm_user', email='comm@example.com', password='pw'
        )
        self.client.login(username='comm_user', password='pw')

    def test_community_page_has_tab_nav(self):
        resp = self.client.get(reverse('accounts:community'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'community-tab-nav')
        self.assertContains(resp, 'Members')
        self.assertContains(resp, 'Groups')

    def test_groups_page_has_tab_nav(self):
        resp = self.client.get(reverse('accounts:groups_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'community-tab-nav')
        self.assertContains(resp, 'Members')
        self.assertContains(resp, 'Groups')

    def test_community_tab_active_on_community_page(self):
        resp = self.client.get(reverse('accounts:community'))
        self.assertContains(resp, 'community-tab-nav__link--active')
        content = resp.content.decode('utf-8')
        active_idx = content.find('community-tab-nav__link--active')
        nearby = content[active_idx:active_idx + 400]
        self.assertIn('Members', nearby)
