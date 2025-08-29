from django.core.management.base import BaseCommand
from apps.support_services.models import SupportService

class Command(BaseCommand):
    help = 'Populate initial support services data'
    
    def handle(self, *args, **options):
        services = [
            {
                'service_id': 'samhsa-helpline',
                'name': 'SAMHSA National Helpline',
                'type': 'helpline',
                'category': 'national',
                'description': 'Free, confidential, 24/7 treatment referral and information service for individuals and families facing mental and/or substance use disorders.',
                'phone': '1-800-662-4357',
                'phone_display': '1-800-662-HELP (4357)',
                'text_support': 'Text ZIP to 435748 (HELP4U)',
                'website': 'https://www.samhsa.gov/find-help/national-helpline',
                'hours': '24/7/365',
                'languages': ['English', 'Spanish'],
                'services': [
                    'Treatment referrals',
                    'Support group information',
                    'Community-based organizations',
                    'Crisis support'
                ],
                'cost': 'free',
                'is_approved': True,
                'is_active': True,
                'is_featured': True,
            },
            {
                'service_id': '988-lifeline',
                'name': '988 Suicide & Crisis Lifeline',
                'type': 'helpline',
                'category': 'national',
                'description': 'The 988 Lifeline provides 24/7, free and confidential support for people in distress, prevention and crisis resources.',
                'phone': '988',
                'phone_display': '988',
                'text_support': 'Text 988',
                'chat_support': 'https://988lifeline.org/chat',
                'website': 'https://988lifeline.org',
                'hours': '24/7/365',
                'languages': ['English', 'Spanish'],
                'services': [
                    'Crisis counseling',
                    'Suicide prevention',
                    'Emotional support',
                    'Resource referrals'
                ],
                'cost': 'free',
                'is_approved': True,
                'is_active': True,
                'is_featured': True,
            },
            {
                'service_id': 'smart-recovery',
                'name': 'SMART Recovery',
                'type': 'support_group',
                'category': 'national',
                'organization': 'SMART Recovery International',
                'description': 'Self-Management and Recovery Training - science-based addiction recovery support groups.',
                'website': 'https://www.smartrecovery.org',
                'meeting_finder': 'https://meetings.smartrecovery.org',
                'services': [
                    'Online meetings',
                    'In-person meetings',
                    '24/7 online community',
                    'Recovery tools and worksheets'
                ],
                'approach': '4-Point Program, cognitive behavioral techniques',
                'cost': 'free',
                'formats': ['online', 'in-person', 'hybrid'],
                'is_approved': True,
                'is_active': True,
            },
        ]
        
        created = 0
        for service_data in services:
            service, was_created = SupportService.objects.get_or_create(
                service_id=service_data['service_id'],
                defaults=service_data
            )
            if was_created:
                created += 1
                self.stdout.write(f'Created: {service.name}')
            else:
                self.stdout.write(f'Already exists: {service.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created} services')
        )