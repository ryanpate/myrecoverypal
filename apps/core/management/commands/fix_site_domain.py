"""
Django management command to fix the Site model domain.
This fixes the issue where sitemaps show example.com instead of the actual domain.
Usage: python manage.py fix_site_domain
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = 'Fixes the Site model domain to use the correct production domain'

    def add_arguments(self, parser):
        parser.add_argument(
            '--domain',
            type=str,
            default=None,
            help='Domain to set (default: from settings.SITE_URL)',
        )

    def handle(self, *args, **options):
        # Get domain from argument or settings
        if options['domain']:
            domain = options['domain']
        else:
            site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')
            # Extract domain from SITE_URL
            domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')

        self.stdout.write(f'Setting site domain to: {domain}')

        try:
            # Get or create the site (SITE_ID = 1)
            site, created = Site.objects.get_or_create(
                pk=settings.SITE_ID,
                defaults={
                    'domain': domain,
                    'name': 'MyRecoveryPal'
                }
            )

            if not created:
                # Update existing site
                site.domain = domain
                site.name = 'MyRecoveryPal'
                site.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Updated Site domain from "{site.domain}" to "{domain}"')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created new Site with domain "{domain}"')
                )

            self.stdout.write('\nSite configuration:')
            self.stdout.write(f'  ID: {site.pk}')
            self.stdout.write(f'  Domain: {site.domain}')
            self.stdout.write(f'  Name: {site.name}')

            self.stdout.write('\n' + self.style.SUCCESS('Site domain fixed successfully!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Visit https://myrecoverypal.com/sitemap.xml to verify')
            self.stdout.write('2. Resubmit sitemap to Google Search Console')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating site domain: {e}')
            )
