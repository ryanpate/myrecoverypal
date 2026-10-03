"""Substance-specific program tracks: short companions to First 30 Days.

One module per track, each defining TRACK. They import A, L and Program
from resources.program_types.

Content rules (reviewed in PRs like all program copy): original writing
only; no medical advice, drug names or doses ("talk to a doctor" instead);
no statistics; the only phone numbers are the track's helplines (988,
SAMHSA 1-800-662-4357, 1-800-GAMBLER) and 911.
"""
TRACK_MODULES = ('alcohol', 'opioids', 'stimulants', 'cannabis', 'gambling')


def _load():
    from importlib import import_module
    return [import_module(f'{__name__}.{name}').TRACK for name in TRACK_MODULES]


TRACKS = _load()
