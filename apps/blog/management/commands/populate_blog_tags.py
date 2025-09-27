from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.blog.models import Tag

class Command(BaseCommand):
    help = 'Populates initial blog tags for MyRecoveryPal'

    def handle(self, *args, **options):
        tags = [
            # Recovery stages
            'early-recovery', 'long-term-recovery', 'celebrating-milestones',
            
            # Support types
            '12-step', 'smart-recovery', 'refuge-recovery', 'secular-recovery',
            
            # Substance specific
            'alcohol', 'opioids', 'stimulants', 'cannabis', 'nicotine',
            
            # Behavioral addictions
            'gambling', 'gaming', 'shopping', 'food-addiction',
            
            # Mental health
            'anxiety', 'depression', 'trauma', 'ptsd', 'bipolar',
            
            # Recovery tools
            'meditation', 'mindfulness', 'exercise', 'nutrition', 'therapy',
            
            # Life aspects
            'relationships', 'parenting', 'career', 'education', 'finances',
            
            # Demographics
            'youth', 'seniors', 'lgbtq', 'veterans', 'women', 'men',
            
            # Content types
            'personal-story', 'tips', 'research', 'news', 'inspiration'
        ]

        created_count = 0
        
        for tag_name in tags:
            tag, created = Tag.objects.get_or_create(
                slug=slugify(tag_name),
                defaults={'name': tag_name.replace('-', ' ').title()}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created tag: {tag.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Created {created_count} new tags!')
        )