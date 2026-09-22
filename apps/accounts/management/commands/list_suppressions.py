# apps/accounts/management/commands/list_suppressions.py
"""Print cold-outreach opt-outs, one address per line.

Outreach is sent from an external tool (Instantly/Smartlead/Apollo) against a
pasted list, so nothing in this codebase can filter the send. This command
exists to make scrubbing a list a copy-paste step instead of a memory step:

    python manage.py list_suppressions > optouts.txt
    grep -vixFf optouts.txt wave7.txt > wave7-clean.txt

Use grep's -i: the unsubscribe view lowercases what it stores, but addresses
added via the admin keep whatever case was typed.
"""
from django.core.management.base import BaseCommand

from apps.accounts.outreach_models import ColdOutreachSuppression


class Command(BaseCommand):
    help = 'Print cold-outreach opt-out addresses, one per line, for scrubbing an outreach list.'

    def handle(self, *args, **options):
        emails = (
            ColdOutreachSuppression.objects
            .order_by('email')
            .values_list('email', flat=True)
        )
        for email in emails:
            self.stdout.write(email)

        # Count goes to stderr so stdout stays pipeable. Without it an empty
        # result is invisible: `grep -vixFf` against an empty file passes the
        # whole list through, so a failed run looks just like a clean scrub.
        self.stderr.write(f'{len(emails)} opt-out(s)')
