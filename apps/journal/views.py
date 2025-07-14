from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import JournalEntry, JournalPrompt, JournalStreak, JournalReminder
from .forms import JournalEntryForm, GuidedJournalForm, JournalReminderForm
import random

@login_required
def journal_dashboard(request):
    """Main journal dashboard showing entries and stats"""
    user = request.user
    
    # Get or create journal streak
    streak, created = JournalStreak.objects.get_or_create(user=user)
    
    # Check if user has written today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    wrote_today = JournalEntry.objects.filter(
        user=user,
        created_at__gte=today_start
    ).exists()
    
    # Get recent entries
    recent_entries = JournalEntry.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Calculate stats for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_stats = JournalEntry.objects.filter(
        user=user,
        created_at__gte=thirty_days_ago
    ).aggregate(
        total_entries=Count('id'),
        avg_mood=Avg('mood_rating'),
        days_with_cravings=Count('id', filter=Q(cravings_today=True))
    )
    
    # Get a daily prompt suggestion
    user_days_sober = user.get_days_sober()
    relevant_prompts = [p for p in JournalPrompt.objects.filter(is_active=True) 
                       if p.is_relevant_for_user(user)]
    daily_prompt = random.choice(relevant_prompts) if relevant_prompts else None
    
    context = {
        'streak': streak,
        'wrote_today': wrote_today,
        'recent_entries': recent_entries,
        'recent_stats': recent_stats,
        'daily_prompt': daily_prompt,
        'total_entries': user.journal_entries.count(),
    }
    
    return render(request, 'journal/dashboard.html', context)

class JournalEntryListView(LoginRequiredMixin, ListView):
    model = JournalEntry
    template_name = 'journal/entry_list.html'
    context_object_name = 'entries'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = JournalEntry.objects.filter(user=self.request.user)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Filter by mood
        mood = self.request.GET.get('mood')
        if mood:
            queryset = queryset.filter(mood_rating=mood)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add mood distribution
        mood_stats = self.get_queryset().values('mood_rating').annotate(
            count=Count('id')
        ).order_by('mood_rating')
        context['mood_stats'] = mood_stats
        
        return context

class JournalEntryDetailView(LoginRequiredMixin, DetailView):
    model = JournalEntry
    template_name = 'journal/entry_detail.html'
    
    def get_queryset(self):
        # Only allow users to view their own entries
        return JournalEntry.objects.filter(user=self.request.user)

@login_required
def create_entry(request):
    """Create a new journal entry"""
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            
            # Update streak
            streak, created = JournalStreak.objects.get_or_create(user=request.user)
            streak.update_streak()
            
            messages.success(request, 'Journal entry saved successfully!')
            return redirect('journal:entry_detail', pk=entry.pk)
    else:
        form = JournalEntryForm()
    
    return render(request, 'journal/entry_form.html', {'form': form})

@login_required
def guided_entry(request, prompt_id=None):
    """Create a journal entry with a specific prompt"""
    if prompt_id:
        prompt = get_object_or_404(JournalPrompt, id=prompt_id)
    else:
        # Get a random prompt relevant to the user
        relevant_prompts = [p for p in JournalPrompt.objects.filter(is_active=True) 
                           if p.is_relevant_for_user(request.user)]
        prompt = random.choice(relevant_prompts) if relevant_prompts else None
    
    if request.method == 'POST':
        form = GuidedJournalForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.prompt = prompt
            entry.title = f"Reflection: {prompt.title}"
            
            # Combine main response with follow-up responses
            full_content = f"**{prompt.prompt}**\n\n{entry.content}"
            
            if prompt.follow_up_1 and form.cleaned_data.get('follow_up_1_response'):
                full_content += f"\n\n**{prompt.follow_up_1}**\n\n{form.cleaned_data['follow_up_1_response']}"
            
            if prompt.follow_up_2 and form.cleaned_data.get('follow_up_2_response'):
                full_content += f"\n\n**{prompt.follow_up_2}**\n\n{form.cleaned_data['follow_up_2_response']}"
            
            entry.content = full_content
            entry.save()
            
            # Update streak
            streak, created = JournalStreak.objects.get_or_create(user=request.user)
            streak.update_streak()
            
            messages.success(request, 'Guided reflection saved successfully!')
            return redirect('journal:entry_detail', pk=entry.pk)
    else:
        form = GuidedJournalForm()
    
    return render(request, 'journal/guided_entry.html', {
        'form': form,
        'prompt': prompt
    })

class PromptsListView(LoginRequiredMixin, ListView):
    model = JournalPrompt
    template_name = 'journal/prompts_list.html'
    context_object_name = 'prompts'
    
    def get_queryset(self):
        # Get prompts relevant to the user
        prompts = JournalPrompt.objects.filter(is_active=True)
        user = self.request.user
        
        # Filter by category if specified
        category = self.request.GET.get('category')
        if category:
            prompts = prompts.filter(category=category)
        
        # Only show relevant prompts based on user's recovery stage
        relevant_prompts = [p for p in prompts if p.is_relevant_for_user(user)]
        
        return relevant_prompts
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = JournalPrompt.CATEGORY_CHOICES
        context['selected_category'] = self.request.GET.get('category', '')
        return context

@login_required
def journal_stats(request):
    """Show detailed journaling statistics"""
    user = request.user
    
    # Overall stats
    total_entries = JournalEntry.objects.filter(user=user).count()
    
    # Mood trends over time (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    mood_trend = JournalEntry.objects.filter(
        user=user,
        created_at__gte=thirty_days_ago,
        mood_rating__isnull=False
    ).values('created_at__date').annotate(
        avg_mood=Avg('mood_rating')
    ).order_by('created_at__date')
    
    # Most used tags
    all_tags = []
    for entry in JournalEntry.objects.filter(user=user):
        all_tags.extend(entry.get_tags_list())
    
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Cravings analysis
    entries_with_mood = JournalEntry.objects.filter(user=user, mood_rating__isnull=False)
    total_with_mood = entries_with_mood.count()
    
    if total_with_mood > 0:
        craving_stats = {
            'total_days': total_with_mood,
            'days_with_cravings': entries_with_mood.filter(cravings_today=True).count(),
            'percentage': (entries_with_mood.filter(cravings_today=True).count() / total_with_mood) * 100,
            'avg_intensity': JournalEntry.objects.filter(
                user=user, 
                cravings_today=True,
                craving_intensity__isnull=False
            ).aggregate(Avg('craving_intensity'))['craving_intensity__avg']
        }
    else:
        craving_stats = None
    
    # Writing patterns (which days/times user journals most)
    entries_by_day = JournalEntry.objects.filter(user=user).values(
        'created_at__week_day'
    ).annotate(count=Count('id')).order_by('created_at__week_day')
    
    # Convert to day names
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    writing_patterns = []
    for entry in entries_by_day:
        day_index = (entry['created_at__week_day'] - 2) % 7  # Django uses 1=Sunday
        writing_patterns.append({
            'day': day_names[day_index],
            'count': entry['count']
        })
    
    context = {
        'total_entries': total_entries,
        'mood_trend': list(mood_trend),
        'top_tags': top_tags,
        'craving_stats': craving_stats,
        'writing_patterns': writing_patterns,
    }
    
    return render(request, 'journal/stats.html', context)

@login_required
def manage_reminders(request):
    """Manage journal reminders"""
    reminder = JournalReminder.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        if reminder:
            form = JournalReminderForm(request.POST, instance=reminder)
        else:
            form = JournalReminderForm(request.POST)
        
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            messages.success(request, 'Journal reminder settings updated!')
            return redirect('journal:dashboard')
    else:
        if reminder:
            form = JournalReminderForm(instance=reminder)
        else:
            form = JournalReminderForm(initial={'time': '20:00'})  # Default 8 PM
    
    return render(request, 'journal/reminder_form.html', {'form': form})