from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.blog.models import Category

class Command(BaseCommand):
    help = 'Populates blog categories for MyRecoveryPal'

    def handle(self, *args, **options):
        categories = [
            # Core Recovery Categories
            {
                'name': 'Personal Journey',
                'description': 'Personal recovery stories, testimonials, milestone celebrations, and day-in-the-life experiences.'
            },
            {
                'name': 'Recovery Fundamentals',
                'description': 'Understanding addiction science, types of addiction, stages of recovery, and common challenges.'
            },
            {
                'name': 'Mental Health & Wellness',
                'description': 'Managing anxiety and depression, trauma healing, self-compassion, mindfulness, and sleep in recovery.'
            },
            {
                'name': 'Coping Strategies',
                'description': 'Dealing with cravings and triggers, stress management, healthy coping mechanisms, and emergency toolkits.'
            },
            {
                'name': 'Relapse Prevention',
                'description': 'Warning signs, prevention planning, learning from setbacks, and managing high-risk situations.'
            },
            
            # Support & Community Categories
            {
                'name': 'Support Systems',
                'description': 'Finding sponsors and mentors, building recovery networks, meeting resources, and being a recovery pal.'
            },
            {
                'name': 'Family & Relationships',
                'description': 'Rebuilding trust, dating in recovery, parenting while recovering, supporting loved ones, and setting boundaries.'
            },
            {
                'name': 'Community Voices',
                'description': 'Guest posts from professionals, therapist insights, sponsor perspectives, and family member stories.'
            },
            
            # Practical Life Categories
            {
                'name': 'Daily Living',
                'description': 'Creating healthy routines, nutrition, exercise, financial recovery, and career rebuilding.'
            },
            {
                'name': 'Life Skills',
                'description': 'Communication skills, time management, goal setting, building hobbies, and finding purpose.'
            },
            {
                'name': 'Resources & Tools',
                'description': 'Book and podcast reviews, app recommendations, program comparisons, and treatment guides.'
            },
            
            # Special Interest Categories
            {
                'name': 'Inspiration & Motivation',
                'description': 'Daily affirmations, success stories, overcoming challenges, and seasonal support.'
            },
            {
                'name': 'Education & Awareness',
                'description': 'Addiction research updates, recovery statistics, myth-busting articles, and policy updates.'
            },
            {
                'name': 'Special Populations',
                'description': 'Young adults, seniors, LGBTQ+, veterans, first responders, and professionals in recovery.'
            },
            {
                'name': 'News & Updates',
                'description': 'Site updates, community events, recovery month activities, and member spotlights.'
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories:
            slug = slugify(cat_data['name'])
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created category: {cat_data["name"]}')
                )
            else:
                # Update description if it's empty or different
                if not category.description or category.description != cat_data['description']:
                    category.description = cat_data['description']
                    category.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated category: {cat_data["name"]}')
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(f'- Category already exists: {cat_data["name"]}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Complete! Created {created_count} new categories, updated {updated_count} categories.'
            )
        )
        
        total_categories = Category.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'Total categories in database: {total_categories}')
        )