from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView, ListView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import GroupPost, User, Milestone, SupportMessage, ActivityFeed, DailyCheckIn, ActivityComment, UserConnection, SponsorRelationship, RecoveryBuddy, RecoveryGroup, GroupMembership
from .forms import CustomUserCreationForm, UserProfileForm, MilestoneForm, SupportMessageForm, SponsorRequestForm, RecoveryBuddyForm, RecoveryGroupForm, GroupPostForm, GroupMembershipForm
from .signals import create_profile_update_activity
from django.core.paginator import Paginator
from django.db import transaction

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
    """Enhanced dashboard with community activity feed"""
    user = request.user

    # Basic user stats
    days_sober = user.get_days_sober()

    # Get recent milestones
    recent_milestones = user.milestones.all()[:5]

    # Get unread messages count
    unread_messages = user.received_messages.filter(is_read=False).count()

    # Activity Feed - Show activities from users this user follows + own activities
    following_users = list(user.get_following().values_list('id', flat=True))
    following_users.append(user.id)  # Include own activities

    recent_activities = ActivityFeed.objects.filter(
        user_id__in=following_users,
        is_public=True
    ).select_related('user').prefetch_related(
        'comments__user', 'likes'
    ).order_by('-created_at')[:15]

    # Community stats for the current week
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)

    recent_milestones_count = Milestone.objects.filter(
        created_at__gte=week_ago
    ).count()

    active_users_week = User.objects.filter(
        last_seen__gte=week_ago,
        is_active=True
    ).count()

    # User's connection stats
    followers_count = user.followers_count
    following_count = user.following_count

    # Suggested users to follow (users not already followed)
    excluded_ids = list(user.get_following().values_list('id', flat=True))
    excluded_ids.append(user.id)

    suggested_users = User.objects.filter(
        is_active=True,
        is_profile_public=True
    ).exclude(id__in=excluded_ids).annotate(
        mutual_count=Count('follower_connections__follower',
                           filter=Q(follower_connections__follower__in=user.get_following()))
    ).order_by('-mutual_count', '-date_joined')[:3]

    # User's recovery connections
    active_sponsor = user.get_active_sponsor()
    recovery_buddy = user.get_recovery_buddy()
    active_sponsorships = user.get_active_sponsorships()[:3]

    # User's groups
    user_groups = user.get_joined_groups()[:3]

    # Check if user has done daily check-in today
    today = timezone.now().date()
    today_checkin = DailyCheckIn.objects.filter(
        user=user,
        date=today
    ).first()

    context = {
        # User basics
        'user': user,
        'days_sober': days_sober,
        'unread_messages': unread_messages,

        # Milestones
        'recent_milestones': recent_milestones,

        # Activity Feed
        'recent_activities': recent_activities,

        # Community stats
        'recent_milestones_count': recent_milestones_count,
        'active_users_week': active_users_week,

        # User connections
        'followers_count': followers_count,
        'following_count': following_count,
        'suggested_users': suggested_users,

        # Recovery connections
        'active_sponsor': active_sponsor,
        'recovery_buddy': recovery_buddy,
        'active_sponsorships': active_sponsorships,

        # Groups
        'user_groups': user_groups,

        # Daily check-in
        'today_checkin': today_checkin,
        'has_checked_in_today': today_checkin is not None,
    }

    return render(request, 'accounts/dashboard.html', context)


@login_required
def daily_checkin_view(request):
    """Handle daily check-in submissions"""
    today = timezone.now().date()

    # Check if user already checked in today
    existing_checkin = DailyCheckIn.objects.filter(
        user=request.user,
        date=today
    ).first()

    if request.method == 'POST':
        if existing_checkin:
            messages.info(request, 'You have already checked in today!')
            return redirect('accounts:dashboard')

        # Get form data from your template
        mood = request.POST.get('mood')
        craving_level = request.POST.get('craving_level', 0)
        energy_level = request.POST.get('energy_level', 3)
        gratitude = request.POST.get('gratitude', '')
        challenge = request.POST.get('challenge', '')
        goal = request.POST.get('goal', '')
        is_shared = request.POST.get('is_shared') == 'on'

        if mood:
            # Create check-in with all the fields from your form
            checkin = DailyCheckIn.objects.create(
                user=request.user,
                date=today,
                mood=int(mood),
                craving_level=int(craving_level),
                energy_level=int(energy_level),
                gratitude=gratitude,
                challenge=challenge,
                goal=goal,
                is_shared=is_shared
            )

            # Create activity if shared
            if is_shared:
                ActivityFeed.objects.create(
                    user=request.user,
                    activity_type='check_in_posted',
                    title=f"Daily Check-in: {checkin.get_mood_display_with_emoji()}",
                    description=f"Feeling {checkin.get_mood_display().lower()}" +
                    (f" - {gratitude[:100]}..." if gratitude else ""),
                    content_object=checkin
                )

            messages.success(request, 'Daily check-in completed! 🌟')
            return redirect('accounts:dashboard')

    context = {
        'existing_checkin': existing_checkin,
    }
    return render(request, 'accounts/daily_checkin.html', context)

@login_required
@require_POST
def like_activity(request, activity_id):
    """AJAX endpoint to like/unlike an activity"""
    activity = get_object_or_404(ActivityFeed, id=activity_id)

    if request.user in activity.likes.all():
        activity.likes.remove(request.user)
        liked = False
    else:
        activity.likes.add(request.user)
        liked = True

    return JsonResponse({
        'success': True,
        'liked': liked,
        'likes_count': activity.likes_count
    })


@login_required
@require_POST
def comment_on_activity(request, activity_id):
    """AJAX endpoint to comment on an activity"""
    activity = get_object_or_404(ActivityFeed, id=activity_id)
    content = request.POST.get('comment', '').strip()

    if content:
        comment = ActivityComment.objects.create(
            activity=activity,
            user=request.user,
            content=content
        )

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': comment.user.get_full_name() or comment.user.username,
                'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
            }
        })

    return JsonResponse({'success': False, 'error': 'Comment cannot be empty'})

@login_required
@require_POST
def like_activity(request, activity_id):
    """AJAX endpoint to like/unlike an activity"""
    activity = get_object_or_404(ActivityFeed, id=activity_id)
    
    if request.user in activity.likes.all():
        activity.likes.remove(request.user)
        liked = False
    else:
        activity.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': activity.likes_count
    })

# Add these view functions to your apps/accounts/views.py file:

# Simple placeholder views (you can enhance these later)


@login_required
def suggested_users(request):
    """Suggest users to follow based on mutual connections and interests"""
    # Users not already followed
    excluded_ids = list(
        request.user.get_following().values_list('id', flat=True))
    excluded_ids.append(request.user.id)

    # Get users with similar recovery goals/interests
    suggested_users = User.objects.filter(
        is_active=True,
        is_profile_public=True
    ).exclude(id__in=excluded_ids)[:10]

    context = {
        'suggested_users': suggested_users,
    }
    return render(request, 'accounts/suggested_users.html', context)


@login_required
def followers_list(request, username):
    """List of user's followers"""
    user = get_object_or_404(User, username=username)
    followers = user.get_followers()

    context = {
        'user': user,
        'followers': followers,
    }
    return render(request, 'accounts/connections_list.html', context)


@login_required
def following_list(request, username):
    """List of users this user is following"""
    user = get_object_or_404(User, username=username)
    following = user.get_following()

    context = {
        'user': user,
        'following': following,
    }
    return render(request, 'accounts/connections_list.html', context)


@login_required
def sponsor_dashboard(request):
    """Dashboard for sponsor relationships"""
    context = {
        'sponsorships': [],
        'sponsor_relationship': None,
        'sponsor_requests': [],
    }
    return render(request, 'accounts/sponsor_dashboard.html', context)


@login_required
def buddy_dashboard(request):
    """Dashboard for recovery buddy relationships"""
    context = {
        'current_buddy': None,
        'sent_requests': [],
    }
    return render(request, 'accounts/buddy_dashboard.html', context)


@login_required
def request_sponsor(request, username):
    """Request a user to be your sponsor"""
    messages.info(request, 'Sponsor request feature coming soon!')
    return redirect('accounts:profile', username=username)


@login_required
def request_buddy(request, username):
    """Request to be recovery buddies"""
    messages.info(request, 'Recovery buddy request feature coming soon!')
    return redirect('accounts:profile', username=username)


@login_required
@require_POST
def respond_sponsor_request(request, relationship_id):
    """Accept or decline a sponsor request"""
    messages.info(request, 'Sponsor response feature coming soon!')
    return redirect('accounts:sponsor_dashboard')


# Group views (simplified for now)
class RecoveryGroupListView(ListView):
    """List all recovery groups"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_list.html'
    context_object_name = 'groups'
    paginate_by = 12

    def get_queryset(self):
        return RecoveryGroup.objects.filter(is_active=True)


class RecoveryGroupDetailView(DetailView):
    """Detailed view of a recovery group"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_detail.html'
    context_object_name = 'group'


@login_required
def create_group(request):
    """Create a new recovery group"""
    if request.method == 'POST':
        name = request.POST.get('name', '')
        description = request.POST.get('description', '')
        if name and description:
            group = RecoveryGroup.objects.create(
                name=name,
                description=description,
                creator=request.user
            )
            messages.success(request, f'Group "{name}" created successfully!')
            return redirect('accounts:groups_list')

    return render(request, 'accounts/groups/create_group.html')


@login_required
def my_groups(request):
    """User's joined groups"""
    groups = request.user.get_joined_groups()
    return render(request, 'accounts/groups/my_groups.html', {'groups': groups})


@login_required
@require_POST
def join_group(request, group_id):
    """Join a recovery group"""
    messages.info(request, 'Group joining feature coming soon!')
    return JsonResponse({'success': True, 'message': 'Feature coming soon'})


@login_required
def daily_checkin_view(request):
    """Handle daily check-in creation"""
    today = timezone.now().date()
    
    # Check if user already checked in today
    existing_checkin = DailyCheckIn.objects.filter(
        user=request.user,
        date=today
    ).first()
    
    if existing_checkin:
        messages.info(request, "You've already checked in today! Come back tomorrow.")
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        # Create check-in from form data
        checkin = DailyCheckIn.objects.create(
            user=request.user,
            date=today,
            mood=int(request.POST.get('mood')),
            craving_level=int(request.POST.get('craving_level', 0)),
            energy_level=int(request.POST.get('energy_level', 3)),
            gratitude=request.POST.get('gratitude', ''),
            challenge=request.POST.get('challenge', ''),
            goal=request.POST.get('goal', ''),
            is_shared=bool(request.POST.get('is_shared'))
        )
        
        messages.success(request, 'Daily check-in completed! 🌟')
        return redirect('accounts:dashboard')
    
    return render(request, 'accounts/daily_checkin.html')


@login_required
@require_POST
def comment_on_activity(request, activity_id):
    """AJAX endpoint to comment on an activity"""
    activity = get_object_or_404(ActivityFeed, id=activity_id)
    content = request.POST.get('content', '').strip()
    
    if content:
        comment = ActivityComment.objects.create(
            activity=activity,
            user=request.user,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': comment.user.get_full_name() or comment.user.username,
                'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Comment cannot be empty'})


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
            )[:5] if hasattr(profile_user, 'blog_posts') else []
            
            # Add recent activities for this user
            context['user_activities'] = ActivityFeed.objects.filter(
                user=profile_user,
                is_public=True
            )[:10]
        else:
            context['show_full_profile'] = False
        
        return context

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            # Create activity for profile update
            create_profile_update_activity(request.user)
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

        # Add follow status for authenticated users
        if self.request.user.is_authenticated:
            # Get list of users this user is following
            following_ids = list(
                self.request.user.get_following().values_list('id', flat=True))

            # Add annotation to show if user is followed
            from django.db.models import Case, When, Value, BooleanField
            queryset = queryset.annotate(
                is_followed=Case(
                    When(id__in=following_ids, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
            )

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(bio__icontains=search) |
                Q(location__icontains=search)
            )

        # Filter by sponsors
        if self.request.GET.get('sponsors_only'):
            queryset = queryset.filter(is_sponsor=True)

        # Filter by connection type
        connection_filter = self.request.GET.get('filter')
        if connection_filter == 'following' and self.request.user.is_authenticated:
            queryset = queryset.filter(
                id__in=self.request.user.get_following())
        elif connection_filter == 'new':
            from datetime import timedelta
            queryset = queryset.filter(
                date_joined__gte=timezone.now() - timedelta(days=30)
            )

        return queryset.order_by('-last_seen')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate total members
        total_members = User.objects.filter(
            is_profile_public=True,
            is_active=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None).count()

        context['total_members'] = total_members
        context['potential_connections'] = total_members

        # Add sponsors count
        context['sponsors_count'] = User.objects.filter(
            is_profile_public=True,
            is_active=True,
            is_sponsor=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None).count()

        # Add user's connection stats if authenticated
        if self.request.user.is_authenticated:
            user = self.request.user
            context.update({
                'followers_count': user.followers_count,
                'following_count': user.following_count,
                'suggested_users': User.objects.filter(
                    is_active=True,
                    is_profile_public=True
                ).exclude(id=user.id).exclude(
                    id__in=user.get_following()
                )[:3],
            })

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


@login_required
@require_POST
def follow_user(request, username):
    """Follow or unfollow a user via AJAX"""
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    # Check if already following
    connection = UserConnection.objects.filter(
        follower=request.user,
        following=target_user,
        connection_type='follow'
    ).first()

    if connection:
        # Unfollow
        connection.delete()
        is_following = False
        action = 'unfollowed'
    else:
        # Follow
        request.user.follow_user(target_user)
        is_following = True
        action = 'followed'

        # Create activity for following
        ActivityFeed.objects.create(
            user=request.user,
            activity_type='user_followed',
            title=f"Started following {target_user.get_full_name() or target_user.username}",
            description=f"You are now following {target_user.username}'s recovery journey"
        )

    # Get updated counts
    followers_count = target_user.followers_count
    following_count = target_user.following_count

    return JsonResponse({
        'success': True,
        'is_following': is_following,
        'action': action,
        'followers_count': followers_count,
        'following_count': following_count
    })


@login_required
def followers_list(request, username):
    """List of user's followers"""
    user = get_object_or_404(User, username=username)
    followers = user.get_followers().select_related('profile')

    paginator = Paginator(followers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user': user,
        'followers': page_obj,
        'is_followers_page': True,
    }
    return render(request, 'accounts/connections_list.html', context)


@login_required
def following_list(request, username):
    """List of users this user is following"""
    user = get_object_or_404(User, username=username)
    following = user.get_following().select_related('profile')

    paginator = Paginator(following, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user': user,
        'following': page_obj,
        'is_following_page': True,
    }
    return render(request, 'accounts/connections_list.html', context)


@login_required
def suggested_users(request):
    """Suggest users to follow based on mutual connections and interests"""
    # Users not already followed
    excluded_ids = list(
        request.user.get_following().values_list('id', flat=True))
    excluded_ids.append(request.user.id)

    # Get users with mutual followers
    mutual_suggestions = User.objects.filter(
        follower_connections__follower__in=request.user.get_following(),
        is_active=True
    ).exclude(id__in=excluded_ids).annotate(
        mutual_count=Count('follower_connections__follower')
    ).order_by('-mutual_count')[:5]

    # Get users with similar recovery goals/interests
    similar_users = User.objects.filter(
        is_active=True,
        recovery_goals__isnull=False
    ).exclude(id__in=excluded_ids).exclude(
        id__in=mutual_suggestions.values_list('id', flat=True)
    )[:5]

    # Get new members
    new_members = User.objects.filter(
        is_active=True,
        date_joined__gte=timezone.now() - timezone.timedelta(days=30)
    ).exclude(id__in=excluded_ids).order_by('-date_joined')[:5]

    context = {
        'mutual_suggestions': mutual_suggestions,
        'similar_users': similar_users,
        'new_members': new_members,
    }
    return render(request, 'accounts/suggested_users.html', context)


# =============================================================================
# SPONSOR RELATIONSHIP VIEWS
# =============================================================================

@login_required
def sponsor_dashboard(request):
    """Dashboard for sponsor relationships"""
    # Current sponsorships (as sponsor)
    sponsorships = request.user.sponsee_relationships.filter(
        status__in=['pending', 'active']
    ).select_related('sponsee__profile')

    # Current sponsor (as sponsee)
    sponsor_relationship = request.user.sponsor_relationships.filter(
        status='active'
    ).select_related('sponsor__profile').first()

    # Sponsor requests received
    sponsor_requests = request.user.sponsee_relationships.filter(
        status='pending'
    ).select_related('sponsee__profile')

    context = {
        'sponsorships': sponsorships,
        'sponsor_relationship': sponsor_relationship,
        'sponsor_requests': sponsor_requests,
        'can_be_sponsor': request.user.is_sponsor,
    }
    return render(request, 'accounts/sponsor_dashboard.html', context)


@login_required
def request_sponsor(request, username):
    """Request a user to be your sponsor"""
    sponsor = get_object_or_404(User, username=username, is_sponsor=True)

    # Check if request already exists
    existing = SponsorRelationship.objects.filter(
        sponsor=sponsor,
        sponsee=request.user
    ).first()

    if existing:
        messages.warning(
            request, 'You already have a relationship with this sponsor.')
        return redirect('accounts:profile', username=username)

    if request.method == 'POST':
        form = SponsorRequestForm(request.POST)
        if form.is_valid():
            relationship = form.save(commit=False)
            relationship.sponsor = sponsor
            relationship.sponsee = request.user
            relationship.save()

            messages.success(
                request, f'Sponsor request sent to {sponsor.get_full_name() or sponsor.username}!')
            return redirect('accounts:sponsor_dashboard')
    else:
        form = SponsorRequestForm()

    context = {
        'form': form,
        'sponsor': sponsor,
    }
    return render(request, 'accounts/request_sponsor.html', context)


@login_required
@require_POST
def respond_sponsor_request(request, relationship_id):
    """Accept or decline a sponsor request"""
    relationship = get_object_or_404(
        SponsorRelationship,
        id=relationship_id,
        sponsor=request.user,
        status='pending'
    )

    action = request.POST.get('action')

    if action == 'accept':
        relationship.status = 'active'
        relationship.save()
        messages.success(
            request, f'You are now sponsoring {relationship.sponsee.username}!')

        # Create activity
        ActivityFeed.objects.create(
            user=request.user,
            activity_type='sponsorship_started',
            title=f"Started sponsoring {relationship.sponsee.get_full_name() or relationship.sponsee.username}",
            description="A new mentorship journey has begun"
        )

    elif action == 'decline':
        relationship.status = 'declined'
        relationship.save()
        messages.info(request, 'Sponsor request declined.')

    return redirect('accounts:sponsor_dashboard')


# =============================================================================
# RECOVERY BUDDY VIEWS
# =============================================================================

@login_required
def buddy_dashboard(request):
    """Dashboard for recovery buddy relationships"""
    # Current buddy
    current_buddy = request.user.get_recovery_buddy()

    # Pending buddy requests (sent and received)
    sent_requests = RecoveryBuddy.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        status='pending'
    ).exclude(
        # Exclude requests I initiated
        Q(user1=request.user, user2__lt=request.user) |
        Q(user2=request.user, user1__lt=request.user)
    )

    received_requests = RecoveryBuddy.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        status='pending'
    ).exclude(id__in=sent_requests.values_list('id', flat=True))

    context = {
        'current_buddy': current_buddy,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
    }
    return render(request, 'accounts/buddy_dashboard.html', context)


@login_required
def request_buddy(request, username):
    """Request to be recovery buddies"""
    buddy_user = get_object_or_404(User, username=username)

    if buddy_user == request.user:
        messages.error(request, "You cannot be your own recovery buddy.")
        return redirect('accounts:profile', username=username)

    # Check for existing relationship
    existing = RecoveryBuddy.objects.filter(
        Q(user1=request.user, user2=buddy_user) |
        Q(user1=buddy_user, user2=request.user)
    ).first()

    if existing:
        messages.warning(
            request, 'You already have a buddy relationship with this user.')
        return redirect('accounts:buddy_dashboard')

    if request.method == 'POST':
        form = RecoveryBuddyForm(request.POST)
        if form.is_valid():
            buddy_relationship = form.save(commit=False)
            buddy_relationship.user1 = request.user
            buddy_relationship.user2 = buddy_user
            buddy_relationship.save()

            messages.success(
                request, f'Recovery buddy request sent to {buddy_user.username}!')
            return redirect('accounts:buddy_dashboard')
    else:
        form = RecoveryBuddyForm()

    context = {
        'form': form,
        'buddy_user': buddy_user,
    }
    return render(request, 'accounts/request_buddy.html', context)


# =============================================================================
# RECOVERY GROUP VIEWS
# =============================================================================

class RecoveryGroupListView(ListView):
    """List all recovery groups"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_list.html'
    context_object_name = 'groups'
    paginate_by = 12

    def get_queryset(self):
        queryset = RecoveryGroup.objects.filter(is_active=True).annotate(
            member_count=Count('memberships', filter=Q(
                memberships__status='active'))
        ).select_related('creator')

        # Filter by group type
        group_type = self.request.GET.get('type')
        if group_type:
            queryset = queryset.filter(group_type=group_type)

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        # Filter by privacy level
        privacy = self.request.GET.get('privacy')
        if privacy:
            queryset = queryset.filter(privacy_level=privacy)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group_types'] = RecoveryGroup.GROUP_TYPES
        context['privacy_levels'] = RecoveryGroup.PRIVACY_LEVELS

        # User's groups
        if self.request.user.is_authenticated:
            context['user_groups'] = self.request.user.get_joined_groups()

        return context


class RecoveryGroupDetailView(DetailView):
    """Detailed view of a recovery group"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.object

        # Check user's membership status
        membership = None
        if self.request.user.is_authenticated:
            membership = GroupMembership.objects.filter(
                user=self.request.user,
                group=group
            ).first()

        context['membership'] = membership
        context['is_member'] = membership and membership.status in [
            'active', 'moderator', 'admin']

        # Recent posts
        if context['is_member']:
            context['recent_posts'] = group.posts.select_related(
                'author').prefetch_related('likes')[:10]

        # Member list (limited for privacy)
        context['members'] = User.objects.filter(
            group_memberships__group=group,
            group_memberships__status__in=['active', 'moderator', 'admin']
        ).select_related('profile')[:12]

        return context


@login_required
def create_group(request):
    """Create a new recovery group"""
    if request.method == 'POST':
        form = RecoveryGroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.creator = request.user
            group.save()

            # Auto-join creator as admin
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                status='admin'
            )

            messages.success(
                request, f'Recovery group "{group.name}" created successfully!')
            return redirect('accounts:group_detail', pk=group.id)
    else:
        form = RecoveryGroupForm()

    context = {'form': form}
    return render(request, 'accounts/groups/create_group.html', context)


@login_required
@require_POST
def join_group(request, group_id):
    """Join a recovery group"""
    group = get_object_or_404(RecoveryGroup, id=group_id, is_active=True)

    # Check if already a member
    existing_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group
    ).first()

    if existing_membership:
        if existing_membership.status == 'left':
            # Rejoin group
            existing_membership.status = 'pending' if group.privacy_level == 'private' else 'active'
            existing_membership.save()
            action = 'rejoined'
        else:
            return JsonResponse({'error': 'Already a member or pending'}, status=400)
    else:
        # Create new membership
        status = 'pending' if group.privacy_level == 'private' else 'active'
        GroupMembership.objects.create(
            user=request.user,
            group=group,
            status=status
        )
        action = 'joined'

    # Check if group is full
    if group.is_full and group.privacy_level == 'public':
        return JsonResponse({'error': 'Group is full'}, status=400)

    return JsonResponse({
        'success': True,
        'action': action,
        'status': status,
        'member_count': group.member_count
    })


@login_required
def my_groups(request):
    """User's joined groups dashboard"""
    memberships = GroupMembership.objects.filter(
        user=request.user,
        status__in=['active', 'moderator', 'admin']
    ).select_related('group').order_by('-last_active')

    context = {
        'memberships': memberships,
    }
    return render(request, 'accounts/groups/my_groups.html', context)


# =============================================================================
# ENHANCED COMMUNITY VIEW WITH CONNECTIONS
# =============================================================================

class EnhancedCommunityView(ListView):
    """Enhanced community view with follow functionality"""
    model = User
    template_name = 'accounts/enhanced_community.html'
    context_object_name = 'members'
    paginate_by = 24

    def get_queryset(self):
        queryset = User.objects.filter(
            is_active=True
        ).exclude(id=self.request.user.id if self.request.user.is_authenticated else None)

        # Add follow status and connection counts
        if self.request.user.is_authenticated:
            following_ids = list(
                self.request.user.get_following().values_list('id', flat=True))
            queryset = queryset.extra(
                select={
                    'is_followed': f"CASE WHEN id IN ({','.join(map(str, following_ids)) or '0'}) THEN 1 ELSE 0 END"
                }
            )

        # Filters
        connection_filter = self.request.GET.get('filter')
        if connection_filter == 'following' and self.request.user.is_authenticated:
            queryset = queryset.filter(
                id__in=self.request.user.get_following())
        elif connection_filter == 'sponsors':
            queryset = queryset.filter(is_sponsor=True)
        elif connection_filter == 'new':
            queryset = queryset.filter(
                date_joined__gte=timezone.now() - timezone.timedelta(days=30)
            )

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(profile__bio__icontains=search)
            )

        return queryset.select_related('profile').order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            user = self.request.user
            context.update({
                'followers_count': user.followers_count,
                'following_count': user.following_count,
                'mutual_followers': user.get_mutual_followers()[:5],
                'suggested_users': User.objects.filter(
                    is_active=True
                ).exclude(id=user.id).exclude(
                    id__in=user.get_following()
                )[:3],
            })

        return context


@login_required
@require_POST
def follow_user(request, username):
    """Follow or unfollow a user via AJAX"""
    target_user = get_object_or_404(User, username=username)

    if target_user == request.user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)

    # Check if already following
    connection = UserConnection.objects.filter(
        follower=request.user,
        following=target_user,
        connection_type='follow'
    ).first()

    if connection:
        # Unfollow
        connection.delete()
        is_following = False
        action = 'unfollowed'
    else:
        # Follow
        request.user.follow_user(target_user)
        is_following = True
        action = 'followed'

        # Create activity for following
        ActivityFeed.objects.create(
            user=request.user,
            activity_type='user_followed',
            title=f"Started following {target_user.get_full_name() or target_user.username}",
            description=f"You are now following {target_user.username}'s recovery journey"
        )

    # Get updated counts
    followers_count = target_user.followers_count
    following_count = target_user.following_count

    return JsonResponse({
        'success': True,
        'is_following': is_following,
        'action': action,
        'followers_count': followers_count,
        'following_count': following_count
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