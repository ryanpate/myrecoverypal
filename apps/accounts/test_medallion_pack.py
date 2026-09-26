"""Tests for the one-time $4.99 HD Medallion Pack (no-watermark HD, square, story)."""
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.medallion_models import MedallionPackPurchase

User = get_user_model()

BADGE = {
    'days': '90', 'style': 'classic', 'name': 'Sam', 'time_format': 'auto',
    'font_size': '110', 'color': 'gold', 'outline': '1',
}


def _img(data):
    return Image.open(BytesIO(data))


class PackVideoTest(TestCase):
    """The animated story video: real render, checked with ffmpeg metadata."""

    def setUp(self):
        cache.clear()

    def test_story_video_is_portrait_mp4_about_five_seconds(self):
        import tempfile
        import imageio_ffmpeg
        from apps.accounts.medallion_video import generate_story_video
        data = generate_story_video(90, style='classic', name='Sam', color='gold')
        self.assertEqual(data[4:8], b'ftyp')
        with tempfile.NamedTemporaryFile(suffix='.mp4') as f:
            f.write(data)
            f.flush()
            reader = imageio_ffmpeg.read_frames(f.name)
            meta = next(reader)
            reader.close()
        self.assertEqual(tuple(meta['size']), (1080, 1920))
        self.assertAlmostEqual(meta['duration'], 5.0, delta=0.2)

    def test_story_video_is_cached(self):
        from apps.accounts import medallion_video
        with patch.object(medallion_video, '_render_video', return_value=b'mp4') as render:
            medallion_video.generate_story_video(30, style='classic')
            medallion_video.generate_story_video(30, style='classic')
        self.assertEqual(render.call_count, 1)


class PackImageTest(TestCase):

    def setUp(self):
        cache.clear()

    def test_default_render_is_unchanged_1080(self):
        from apps.accounts.milestone_image import generate_milestone_image
        self.assertEqual(_img(generate_milestone_image(90)).size, (1080, 1080))

    def test_hd_render_without_watermark(self):
        from apps.accounts.milestone_image import generate_milestone_image
        hd = generate_milestone_image(90, size=2048, watermark=False)
        self.assertEqual(_img(hd).size, (2048, 2048))

    def test_watermark_flag_changes_the_image(self):
        from apps.accounts.milestone_image import generate_milestone_image
        a = generate_milestone_image(90, watermark=True)
        b = generate_milestone_image(90, watermark=False)
        self.assertNotEqual(a, b)

    def test_story_render_is_portrait(self):
        from apps.accounts.milestone_image import generate_story_image
        self.assertEqual(_img(generate_story_image(90)).size, (1080, 1920))


def _purchase(**kw):
    fields = dict(days=90, style='classic', name='Sam', time_format='auto',
                  font_size=110, color='gold', outline=True,
                  amount_cents=499, status='paid', email='buyer@example.com')
    fields.update(kw)
    return MedallionPackPurchase.objects.create(**fields)


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PackCheckoutTest(TestCase):

    def setUp(self):
        cache.clear()

    @patch('apps.accounts.medallion_pack_views.stripe.checkout.Session.create')
    def test_anonymous_checkout_creates_pending_purchase_and_redirects(self, create):
        create.return_value = SimpleNamespace(id='cs_test_1', url='https://checkout.stripe.test/1')
        resp = self.client.post(reverse('accounts:medallion_pack_checkout'), BADGE)
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp['Location'], 'https://checkout.stripe.test/1')
        p = MedallionPackPurchase.objects.get()
        self.assertEqual((p.status, p.stripe_session_id, p.days, p.color, p.name),
                         ('pending', 'cs_test_1', 90, 'gold', 'Sam'))
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['mode'], 'payment')
        self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'], 499)
        self.assertEqual(kwargs['metadata']['kind'], 'medallion_pack')
        self.assertEqual(kwargs['metadata']['purchase_id'], str(p.id))

    @patch('apps.accounts.medallion_pack_views.stripe.checkout.Session.create')
    def test_premium_user_gets_pack_free_without_stripe(self, create):
        user = User.objects.create_user(username='prem', email='prem@example.com', password='pw')
        user.subscription.tier = 'premium'
        user.subscription.status = 'active'
        user.subscription.save()
        self.client.login(username='prem', password='pw')
        resp = self.client.post(reverse('accounts:medallion_pack_checkout'), BADGE)
        create.assert_not_called()
        p = MedallionPackPurchase.objects.get()
        self.assertEqual((p.status, p.amount_cents, p.user), ('paid', 0, user))
        self.assertRedirects(resp, reverse('accounts:medallion_pack', args=[p.token]),
                             fetch_redirect_response=False)

    @patch('apps.accounts.medallion_pack.send_email')
    @patch('apps.accounts.medallion_pack_views.stripe.checkout.Session.retrieve')
    def test_success_page_confirms_payment_and_emails_once(self, retrieve, send):
        p = _purchase(status='pending', email='', stripe_session_id='cs_ok')
        retrieve.return_value = {
            'id': 'cs_ok', 'payment_status': 'paid', 'payment_intent': 'pi_1',
            'metadata': {'kind': 'medallion_pack', 'purchase_id': str(p.id)},
            'customer_details': {'email': 'buyer@example.com'},
        }
        url = reverse('accounts:medallion_pack_success') + '?session_id=cs_ok'
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('accounts:medallion_pack', args=[p.token]),
                             fetch_redirect_response=False)
        self.client.get(url)  # reload must not double-email
        p.refresh_from_db()
        self.assertEqual((p.status, p.stripe_payment_intent_id, p.email),
                         ('paid', 'pi_1', 'buyer@example.com'))
        self.assertEqual(send.call_count, 1)

    @patch('apps.accounts.medallion_pack_views.stripe.checkout.Session.retrieve')
    def test_success_page_unpaid_session_does_not_unlock(self, retrieve):
        p = _purchase(status='pending', stripe_session_id='cs_wait')
        retrieve.return_value = {
            'id': 'cs_wait', 'payment_status': 'unpaid', 'payment_intent': None,
            'metadata': {'kind': 'medallion_pack', 'purchase_id': str(p.id)},
            'customer_details': {},
        }
        self.client.get(reverse('accounts:medallion_pack_success') + '?session_id=cs_wait')
        p.refresh_from_db()
        self.assertEqual(p.status, 'pending')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class PackDownloadTest(TestCase):

    def setUp(self):
        cache.clear()

    def test_paid_pack_serves_all_three_formats(self):
        p = _purchase()
        sizes = {'hd': (2048, 2048), 'square': (1080, 1080), 'story': (1080, 1920)}
        for fmt, size in sizes.items():
            resp = self.client.get(reverse('accounts:medallion_pack_file', args=[p.token, fmt]))
            self.assertEqual(resp.status_code, 200, fmt)
            self.assertIn('attachment', resp['Content-Disposition'])
            self.assertEqual(_img(resp.content).size, size, fmt)

    @patch('apps.accounts.medallion_pack_views.generate_story_video', return_value=b'mp4-bytes')
    def test_paid_pack_serves_video(self, render):
        p = _purchase()
        resp = self.client.get(reverse('accounts:medallion_pack_file', args=[p.token, 'video']))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'video/mp4')
        self.assertIn('.mp4', resp['Content-Disposition'])
        self.assertEqual(resp.content, b'mp4-bytes')

    def test_pack_page_lists_downloads(self):
        p = _purchase()
        resp = self.client.get(reverse('accounts:medallion_pack', args=[p.token]))
        self.assertEqual(resp.status_code, 200)
        for fmt in ('hd', 'square', 'story', 'video'):
            self.assertContains(resp, reverse('accounts:medallion_pack_file', args=[p.token, fmt]))

    def test_unpaid_or_refunded_pack_is_not_downloadable(self):
        for status in ('pending', 'refunded'):
            p = _purchase(status=status)
            resp = self.client.get(reverse('accounts:medallion_pack_file', args=[p.token, 'hd']))
            self.assertEqual(resp.status_code, 404, status)

    def test_unknown_format_404(self):
        p = _purchase()
        resp = self.client.get(reverse('accounts:medallion_pack_file', args=[p.token, 'gif']))
        self.assertEqual(resp.status_code, 404)


class PackWebhookTest(TestCase):

    @patch('apps.accounts.medallion_pack.send_email')
    def test_checkout_completed_marks_pack_paid_idempotently(self, send):
        from apps.accounts.payment_views import handle_checkout_session_completed
        p = _purchase(status='pending', email='', stripe_session_id='cs_wh')
        session = {
            'id': 'cs_wh', 'customer': None, 'subscription': None, 'mode': 'payment',
            'payment_status': 'paid', 'payment_intent': 'pi_wh',
            'metadata': {'kind': 'medallion_pack', 'purchase_id': str(p.id)},
            'customer_details': {'email': 'wh@example.com'},
        }
        handle_checkout_session_completed(session)
        handle_checkout_session_completed(session)
        p.refresh_from_db()
        self.assertEqual((p.status, p.email), ('paid', 'wh@example.com'))
        self.assertEqual(send.call_count, 1)

    def test_refund_revokes_pack(self):
        from apps.accounts.payment_views import handle_charge_refunded
        p = _purchase(stripe_payment_intent_id='pi_refund')
        handle_charge_refunded({'id': 'ch_1', 'customer': None, 'amount_refunded': 499,
                                'payment_intent': 'pi_refund', 'currency': 'usd'})
        p.refresh_from_db()
        self.assertEqual(p.status, 'refunded')


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class CreatorPackCtaTest(TestCase):

    def test_anonymous_sees_paid_cta_hidden_on_ios(self):
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertContains(resp, 'id="pack-cta"')
        self.assertContains(resp, '$4.99')
        html = resp.content.decode()
        form_start = html.rfind('<form', 0, html.find('id="pack-cta"'))
        form_tag = html[form_start:html.find('>', form_start)]
        self.assertIn('stripe-only', form_tag)

    def test_premium_user_sees_included_cta(self):
        user = User.objects.create_user(username='prem2', email='p2@example.com', password='pw')
        user.subscription.tier = 'premium'
        user.subscription.status = 'active'
        user.subscription.save()
        self.client.login(username='prem2', password='pw')
        resp = self.client.get(reverse('accounts:milestone_badge_creator'))
        self.assertContains(resp, 'Included with Premium')
        self.assertNotContains(resp, '$4.99')
