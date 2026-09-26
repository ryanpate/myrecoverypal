"""Delete vulnerability-scanner probes from the coverage-gap table.

93 of the first 113 rows were SQL-injection probes ("union all select ...").
The rule is frozen here (migrations must not depend on code that can change);
apps.support_services.coverage.is_plausible_query applies the same rule to new
searches.
"""
import re

from django.db import migrations

ALLOWED_RE = re.compile(r"^[\w\s,.'’#&/:-]+$")
SQL_RE = re.compile(
    r"(--|/\*|\b(select|union|insert|update|delete|drop|sleep|benchmark|extractvalue|"
    r"updatexml|concat|waitfor|information_schema|order\s+by|null)\b)",
    re.IGNORECASE)


def _plausible(query):
    q = (query or '').strip().lower()
    if not q or not ALLOWED_RE.match(q) or SQL_RE.search(q):
        return False
    compact = q.replace(' ', '').replace('-', '')
    return not (compact.isdigit() and len(compact) not in (5, 9))


def purge(apps, schema_editor):
    CoverageRequest = apps.get_model('support_services', 'CoverageRequest')
    junk = [r.pk for r in CoverageRequest.objects.only('pk', 'query') if not _plausible(r.query)]
    CoverageRequest.objects.filter(pk__in=junk).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('support_services', '0005_widen_conference_url'),
    ]

    operations = [
        migrations.RunPython(purge, migrations.RunPython.noop),
    ]
