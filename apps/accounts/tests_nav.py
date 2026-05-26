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


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class TopNavCourtComplianceTest(TestCase):
    """Court Compliance pill is visible in the top nav for all authenticated users."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='nav_user', email='nav@example.com', password='pw'
        )
        self.client.login(username='nav_user', password='pw')

    def test_court_compliance_pill_in_top_nav(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'court-cta')
        self.assertContains(resp, 'Court Compliance')
        self.assertContains(resp, 'fa-gavel')

    def test_court_pill_links_to_public_landing_for_non_court_user(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertContains(resp, '/court-ordered-meeting-tracker/')

    def test_court_pill_links_to_dashboard_for_court_user(self):
        self.user.subscription.tier = 'court'
        self.user.subscription.status = 'active'
        self.user.subscription.save()
        resp = self.client.get(reverse('accounts:social_feed'))
        content = resp.content.decode('utf-8')
        cta_idx = content.find('court-cta')
        nearby = content[max(0, cta_idx - 200):cta_idx + 400]
        self.assertIn('/accounts/court/', nearby)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class DropdownReorgTest(TestCase):
    """Desktop user dropdown has 3 labeled sections and no duplicate/removed items."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='drop_user', email='drop@example.com', password='pw'
        )
        self.client.login(username='drop_user', password='pw')

    def test_dropdown_has_three_section_labels(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        content = resp.content.decode('utf-8')
        self.assertIn('user-dropdown-section-label', content)
        self.assertIn('My Recovery', content)
        self.assertIn('Community', content)
        self.assertIn('Account', content)

    def test_dropdown_does_not_contain_myrecoverycircle(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertNotContains(resp, 'MyRecoveryCircle')

    def test_dropdown_does_not_contain_install_app_link(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertNotContains(resp, '>Install App<')

    def test_dropdown_does_not_contain_separate_create_medallion(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        content = resp.content.decode('utf-8')
        dropdown_start = content.find('user-dropdown')
        # Find the matching end of the user-dropdown container (rough heuristic)
        dropdown_end = content.find('notification-dropdown', dropdown_start)
        if dropdown_end == -1:
            dropdown_end = dropdown_start + 5000
        dropdown_html = content[dropdown_start:dropdown_end]
        self.assertNotIn('Create Medallion', dropdown_html)

    def test_dropdown_contains_court_compliance_for_all_users(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        content = resp.content.decode('utf-8')
        # Court Compliance appears in top nav AND in dropdown (at least 2 occurrences)
        self.assertGreaterEqual(content.count('Court Compliance'), 2)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class MobileSlideOutReorgTest(TestCase):
    """Mobile slide-out menu uses the same labeled sections as the desktop dropdown."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='mob_user', email='mob@example.com', password='pw'
        )
        self.client.login(username='mob_user', password='pw')

    def test_mobile_menu_has_my_recovery_section(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        content = resp.content.decode('utf-8')
        self.assertIn('mobile-menu-label', content)
        self.assertIn('My Recovery', content)

    def test_mobile_menu_no_install_app_no_myrecoverycircle(self):
        resp = self.client.get(reverse('accounts:social_feed'))
        self.assertNotContains(resp, 'MyRecoveryCircle')
        self.assertNotContains(resp, '>Install App<')
