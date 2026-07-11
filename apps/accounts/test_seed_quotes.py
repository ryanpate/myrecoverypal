"""Acceptance tests for the expanded daily-quote corpus."""
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.management.commands.seed_recovery_quotes import QUOTES
from apps.accounts.models import DailyRecoveryThought


class QuoteCorpusTests(TestCase):
    def test_corpus_has_365_entries(self):
        self.assertEqual(len(QUOTES), 365)

    def test_all_quotes_unique(self):
        texts = [q["quote"].strip().lower() for q in QUOTES]
        self.assertEqual(len(texts), len(set(texts)))

    def test_new_entries_all_have_prompts(self):
        # Entries beyond the original 108 must each carry a prompt.
        missing = [i for i, q in enumerate(QUOTES[108:], start=108)
                   if not q.get("prompt")]
        self.assertEqual(missing, [])

    def test_command_is_idempotent(self):
        call_command("seed_recovery_quotes", start_date="2030-01-01")
        first_count = DailyRecoveryThought.objects.count()
        call_command("seed_recovery_quotes", start_date="2030-01-01")
        self.assertEqual(DailyRecoveryThought.objects.count(), first_count)
        self.assertEqual(first_count, 365)
