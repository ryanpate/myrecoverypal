# apps/resources/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.template.loader import get_template
from django.db.models import Count, Q
from django.utils import timezone
import json

from .models import (
    Resource, ResourceCategory, ResourceType,
    ResourceBookmark, ResourceRating, ResourceUsage,
    InteractiveResourceProgress, CrisisResource
)


class ResourceListView(ListView):
    """Main resources page showing categories and search"""
    model = Resource
    template_name = 'resources/resource_list.html'
    context_object_name = 'resources'
    paginate_by = 12

    def get_queryset(self):
        queryset = Resource.objects.filter(is_active=True)

        # Handle search
        self.query = self.request.GET.get('q', '')
        if self.query:
            queryset = queryset.filter(
                Q(title__icontains=self.query) |
                Q(description__icontains=self.query) |
                Q(content__icontains=self.query)
            ).select_related('category', 'resource_type')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add search query
        context['query'] = self.query

        # Only show categories and featured resources when not searching
        if not self.query:
            context['categories'] = ResourceCategory.objects.filter(
                is_active=True
            ).annotate(
                resource_count=Count('resources')
            ).order_by('order', 'name')

            context['featured_resources'] = Resource.objects.filter(
                is_active=True,
                featured=True
            ).select_related('category', 'resource_type')[:3]

        # Always show crisis resources
        context['crisis_resources'] = CrisisResource.objects.filter(
            is_active=True
        ).order_by('order')

        return context


class CategoryDetailView(ListView):
    """Display all resources within a specific category"""
    model = Resource
    # Changed from 'resources/category_detail.html'
    template_name = 'resources/resource_category.html'
    context_object_name = 'resources'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(
            ResourceCategory,
            slug=self.kwargs['slug'],
            is_active=True
        )
        queryset = Resource.objects.filter(
            category=self.category,
            is_active=True
        ).select_related('resource_type', 'category').order_by('-featured', '-created_at')

        # Handle type filtering
        resource_type = self.request.GET.get('type')
        if resource_type:
            queryset = queryset.filter(resource_type__slug=resource_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category

        # Get other categories for the sidebar
        context['categories'] = ResourceCategory.objects.filter(
            is_active=True
        ).exclude(pk=self.category.pk).order_by('order', 'name')

        # Get resource types for filtering
        context['resource_types'] = ResourceType.objects.filter(
            resource__category=self.category,
            resource__is_active=True
        ).distinct()

        return context

class ResourceDetailView(DetailView):
    """Display a single resource"""
    model = Resource
    template_name = 'resources/resource_detail.html'
    context_object_name = 'resource'

    def get_queryset(self):
        return Resource.objects.filter(is_active=True)

    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.increment_views()

        # Track usage
        if self.request.user.is_authenticated:
            ResourceUsage.objects.create(
                user=self.request.user,
                resource=obj,
                action='view'
            )

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.object

        # Check if user has bookmarked this resource
        if self.request.user.is_authenticated:
            context['is_bookmarked'] = ResourceBookmark.objects.filter(
                user=self.request.user,
                resource=resource
            ).exists()

            # Get user's rating if exists
            try:
                context['user_rating'] = ResourceRating.objects.get(
                    user=self.request.user,
                    resource=resource
                )
            except ResourceRating.DoesNotExist:
                context['user_rating'] = None

        # Get related resources
        context['related_resources'] = Resource.objects.filter(
            category=resource.category,
            is_active=True
        ).exclude(pk=resource.pk)[:4]

        return context


@login_required
def interactive_resource_view(request, slug):
    """Display the interactive version of a resource"""
    resource = get_object_or_404(
        Resource,
        slug=slug,
        is_active=True,
        is_interactive=True
    )

    # Check access level
    if resource.access_level == 'registered' and not request.user.is_authenticated:
        return redirect('accounts:login')
    elif resource.access_level == 'premium' and not hasattr(request.user, 'has_premium'):
        return redirect('store:premium')

    # Track usage
    ResourceUsage.objects.create(
        user=request.user,
        resource=resource,
        action='interact'
    )

    # Get or create progress tracking
    progress, created = InteractiveResourceProgress.objects.get_or_create(
        user=request.user,
        resource=resource
    )

    # Determine which template to use based on the component
    template_map = {
        'CopingSkillsChecklist': 'resources/interactive/coping_skills_checklist.html',
        'DailyRecoveryChecklist': 'resources/interactive/daily_checklist.html',
        # Add more interactive components here as needed
    }

    template_name = template_map.get(
        resource.interactive_component,
        'resources/interactive/default.html'
    )

    context = {
        'resource': resource,
        'progress': progress,
    }

    return render(request, template_name, context)


# Update the download_resource_pdf function in your views.py

@login_required
def download_resource_pdf(request, slug):
    """Generate and download PDF version of a resource"""
    resource = get_object_or_404(
        Resource,
        slug=slug,
        is_active=True
    )

    # Check access level
    if resource.access_level == 'premium' and not hasattr(request.user, 'has_premium'):
        return redirect('store:premium')

    # Track download
    resource.increment_downloads()
    ResourceUsage.objects.create(
        user=request.user,
        resource=resource,
        action='download'
    )

    # If there's an existing PDF file, serve it
    if resource.file:
        response = HttpResponse(resource.file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{resource.slug}.pdf"'
        return response

    # Otherwise, generate PDF from HTML content
    try:
        from weasyprint import HTML

        # Define the HTML content for each resource
        if resource.slug == 'coping-skills-for-cravings':
            html_content = get_coping_skills_pdf_html(resource)
        elif resource.slug == 'daily-recovery-checklist':
            html_content = get_daily_checklist_pdf_html(resource)
        else:
            # Generic PDF template
            html_content = get_generic_pdf_html(resource)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{resource.slug}.pdf"'
        HTML(string=html_content).write_pdf(response)
        return response

    except Exception as e:
        raise Http404(f"PDF generation failed: {str(e)}")

@login_required
def professional_help_view(request):
    return render(request, 'resources/professional_help.html')

def get_coping_skills_pdf_html(resource):
    """Generate HTML for Coping Skills PDF"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: letter; margin: 0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { width: 8.5in; min-height: 11in; margin: 0 auto; background: white; }
        .header { background: linear-gradient(135deg, #8b7ff0 0%, #7f6ed9 100%); color: white; padding: 60px 40px; text-align: center; }
        .logo { font-size: 18px; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; }
        .title { font-size: 36px; font-weight: 700; margin-bottom: 15px; }
        .subtitle { font-size: 18px; opacity: 0.9; }
        .content { padding: 40px; }
        .intro { font-size: 16px; color: #666; margin-bottom: 30px; text-align: center; }
        .strategies { display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; margin-bottom: 40px; }
        .strategy { display: flex; align-items: flex-start; gap: 15px; }
        .strategy-icon { font-size: 28px; flex-shrink: 0; }
        .strategy-content { flex: 1; }
        .strategy-title { font-weight: 700; color: #7f6ed9; margin-bottom: 3px; font-size: 16px; }
        .strategy-desc { font-size: 14px; color: #666; }
        .quote-section { background: #f8f7fd; border-radius: 12px; padding: 30px; text-align: center; margin-top: 40px; }
        .quote { font-size: 18px; font-style: italic; color: #555; margin-bottom: 10px; }
        .quote-author { font-size: 14px; color: #7f6ed9; font-weight: 600; }
        .footer { text-align: center; padding: 20px; color: #999; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">MYRECOVERYPAL</div>
            <h1 class="title">Coping Skills for Cravings</h1>
            <p class="subtitle">Quick Strategies to Stay on Track</p>
        </div>
        <div class="content">
            <p class="intro">Cravings are a normal part of recovery. Use these evidence-based strategies to ride out the urge and stay on your path to healing.</p>
            <div class="strategies">
                <div class="strategy">
                    <div class="strategy-icon">⏱️</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Delay & Wait</div>
                        <div class="strategy-desc">Tell yourself you'll wait 10 minutes before acting on the craving. Often, the urge will pass.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">🫁</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Deep Breathing</div>
                        <div class="strategy-desc">Practice 4-7-8 breathing: inhale for 4 seconds, hold for 7, exhale for 8.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">🎯</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Distract & Engage</div>
                        <div class="strategy-desc">Shift focus with an enjoyable activity: read, listen to music, or watch a video.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">🌊</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Urge Surfing</div>
                        <div class="strategy-desc">Notice the craving as a wave—observe it rising and falling without judgment.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">💧</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Hydrate & Nourish</div>
                        <div class="strategy-desc">Drink water slowly and mindfully. Hydration can reduce physical tension.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">🏃</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Move Your Body</div>
                        <div class="strategy-desc">Go for a walk, stretch, or do jumping jacks to shift your energy and focus.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">🧘</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Practice Mindfulness</div>
                        <div class="strategy-desc">Ground yourself: name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">📞</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Reach Out</div>
                        <div class="strategy-desc">Call or text a friend, sponsor, or support group member for connection.</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">💭</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Positive Self-Talk</div>
                        <div class="strategy-desc">Use affirmations: "I am strong," "This feeling will pass," "I choose my recovery."</div>
                    </div>
                </div>
                <div class="strategy">
                    <div class="strategy-icon">📝</div>
                    <div class="strategy-content">
                        <div class="strategy-title">Journal It Out</div>
                        <div class="strategy-desc">Write about the trigger, your feelings, and which strategy you used.</div>
                    </div>
                </div>
            </div>
            <div class="quote-section">
                <p class="quote">"You don't have to see the whole staircase, just take the first step."</p>
                <p class="quote-author">— Martin Luther King Jr.</p>
            </div>
        </div>
        <div class="footer">
            <p>Your journey matters. Every step counts.</p>
            <p>www.myrecoverypal.com</p>
        </div>
    </div>
</body>
</html>'''


def get_daily_checklist_pdf_html(resource):
    """Generate HTML for Daily Checklist PDF"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: letter; margin: 0.5in; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: linear-gradient(135deg, #8b7ff0 0%, #7f6ed9 100%); color: white; padding: 40px; text-align: center; margin: -0.5in -0.5in 0; }
        .logo { font-size: 16px; font-weight: 700; letter-spacing: 2px; margin-bottom: 15px; }
        .title { font-size: 32px; font-weight: 700; margin-bottom: 10px; }
        .subtitle { font-size: 16px; opacity: 0.9; }
        .content { padding: 30px 0; }
        .intro { text-align: center; color: #666; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px; }
        .section-icon { font-size: 24px; }
        .section-title { font-size: 20px; font-weight: 700; color: #1f2937; }
        .checklist-item { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; padding: 8px 0; }
        .checkbox { width: 20px; height: 20px; border: 2px solid #d1d5db; border-radius: 4px; flex-shrink: 0; }
        .item-text { color: #4b5563; }
        .quote-section { background: #f8f7fd; padding: 25px; text-align: center; margin-top: 30px; border-radius: 8px; }
        .quote { font-style: italic; color: #555; margin-bottom: 8px; }
        .quote-author { color: #7f6ed9; font-weight: 600; font-size: 14px; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">MYRECOVERYPAL</div>
        <h1 class="title">Daily Recovery Checklist</h1>
        <p class="subtitle">Your Personal Guide to Sustainable Recovery</p>
    </div>
    <div class="content">
        <p class="intro">Welcome to your recovery journey. This daily checklist is designed to help you establish healthy habits, strengthen your support network, and build lasting momentum.</p>
        
        <div class="section">
            <div class="section-header">
                <span class="section-icon">🤝</span>
                <h2 class="section-title">Connection & Support</h2>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Reach out to your support network (call, text, or attend a meeting)</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Review and update emergency contacts in your phone</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <span class="section-icon">🧠</span>
                <h2 class="section-title">Mental Wellness</h2>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Practice 5-10 minutes of mindful breathing or meditation</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Journal about your feelings, thoughts, and progress</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Identify and document your top 3 triggers</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <span class="section-icon">💪</span>
                <h2 class="section-title">Physical Health</h2>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Drink at least 8 cups of water throughout the day</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Eat balanced meals with protein, carbohydrates, and healthy fats</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Engage in 20-30 minutes of physical activity (walk, stretch, or yoga)</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-header">
                <span class="section-icon">✨</span>
                <h2 class="section-title">Personal Growth</h2>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Practice gratitude by listing 3 things you're thankful for</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Schedule one meaningful self-care activity</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Set a small, achievable goal for tomorrow</span>
            </div>
            <div class="checklist-item">
                <div class="checkbox"></div>
                <span class="item-text">Reflect on a personal strength and how you'll use it today</span>
            </div>
        </div>
        
        <div class="quote-section">
            <p class="quote">"Recovery is not a race. You don't have to feel guilty if it takes you longer than you thought it would."</p>
            <p class="quote-author">— Recovery Wisdom</p>
        </div>
    </div>
    <div class="footer">
        <p>Your journey matters. Every step counts.</p>
        <p>www.myrecoverypal.com</p>
    </div>
</body>
</html>'''


def get_generic_pdf_html(resource):
    """Generate generic PDF HTML for resources without specific templates"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        h1 {{ color: #7f6ed9; }}
        .header {{ text-align: center; margin-bottom: 2em; }}
        .content {{ margin: 2em 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{resource.title}</h1>
        <p>{resource.description}</p>
    </div>
    <div class="content">
        {resource.content}
    </div>
    <div style="text-align: center; margin-top: 3em; color: #999;">
        <p>www.myrecoverypal.com</p>
    </div>
</body>
</html>'''

@login_required
def bookmark_resource(request, pk):
    """Toggle bookmark for a resource"""
    resource = get_object_or_404(Resource, pk=pk, is_active=True)

    bookmark, created = ResourceBookmark.objects.get_or_create(
        user=request.user,
        resource=resource
    )

    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'bookmarked': bookmarked})

    return redirect(resource.get_absolute_url())


@login_required
def my_bookmarks_view(request):
    """Display user's bookmarked resources"""
    bookmarks = ResourceBookmark.objects.filter(
        user=request.user
    ).select_related('resource__category', 'resource__resource_type')

    context = {
        'bookmarks': bookmarks,
    }

    return render(request, 'resources/my_bookmarks.html', context)


@login_required
def save_interactive_progress(request, slug):
    """Save progress for interactive resources via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        resource = get_object_or_404(
            Resource,
            slug=slug,
            is_active=True,
            is_interactive=True
        )

        progress, created = InteractiveResourceProgress.objects.get_or_create(
            user=request.user,
            resource=resource
        )

        # Update progress data
        data = json.loads(request.body)

        progress.session_data = data.get('session_data', {})
        progress.completed_items = data.get('completed_items', 0)
        progress.total_items = data.get('total_items', 0)
        progress.calculate_completion()

        if progress.completion_percentage >= 100:
            progress.completed_at = timezone.now()

            # Track completion
            ResourceUsage.objects.create(
                user=request.user,
                resource=resource,
                action='complete',
                completed=True
            )

        progress.save()

        return JsonResponse({
            'success': True,
            'completion_percentage': progress.completion_percentage
        })

    return JsonResponse({'success': False}, status=400)

@login_required
def rate_resource(request, slug):
    """Rate a resource"""
    if request.method == 'POST':
        resource = get_object_or_404(Resource, slug=slug, is_active=True)
        rating_value = int(request.POST.get('rating', 0))

        if 1 <= rating_value <= 5:
            rating, created = ResourceRating.objects.update_or_create(
                user=request.user,
                resource=resource,
                defaults={
                    'rating': rating_value,
                    'review': request.POST.get('review', '')
                }
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'rating': rating_value
                })

    return redirect('resources:detail', slug=slug)

def educational_resources_view(request):
    """Display the educational resources page"""
    # Get the resource object for tracking views
    try:
        resource = Resource.objects.get(
            slug='comprehensive-educational-resources')
        # Track view
        resource.increment_views()
        if request.user.is_authenticated:
            ResourceUsage.objects.create(
                user=request.user,
                resource=resource,
                action='view'
            )
    except Resource.DoesNotExist:
        resource = None

    context = {
        'resource': resource,
    }

    return render(request, 'resources/educational_resources.html', context)
