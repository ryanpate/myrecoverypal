"""Tests for the onboarding + re-engagement email sequences."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.template.loader import render_to_string

from apps.accounts.models import (
    User, DailyCheckIn, SocialPost, RecoveryCoachSession, CoachMessage,
)
from apps.journal.models import JournalEntry
from apps.accounts import email_sequences as seq


def make_user(username='pal', days_ago=0, **kwargs):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='x',
        **kwargs,
    )
    if days_ago:
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timedelta(days=days_ago))
        user.refresh_from_db()
    return user


class EligibilityHelperTests(TestCase):
    def test_activation_requires_all_three_actions(self):
        user = make_user()
        self.assertFalse(seq.is_activated(user))
        DailyCheckIn.objects.create(user=user, mood=3, energy_level=3)
        JournalEntry.objects.create(user=user, content='one line')
        self.assertFalse(seq.is_activated(user))
        SocialPost.objects.create(author=user, content='hello')
        self.assertTrue(seq.is_activated(user))

    def test_has_used_anchor(self):
        user = make_user()
        self.assertFalse(seq.has_used_anchor(user))
        session = RecoveryCoachSession.objects.create(user=user)
        CoachMessage.objects.create(session=session, role='user', content='hi')
        self.assertTrue(seq.has_used_anchor(user))

    def test_crisis_suppression_window(self):
        user = make_user()
        self.assertFalse(seq.is_crisis_suppressed(user))
        session = RecoveryCoachSession.objects.create(
            user=user, trigger='checkin_support')
        self.assertTrue(seq.is_crisis_suppressed(user))
        # Age the session past 48h
        RecoveryCoachSession.objects.filter(pk=session.pk).update(
            updated_at=timezone.now() - timedelta(hours=49))
        self.assertFalse(seq.is_crisis_suppressed(user))

    def test_get_last_activity_takes_most_recent_signal(self):
        user = make_user(days_ago=30)
        self.assertEqual(seq.get_last_activity(user), user.date_joined)
        user.last_seen = timezone.now() - timedelta(days=2)
        self.assertEqual(seq.get_last_activity(user), user.last_seen)

    def test_unsubscribe_url_contains_token_path(self):
        user = make_user()
        url = seq.marketing_unsubscribe_url(user)
        self.assertIn('/email/unsubscribe/', url)
        self.assertTrue(url.startswith('http'))


class TemplateRenderTests(TestCase):
    def test_all_sequence_templates_render(self):
        user = make_user(username='render')
        templates = (
            ['emails/onboarding_1.html']
            + [e['template'] for e in seq.ONBOARDING_EMAILS]
            + [e['template'] for e in seq.REENGAGEMENT_EMAILS]
        )
        for tpl in templates:
            html = render_to_string(tpl, {
                'user': user,
                'site_url': 'https://www.myrecoverypal.com',
                'current_year': 2026,
                'unsubscribe_url': 'https://www.myrecoverypal.com/email/unsubscribe/x/',
                'streak': 3,
                'has_streak': True,
            })
            self.assertIn('unsubscribe', html.lower(), tpl)
            self.assertIn('render', html, tpl)  # greeting uses username fallback


class WelcomeEmailE1Tests(TestCase):
    @patch('apps.accounts.tasks.send_email', return_value=(True, None))
    def test_e1_uses_new_subject_and_marks_sent(self, mock_send):
        from apps.accounts.tasks import send_welcome_email_day_1
        user = make_user(username='e1user')
        send_welcome_email_day_1(user.id)
        user.refresh_from_db()
        self.assertIsNotNone(user.welcome_email_1_sent)
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs['subject'],
                         "Welcome in. You're a founding member. 💙")
        self.assertIn('unsubscribe', kwargs['html_message'].lower())
