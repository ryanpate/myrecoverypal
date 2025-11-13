"""
Django management command to generate a static sitemap.xml file.
Usage: python manage.py generate_sitemap
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.contrib.sitemaps import GenericSitemap
from django.urls import reverse
from django.utils import timezone
from recovery_hub.sitemaps import sitemaps
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Generates a static sitemap.xml file for search engines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='sitemap.xml',
            help='Output filename (default: sitemap.xml)',
        )

    def handle(self, *args, **options):
        output_file = options['output']

        # Determine output path - save to static root or project root
        if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
            output_path = os.path.join(settings.STATIC_ROOT, output_file)
        else:
            output_path = os.path.join(settings.BASE_DIR, output_file)

        self.stdout.write(f'Generating sitemap at: {output_path}')

        # Get site domain
        try:
            site = Site.objects.get_current()
            domain = site.domain
        except:
            domain = 'www.myrecoverypal.com'

        # Start building sitemap XML
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # Process each sitemap
        for sitemap_name, sitemap_class in sitemaps.items():
            self.stdout.write(f'Processing {sitemap_name} sitemap...')

            try:
                sitemap_instance = sitemap_class()
                items = sitemap_instance.items()

                for item in items:
                    try:
                        # Get location
                        location = sitemap_instance.location(item)
                        if not location.startswith('http'):
                            location = f'https://{domain}{location}'

                        # Get last modified date
                        if hasattr(sitemap_instance, 'lastmod'):
                            try:
                                lastmod = sitemap_instance.lastmod(item)
                                lastmod_str = lastmod.strftime('%Y-%m-%d') if lastmod else ''
                            except:
                                lastmod_str = timezone.now().strftime('%Y-%m-%d')
                        else:
                            lastmod_str = timezone.now().strftime('%Y-%m-%d')

                        # Get change frequency
                        changefreq = getattr(sitemap_instance, 'changefreq', 'weekly')
                        if callable(changefreq):
                            try:
                                changefreq = changefreq(item)
                            except:
                                changefreq = 'weekly'

                        # Get priority
                        if hasattr(sitemap_instance, 'priority'):
                            priority_attr = sitemap_instance.priority
                            if callable(priority_attr):
                                try:
                                    priority = priority_attr(item)
                                except:
                                    priority = 0.5
                            else:
                                priority = priority_attr
                        else:
                            priority = 0.5

                        # Add URL to sitemap
                        xml_content += '  <url>\n'
                        xml_content += f'    <loc>{location}</loc>\n'
                        if lastmod_str:
                            xml_content += f'    <lastmod>{lastmod_str}</lastmod>\n'
                        xml_content += f'    <changefreq>{changefreq}</changefreq>\n'
                        xml_content += f'    <priority>{priority:.1f}</priority>\n'
                        xml_content += '  </url>\n'

                        self.stdout.write(f'  Added: {location}')

                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'  Warning: Could not process item: {e}')
                        )
                        continue

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {sitemap_name}: {e}')
                )
                continue

        xml_content += '</urlset>\n'

        # Write to file
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully generated sitemap: {output_path}')
            )
            self.stdout.write(
                f'Total size: {len(xml_content)} bytes'
            )
            self.stdout.write(
                '\nNext steps:'
            )
            self.stdout.write(
                '1. Verify the sitemap is accessible at https://www.myrecoverypal.com/sitemap.xml'
            )
            self.stdout.write(
                '2. Submit the sitemap URL to Google Search Console'
            )
            self.stdout.write(
                '3. Run this command again whenever you add new pages or blog posts'
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error writing sitemap file: {e}')
            )
