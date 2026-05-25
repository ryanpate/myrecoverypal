# apps/accounts/username_generator.py
"""Generate friendly anonymous usernames for new signups.

The default username is intentionally not derived from the user's email
(privacy) and is intentionally human-readable rather than UUID-based
(less intimidating in the social feed).
"""
import random

from django.contrib.auth import get_user_model

User = get_user_model()

WORDLIST = [
    'Friend',
    'NewMember',
    'Recovering',
    'Hopeful',
    'Brave',
    'Strong',
    'Anchored',
    'Steady',
    'Rising',
    'OneDay',
]

MAX_ATTEMPTS = 10


def generate_unique_username() -> str:
    """Return a unique username like 'Friend1234'.

    Tries a wordlist + 4-digit suffix up to MAX_ATTEMPTS times. Falls back to
    an extended 8-digit numeric suffix on persistent collision (vanishingly
    unlikely under normal load; this branch exists for test determinism and
    pathological collision scenarios).
    """
    for _ in range(MAX_ATTEMPTS):
        word = random.choice(WORDLIST)
        suffix = random.randint(1000, 9999)
        candidate = f'{word}{suffix}'
        if not User.objects.filter(username=candidate).exists():
            return candidate

    # Pathological collision case — extend suffix
    while True:
        candidate = f'Friend{random.randint(10_000_000, 99_999_999)}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
