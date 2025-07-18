# File: recovery-hub/resources/management/commands/add_recovery_journal.py

from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceCategory, ResourceType
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Add the 30-Day Recovery Journal as a featured resource'

    def handle(self, *args, **kwargs):
        # Get or create the Tools category
        tools_category, _ = ResourceCategory.objects.get_or_create(
            slug='tools',
            defaults={
                'name': 'Recovery Tools',
                'icon': '🛠️',
                'description': 'Practical worksheets, trackers, and exercises for daily recovery work',
                'order': 3
            }
        )

        # Get or create PDF Guide resource type
        pdf_type, _ = ResourceType.objects.get_or_create(
            slug='pdf-guide',
            defaults={
                'name': 'PDF Guide',
                'color': '#3B82F6'
            }
        )

        # Create the journal resource
        journal_resource, created = Resource.objects.get_or_create(
            slug='30-day-recovery-journal',
            defaults={
                'title': '30-Day Recovery Journal',
                'category': tools_category,
                'resource_type': pdf_type,
                'description': 'A comprehensive daily journal with prompts, quotes, and reflections to guide your first 30 days of recovery. Includes daily affirmations, gratitude lists, trigger logs, and meditation exercises.',
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'meta_description': 'Free 30-day recovery journal PDF with daily prompts, quotes, affirmations, and reflection questions to support your addiction recovery journey.'
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully created 30-Day Recovery Journal resource.\n'
                    'Please upload the PDF file through the admin panel.'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('30-Day Recovery Journal already exists.')
            )

        # Create sample content for the resource
        if not journal_resource.content:
            journal_resource.content = """## About This Journal

This 30-day recovery journal is designed to support you through your first month of recovery with daily structure and reflection. Each day includes:

### Daily Components:
- **Inspirational Quote**: Start each day with wisdom from recovery literature and thought leaders
- **Meditation Prompt**: Simple mindfulness exercises to center yourself
- **Reflection Question**: Thought-provoking questions to deepen self-awareness
- **Gratitude List**: Space to acknowledge the positive aspects of your life
- **Daily Affirmation**: Positive statements to reinforce your recovery
- **Trigger Log**: Track and understand your triggers and responses
- **Random Insight**: Creative prompts for additional reflection

### How to Use This Journal:
1. Set aside 10-15 minutes each day for journaling
2. Find a quiet, comfortable space
3. Be honest and compassionate with yourself
4. There are no right or wrong answers
5. Review your entries weekly to track patterns and progress

### Featured Quotes Include:
- "Progress, not perfection" - A core principle of recovery
- "One day at a time" - From the AA Serenity Prayer
- "Let go or be dragged" - AA Big Book wisdom
- And many more inspirational messages

This journal is completely free and designed to be a companion through your early recovery journey. Download it, print it, or fill it out digitally - whatever works best for you.

Remember: Recovery is a journey, not a destination. Be patient and kind with yourself."""
            journal_resource.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'\nResource details:\n'
                f'Title: {journal_resource.title}\n'
                f'Category: {journal_resource.category}\n'
                f'Type: {journal_resource.resource_type}\n'
                f'Access Level: {journal_resource.access_level}\n'
                f'Featured: {journal_resource.featured}\n'
                f'URL: /resources/resource/30-day-recovery-journal/'
            )
        )
