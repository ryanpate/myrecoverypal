"""Register the Printify order:shipment:created webhook for keepsake tracking emails.

Idempotent: does nothing if a webhook for that topic already points at our URL.
Requires PRINTIFY_API_KEY and PRINTIFY_WEBHOOK_SECRET in the environment.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from apps.accounts import printify

TOPIC = 'order:shipment:created'


class Command(BaseCommand):
    help = 'Register the Printify shipment webhook for medallion keepsakes.'

    def handle(self, *args, **options):
        if not settings.PRINTIFY_WEBHOOK_SECRET:
            raise CommandError('Set PRINTIFY_WEBHOOK_SECRET first.')
        url = settings.SITE_URL.rstrip('/') + reverse('accounts:printify_webhook')
        for hook in printify.list_webhooks():
            if hook.get('topic') == TOPIC and hook.get('url') == url:
                self.stdout.write(f'Already registered: {TOPIC} -> {url}')
                return
        hook = printify.create_webhook(TOPIC, url, settings.PRINTIFY_WEBHOOK_SECRET)
        self.stdout.write(self.style.SUCCESS(f'Registered {TOPIC} -> {hook.get("url", url)}'))
