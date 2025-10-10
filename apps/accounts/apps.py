from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts'
    
    def ready(self):
        import apps.accounts.signals
        
        from django.conf import settings
        logger = logging.getLogger('apps.accounts')

        logger.info('='*70)
        logger.info('📧 EMAIL CONFIGURATION ON STARTUP')
        logger.info('='*70)
        logger.info(f'Backend: {settings.EMAIL_BACKEND}')
        logger.info(f'Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        logger.info(f'TLS: {settings.EMAIL_USE_TLS}')
        logger.info(f'User: {settings.EMAIL_HOST_USER}')
        logger.info(
            f'Password Set: {"YES ✓" if settings.EMAIL_HOST_PASSWORD else "NO ✗ MISSING!"}')
        logger.info(f'From: {settings.DEFAULT_FROM_EMAIL}')
        logger.info(f'Site URL: {settings.SITE_URL}')
        logger.info('='*70)
