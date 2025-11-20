from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """
        This method is called when Django starts.
        We use it to automatically update the Site model domain.
        """
        # Only run this in production or when running the server
        # Skip during migrations, collectstatic, etc.
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            self.update_site_domain()

    def update_site_domain(self):
        """Automatically update the Site model with the correct domain"""
        try:
            from django.conf import settings
            from django.contrib.sites.models import Site

            # Get the site domain from settings
            site_url = getattr(settings, 'SITE_URL', 'https://myrecoverypal.com')
            domain = site_url.replace('https://', '').replace('http://', '').rstrip('/')

            # Update or create the site
            site, created = Site.objects.get_or_create(
                pk=getattr(settings, 'SITE_ID', 1),
                defaults={
                    'domain': domain,
                    'name': 'MyRecoveryPal'
                }
            )

            if not created and site.domain != domain:
                site.domain = domain
                site.name = 'MyRecoveryPal'
                site.save()
                print(f'✓ Updated Site domain to: {domain}')

        except Exception as e:
            # Don't crash if Site model isn't available yet
            # (e.g., during initial migrations)
            pass