"""Landing page toolkit + plans, pricing copy, and the "What's new" popup."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.payment_models import SubscriptionPlan
from apps.core.context_processors import WHATS_NEW_VERSION
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()


def set_plan(period, price):
    SubscriptionPlan.objects.update_or_create(
        tier='premium', billing_period=period,
        defaults={'name': f'Premium {period}', 'price': Decimal(price), 'is_active': True})


def member(username='member', days_old=10):
    user = User.objects.create_user(username, f'{username}@example.com', 'pw12345!')
    User.objects.filter(pk=user.pk).update(date_joined=timezone.now() - timedelta(days=days_old))
    user.refresh_from_db()
    return user


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LandingPageTests(TestCase):
    def test_toolkit_links_to_every_new_feature(self):
        resp = self.client.get(reverse('core:index'))
        self.assertEqual(resp.status_code, 200)
        for url in (reverse('resources:audio'), reverse('resources:programs'),
                    reverse('resources:reflections'), reverse('resources:worksheets'),
                    reverse('resources:program_detail', args=['family-and-friends']),
                    reverse('core:craving_sos')):
            self.assertContains(resp, f'href="{url}"')
        self.assertContains(resp, 'id="ml-toolkit"')
        self.assertContains(resp, 'href="#ml-toolkit"')  # hero "New" tag

    def test_plans_use_live_prices_hidden_in_ios_app(self):
        set_plan('monthly', '9.99')
        set_plan('yearly', '59.99')
        resp = self.client.get(reverse('core:index'))
        self.assertContains(resp, '$59.99')
        self.assertContains(resp, 'or $9.99 monthly')
        html = resp.content.decode()
        plan_price = html.index('class="ml-plan-price stripe-only"')
        self.assertIn('$59.99', html[plan_price:plan_price + 200])

    def test_no_prices_without_plans(self):
        SubscriptionPlan.objects.filter(tier='premium').update(is_active=False)
        resp = self.client.get(reverse('core:index'))
        self.assertNotContains(resp, 'ml-plan-price stripe-only')
        self.assertContains(resp, 'Start your free trial')

    def test_no_whats_new_popup_for_visitors(self):
        self.assertNotContains(self.client.get(reverse('core:index')), 'id="whatsNew"')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PricingCopyTests(TestCase):
    def test_lists_new_features(self):
        set_plan('monthly', '9.99')
        resp = self.client.get(reverse('accounts:pricing'))
        for text in ('Every guided program in full', 'The full guided audio library',
                     'All 30 daily reflections', 'free guided audio', 'first week of every guided program'):
            self.assertContains(resp, text)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class WhatsNewPopupTests(TestCase):
    def test_shown_on_progress_home_to_free_member(self):
        user = member()
        make_free(user)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'id="whatsNew"')
        self.assertContains(resp, f'data-version="{WHATS_NEW_VERSION}"')
        self.assertContains(resp, 'Your recovery toolkit just grew')
        self.assertContains(resp, f'href="{reverse("accounts:pricing")}" data-promo="whats_new_premium"')

    def test_premium_member_gets_no_upsell(self):
        user = member()
        make_premium(user)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'More is included in your Premium')
        self.assertNotContains(resp, 'whats_new_premium')

    def test_not_on_crisis_or_sos_pages(self):
        self.client.force_login(member())
        for name in ('core:craving_sos', 'core:crisis', 'accounts:pricing'):
            self.assertNotContains(self.client.get(reverse(name)), 'id="whatsNew"', msg_prefix=name)

    def test_not_in_first_day(self):
        self.client.force_login(member(days_old=0))
        self.assertNotContains(self.client.get(reverse('accounts:progress')), 'id="whatsNew"')

    def test_not_for_supporters(self):
        user = member()
        sub = user.subscription
        sub.tier, sub.status = 'supporter', 'active'
        sub.save()
        self.client.force_login(user)
        self.assertNotContains(self.client.get(reverse('accounts:progress')), 'id="whatsNew"')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class UpsellCardTests(TestCase):
    def test_card_lists_new_features_and_is_accurate(self):
        user = member()
        make_free(user)
        self.client.force_login(user)
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'Every guided program, the full audio')
        self.assertNotContains(resp, 'unlimited Anchor')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class IOSWebPriceTests(TestCase):
    """App Store Guideline 3.1: no web prices inside the iOS app. Every web
    price on an in-app surface sits in a `.stripe-only` element, and the
    native class is set in <head> so prices never flash before hiding."""

    def price_is_stripe_only(self, html, price_text):
        i = html.index(price_text)
        opening = html.rfind('<', 0, html.rfind('class=', 0, i))
        self.assertIn('stripe-only', html[opening:i], price_text)

    def test_native_class_set_in_head(self):
        html = self.client.get(reverse('core:index')).content.decode()
        head = html[:html.index('</head>')]
        self.assertIn("classList.add(C.getPlatform() + '-native-app')", head)

    def test_trial_banner_price_hidden_in_app(self):
        user = member()
        sub = user.subscription
        sub.tier, sub.status = 'premium', 'trialing'
        sub.trial_end = timezone.now() + timedelta(days=1)
        sub.stripe_subscription_id = ''
        sub.save()
        self.client.force_login(user)
        html = self.client.get(reverse('accounts:progress')).content.decode()
        self.assertIn('Keep Premium', html)
        self.price_is_stripe_only(html, '$9.99/mo')

    def test_progress_analytics_gate_price_hidden_in_app(self):
        from apps.accounts.models import DailyCheckIn
        user = member()
        make_free(user)
        DailyCheckIn.objects.create(user=user, mood=3, energy_level=3)
        self.client.force_login(user)
        html = self.client.get(reverse('accounts:progress')).content.decode()
        self.price_is_stripe_only(html, 'From $5/month')
