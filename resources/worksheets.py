"""Interactive recovery worksheet definitions.

Worksheets are defined in code (not the database) so the wording is reviewed
in pull requests like any other copy. Each worksheet is a list of sections,
and each section a list of fields. A saved answer set lives in
`WorksheetEntry.data`, keyed by field key.

Field types:
    text      single line, up to TEXT_MAX characters
    textarea  multi-line, up to TEXTAREA_MAX characters
    scale     whole number 0-10

Access: anyone can read a worksheet, fill it in on screen, print it, or
download the blank PDF. Saving, the filled-in PDF, and "Discuss with Anchor"
are Premium (see worksheet_views.py).

The exercises are long-standing, widely taught CBT / motivational tools
(decisional balance, ABC thought records, urge logs, values work, a nightly
review). All copy here is original to MyRecoveryPal; don't paste text from
other programs' worksheets, which are copyrighted.
"""
from dataclasses import dataclass, field
from typing import List, Optional

TEXT_MAX = 300
TEXTAREA_MAX = 5000


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    type: str = 'textarea'
    help: str = ''
    placeholder: str = ''
    # Scale anchors, shown under 0 and 10.
    low: str = ''
    high: str = ''
    # Taller boxes on screen and more writing room in the printed PDF.
    rows: int = 4


@dataclass(frozen=True)
class Section:
    title: str
    fields: List[Field]
    intro: str = ''
    # 2 lays fields out side by side on wide screens and in the PDF.
    columns: int = 1


@dataclass(frozen=True)
class Worksheet:
    slug: str
    title: str
    icon: str
    summary: str
    intro: str
    time: str
    when_to_use: str
    sections: List[Section]
    meta_description: str
    # Field whose answer names a saved entry in lists ("Urge log - Friday").
    title_field: Optional[str] = None
    tip: str = ''
    fields_by_key: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        for section in self.sections:
            for f in section.fields:
                if f.key in self.fields_by_key:
                    raise ValueError(f'Duplicate field key {f.key!r} in {self.slug}')
                self.fields_by_key[f.key] = f

    @property
    def fields(self):
        return list(self.fields_by_key.values())


def _scale(key, label, low, high, help=''):
    return Field(key=key, label=label, type='scale', low=low, high=high, help=help)


WORKSHEETS = [
    Worksheet(
        slug='cost-benefit-analysis',
        title='Cost-Benefit Analysis',
        icon='⚖️',
        summary='Weigh what using gives you against what it costs, so the decision is yours and not the craving\'s.',
        intro=(
            'Part of you wants to change and part of you doesn\'t. That\'s normal, and '
            'pretending the "pros" of using don\'t exist rarely works. This exercise puts '
            'both sides on paper, including the honest benefits of using and the real '
            'costs of quitting, so you can see the whole picture in one place.'
        ),
        time='10-15 minutes',
        when_to_use='When you feel stuck or torn, or when "just one" starts sounding reasonable.',
        meta_description=(
            'Free cost-benefit analysis worksheet for addiction recovery. Weigh the pros '
            'and cons of using vs. staying sober. Fill it in online or print the PDF.'
        ),
        title_field='change',
        tip='Come back to this one when your motivation dips. Re-reading your own words is powerful.',
        sections=[
            Section('The decision', [
                Field('change', 'What change are you weighing?', type='text',
                      placeholder='e.g. Quitting drinking, staying off pills, not gambling this month'),
            ]),
            Section('Four boxes', columns=2, intro='Be honest in every box. There are no wrong answers.', fields=[
                Field('benefits_using', 'Benefits of using',
                      help='What does it give you, even short-term? Relief, sleep, confidence, fun?', rows=5),
                Field('costs_using', 'Costs of using',
                      help='Health, money, relationships, work, self-respect, legal trouble.', rows=5),
                Field('benefits_stopping', 'Benefits of staying sober',
                      help='What gets better? What becomes possible?', rows=5),
                Field('costs_stopping', 'Costs of staying sober',
                      help='What will be hard or what will you lose? Friends, a way to cope, routines?', rows=5),
            ]),
            Section('What it adds up to', [
                Field('takeaway', 'Looking at all four boxes, what stands out?'),
                _scale('importance', 'How important is this change to you right now?',
                       'Not important', 'Most important thing'),
                _scale('confidence', 'How confident are you that you can make it?',
                       'Not confident', 'Completely confident'),
                Field('raise_confidence', 'What would raise your confidence by one point?', rows=3),
            ]),
        ],
    ),
    Worksheet(
        slug='abc-thought-record',
        title='ABC Thought Record',
        icon='🧠',
        summary='Catch the thought between a trigger and a craving, then talk back to it.',
        intro=(
            'It usually isn\'t the event that sends us toward using; it\'s what we tell '
            'ourselves about it. This classic CBT exercise slows a moment down: the '
            'Activating event, the Beliefs it set off, and the Consequences. Then you '
            'Dispute the unhelpful thought and write a more Effective one.'
        ),
        time='10 minutes',
        when_to_use='After a moment that rattled you, while it\'s still fresh.',
        meta_description=(
            'Free ABC thought record worksheet for addiction recovery (CBT). Identify '
            'triggers, challenge unhelpful thoughts, and reduce cravings. Fill in online or print.'
        ),
        title_field='activating_event',
        sections=[
            Section('A: Activating event', [
                Field('activating_event', 'What happened?', type='text',
                      help='Just the facts, like a camera would record it.',
                      placeholder='e.g. My boss criticized my report in front of the team'),
            ]),
            Section('B: Beliefs', [
                Field('beliefs', 'What did you tell yourself about it?',
                      help='Write the thoughts word for word, e.g. "I always mess up. I deserve a drink after this."'),
            ]),
            Section('C: Consequences', [
                Field('consequences', 'How did you feel, and what did you want to do or actually do?'),
                _scale('emotion_before', 'How strong was the feeling?', 'Barely there', 'Overwhelming'),
                _scale('craving_before', 'How strong was the urge to use?', 'None', 'Intense'),
            ]),
            Section('D: Dispute', intro='Question the belief the way a good friend would.', fields=[
                Field('dispute', 'Is the thought 100% true? Is it helpful? What would you tell a friend who thought this?',
                      rows=5),
            ]),
            Section('E: Effective new thought', [
                Field('effective_belief', 'What is a more balanced, helpful way to see it?'),
                _scale('emotion_after', 'How strong is the feeling now?', 'Barely there', 'Overwhelming'),
                _scale('craving_after', 'How strong is the urge now?', 'None', 'Intense'),
            ]),
        ],
    ),
    Worksheet(
        slug='urge-log',
        title='Urge Log',
        icon='🌊',
        summary='Record a craving from start to finish and learn your own patterns.',
        intro=(
            'Every craving you ride out without using teaches you that urges rise, peak, '
            'and pass. Logging them turns each one into data: when they hit, what sets '
            'them off, and which responses actually work for you. Keep a new log for '
            'each urge; patterns show up after a week or two.'
        ),
        time='3-5 minutes',
        when_to_use='During or right after a craving.',
        meta_description=(
            'Free urge log / craving log worksheet for recovery. Track cravings, triggers '
            'and what worked so you can spot patterns. Fill in online or print.'
        ),
        title_field='when',
        tip='Hit a craving right now? The Craving SOS page has breathing and urge-surfing tools.',
        sections=[
            Section('The urge', [
                Field('when', 'When did it happen?', type='text', placeholder='e.g. Friday 6pm, driving home'),
                Field('where_who', 'Where were you, and who were you with?', type='text'),
                Field('trigger', 'What set it off?',
                      help='A place, person, feeling, time of day, smell, memory, argument?', rows=3),
                _scale('intensity_start', 'Intensity at its peak', 'Mild', 'Unbearable'),
            ]),
            Section('Riding it out', [
                Field('response', 'What did you do instead of using?', rows=3),
                Field('duration', 'How long did it last?', type='text', placeholder='e.g. About 20 minutes'),
                _scale('intensity_end', 'Intensity afterwards', 'Gone', 'Unbearable'),
            ]),
            Section('What you learned', [
                Field('learned', 'What would you do the same or differently next time?', rows=3),
            ]),
        ],
    ),
    Worksheet(
        slug='trigger-map',
        title='Trigger Map',
        icon='🗺️',
        summary='Map the people, places, feelings and times that put your recovery at risk, and plan for the big ones.',
        intro=(
            'Triggers lose a lot of their power once you can see them coming. Work '
            'through each category below, then pick your three highest-risk triggers '
            'and decide in advance whether you\'ll avoid, change, or cope with each one.'
        ),
        time='15-20 minutes',
        when_to_use='Early in recovery, and again whenever your life changes (new job, move, breakup).',
        meta_description=(
            'Free trigger identification worksheet for addiction recovery. Map people, places, '
            'feelings and times that trigger cravings, and plan for each. Fill in online or print.'
        ),
        sections=[
            Section('Your triggers', columns=2, fields=[
                Field('people', 'People', help='Who do you associate with using?', rows=3),
                Field('places', 'Places', help='Bars, a friend\'s house, a route home, the couch?', rows=3),
                Field('things', 'Things and situations',
                      help='Payday, parties, sports, being alone, certain music?', rows=3),
                Field('feelings', 'Feelings', help='Stress, boredom, loneliness, celebration, shame?', rows=3),
                Field('times', 'Times', help='Times of day, days of the week, holidays, anniversaries.', rows=3),
                Field('body', 'Physical states', help='Pain, poor sleep, hunger, exhaustion, illness.', rows=3),
            ]),
            Section('Your three highest-risk triggers',
                    intro='For each one: can you avoid it, change it, or do you need a plan to cope with it?',
                    fields=[
                        Field('top_1', 'Trigger #1 and my plan', rows=3),
                        Field('top_2', 'Trigger #2 and my plan', rows=3),
                        Field('top_3', 'Trigger #3 and my plan', rows=3),
                    ]),
            Section('Backup', [
                Field('call_list', 'Who will you call or text if a trigger catches you off guard?', type='text'),
            ]),
        ],
    ),
    Worksheet(
        slug='values-compass',
        title='Values Compass',
        icon='🧭',
        summary='Name what matters most to you and check whether your days point that way.',
        intro=(
            'Recovery sticks when it\'s about moving toward something, not just away '
            'from a substance. Your values are what you want your life to stand for. '
            'Here you\'ll name your top five, look honestly at how using fit with them, '
            'and pick one small action for this week.'
        ),
        time='15 minutes',
        when_to_use='When recovery feels like a list of "don\'ts" and you need a "why".',
        meta_description=(
            'Free values worksheet for addiction recovery. Identify your core values, see how '
            'using conflicted with them, and plan values-based actions. Fill in online or print.'
        ),
        sections=[
            Section('Your top five values',
                    intro='Examples: family, honesty, health, faith, freedom, creativity, '
                          'loyalty, adventure, learning, service, respect, security.',
                    fields=[
                        Field('value_1', '1 (most important)', type='text'),
                        Field('value_2', '2', type='text'),
                        Field('value_3', '3', type='text'),
                        Field('value_4', '4', type='text'),
                        Field('value_5', '5', type='text'),
                    ]),
            Section('Honest look', [
                Field('using_vs_values', 'How did using pull you away from these values?'),
                Field('recovery_vs_values', 'How does recovery bring you closer to them?'),
                _scale('alignment', 'Right now, how closely does your daily life match your values?',
                       'Not at all', 'Completely'),
            ]),
            Section('This week', [
                Field('action', 'One small, specific action this week that honors your #1 value', rows=3,
                      placeholder='e.g. Phone my sister on Sunday and actually listen'),
            ]),
        ],
    ),
    Worksheet(
        slug='lifestyle-balance-wheel',
        title='Lifestyle Balance Wheel',
        icon='🎡',
        summary='Rate eight areas of your life to see where recovery needs support next.',
        intro=(
            'Stopping is the first step; building a life you don\'t want to escape from '
            'is what keeps you there. Rate how satisfied you are with each area of your '
            'life today, then choose one low-scoring area to nudge up a little.'
        ),
        time='10 minutes',
        when_to_use='Monthly. Comparing your wheels over time shows your progress.',
        meta_description=(
            'Free lifestyle balance wheel worksheet for recovery. Rate health, relationships, '
            'work, money, fun and more to find what to work on next. Fill in online or print.'
        ),
        sections=[
            Section('Rate your satisfaction with each area', intro='0 = very unsatisfied, 10 = completely satisfied.',
                    columns=2, fields=[
                        _scale('physical', 'Physical health', 'Unsatisfied', 'Satisfied'),
                        _scale('emotional', 'Emotional & mental health', 'Unsatisfied', 'Satisfied'),
                        _scale('relationships', 'Family & relationships', 'Unsatisfied', 'Satisfied'),
                        _scale('social', 'Friends & social life', 'Unsatisfied', 'Satisfied'),
                        _scale('work', 'Work, school or purpose', 'Unsatisfied', 'Satisfied'),
                        _scale('finances', 'Money', 'Unsatisfied', 'Satisfied'),
                        _scale('fun', 'Fun & recreation', 'Unsatisfied', 'Satisfied'),
                        _scale('meaning', 'Spirituality or meaning', 'Unsatisfied', 'Satisfied'),
                    ]),
            Section('Next step', [
                Field('lowest', 'Which area would make the biggest difference if it improved?', type='text'),
                Field('step', 'One small step you\'ll take in that area in the next 7 days', rows=3),
                Field('support', 'Who or what could help you with it?', type='text'),
            ]),
        ],
    ),
    Worksheet(
        slug='nightly-review',
        title='Nightly Review',
        icon='🌙',
        summary='A five-minute end-of-day inventory: what went well, where you slipped from your values, and tomorrow.',
        intro=(
            'Many people in recovery close each day with a short, honest review, '
            'sometimes called a daily or 10th-step inventory. It isn\'t about beating '
            'yourself up. It\'s about noticing, putting things right quickly, and going '
            'to bed with a clear head.'
        ),
        time='5 minutes',
        when_to_use='Every evening, ideally before bed.',
        meta_description=(
            'Free nightly review / daily inventory worksheet for recovery (10th step style). '
            'Reflect on your day, gratitude, and tomorrow. Fill in online or print.'
        ),
        title_field='date',
        sections=[
            Section('Today', [
                Field('date', 'Date', type='text'),
                Field('went_well', 'What went well today? What are you proud of?', rows=3),
                Field('fell_short', 'Where did you fall short of your values? Were you resentful, '
                                    'dishonest, selfish, or afraid?', rows=3),
                Field('amends', 'Do you owe anyone an apology or a phone call?', type='text'),
                Field('grateful', 'Three things you\'re grateful for', rows=3),
            ]),
            Section('Tomorrow', [
                Field('tomorrow', 'What will you do differently, or keep doing, tomorrow?', rows=3),
                _scale('day_rating', 'How was today overall?', 'Really hard', 'Great day'),
            ]),
        ],
    ),
]

WORKSHEETS_BY_SLUG = {w.slug: w for w in WORKSHEETS}


def get_worksheet(slug):
    return WORKSHEETS_BY_SLUG.get(slug)


def clean_answers(worksheet, post):
    """Pull this worksheet's answers out of a POST dict.

    Unknown keys are ignored, text is stripped and length-capped, and scales
    are clamped to 0-10. Blank answers are dropped, so an all-blank
    submission returns {}.
    """
    data = {}
    for f in worksheet.fields:
        raw = (post.get(f.key) or '').strip()
        if not raw:
            continue
        if f.type == 'scale':
            try:
                n = int(raw)
            except ValueError:
                continue
            data[f.key] = max(0, min(10, n))
        elif f.type == 'text':
            data[f.key] = raw[:TEXT_MAX]
        else:
            data[f.key] = raw[:TEXTAREA_MAX]
    return data


def build_sections(worksheet, data=None):
    """Sections with each field's saved value attached, ready for templates."""
    data = data or {}
    out = []
    for section in worksheet.sections:
        fields = []
        for f in section.fields:
            fields.append({
                'key': f.key, 'label': f.label, 'type': f.type, 'help': f.help,
                'placeholder': f.placeholder, 'low': f.low, 'high': f.high,
                'rows': f.rows, 'value': data.get(f.key, ''),
                # Writing room in the blank PDF (~18pt per line).
                'box_height_pt': f.rows * 18,
            })
        out.append({'title': section.title, 'intro': section.intro,
                    'columns': section.columns, 'fields': fields})
    return out


def answers_as_text(worksheet, data):
    """Plain-text rendering of a filled worksheet (for Anchor)."""
    lines = []
    for f in worksheet.fields:
        if f.key not in data:
            continue
        value = data[f.key]
        if f.type == 'scale':
            value = f'{value}/10'
        lines.append(f'{f.label}\n{value}')
    return '\n\n'.join(lines)
