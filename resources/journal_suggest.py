"""Suggest a worksheet after a journal entry (shown only to its author).

Privacy: journal entries are always private. The match runs on the server
at view time, against the entry's own text. Nothing about it is stored,
logged or sent to analytics, and the suggestion never quotes the entry.

Safety comes first: language about suicide or self-harm shows 988 and
Craving SOS instead of a worksheet, every time the author opens that entry.
A worksheet suggestion is shown only while the entry is fresh, so rereading
old entries doesn't keep nudging.
"""
import re
from datetime import timedelta

from django.utils import timezone

FRESH_FOR = timedelta(minutes=30)

CRISIS_PATTERNS = (
    r'suicid', r'kill myself', r'end my life', r'want to die', r'wanna die', r'end it all',
    r'better off dead', r'hurt myself', r'self[- ]?harm', r'overdos', r'no reason to live',
)

# (worksheet slug, why it fits, patterns). First match wins, so the order
# goes from the most specific need to the most general.
RULES = (
    ('urge-log', "Writing about a craving? The Urge Log helps you see what sets them off and what gets you through.",
     (r'crav', r'\burges?\b', r'want(ed)? to (drink|use)', r'relaps', r'\bslip(ped)?\b', r'close to using')),
    ('cost-benefit-analysis', "Feeling torn? A cost-benefit analysis lays both sides out on paper, where they're easier to weigh.",
     (r'miss (drinking|using|getting high)', r'just (one|once)', r'why bother', r'worth it', r'\bpart of me\b',
      r'not sure (i|if)')),
    ('trigger-map', "When a situation or a person keeps setting things off, a Trigger Map helps you plan around it.",
     (r'trigger', r'\bstress', r'argument', r'\bfight\b', r'\bparty\b', r'happy hour', r'payday', r'my ex\b')),
    ('abc-thought-record', "Heavy feelings like these often ride on a thought. A thought record helps you catch it and look again.",
     (r'\bang(ry|er)\b', r'resent', r'\bashamed\b', r'\bshame\b', r'guilt', r'worthless', r'failure',
      r'hate myself', r'anxious', r'anxiety', r'\bpanic', r'nobody cares')),
    ('lifestyle-balance-wheel', "Boredom, loneliness and burnout leave gaps. The Balance Wheel shows where your week needs filling.",
     (r'\bbored', r'lonely', r'loneliness', r'burn(ed|t)? ?out', r'exhausted', r'no time', r'empty')),
    ('values-compass', "Thinking about direction? The Values Compass helps you name what matters and take one step toward it.",
     (r'purpose', r'meaning', r'who i want to be', r'\bvalues?\b', r'direction', r'\blost\b')),
)


def _text(entry):
    return ' '.join(filter(None, [entry.title, entry.content, entry.tags])).lower()


def _matches(text, patterns):
    return any(re.search(p, text) for p in patterns)


def suggestion_for(entry, now=None):
    """None, {'kind': 'crisis'}, or {'kind': 'worksheet', 'worksheet': ..., 'reason': ...}."""
    from .worksheets import get_worksheet
    text = _text(entry)
    if _matches(text, CRISIS_PATTERNS):
        return {'kind': 'crisis'}
    if (now or timezone.now()) - entry.created_at > FRESH_FOR:
        return None
    for slug, reason, patterns in RULES:
        if _matches(text, patterns):
            return {'kind': 'worksheet', 'worksheet': get_worksheet(slug), 'reason': reason}
    if entry.cravings_today:
        return {'kind': 'worksheet', 'worksheet': get_worksheet('urge-log'), 'reason': RULES[0][1]}
    if entry.mood_rating is not None and entry.mood_rating <= 3:
        return {'kind': 'worksheet', 'worksheet': get_worksheet('abc-thought-record'), 'reason': RULES[3][1]}
    return {'kind': 'worksheet', 'worksheet': get_worksheet('nightly-review'),
            'reason': "Want to build on this? The Nightly Review turns a few minutes of reflection into a daily habit."}
