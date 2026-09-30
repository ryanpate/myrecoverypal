import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Post bodies are written by any logged-in member in a rich-text editor, so
# they are untrusted HTML. nh3's default allowlist drops <script>, <style>,
# <iframe>, forms, event-handler attributes and javascript: URLs; on top of it
# we keep `class` (pasted/seeded formatting) and link targets.
_ATTRIBUTES = {tag: set(attrs) | {'class'} for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()}
for _tag in nh3.ALLOWED_TAGS:
    _ATTRIBUTES.setdefault(_tag, {'class'})
_ATTRIBUTES['a'] |= {'target'}


@register.filter
def sanitize_html(value):
    return mark_safe(nh3.clean(value or '', attributes=_ATTRIBUTES))
