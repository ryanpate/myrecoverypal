from django.core.management.base import BaseCommand
from apps.journal.models import JournalPrompt

class Command(BaseCommand):
    help = 'Creates sample journal prompts for different recovery stages'

    def handle(self, *args, **kwargs):
        prompts = [
            # Gratitude prompts
            {
                'title': 'Three Things',
                'prompt': 'What are three things you\'re grateful for today?',
                'category': 'gratitude',
                'stage': 'all',
                'follow_up_1': 'Why are these things meaningful to you?',
                'follow_up_2': 'How can you show appreciation for these things?',
            },
            {
                'title': 'Recovery Gratitude',
                'prompt': 'What aspect of your recovery are you most grateful for today?',
                'category': 'gratitude',
                'stage': 'all',
                'min_days_sober': 1,
            },
            
            # Early recovery prompts (0-30 days)
            {
                'title': 'Day One Reflection',
                'prompt': 'Today marks the beginning of your recovery journey. What brought you here? What do you hope to achieve?',
                'category': 'reflection',
                'stage': 'early',
                'min_days_sober': 0,
                'max_days_sober': 1,
            },
            {
                'title': 'First Week Check-in',
                'prompt': 'You\'ve made it through your first week. What has been the most challenging part? What has surprised you?',
                'category': 'reflection',
                'stage': 'early',
                'min_days_sober': 7,
                'max_days_sober': 7,
            },
            {
                'title': 'Trigger Identification',
                'prompt': 'What situations, people, or feelings have triggered cravings today? How did you handle them?',
                'category': 'triggers',
                'stage': 'early',
                'follow_up_1': 'What coping strategies worked best?',
                'follow_up_2': 'What will you do differently next time?',
            },
            {
                'title': 'Support System',
                'prompt': 'Who are the people supporting your recovery? How can you strengthen these relationships?',
                'category': 'relationships',
                'stage': 'early',
            },
            
            # Sustained recovery prompts (31-365 days)
            {
                'title': 'Monthly Milestone',
                'prompt': 'You\'ve completed another month of recovery. What positive changes have you noticed in yourself?',
                'category': 'milestones',
                'stage': 'middle',
                'min_days_sober': 30,
            },
            {
                'title': 'New Habits',
                'prompt': 'What healthy habits have you developed in recovery? Which ones do you want to strengthen?',
                'category': 'self_care',
                'stage': 'middle',
                'min_days_sober': 60,
            },
            {
                'title': 'Emotional Growth',
                'prompt': 'How has your emotional awareness changed since beginning recovery? What emotions are you better at handling now?',
                'category': 'emotions',
                'stage': 'middle',
                'min_days_sober': 90,
            },
            
            # Ongoing recovery prompts (1+ years)
            {
                'title': 'Annual Reflection',
                'prompt': 'You\'ve maintained your recovery for over a year. What wisdom would you share with someone just starting out?',
                'category': 'reflection',
                'stage': 'ongoing',
                'min_days_sober': 365,
            },
            {
                'title': 'Giving Back',
                'prompt': 'How are you helping others in their recovery journey? What does service mean to you?',
                'category': 'relationships',
                'stage': 'ongoing',
                'min_days_sober': 365,
            },
            
            # Daily reflection prompts (all stages)
            {
                'title': 'Daily Check-in',
                'prompt': 'How are you feeling physically, emotionally, and spiritually today?',
                'category': 'emotions',
                'stage': 'all',
                'follow_up_1': 'What do you need to take care of yourself today?',
            },
            {
                'title': 'Coping Strategies',
                'prompt': 'What coping strategies did you use today? Which ones were most effective?',
                'category': 'coping',
                'stage': 'all',
            },
            {
                'title': 'Progress Recognition',
                'prompt': 'What small victory or progress did you make today, no matter how minor it might seem?',
                'category': 'milestones',
                'stage': 'all',
            },
            {
                'title': 'Self-Care Assessment',
                'prompt': 'How did you take care of yourself today? What self-care activities helped you most?',
                'category': 'self_care',
                'stage': 'all',
            },
            {
                'title': 'Goal Setting',
                'prompt': 'What are your goals for tomorrow? How will you work toward your long-term recovery goals?',
                'category': 'goals',
                'stage': 'all',
            },
        ]
        
        created_count = 0
        for prompt_data in prompts:
            prompt, created = JournalPrompt.objects.get_or_create(
                title=prompt_data['title'],
                defaults=prompt_data
            )
            if created:
                created_count += 1
                self.stdout.write(f"Created prompt: {prompt.title}")
            else:
                self.stdout.write(f"Prompt already exists: {prompt.title}")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} journal prompts'))