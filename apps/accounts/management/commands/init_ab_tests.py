"""
Management command to initialize A/B tests for MyRecoveryPal.

Usage:
    python manage.py init_ab_tests

This will create the default onboarding A/B test with control and variant groups.
"""

from django.core.management.base import BaseCommand
from apps.accounts.ab_testing import ABTestingService


class Command(BaseCommand):
    help = 'Initialize A/B tests for the application'

    def handle(self, *args, **options):
        self.stdout.write('Initializing A/B tests...\n')

        # Create the onboarding flow A/B test
        test = ABTestingService.create_onboarding_test()

        if test:
            variants = test.variants.all()
            self.stdout.write(self.style.SUCCESS(
                f'Created/Found A/B test: "{test.name}"'
            ))
            self.stdout.write(f'  Description: {test.description}')
            self.stdout.write(f'  Status: {"Active" if test.is_active else "Inactive"}')
            self.stdout.write(f'  Traffic: {test.traffic_percentage}%')
            self.stdout.write(f'  Variants: {variants.count()}')

            for variant in variants:
                self.stdout.write(f'    - {variant.name}: {variant.description}')
                if variant.config:
                    self.stdout.write(f'      Config: {variant.config}')

        self.stdout.write(self.style.SUCCESS('\nA/B tests initialized successfully!'))
        self.stdout.write('View results at: /admin/dashboard/ab-tests/')
