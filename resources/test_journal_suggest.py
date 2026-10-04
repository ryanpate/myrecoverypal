"""After a journal entry: a related worksheet, or crisis resources."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.journal.models import JournalEntry
from resources.journal_suggest import FRESH_FOR, RULES, suggestion_for
from resources.worksheets import get_worksheet

User = get_user_model()


def entry(user, content, title='', **kw):
    return JournalEntry.objects.create(user=user, title=title, content=content, **kw)


class SuggestionRuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('writer', 'w@example.com', 'pw-12345!')

    def slug(self, content, **kw):
        s = suggestion_for(entry(self.user, content, **kw))
        return s and (s['kind'] if s['kind'] == 'crisis' else s['worksheet'].slug)

    def test_every_rule_points_at_a_real_worksheet(self):
        for slug, _, _ in RULES:
            self.assertIsNotNone(get_worksheet(slug), slug)

    def test_matches(self):
        self.assertEqual(self.slug('The cravings were bad after work.'), 'urge-log')
        self.assertEqual(self.slug('I still resent my dad for that.'), 'abc-thought-record')
        self.assertEqual(self.slug('Big argument with my sister.'), 'trigger-map')
        self.assertEqual(self.slug('So bored and lonely tonight.'), 'lifestyle-balance-wheel')
        self.assertEqual(self.slug('Part of me misses it. Just one would be fine?'), 'cost-benefit-analysis')
        self.assertEqual(self.slug('Trying to work out my purpose.'), 'values-compass')

    def test_fallbacks(self):
        self.assertEqual(self.slug('A quiet day.', cravings_today=True), 'urge-log')
        self.assertEqual(self.slug('A quiet day.', mood_rating=2), 'abc-thought-record')
        self.assertEqual(self.slug('A quiet day.', mood_rating=8), 'nightly-review')

    def test_crisis_language_wins(self):
        self.assertEqual(self.slug('Cravings all day and I want to die.'), 'crisis')
        self.assertEqual(self.slug('Thinking about self-harm again.'), 'crisis')

    def test_old_entry_gets_no_worksheet_but_still_crisis(self):
        later = timezone.now() + FRESH_FOR + timedelta(minutes=1)
        self.assertIsNone(suggestion_for(entry(self.user, 'Cravings were bad.'), now=later))
        self.assertEqual(suggestion_for(entry(self.user, 'I want to end my life.'), now=later),
                         {'kind': 'crisis'})


@override_settings(PREPEND_WWW=False, SECURE_SSL_REDIRECT=False)
class EntryDetailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('writer', 'w@example.com', 'pw-12345!')
        self.client.force_login(self.user)

    def get(self, e):
        return self.client.get(reverse('journal:entry_detail', args=[e.pk]))

    def test_worksheet_card(self):
        r = self.get(entry(self.user, 'I resent how that meeting went.'))
        self.assertContains(r, reverse('resources:worksheet_detail', args=['abc-thought-record']))
        self.assertContains(r, 'Only you can see this suggestion')
        self.assertNotContains(r, 'tel:988')

    def test_crisis_card(self):
        r = self.get(entry(self.user, 'Some days I feel better off dead.'))
        self.assertContains(r, 'tel:988')
        self.assertContains(r, reverse('core:craving_sos'))
        self.assertNotContains(r, 'Only you can see this suggestion')

    def test_reason_never_quotes_the_entry(self):
        secret = 'cravings near the Blue Lantern bar on 5th street'
        r = self.get(entry(self.user, secret))
        self.assertContains(r, 'Urge Log')
        # The entry body appears once (in the entry itself), never in the card.
        self.assertEqual(r.content.decode().count('Blue Lantern'), 1)

    def test_other_members_cannot_see_entry_or_suggestion(self):
        e = entry(self.user, 'I want to die.')
        other = User.objects.create_user('other', 'o@example.com', 'pw-12345!')
        self.client.force_login(other)
        self.assertEqual(self.get(e).status_code, 404)

    def test_entry_itself_renders(self):
        r = self.get(entry(self.user, 'A quiet, good day.', title='Sunday'))
        self.assertContains(r, 'A quiet, good day.')
        self.assertContains(r, 'Sunday')
