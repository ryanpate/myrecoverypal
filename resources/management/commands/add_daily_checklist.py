# File: recovery-hub/resources/management/commands/add_daily_checklist.py

from django.core.management.base import BaseCommand
from resources.models import Resource, ResourceCategory, ResourceType
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Add the Daily Recovery Checklist as a resource'

    def handle(self, *args, **kwargs):
        # Get the Tools category
        tools_category, _ = ResourceCategory.objects.get_or_create(
            slug='tools',
            defaults={
                'name': 'Recovery Tools',
                'icon': '🛠️',
                'description': 'Practical worksheets, trackers, and exercises for daily recovery work',
                'order': 3
            }
        )
        
        # Get or create resource types
        pdf_type, _ = ResourceType.objects.get_or_create(
            slug='pdf-guide',
            defaults={
                'name': 'PDF Guide',
                'color': '#3B82F6'
            }
        )
        
        tool_type, _ = ResourceType.objects.get_or_create(
            slug='tool',
            defaults={
                'name': 'Interactive Tool',
                'color': '#8B5CF6'
            }
        )
        
        # Create the PDF version
        pdf_resource, pdf_created = Resource.objects.get_or_create(
            slug='daily-recovery-checklist-pdf',
            defaults={
                'title': 'Daily Recovery Checklist (PDF)',
                'category': tools_category,
                'resource_type': pdf_type,
                'description': 'A printable daily checklist to track your recovery activities across Connection & Support, Mental Wellness, Physical Health, and Personal Growth.',
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'meta_description': 'Free printable daily recovery checklist PDF to track your progress in addiction recovery.',
                'content': self.get_pdf_content()
            }
        )
        
        # Create the interactive version
        interactive_resource, interactive_created = Resource.objects.get_or_create(
            slug='daily-recovery-checklist-interactive',
            defaults={
                'title': 'Daily Recovery Checklist (Interactive)',
                'category': tools_category,
                'resource_type': tool_type,
                'description': 'An interactive daily checklist you can fill out online and download as a personalized PDF with your progress tracked.',
                'access_level': 'free',
                'featured': True,
                'is_active': True,
                'external_url': '/resources/tools/daily-checklist/',  # We'll create this URL
                'meta_description': 'Interactive daily recovery checklist - track your progress online and download personalized PDFs.',
                'content': self.get_interactive_content()
            }
        )
        
        if pdf_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created PDF checklist resource\n'
                    f'   Please upload the PDF file through admin: /admin/resources/resource/{pdf_resource.id}/\n'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('PDF checklist already exists')
            )
            
        if interactive_created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created interactive checklist resource\n'
                    f'   URL: /resources/tools/daily-checklist/\n'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('Interactive checklist already exists')
            )
            
    def get_pdf_content(self):
        return """## About the Daily Recovery Checklist

This comprehensive daily checklist helps you establish and maintain healthy recovery habits across four key areas:

### 🤝 Connection & Support
Build and maintain your support network through daily connection and emergency preparedness.

### 🧠 Mental Wellness
Strengthen your mental health through mindfulness, journaling, and trigger awareness.

### 💪 Physical Health
Support your body's recovery with proper hydration, nutrition, and exercise.

### ✨ Personal Growth
Foster continuous improvement through gratitude, self-care, and goal-setting.

### How to Use This Checklist:

1. **Print multiple copies** - Keep them handy for daily use
2. **Check off items** as you complete them throughout the day
3. **Be flexible** - Not every item needs to be completed every day
4. **Track patterns** - Notice which areas need more attention
5. **Celebrate progress** - Every checked box is a victory

Remember: "Recovery is not a race. You don't have to feel guilty if it takes you longer than you thought it would."

Download the PDF and start tracking your daily recovery progress today!"""

    def get_interactive_content(self):
        return """## Interactive Daily Recovery Checklist

This digital version of our Daily Recovery Checklist allows you to:

### ✅ Track Progress Online
- Check off items as you complete them
- See your completion percentage
- Track streaks and patterns

### 📊 View Your Statistics
- Daily completion rates
- Weekly and monthly trends
- Areas of strength and growth

### 📥 Download Personalized PDFs
- Generate PDFs with your progress
- Include notes and reflections
- Create weekly or monthly reports

### 🔄 Reset and Reuse
- Start fresh each day
- Save previous checklists
- Build a recovery journal

### Features Include:
- **Auto-save**: Your progress is saved automatically
- **Mobile-friendly**: Use on any device
- **Private & Secure**: Your data stays on your device
- **Customizable**: Add your own items to the checklist
- **Shareable**: Export reports to share with sponsors or therapists

Start using the interactive checklist to make your daily recovery tracking easier and more insightful!"""