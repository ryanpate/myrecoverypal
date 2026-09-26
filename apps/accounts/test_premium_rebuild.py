"""Premium rebuild (2026-09-26): celebration + accountability.

- One Supporter seat included: a Premium member's earliest-connected supporter
  sees the dashboard without their own Supporter plan.
- Milestone medallion: at each milestone Premium members get their HD pack
  (video pre-rendered) instead of the shop promo email.
- 20% off keepsakes for Premium.
- Groups, private groups and challenge creation are free for everyone.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.medallion_models import KeepsakeOrder, MedallionPackPurchase
from apps.accounts.supporter_models import SupporterLink

User = get_user_model()


def _user(username, tier='free'):
    user = User.objects.create_user(username=username, email=f'{username}@example.com', password='pw')
    user.subscription.tier = tier
    user.subscription.status = 'active'
    user.subscription.save()
    return user


def _link(member, supporter, minutes_ago=0):
    link = SupporterLink.objects.create(member=member, supporter=supporter, initiated_by='member',
                                        status='active', preset='standard')
    SupporterLink.objects.filter(pk=link.pk).update(
        consented_at=timezone.now() - timedelta(minutes=minutes_ago))
    link.refresh_from_db()
    return link


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class IncludedSupporterSeatTest(TestCase):

    def setUp(self):
        self.member = _user('member', tier='premium')
        self.mom = _user('mom')
        self.dad = _user('dad')
        self.first = _link(self.member, self.mom, minutes_ago=60)
        self.second = _link(self.member, self.dad, minutes_ago=10)

    def _dashboard(self, who, link):
        self.client.force_login(who)
        return self.client.get(reverse('accounts:supporter_dashboard', args=[link.id]))

    def test_premium_members_first_supporter_views_free(self):
        self.assertEqual(self._dashboard(self.mom, self.first).status_code, 200)
        self.assertTrue(self.first.is_included_seat())

    def test_only_one_seat_is_included(self):
        resp = self._dashboard(self.dad, self.second)
        self.assertRedirects(resp, reverse('accounts:supporter_renew'), fetch_redirect_response=False)
        self.assertFalse(self.second.is_included_seat())

    def test_no_seat_when_member_is_not_premium(self):
        self.member.subscription.tier = 'free'
        self.member.subscription.save()
        resp = self._dashboard(self.mom, self.first)
        self.assertRedirects(resp, reverse('accounts:supporter_renew'), fetch_redirect_response=False)

    def test_supporter_with_own_plan_still_works(self):
        self.dad.subscription.tier = 'supporter'
        self.dad.subscription.save()
        self.assertEqual(self._dashboard(self.dad, self.second).status_code, 200)

    def test_seat_moves_to_next_supporter_when_first_is_revoked(self):
        self.first.revoke()
        self.second.refresh_from_db()
        self.assertTrue(self.second.is_included_seat())

    def test_member_sees_which_supporter_is_included(self):
        self.client.force_login(self.member)
        resp = self.client.get(reverse('accounts:supporter_manage'))
        self.assertContains(resp, 'Included with Premium', count=1)


class MilestoneMedallionTest(TestCase):

    def setUp(self):
        self.user = _user('ninety', tier='premium')
        self.user.sobriety_date = timezone.localdate() - timedelta(days=90)
        self.user.marketing_emails_enabled = True
        self.user.save()

    @patch('apps.accounts.medallion_pack.queue_video_prerender')
    @patch('apps.accounts.medallion_pack.send_email')
    @patch('apps.store.tasks.send_milestone_celebration_email')
    def test_premium_member_gets_their_medallion_instead_of_shop_email(self, shop_email, send, prerender):
        from apps.store.tasks import daily_milestone_celebration_task
        daily_milestone_celebration_task.apply()
        shop_email.assert_not_called()
        pack = MedallionPackPurchase.objects.get(user=self.user)
        self.assertEqual((pack.days, pack.status, pack.amount_cents), (90, 'paid', 0))
        prerender.assert_called_once_with(pack.id)
        body = send.call_args.kwargs['plain_message']
        self.assertIn(reverse('accounts:medallion_pack', args=[pack.token]), body)
        # Once per milestone, even if the task runs again the same day.
        daily_milestone_celebration_task.apply()
        self.assertEqual(MedallionPackPurchase.objects.filter(user=self.user).count(), 1)

    @patch('apps.accounts.medallion_pack.queue_video_prerender')
    @patch('apps.accounts.medallion_pack.send_email')
    def test_uses_their_last_saved_medallion_design(self, send, prerender):
        from apps.accounts.models import SavedBadge
        from apps.accounts.medallion_pack import send_premium_milestone_medallion
        SavedBadge.objects.create(user=self.user, days=30, style='emerald', name='Sam',
                                  time_format='auto', font_size=120, color='gold', outline=True)
        send_premium_milestone_medallion(self.user, 90)
        pack = MedallionPackPurchase.objects.get(user=self.user)
        self.assertEqual((pack.style, pack.name, pack.color, pack.days), ('emerald', 'Sam', 'gold', 90))

    @patch('apps.store.tasks.send_milestone_celebration_email', return_value=True)
    def test_free_users_still_get_the_shop_email(self, shop_email):
        from apps.store.tasks import daily_milestone_celebration_task
        self.user.subscription.tier = 'free'
        self.user.subscription.save()
        daily_milestone_celebration_task.apply()
        shop_email.assert_called_once()
        self.assertFalse(MedallionPackPurchase.objects.exists())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class KeepsakeDiscountTest(TestCase):
    DESIGN = {'days': '90', 'style': 'classic', 'product': 'mug'}

    @patch('apps.accounts.keepsake_views.stripe.checkout.Session.create')
    def test_premium_members_pay_20_percent_less(self, create):
        create.return_value = SimpleNamespace(id='cs_d', url='https://checkout.stripe.test/d')
        self.client.force_login(_user('prem', tier='premium'))
        self.client.post(reverse('accounts:keepsake_checkout'), self.DESIGN)
        self.assertEqual(KeepsakeOrder.objects.get().amount_cents, 1999)
        self.assertEqual(create.call_args.kwargs['line_items'][0]['price_data']['unit_amount'], 1999)

    @patch('apps.accounts.keepsake_views.stripe.checkout.Session.create')
    def test_others_pay_full_price(self, create):
        create.return_value = SimpleNamespace(id='cs_f', url='https://checkout.stripe.test/f')
        self.client.post(reverse('accounts:keepsake_checkout'), self.DESIGN)
        self.assertEqual(KeepsakeOrder.objects.get().amount_cents, 2499)

    def test_creator_shows_premium_prices(self):
        self.client.force_login(_user('prem2', tier='premium'))
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertContains(resp, '$19.99')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class FreeCommunityFeaturesTest(TestCase):

    def setUp(self):
        self.user = _user('free_member')
        self.client.force_login(self.user)

    def test_free_user_can_create_a_challenge(self):
        resp = self.client.get(reverse('accounts:create_challenge'))
        self.assertEqual(resp.status_code, 200)

    def test_free_user_can_join_more_than_five_groups(self):
        from apps.accounts.models import RecoveryGroup
        owner = _user('owner')
        for i in range(6):
            g = RecoveryGroup.objects.create(name=f'G{i}', description='d', group_type='interest',
                                             privacy_level='public', creator=owner)
            resp = self.client.post(reverse('accounts:join_group', args=[g.id]))
            self.assertTrue(resp.json().get('success'), (i, resp.json()))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PremiumPitchTest(TestCase):

    def test_pricing_sells_the_new_premium(self):
        content = self.client.get(reverse('accounts:pricing')).content.decode()
        for claim in ('Supporter seat included', 'milestone medallion', '20% off keepsakes'):
            self.assertIn(claim, content)
        for dead in ('private groups', 'Create custom challenges', 'Unlimited groups'):
            self.assertNotIn(dead, content)
