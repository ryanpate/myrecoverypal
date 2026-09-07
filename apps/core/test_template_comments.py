"""No template may use a multi-line {# #} comment.

Django's {# #} comment is single-line only. A multi-line one is not parsed
as a comment at all — it renders as visible body text. This shipped twice:
once on the meeting finder and all 6,451 meeting detail pages, and once in
base.html where it would have appeared right after a signup or purchase.

Use {% comment %} ... {% endcomment %} for anything spanning lines.
"""
import os
import re

from django.test import TestCase

SKIP_DIRS = {'node_modules', '.git', 'venv', '.venv', 'ios', 'android',
             'staticfiles', '__pycache__'}


def _template_files():
    for root, dirs, files in os.walk(os.getcwd()):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith('.html'):
                yield os.path.join(root, f)


class MultiLineTemplateCommentTests(TestCase):
    def test_no_template_uses_a_multiline_hash_comment(self):
        offenders = []
        for path in _template_files():
            try:
                source = open(path, encoding='utf-8').read()
            except (OSError, UnicodeDecodeError):
                continue
            for match in re.finditer(r'\{#(.*?)#\}', source, re.S):
                if '\n' in match.group(1):
                    rel = os.path.relpath(path, os.getcwd())
                    offenders.append(f'{rel}: {match.group(0)[:60]!r}')
                    break
        self.assertEqual(
            offenders, [],
            'Multi-line {# #} renders as visible page text. Use '
            '{% comment %}...{% endcomment %}:\n  ' + '\n  '.join(offenders))
