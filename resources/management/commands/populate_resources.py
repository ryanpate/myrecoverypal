from django.core.management.base import BaseCommand
from resources.models import ResourceCategory, ResourceType, CrisisResource

class Command(BaseCommand):
    help = 'Populate initial resource data'

    def handle(self, *args, **kwargs):
        # Create resource types
        resource_types = [
            ('pdf-guide', 'PDF Guide', '#3B82F6'),
            ('article', 'Article', '#10B981'),
            ('video', 'Video', '#EF4444'),
            ('worksheet', 'Worksheet', '#F59E0B'),
            ('tool', 'Tool', '#8B5CF6'),
            ('directory', 'Directory', '#EC4899'),
        ]
        
        for slug, name, color in resource_types:
            ResourceType.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'color': color}
            )
        
        # Create categories
        categories = [
            ('educational', 'Educational Materials', '📚', 'Learn about addiction, recovery processes, and evidence-based treatment approaches', 1),
            ('support', 'Support Services', '🤝', 'Find support groups, helplines, and community resources near you', 2),
            ('tools', 'Recovery Tools', '🛠️', 'Practical worksheets, trackers, and exercises for daily recovery work', 3),
            ('wellness', 'Wellness Resources', '🧘', 'Mindfulness, meditation, and holistic health resources', 4),
            ('family', 'Family & Friends', '👨‍👩‍👧‍👦', 'Resources for loved ones supporting someone in recovery', 5),
            ('professional', 'Professional Help', '⚕️', 'Find treatment centers, therapists, and medical professionals', 6),
        ]
        
        for slug, name, icon, desc, order in categories:
            ResourceCategory.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'icon': icon,
                    'description': desc,
                    'order': order
                }
            )
        
        # Create crisis resources
        crisis_resources = [
            ('Suicide & Crisis Lifeline', '988', '', 'Available 24/7 for crisis support', 'https://988lifeline.org/', 1),
            ('Crisis Text Line', '', 'Text "HELLO" to 741741', 'Free 24/7 text support', 'https://www.crisistextline.org/', 2),
            ('SAMHSA National Helpline', '1-800-662-4357', '', 'Treatment referral and information service', 'https://www.samhsa.gov/find-help/national-helpline', 3),
        ]
        
        for name, phone, text, desc, url, order in crisis_resources:
            CrisisResource.objects.get_or_create(
                name=name,
                defaults={
                    'phone_number': phone,
                    'text_number': text,
                    'description': desc,
                    'url': url,
                    'order': order
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated resource data'))