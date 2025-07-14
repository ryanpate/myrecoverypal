from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates sample users for testing'

    def handle(self, *args, **kwargs):
        # Sample user data
        users_data = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'password': 'testpass123',
                'sobriety_date': date.today() - timedelta(days=365),
                'bio': 'One year sober and grateful for every day.',
                'location': 'New York, NY',
                'is_sponsor': True,
                'is_profile_public': True,
            },
            {
                'username': 'sarah_smith',
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Smith',
                'password': 'testpass123',
                'sobriety_date': date.today() - timedelta(days=90),
                'bio': '90 days clean and feeling stronger every day.',
                'location': 'Los Angeles, CA',
                'is_profile_public': True,
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'password': 'testpass123',
                'sobriety_date': date.today() - timedelta(days=30),
                'bio': 'New to recovery but committed to change.',
                'location': 'Chicago, IL',
                'is_profile_public': True,
            },
        ]
        
        for user_data in users_data:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f'Created user: {user.username}')
                
                # Create some milestones
                from apps.accounts.models import Milestone
                
                if user.sobriety_date:
                    Milestone.objects.create(
                        user=user,
                        title="Started My Recovery Journey",
                        description="The day I decided to change my life.",
                        date_achieved=user.sobriety_date,
                        milestone_type='days',
                        days_sober=0
                    )
                    
                    # Add some random milestones
                    milestone_ideas = [
                        ("Found a sponsor", "personal"),
                        ("Completed first step", "personal"),
                        ("Returned to work", "career"),
                        ("Repaired family relationship", "relationship"),
                        ("Started exercising regularly", "health"),
                    ]
                    
                    for i in range(random.randint(1, 3)):
                        title, m_type = random.choice(milestone_ideas)
                        days_ago = random.randint(1, (date.today() - user.sobriety_date).days)
                        Milestone.objects.create(
                            user=user,
                            title=title,
                            milestone_type=m_type,
                            date_achieved=user.sobriety_date + timedelta(days=days_ago)
                        )
        
        self.stdout.write(self.style.SUCCESS('Sample users created successfully!'))