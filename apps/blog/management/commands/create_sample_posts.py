from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.blog.models import Category, Tag, Post
from django.utils.text import slugify
import random

class Command(BaseCommand):
    help = 'Creates sample blog posts'

    def handle(self, *args, **kwargs):
        # Create categories
        categories = [
            ('Personal Stories', 'Real experiences from people in recovery'),
            ('Tips & Strategies', 'Practical advice for recovery'),
            ('Resources', 'Helpful tools and information'),
            ('Family & Friends', 'Support for loved ones'),
            ('Milestones', 'Celebrating recovery achievements'),
        ]
        
        for name, desc in categories:
            Category.objects.get_or_create(
                name=name,
                defaults={'description': desc, 'slug': slugify(name)}
            )
        
        # Create tags
        tag_names = ['sobriety', 'support', 'mental-health', 'wellness', 
                    'meditation', 'exercise', 'nutrition', 'relationships',
                    'coping-strategies', 'inspiration']
        
        for tag_name in tag_names:
            Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': slugify(tag_name)}
            )
        
        # Get or create a superuser for posts
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write('No superuser found. Please create one first.')
            return
        
        # Sample post content
        sample_posts = [
            {
                'title': 'My Journey: One Year Sober',
                'excerpt': 'Reflecting on 365 days of sobriety and the lessons learned along the way.',
                'content': '''It's hard to believe it's been a full year since I took my last drink. 
                When I started this journey, I couldn't imagine making it through a single day, 
                let alone 365 of them. But here I am, and I want to share what I've learned.

                The first few weeks were the hardest. I had to completely restructure my life, 
                find new ways to cope with stress, and learn to be comfortable with feeling uncomfortable. 
                But each day got a little easier, and the small victories added up.

                Today, I'm grateful for my sobriety and all the gifts it has brought me: 
                clearer thinking, better relationships, improved health, and most importantly, 
                self-respect. To anyone just starting out: keep going. It gets better.''',
                'is_personal_story': True,
                'category': 'Personal Stories',
                'tags': ['sobriety', 'inspiration', 'milestones']
            },
            {
                'title': '5 Coping Strategies That Actually Work',
                'excerpt': 'Practical techniques for managing cravings and difficult emotions in recovery.',
                'content': '''Recovery isn't just about stopping substance use—it's about learning 
                new ways to handle life's challenges. Here are five strategies that have helped 
                countless people in recovery:

                1. **The HALT Check**: When you're feeling triggered, ask yourself if you're 
                Hungry, Angry, Lonely, or Tired. Address these basic needs first.

                2. **The 5-4-3-2-1 Grounding Technique**: Name 5 things you can see, 4 you can touch, 
                3 you can hear, 2 you can smell, and 1 you can taste. This brings you back to the present.

                3. **Call Before You Fall**: Keep a list of supportive people and reach out 
                before making any decisions you might regret.

                4. **Move Your Body**: Exercise releases natural endorphins and helps process 
                difficult emotions. Even a 10-minute walk can make a difference.

                5. **Write It Out**: Journaling helps you process thoughts and feelings without 
                judgment. It's like having a conversation with yourself.''',
                'category': 'Tips & Strategies',
                'tags': ['coping-strategies', 'mental-health', 'wellness']
            },
            {
                'title': 'Understanding Triggers in Early Recovery',
                'excerpt': 'Learn to identify and manage the situations that challenge your sobriety.',
                'content': '''Triggers are a normal part of recovery, but understanding them 
                is key to maintaining sobriety. They can be external (people, places, things) 
                or internal (emotions, thoughts, physical sensations).

                Common triggers include stress, certain social situations, specific locations, 
                and even positive emotions. The key is not to avoid all triggers—that's impossible—
                but to develop healthy responses to them.

                Start by keeping a trigger journal. Note what situations make you think about 
                using, how you feel in those moments, and what helps you get through them. 
                Over time, you'll see patterns and can develop personalized strategies.

                Remember: having triggers doesn't mean you're weak or failing. It means you're 
                human, and you're learning. Each time you successfully navigate a trigger, 
                you're building resilience.''',
                'trigger_warning': True,
                'trigger_description': 'Discussion of substance use triggers',
                'category': 'Resources',
                'tags': ['coping-strategies', 'sobriety', 'mental-health']
            }
        ]
        
        # Create sample posts
        categories_obj = {c.name: c for c in Category.objects.all()}
        tags_obj = {t.name: t for t in Tag.objects.all()}
        
        for post_data in sample_posts:
            tags = post_data.pop('tags', [])
            category_name = post_data.pop('category')
            
            post, created = Post.objects.get_or_create(
                title=post_data['title'],
                defaults={
                    'author': admin,
                    'category': categories_obj.get(category_name),
                    'status': 'published',
                    **post_data
                }
            )
            
            if created:
                # Add tags
                for tag_name in tags:
                    if tag_name in tags_obj:
                        post.tags.add(tags_obj[tag_name])
                
                self.stdout.write(f'Created post: {post.title}')
            else:
                self.stdout.write(f'Post already exists: {post.title}')
        
        self.stdout.write(self.style.SUCCESS('Sample posts created successfully!'))