# apps/accounts/tests_signup.py
"""Tests for the friction-reduced signup flow (Audit Priority #2)."""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class UsernameGeneratorTest(TestCase):
    """generate_unique_username() returns a friendly anonymous identifier."""

    def test_returns_string_matching_pattern(self):
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        u = generate_unique_username()
        self.assertIsInstance(u, str)
        # Pattern: one wordlist entry followed by exactly 4 digits
        pattern = re.compile(rf'^({"|".join(WORDLIST)})\d{{4}}$')
        self.assertRegex(u, pattern)

    def test_returns_unique_value_when_collision(self):
        """If all preferred candidates are taken, the generator still returns
        a unique value (extended-suffix fallback)."""
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        # Pre-populate the username table with all 10 wordlist words at one
        # specific suffix so collisions happen, then assert we still get a
        # unique result back
        for word in WORDLIST:
            User.objects.create_user(
                username=f'{word}1234',
                email=f'{word.lower()}1234@example.com',
                password='pw'
            )
        existing = set(User.objects.values_list('username', flat=True))
        u = generate_unique_username()
        self.assertNotIn(u, existing)
        self.assertFalse(User.objects.filter(username=u).exists())

    def test_uses_wordlist_words_only(self):
        """Across 25 calls, every generated username's prefix is in WORDLIST."""
        from apps.accounts.username_generator import generate_unique_username, WORDLIST
        for _ in range(25):
            u = generate_unique_username()
            # Strip trailing digits; what's left should be a wordlist entry
            prefix = re.sub(r'\d+$', '', u)
            self.assertIn(prefix, WORDLIST, f'{prefix!r} (from {u!r}) not in WORDLIST')


class SignupFormTest(TestCase):
    """The slimmed CustomUserCreationForm: email + password only."""

    def test_form_has_only_email_and_password(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm()
        # The visible fields must be exactly email + password
        self.assertEqual(set(form.fields.keys()), {'email', 'password'})

    def test_email_required(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={'password': 'abcdefgh'})
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_minimum_length_enforced(self):
        from apps.accounts.forms import CustomUserCreationForm
        # 7 chars — should fail
        form = CustomUserCreationForm(data={
            'email': 'a@b.com', 'password': '1234567'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)
        # 8 chars — should pass
        form = CustomUserCreationForm(data={
            'email': 'a@b.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_email_rejected_with_friendly_message(self):
        User.objects.create_user(
            username='existing', email='taken@example.com', password='pw'
        )
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'taken@example.com', 'password': '12345678'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        # Must contain a hint that "sign in" is the right next action
        self.assertTrue(
            any('sign in' in str(e).lower() or 'already exists' in str(e).lower()
                for e in form.errors['email']),
            f'Expected friendly duplicate-email message, got: {form.errors["email"]}'
        )

    def test_email_is_lowercased_on_save(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'Mixed.Case@EXAMPLE.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, 'mixed.case@example.com')

    def test_save_generates_username_matching_pattern(self):
        import re
        from apps.accounts.forms import CustomUserCreationForm
        from apps.accounts.username_generator import WORDLIST
        form = CustomUserCreationForm(data={
            'email': 'new@example.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertRegex(
            user.username,
            re.compile(rf'^({"|".join(WORDLIST)})\d{{4}}$')
        )

    def test_save_hashes_password(self):
        from apps.accounts.forms import CustomUserCreationForm
        form = CustomUserCreationForm(data={
            'email': 'hash@example.com', 'password': '12345678'
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertNotEqual(user.password, '12345678')  # hashed
        self.assertTrue(user.check_password('12345678'))


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RegisterViewTest(TestCase):
    """The /accounts/register/ endpoint integrates the slimmed form."""

    def setUp(self):
        # Default SystemSettings is invite_only_mode=True; force public mode.
        from apps.accounts.invite_models import SystemSettings
        s = SystemSettings.get_settings()
        s.invite_only_mode = False
        s.save()
        # RateLimitMiddleware caches across TestCase methods; reset it.
        from django.core.cache import caches
        for name in ('rate_limiting', 'default'):
            try:
                caches[name].clear()
            except Exception:
                pass

    def test_get_renders_form(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(resp.status_code, 200)
        # Form fields are present in HTML
        self.assertContains(resp, 'name="email"')
        self.assertContains(resp, 'name="password"')
        # Old fields are absent
        self.assertNotContains(resp, 'name="password1"')
        self.assertNotContains(resp, 'name="password2"')
        self.assertNotContains(resp, 'name="sobriety_date"')

    def test_post_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'new@example.com',
            'password': 'mysecurepw123',
        })
        # Should redirect (302) somewhere authenticated, not stay on the form
        self.assertEqual(resp.status_code, 302)
        # User exists
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
        # User is logged in (session has _auth_user_id)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_creates_subscription(self):
        # A Subscription is auto-created by post_save signal on User creation
        # (14-day premium trial). The view also calls get_or_create as a safety
        # net. Either way: a Subscription must exist after signup.
        from apps.accounts.payment_models import Subscription
        self.client.post(reverse('accounts:register'), {
            'email': 'sub@example.com',
            'password': 'mysecurepw123',
        })
        user = User.objects.get(email='sub@example.com')
        self.assertTrue(Subscription.objects.filter(user=user).exists())

    def test_post_invalid_email_returns_form_with_errors(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'not-an-email',
            'password': 'mysecurepw123',
        })
        # Form re-renders (200, not 302), no user created
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='not-an-email').exists())

    def test_post_short_password_returns_form_with_errors(self):
        resp = self.client.post(reverse('accounts:register'), {
            'email': 'short@example.com',
            'password': '1234567',  # 7 chars
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='short@example.com').exists())


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class RegisterTemplateTest(TestCase):
    """The rendered register page matches Approach C from the brainstorm."""

    def setUp(self):
        # Default SystemSettings is invite_only_mode=True; force public mode.
        from apps.accounts.invite_models import SystemSettings
        s = SystemSettings.get_settings()
        s.invite_only_mode = False
        s.save()
        # RateLimitMiddleware caches across TestCase methods; reset it.
        from django.core.cache import caches
        for name in ('rate_limiting', 'default'):
            try:
                caches[name].clear()
            except Exception:
                pass

    def test_renders_simplified_layout(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertEqual(resp.status_code, 200)
        # New layout markers
        self.assertContains(resp, 'Create your account')
        self.assertContains(resp, 'Anchor AI Coach')
        self.assertContains(resp, 'Free forever')
        # Eye toggle present
        self.assertContains(resp, 'password-eye-toggle')
        # Sign-in link present
        self.assertContains(resp, 'Already have an account?')
        # Old layout markers gone
        self.assertNotContains(resp, '✨ Join MyRecoveryPal')
        self.assertNotContains(resp, 'What you get')
        self.assertNotContains(resp, 'name="username"')
        self.assertNotContains(resp, 'name="password1"')
        self.assertNotContains(resp, 'name="password2"')
        self.assertNotContains(resp, 'name="sobriety_date"')

    def test_email_input_has_mobile_keyboard_attributes(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertContains(resp, 'inputmode="email"')
        self.assertContains(resp, 'autocapitalize="off"')
        self.assertContains(resp, 'autocomplete="email"')

    def test_password_input_has_signup_autocomplete(self):
        resp = self.client.get(reverse('accounts:register'))
        self.assertContains(resp, 'autocomplete="new-password"')
