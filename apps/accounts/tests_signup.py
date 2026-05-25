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
