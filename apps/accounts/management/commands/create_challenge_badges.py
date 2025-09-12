from django.core.management.base import BaseCommand
from apps.accounts.models import ChallengeBadge


class Command(BaseCommand):
    help = 'Create initial challenge badges for the system'

    def handle(self, *args, **options):
        badges_data = [
            # Completion Badges
            {
                'name': 'Challenge Starter',
                'description': 'Completed your first challenge',
                'badge_type': 'completion',
                'icon': '🌟',
                'required_completions': 1,
                'rarity_level': 1,
                'points_value': 50,
            },
            {
                'name': 'Challenge Champion',
                'description': 'Completed 5 challenges',
                'badge_type': 'completion',
                'icon': '🏆',
                'required_completions': 5,
                'rarity_level': 3,
                'points_value': 250,
            },
            # Add more badges as needed...
        ]

        created_count = 0
        
        for badge_data in badges_data:
            badge, created = ChallengeBadge.objects.get_or_create(
                name=badge_data['name'],
                defaults=badge_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created badge: {badge.icon} {badge.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'🏆 Created {created_count} new badges!')
        )