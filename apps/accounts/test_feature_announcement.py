"""send_feature_announcement: the one-off recovery-toolkit email."""
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.management.commands.send_feature_announcement import KEY
from apps.accounts.models import AnnouncementDelivery, DailyCheckIn
from resources.test_premium_gating import make_free, make_premium

User = get_user_model()
SEND = 'apps.accounts.management.commands.send_feature_announcement.send_email'


def user(name, **fields):
    u = User.objects.create_user(name, f'{name}@example.com', 'pw12345!')
    User.objects.filter(pk=u.pk).update(**fields)
    u.refresh_from_db()
    return u


@override_settings(SITE_URL='https://www.myrecoverypal.com')
class FeatureAnnouncementTests(TestCase):
    def run_cmd(self, *args):
        out = StringIO()
        with patch(SEND) as send:
            call_command('send_feature_announcement', *args, '--sleep', '0', stdout=out, stderr=StringIO())
        return out.getvalue(), send

    def setUp(self):
        self.free = user('freeone')
        make_free(self.free)
        self.prem = user('premone')
        make_premium(self.prem)
        self.optout = user('optout', marketing_emails_enabled=False)
        self.inactive = user('gone', is_active=False)

    def test_dry_run_sends_nothing(self):
        out, send = self.run_cmd('--segment', 'all')
        send.assert_not_called()
        self.assertIn('Recipients: 2 (1 Premium, 1 free)', out)
        self.assertIn('DRY-RUN', out)
        self.assertFalse(AnnouncementDelivery.objects.exists())

    def test_commit_sends_once_and_records(self):
        out, send = self.run_cmd('--segment', 'all', '--commit')
        self.assertEqual(send.call_count, 2)
        sent_to = {c.kwargs['recipient_email'] for c in send.call_args_list}
        self.assertEqual(sent_to, {'freeone@example.com', 'premone@example.com'})
        self.assertEqual(AnnouncementDelivery.objects.filter(key=KEY).count(), 2)
        # Re-running never emails anyone twice.
        out, send = self.run_cmd('--segment', 'all', '--commit')
        send.assert_not_called()
        self.assertIn('Recipients: 0', out)

    def test_premium_gets_thank_you_free_gets_offer(self):
        _, send = self.run_cmd('--segment', 'all', '--commit')
        html = {c.kwargs['recipient_email']: c.kwargs['html_message'] for c in send.call_args_list}
        self.assertIn('already included in your Premium', html['premone@example.com'])
        self.assertNotIn('Try Premium', html['premone@example.com'])
        self.assertIn('Premium', html['freeone@example.com'])
        self.assertNotIn('already included', html['freeone@example.com'])
        for body in html.values():
            self.assertIn('/email/unsubscribe/', body)
            self.assertIn(f'utm_campaign={KEY}', body)
            self.assertIn(reverse('resources:audio'), body)
            self.assertIn('988', body)

    def test_engaged_segment_needs_recent_checkin(self):
        DailyCheckIn.objects.create(user=self.free, mood=3, energy_level=3, date=timezone.localdate())
        out, send = self.run_cmd('--commit')
        self.assertEqual([c.kwargs['recipient_email'] for c in send.call_args_list], ['freeone@example.com'])

    def test_one_failure_does_not_stop_the_run(self):
        out = StringIO()
        with patch(SEND, side_effect=[RuntimeError('bounce'), None]):
            call_command('send_feature_announcement', '--segment', 'all', '--commit', '--sleep', '0',
                         stdout=out, stderr=StringIO())
        self.assertIn('Sent 1, failed 1', out.getvalue())
        self.assertEqual(AnnouncementDelivery.objects.count(), 1)  # the failed one can be retried

    def test_test_email_not_recorded(self):
        out, send = self.run_cmd('--test', 'founder@example.com')
        self.assertEqual(send.call_args.kwargs['recipient_email'], 'founder@example.com')
        self.assertTrue(send.call_args.kwargs['subject'].startswith('[TEST]'))
        self.assertFalse(AnnouncementDelivery.objects.exists())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class LibraryNavTests(TestCase):
    def test_library_link_for_visitors_and_members(self):
        url = reverse('resources:list')
        resp = self.client.get(reverse('core:index'))
        self.assertContains(resp, 'class="nav-library ')
        self.assertContains(resp, f'href="{url}"')
        self.client.force_login(user('navuser'))
        resp = self.client.get(reverse('accounts:progress'))
        self.assertContains(resp, 'class="nav-library ')

    def test_library_active_on_resource_pages(self):
        resp = self.client.get(reverse('resources:audio'))
        self.assertContains(resp, 'class="nav-library active"')
