"""The community feed is the composer and the feed: the check-in prompt shows
only until today's check-in is done, and the daily thought lives on Today."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import DailyCheckIn

User = get_user_model()


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FeedLayoutTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='feed_layout', email='feed@example.com', password='pw')
        self.client.login(username='feed_layout', password='pw')

    def feed(self):
        return self.client.get(reverse('accounts:social_feed')).content.decode()

    def test_checkin_prompt_shows_before_todays_checkin(self):
        self.assertIn('id="ckNudgeGrid"', self.feed())

    def test_checkin_prompt_is_gone_once_checked_in(self):
        DailyCheckIn.objects.create(
            user=self.user, date=timezone.localdate(), mood=4, craving_level=0, energy_level=3)
        self.assertNotIn('id="ckNudgeGrid"', self.feed())

    def test_support_row_and_no_daily_thought_card(self):
        html = self.feed()
        self.assertIn('class="support-row"', html)
        self.assertIn('I need support', html)
        self.assertNotIn('Daily recovery thought', html)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FeedEngagementTest(TestCase):
    """Author links, the "who reacted" line and the daily composer prompt."""

    def setUp(self):
        from apps.accounts.models import SocialPost
        self.user = User.objects.create_user(username='viewer', email='v@example.com', password='pw')
        self.author = User.objects.create_user(
            username='poster', email='p@example.com', password='pw', first_name='Sam', last_name='Lee')
        self.post = SocialPost.objects.create(author=self.author, content='Day 30.')
        self.client.login(username='viewer', password='pw')

    def feed(self):
        return self.client.get(reverse('accounts:social_feed')).content.decode()

    def react(self, user, kind='support'):
        from apps.accounts.models import PostReaction
        return PostReaction.objects.create(post=self.post, user=user, reaction_type=kind)

    def test_author_name_links_to_profile(self):
        profile = reverse('accounts:profile', args=['poster'])
        self.assertIn(f'<a href="{profile}" class="post-author-name">Sam Lee', self.feed())

    def test_no_reactions_shows_no_count(self):
        html = self.feed()
        self.assertIn('<div class="reaction-summary" aria-live="polite"></div>', html)
        self.assertNotIn('class="reaction-count"', html)

    def test_reaction_summary_is_anonymous(self):
        from apps.accounts.views import reaction_summary
        self.assertEqual(reaction_summary([], self.user), '')
        first = self.react(self.author)
        self.assertEqual(reaction_summary([first], self.user), '1 person reacted')
        mine = self.react(self.user)
        self.assertEqual(reaction_summary([first, mine], self.user), 'You and 1 other reacted')
        third = self.react(User.objects.create_user(username='third', email='t@example.com', password='pw'))
        self.assertEqual(reaction_summary([first, mine, third], self.user), 'You and 2 others reacted')
        html = self.feed()
        self.assertIn('>You and 2 others reacted</div>', html)
        self.assertEqual(reaction_summary([first, third], self.user), '2 people reacted')

    def test_react_endpoint_returns_summary(self):
        self.react(self.author)
        data = self.client.post(
            reverse('accounts:react_to_post', args=[self.post.id]), {'reaction_type': 'support'}).json()
        self.assertEqual(data['reaction_summary'], 'You and 1 other reacted')

    def test_composer_shows_todays_prompt(self):
        from apps.accounts.views import COMPOSER_PROMPTS, composer_prompt
        import datetime
        self.assertIn(composer_prompt(), COMPOSER_PROMPTS)
        self.assertNotEqual(
            composer_prompt(datetime.date(2026, 11, 21)), composer_prompt(datetime.date(2026, 11, 22)))
        from django.utils.html import escape
        self.assertIn(f'placeholder="{escape(composer_prompt())}"', self.feed())

    def test_today_feed_tab_opens_the_real_feed(self):
        """One feed only: the Today page links to it rather than embedding a copy."""
        html = self.client.get(reverse('accounts:progress')).content.decode()
        self.assertIn(f'<a class="landing-tab" href="{reverse("accounts:social_feed")}">', html)
        self.assertNotIn('fragment=1', html)
