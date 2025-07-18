# Create this file: resources/management/commands/create_coping_skills.py

from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceCategory, ResourceType


class Command(BaseCommand):
    help = 'Creates the Coping Skills for Cravings resource'

    def handle(self, *args, **options):
        # Get or create the tools category
        tools_category, _ = ResourceCategory.objects.get_or_create(
            slug='tools',
            defaults={
                'name': 'Recovery Tools',
                'description': 'Practical tools and worksheets to support your recovery journey',
                'icon': '🛠️',
                'order': 2,
                'is_active': True
            }
        )

        # Create resource types if they don't exist
        pdf_type, _ = ResourceType.objects.get_or_create(
            slug='pdf',
            defaults={
                'name': 'PDF Document',
                'color': '#EF4444',
                'icon': '📄'
            }
        )

        checklist_type, _ = ResourceType.objects.get_or_create(
            slug='checklist',
            defaults={
                'name': 'Interactive Checklist',
                'color': '#8B5CF6',
                'icon': '✅'
            }
        )

        # Create or update the coping skills resource
        coping_resource, created = Resource.objects.update_or_create(
            slug='coping-skills-for-cravings',
            defaults={
                'title': 'Coping Skills for Cravings',
                'category': tools_category,
                'resource_type': checklist_type,  # Primary type is checklist since it's hybrid
                'description': 'Evidence-based strategies to help you manage cravings in the moment. Available as both an interactive checklist and downloadable PDF.',
                'interaction_type': 'hybrid',
                'is_interactive': True,
                'interactive_component': 'CopingSkillsChecklist',
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'estimated_time': '5-10 minutes',
                'difficulty_level': 'beginner',
                'meta_description': 'Free coping skills checklist for addiction recovery. Evidence-based strategies to manage cravings including breathing techniques, mindfulness, and more.',
                'content': '''
                <h2>About This Resource</h2>
                <p>Cravings are a normal part of recovery. This resource provides 10 evidence-based strategies to help you manage cravings when they arise.</p>
                
                <h3>What's Included:</h3>
                <ul>
                    <li>10 proven coping strategies</li>
                    <li>Quick techniques (2-10 minutes each)</li>
                    <li>Interactive checklist to track what works for you</li>
                    <li>Downloadable PDF for offline use</li>
                </ul>
                
                <h3>How to Use:</h3>
                <p>When you experience a craving, open this resource and try one or more of the strategies. Use the interactive version to check off techniques as you try them, or download the PDF to keep with you.</p>
                '''
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                'Created "Coping Skills for Cravings" resource'))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Updated "Coping Skills for Cravings" resource'))

        # Also create other recovery tools
        self.stdout.write('\nCreating additional recovery tools...')

        # Daily Recovery Checklist
        daily_checklist, created = Resource.objects.update_or_create(
            slug='daily-recovery-checklist',
            defaults={
                'title': 'Daily Recovery Checklist',
                'category': tools_category,
                'resource_type': pdf_type,
                'description': 'A comprehensive daily checklist to help you establish healthy habits and maintain your recovery momentum.',
                'interaction_type': 'static',
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'estimated_time': '5 minutes',
                'difficulty_level': 'beginner'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                'Created "Daily Recovery Checklist"'))

        # List all resources in tools category
        self.stdout.write('\nResources in Recovery Tools category:')
        for resource in Resource.objects.filter(category=tools_category, is_active=True):
            self.stdout.write(
                f'  - {resource.title} ({resource.interaction_type})')
