# apps/resources/migrations/0003_add_coping_skills_resources.py

from django.db import migrations


def create_coping_skills_resources(apps, schema_editor):
    ResourceCategory = apps.get_model('resources', 'ResourceCategory')
    ResourceType = apps.get_model('resources', 'ResourceType')
    Resource = apps.get_model('resources', 'Resource')

    # Get or create the tools category (should already exist)
    tools_category, created = ResourceCategory.objects.get_or_create(
        slug='tools',
        defaults={
            'name': 'Recovery Tools',
            'description': 'Practical tools and worksheets to support your recovery journey',
            'icon': '🛠️',
            'order': 2
        }
    )

    # If the category already exists but needs updating
    if not created and tools_category.icon != '🛠️':
        tools_category.icon = '🛠️'
        tools_category.save()

    # Create or get resource types
    pdf_type, _ = ResourceType.objects.get_or_create(
        slug='pdf',
        defaults={
            'name': 'PDF Document',
            'color': '#EF4444',
            'icon': '📄'
        }
    )

    checklist_type, _ = ResourceType.objects.get_or_create(
        slug='checklist',
        defaults={
            'name': 'Interactive Checklist',
            'color': '#8B5CF6',
            'icon': '✅'
        }
    )

    # Create the coping skills resource under tools category
    coping_resource, created = Resource.objects.get_or_create(
        slug='coping-skills-for-cravings',
        defaults={
            'title': 'Coping Skills for Cravings',
            'category': tools_category,  # Using tools category
            'resource_type': checklist_type,
            'description': 'Evidence-based strategies to help you manage cravings in the moment. Available as both an interactive checklist and downloadable PDF.',
            'interaction_type': 'hybrid',
            'is_interactive': True,
            'interactive_component': 'CopingSkillsChecklist',
            'access_level': 'free',
            'featured': True,
            'estimated_time': '5-10 minutes',
            'difficulty_level': 'beginner',
            'meta_description': 'Free coping skills checklist for addiction recovery. Evidence-based strategies to manage cravings including breathing techniques, mindfulness, and more.'
        }
    )

    # Also create other useful tools while we're at it
    Resource.objects.get_or_create(
        slug='daily-recovery-checklist',
        defaults={
            'title': 'Daily Recovery Checklist',
            'category': tools_category,
            'resource_type': pdf_type,
            'description': 'A comprehensive daily checklist to help you establish healthy habits and maintain your recovery momentum.',
            'interaction_type': 'static',
            'access_level': 'free',
            'featured': True,
            'estimated_time': '5 minutes',
            'difficulty_level': 'beginner'
        }
    )

    Resource.objects.get_or_create(
        slug='trigger-identification-worksheet',
        defaults={
            'title': 'Trigger Identification Worksheet',
            'category': tools_category,
            'resource_type': pdf_type,
            'description': 'Identify and document your personal triggers to better prepare for challenging situations.',
            'interaction_type': 'static',
            'access_level': 'registered',
            'estimated_time': '15-20 minutes',
            'difficulty_level': 'intermediate'
        }
    )

    Resource.objects.get_or_create(
        slug='relapse-prevention-plan',
        defaults={
            'title': 'Relapse Prevention Plan Template',
            'category': tools_category,
            'resource_type': pdf_type,
            'description': 'Create a personalized plan to help you stay on track and handle high-risk situations.',
            'interaction_type': 'static',
            'access_level': 'registered',
            'featured': True,
            'estimated_time': '30 minutes',
            'difficulty_level': 'intermediate'
        }
    )


def reverse_create_coping_skills_resources(apps, schema_editor):
    Resource = apps.get_model('resources', 'Resource')
    # Remove all resources created in this migration
    Resource.objects.filter(slug__in=[
        'coping-skills-for-cravings',
        'daily-recovery-checklist',
        'trigger-identification-worksheet',
        'relapse-prevention-plan'
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Replace with your actual previous migration
        ('resources', '0002_resource_difficulty_level_resource_estimated_time_and_more'),
    ]

    operations = [
        migrations.RunPython(
            create_coping_skills_resources,
            reverse_create_coping_skills_resources
        ),
    ]
