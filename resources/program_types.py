"""Building blocks for guided programs: Program, Lesson, Action and the
L()/A() helpers. Kept separate from resources/programs.py so track modules
can import them without a circular import.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple

FREE_DAYS = 7


@dataclass(frozen=True)
class Action:
    label: str
    url_name: str
    args: Tuple = ()
    # Shown under the button: what to actually do there.
    detail: str = ''


@dataclass(frozen=True)
class Lesson:
    title: str
    paragraphs: Tuple[str, ...]
    action: Optional[Action]
    prompt: str
    # Filled in by Program.__post_init__.
    day: int = 0


@dataclass(frozen=True)
class Program:
    slug: str
    title: str
    icon: str
    summary: str
    intro: str
    audience: str
    meta_description: str
    lessons: Tuple[Lesson, ...]
    weeks: Tuple[str, ...] = field(default=())
    free_days: int = FREE_DAYS
    kind: str = 'core'
    # Tracks only: what the track is about, e.g. 'Opioids'.
    substance: str = ''
    # ((label, number), ...) shown on the overview and lesson pages.
    helplines: Tuple[Tuple[str, str], ...] = field(default=())

    def __post_init__(self):
        numbered = tuple(
            Lesson(l.title, l.paragraphs, l.action, l.prompt, day=i)
            for i, l in enumerate(self.lessons, start=1))
        object.__setattr__(self, 'lessons', numbered)

    @property
    def length(self):
        return len(self.lessons)

    @property
    def helpline_rows(self):
        """[(label, display, tel_digits)]: keypad letters become digits for tel: links."""
        keypad = {c: d for d, letters in {
            '2': 'ABC', '3': 'DEF', '4': 'GHI', '5': 'JKL', '6': 'MNO',
            '7': 'PQRS', '8': 'TUV', '9': 'WXYZ'}.items() for c in letters}
        return [(label, number, ''.join(keypad.get(c, c) for c in number.upper() if c.isalnum()))
                for label, number in self.helplines]

    def lesson(self, day):
        if 1 <= day <= len(self.lessons):
            return self.lessons[day - 1]
        return None

    def week_title(self, day):
        index = (day - 1) // 7
        return self.weeks[index] if index < len(self.weeks) else 'Moving forward'


def L(title, paragraphs, action, prompt):
    return Lesson(title=title, paragraphs=tuple(paragraphs), action=action, prompt=prompt)


A = Action
