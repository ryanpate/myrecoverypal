# Add to recovery-hub/resources/views.py

from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
import json

def daily_checklist_interactive(request):
    """Interactive daily recovery checklist"""
    context = {
        'page_title': 'Daily Recovery Checklist',
        'checklist_data': {
            'sections': [
                {
                    'id': 'connection',
                    'title': 'Connection & Support',
                    'icon': '🤝',
                    'items': [
                        'Reach out to your support network (call, text, or attend a meeting)',
                        'Review and update emergency contacts in your phone'
                    ]
                },
                {
                    'id': 'mental',
                    'title': 'Mental Wellness',
                    'icon': '🧠',
                    'items': [
                        'Practice 5-10 minutes of mindful breathing or meditation',
                        'Journal about your feelings, thoughts, and progress',
                        'Identify and document your top 3 triggers'
                    ]
                },
                {
                    'id': 'physical',
                    'title': 'Physical Health',
                    'icon': '💪',
                    'items': [
                        'Drink at least 8 cups of water throughout the day',
                        'Eat balanced meals with protein, carbohydrates, and healthy fats',
                        'Engage in 20-30 minutes of physical activity (walk, stretch, or yoga)'
                    ]
                },
                {
                    'id': 'growth',
                    'title': 'Personal Growth',
                    'icon': '✨',
                    'items': [
                        'Practice gratitude by listing 3 things you\'re thankful for',
                        'Schedule one meaningful self-care activity',
                        'Set a small, achievable goal for tomorrow',
                        'Reflect on a personal strength and how you\'ll use it today'
                    ]
                }
            ]
        }
    }
    return render(request, 'resources/daily_checklist.html', context)


def download_checklist_pdf(request):
    """Generate and download a PDF of the checklist with user's progress"""
    # Get the checked items from the request
    checked_items = json.loads(request.POST.get('checked_items', '[]'))
    
    # For now, return the static PDF
    # In a full implementation, you'd generate a custom PDF with checkmarks
    try:
        resource = Resource.objects.get(slug='daily-recovery-checklist-pdf')
        if resource.file:
            response = HttpResponse(
                resource.file.read(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = 'attachment; filename="daily-recovery-checklist.pdf"'
            return response
    except:
        pass
    
    # Fallback: generate a simple HTML version
    html_content = render_to_string('resources/checklist_pdf.html', {
        'checked_items': checked_items
    })
    
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = 'attachment; filename="daily-recovery-checklist.html"'
    return response


# Add these URLs to recovery-hub/resources/urls.py:
# path('tools/daily-checklist/', views.daily_checklist_interactive, name='daily_checklist'),
# path('tools/daily-checklist/download/', views.download_checklist_pdf, name='download_checklist'),