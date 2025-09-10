from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView, ListView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils import timezone
from .models import User, Milestone, SupportMessage
from .forms import CustomUserCreationForm, UserProfileForm, MilestoneForm, SupportMessageForm

def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            messages.success(request, f'Welcome to the community, {username}!')
            
            # Auto-login after registration
            user = authenticate(username=username, password=password)
            login(request, user)
            
            # Create automatic milestone if sobriety date provided
            if user.sobriety_date:
                Milestone.objects.create(
                    user=user,
                    title="Started My Recovery Journey",
                    description="The day I decided to change my life.",
                    date_achieved=user.sobriety_date,
                    milestone_type='days',
                    days_sober=0
                )
            
            return redirect('accounts:dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard_view(request):
    user = request.user
    context = {
        'user': user,
        'days_sober': user.get_days_sober(),
        'sobriety_milestone': user.get_sobriety_milestone(),
        'recent_milestones': user.milestones.all()[:5],
        'recent_posts': user.blog_posts.all()[:5],
        'unread_messages': user.received_messages.filter(is_read=False).count(),
    }
    
    # Check for milestone achievements
    days_sober = user.get_days_sober()
    milestone_days = [1, 7, 30, 60, 90, 180, 365, 730]
    
    for days in milestone_days:
        if days_sober == days:
            # Check if milestone already exists
            exists = Milestone.objects.filter(
                user=user,
                days_sober=days,
                milestone_type='days'
            ).exists()
            
            if not exists:
                Milestone.objects.create(
                    user=user,
                    title=f"{days} Days Sober!",
                    description=f"Congratulations on reaching {days} days of sobriety!",
                    milestone_type='days',
                    days_sober=days
                )
                messages.success(request, f'Congratulations on {days} days sober! 🎉')
    
    return render(request, 'accounts/dashboard.html', context)

class ProfileView(DetailView):
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        
        # Only show certain information if profile is public or it's the user's own profile
        if profile_user == self.request.user or profile_user.is_profile_public:
            context['show_full_profile'] = True
            context['milestones'] = profile_user.milestones.all()[:10]
            context['recent_posts'] = profile_user.blog_posts.filter(
                status='published'
            )[:5]
        else:
            context['show_full_profile'] = False
        
        return context

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:profile', username=request.user.username)
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})

class MilestoneListView(LoginRequiredMixin, ListView):
    model = Milestone
    template_name = 'accounts/milestones.html'
    context_object_name = 'milestones'
    paginate_by = 20
    
    def get_queryset(self):
        return self.request.user.milestones.all()

class MilestoneCreateView(LoginRequiredMixin, CreateView):
    model = Milestone
    form_class = MilestoneForm
    template_name = 'accounts/milestone_form.html'
    success_url = reverse_lazy('accounts:milestones')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Milestone added successfully!')
        return super().form_valid(form)


class CommunityView(ListView):
    model = User
    template_name = 'accounts/community.html'
    context_object_name = 'members'
    paginate_by = 24

    def get_queryset(self):
        # Only show users with public profiles
        queryset = User.objects.filter(
            is_profile_public=True,
            is_active=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None)

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(bio__icontains=search) |
                Q(location__icontains=search)  # Added location to search
            )

        # Filter by sponsors
        if self.request.GET.get('sponsors_only'):
            queryset = queryset.filter(is_sponsor=True)

        return queryset.order_by('-last_seen')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate total members (all active users with public profiles except current user)
        total_members = User.objects.filter(
            is_profile_public=True,
            is_active=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None).count()
        
        # Potential connections is the same as total members (everyone you can connect with)
        context['total_members'] = total_members
        context['potential_connections'] = total_members
        
        # Add sponsors count
        context['sponsors_count'] = User.objects.filter(
            is_profile_public=True,
            is_active=True,
            is_sponsor=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None).count()
        
        return context    
@login_required
def send_message_view(request, username):
    recipient = get_object_or_404(User, username=username)
    
    # Check if recipient allows messages
    if not recipient.allow_messages and not request.user.is_staff:
        messages.error(request, 'This user has disabled messages.')
        return redirect('accounts:profile', username=username)
    
    if request.method == 'POST':
        form = SupportMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.recipient = recipient
            message.save()
            messages.success(request, 'Your message has been sent!')
            return redirect('accounts:profile', username=username)
    else:
        form = SupportMessageForm()
    
    return render(request, 'accounts/send_message.html', {
        'form': form,
        'recipient': recipient
    })

class MessageListView(LoginRequiredMixin, ListView):
    model = SupportMessage
    template_name = 'accounts/messages.html'
    context_object_name = 'messages'
    paginate_by = 20
    
    def get_queryset(self):
        # Mark messages as read when viewing
        SupportMessage.objects.filter(
            recipient=self.request.user,
            is_read=False
        ).update(is_read=True)
        
        return SupportMessage.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).order_by('-created_at')