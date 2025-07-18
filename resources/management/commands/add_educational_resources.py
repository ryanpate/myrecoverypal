# Create this file: resources/management/commands/add_educational_resources.py

from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceCategory, ResourceType

class Command(BaseCommand):
    help = 'Creates the Educational Resources page'

    def handle(self, *args, **options):
        # Get or create the educational category
        educational_category, created = ResourceCategory.objects.get_or_create(
            slug='educational',
            defaults={
                'name': 'Educational Materials',
                'description': 'Learn about addiction, recovery, and support strategies',
                'icon': '📚',
                'order': 1,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created "Educational Materials" category'))
        else:
            self.stdout.write(self.style.SUCCESS('Found existing "Educational Materials" category'))
        
        # Create or get the article type
        article_type, _ = ResourceType.objects.get_or_create(
            slug='article',
            defaults={
                'name': 'Article',
                'color': '#059669',
                'icon': '📰'
            }
        )
        
        # Create the educational resources page
        educational_resource, created = Resource.objects.update_or_create(
            slug='comprehensive-educational-resources',
            defaults={
                'title': 'Comprehensive Educational Resources',
                'category': educational_category,
                'resource_type': article_type,
                'description': 'Curated collection of websites, podcasts, books, and support resources for people in recovery and their loved ones.',
                'interaction_type': 'static',
                'is_interactive': False,
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'meta_description': 'Free educational resources for addiction recovery including websites, podcasts, books, and support groups for individuals and families.',
                'content': '''
                <p>This comprehensive guide provides carefully curated resources for both individuals in recovery and their support network. All resources are evidence-based and recommended by recovery professionals.</p>
                '''
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created "Comprehensive Educational Resources"'))
        else:
            self.stdout.write(self.style.SUCCESS('Updated "Comprehensive Educational Resources"'))
        
        # List all resources in educational category
        self.stdout.write('\nResources in Educational Materials category:')
        for resource in Resource.objects.filter(category=educational_category, is_active=True):
            self.stdout.write(f'  - {resource.title}')