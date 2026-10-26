"""Groups, challenges and sponsor matching are hidden behind
SHOW_GROUPS_CHALLENGES_SPONSORS (2026-10: near-zero use). The pages still
work; only the ways in are hidden, and flipping the setting restores them."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()
HIDDEN = ('accounts:groups_list', 'accounts:create_group', 'accounts:sponsor_dashboard',
          'accounts:challenges_home')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class HiddenSocialFeaturesTest(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user('hide', 'h@example.com', 'pw'))

    def _links(self, url_name):
        html = self.client.get(reverse(url_name)).content.decode()
        return [n for n in HIDDEN if f'href="{reverse(n)}"' in html]

    def test_entry_points_are_hidden(self):
        for page in ('accounts:community', 'accounts:progress', 'accounts:pal_dashboard',
                     'blog:post_list', 'core:alcohol_recovery_app', 'core:sobriety_counter_app'):
            with self.subTest(page=page):
                self.assertEqual(self._links(page), [])

    @override_settings(SHOW_GROUPS_CHALLENGES_SPONSORS=True)
    def test_flag_brings_them_back(self):
        self.assertIn('accounts:groups_list', self._links('accounts:community'))
        self.assertIn('accounts:sponsor_dashboard', self._links('accounts:community'))

    def test_pages_still_work_for_existing_members(self):
        self.assertEqual(self.client.get(reverse('accounts:groups_list')).status_code, 200)
