from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView, ListView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, Prefetch, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import GroupPost, User, Milestone, SupportMessage, ActivityFeed, DailyCheckIn, ActivityComment, UserConnection, SponsorRelationship, RecoveryPal, RecoveryGroup, GroupMembership
from .forms import CustomUserCreationForm, UserProfileForm, MilestoneForm, SupportMessageForm, SponsorRequestForm, RecoveryPalForm, RecoveryGroupForm, GroupPostForm, GroupMembershipForm
from .signals import create_profile_update_activity
from django.core.paginator import Paginator
from django.db import transaction
from datetime import timedelta, datetime
from django.conf import settings
import cloudinary.uploader
from django.core.serializers import serialize
import json

from .models import (
    GroupChallenge, ChallengeParticipant, ChallengeCheckIn,
    ChallengeComment, ChallengeBadge, UserChallengeBadge, Notification
)
from .forms import (
    GroupChallengeForm, JoinChallengeForm, ChallengeCheckInForm,
    ChallengeCommentForm, PalRequestForm, ChallengeFilterForm
)

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
    recovery_pal = user.get_recovery_pal()
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
        'recovery_pal': recovery_pal,
        'active_sponsorships': active_sponsorships,

        # Groups
        'user_groups': user_groups,

        # Daily check-in
        'today_checkin': today_checkin,
        'has_checked_in_today': today_checkin is not None,
    }

    return render(request, 'accounts/enhanced_dashboard.html', context)


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


# UPDATED FUNCTIONS WITH FIX FOR FOLLOWERS/FOLLOWING PAGES
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
        'page_obj': page_obj,  # Added for pagination in template
        'is_followers_page': True,
        'is_following_page': False,  # Explicitly set to False
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
        'page_obj': page_obj,  # Added for pagination in template
        'is_following_page': True,
        'is_followers_page': False,  # Explicitly set to False
    }
    return render(request, 'accounts/connections_list.html', context)


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
def pal_dashboard(request):
    """Dashboard for recovery pal relationships"""
    # Current pal
    current_pal = request.user.get_recovery_pal()

    # Pending pal requests (sent and received)
    sent_requests = RecoveryPal.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        status='pending'
    ).exclude(
        # Exclude requests I initiated
        Q(user1=request.user, user2__lt=request.user) |
        Q(user2=request.user, user1__lt=request.user)
    )

    received_requests = RecoveryPal.objects.filter(
        Q(user1=request.user) | Q(user2=request.user),
        status='pending'
    ).exclude(id__in=sent_requests.values_list('id', flat=True))

    context = {
        'current_pal': current_pal,
        'sent_requests': sent_requests,
        'received_requests': received_requests,
    }
    return render(request, 'accounts/pal_dashboard.html', context)


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
def request_pal(request, username):
    """Request to be recovery pals"""
    pal_user = get_object_or_404(User, username=username)

    if pal_user == request.user:
        messages.error(request, "You cannot be your own recovery pal.")
        return redirect('accounts:profile', username=username)

    # Check for existing relationship
    existing = RecoveryPal.objects.filter(
        Q(user1=request.user, user2=pal_user) |
        Q(user1=pal_user, user2=request.user)
    ).first()

    if existing:
        messages.warning(
            request, 'You already have a pal relationship with this user.')
        return redirect('accounts:pal_dashboard')

    if request.method == 'POST':
        form = RecoveryPalForm(request.POST)
        if form.is_valid():
            pal_relationship = form.save(commit=False)
            pal_relationship.user1 = request.user
            pal_relationship.user2 = pal_user
            pal_relationship.save()

            # Create notification
            create_notification(
                recipient=pal_user,
                sender=request.user,
                notification_type='pal_request',
                title='Recovery Pal Request',
                message=f"{request.user.get_full_name() or request.user.username} wants to be your recovery pal",
                link='/accounts/pals/',
                content_object=pal_relationship
            )

            messages.success(
                request, f'Recovery pal request sent to {pal_user.username}!')
            return redirect('accounts:pal_dashboard')
    else:
        form = RecoveryPalForm()

    context = {
        'form': form,
        'pal_user': pal_user,
    }
    return render(request, 'accounts/request_pal.html', context)

@login_required
def request_challenge_pal(request, challenge_id, user_id):
    """Request accountability partner for a challenge"""
    challenge = get_object_or_404(GroupChallenge, id=challenge_id)
    target_user = get_object_or_404(User, id=user_id)

    # Check if both users are participating
    try:
        user_participation = challenge.participants.get(
            user=request.user, status='active')
        target_participation = challenge.participants.get(
            user=target_user, status='active')
    except ChallengeParticipant.DoesNotExist:
        messages.error(
            request, "Both users must be participating in the challenge.")
        return redirect('accounts:challenge_detail', challenge_id=challenge_id)

    # Check if already partners or request exists
    if user_participation.accountability_partner == target_participation:
        messages.info(request, "You are already accountability partners!")
        return redirect('accounts:challenge_detail', challenge_id=challenge_id)

    if request.method == 'POST':
        form = PalRequestForm(request.POST)
        if form.is_valid():
            # Send pal request (you could implement a notification system here)
            # For now, just pair them up directly
            user_participation.accountability_partner = target_participation
            target_participation.accountability_partner = user_participation
            user_participation.save()
            target_participation.save()

            messages.success(
                request, f"You are now accountability partners with {target_user.get_full_name() or target_user.username}!")
            return redirect('accounts:challenge_detail', challenge_id=challenge_id)
    else:
        form = PalRequestForm()

    context = {
        'form': form,
        'challenge': challenge,
        'target_user': target_user,
    }

    return render(request, 'accounts/challenges/request_pal.html', context)

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


# Group views
class RecoveryGroupListView(ListView):
    """List all recovery groups"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_list.html'
    context_object_name = 'groups'
    paginate_by = 12

    def get_queryset(self):
        queryset = RecoveryGroup.objects.filter(is_active=True).annotate(
            active_member_count=Count('memberships', filter=Q(
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
def update_last_seen(request):
    """AJAX endpoint to update user's last seen timestamp"""
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])
    return JsonResponse({'status': 'updated'})

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        # Use the UserProfileForm to handle form submission
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            user = form.save(commit=False)

            # Handle avatar upload with special processing if needed
            if 'avatar' in request.FILES:
                avatar_file = request.FILES['avatar']

                # Validate file size (5MB limit)
                if avatar_file.size > 5 * 1024 * 1024:
                    messages.error(
                        request, 'Image file too large. Please use an image under 5MB.')
                    return redirect('accounts:edit_profile')

                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg',
                                 'image/png', 'image/gif', 'image/webp']
                if avatar_file.content_type not in allowed_types:
                    messages.error(
                        request, 'Invalid file type. Please use JPG, PNG, GIF, or WebP.')
                    return redirect('accounts:edit_profile')

                try:
                    # If using Cloudinary
                    if hasattr(settings, 'DEFAULT_FILE_STORAGE') and 'cloudinary' in settings.DEFAULT_FILE_STORAGE:
                        # Delete old avatar from Cloudinary if exists
                        if user.avatar:
                            # Extract public_id from URL
                            old_public_id = user.avatar.name.rsplit('.', 1)[0]
                            try:
                                cloudinary.uploader.destroy(old_public_id)
                            except:
                                pass  # Ignore errors when deleting old image

                        # Cloudinary handles optimization automatically
                        user.avatar = avatar_file
                    else:
                        # Local storage with PIL optimization
                        from PIL import Image
                        from io import BytesIO
                        import sys
                        import os

                        img = Image.open(avatar_file)

                        # Convert RGBA to RGB if necessary
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new(
                                'RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()
                                             [-1] if img.mode == 'RGBA' else None)
                            img = background

                        # Resize and optimize
                        max_size = (800, 800)
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)

                        output = BytesIO()
                        img.save(output, format='JPEG',
                                 quality=85, optimize=True)
                        output.seek(0)

                        from django.core.files.uploadedfile import InMemoryUploadedFile
                        avatar_file = InMemoryUploadedFile(
                            output, 'ImageField',
                            f"{user.username}_avatar.jpg",
                            'image/jpeg',
                            sys.getsizeof(output),
                            None
                        )

                        # Delete old local file
                        if user.avatar and os.path.exists(user.avatar.path):
                            os.remove(user.avatar.path)

                        user.avatar = avatar_file

                except Exception as e:
                    messages.error(
                        request, f'Error processing image: {str(e)}')
                    print(f"Avatar processing error: {e}")

            # Save all form data
            try:
                user.save()
                messages.success(request, 'Profile updated successfully!')

                # Optional: Create activity feed entry for profile update
                if hasattr(user, 'activityfeed_set'):
                    from .models import ActivityFeed
                    ActivityFeed.objects.create(
                        user=user,
                        activity_type='profile_update',
                        title='Profile Updated',
                        description='Updated profile information'
                    )

            except Exception as e:
                messages.error(
                    request, 'Failed to save profile. Please try again.')
                print(f"Profile save error: {e}")
                return redirect('accounts:edit_profile')

            return redirect('accounts:profile', username=user.username)
        else:
            # Form is invalid, display errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # GET request - display form with current user data
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

            # Create notification
            create_notification(
                recipient=recipient,
                sender=request.user,
                notification_type='message',
                title='New Message',
                message=f"You have a new message from {request.user.get_full_name() or request.user.username}",
                link='/accounts/messages/',
                content_object=message
            )

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

        # Create notification for the followed user
        create_notification(
            recipient=target_user,
            sender=request.user,
            notification_type='follow',
            title='New Follower',
            message=f"{request.user.get_full_name() or request.user.username} started following you",
            link=f"/accounts/profile/{request.user.username}/"
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

            # Use proper table alias to avoid ambiguous column name
            from django.db.models import Case, When, Value, BooleanField
            queryset = queryset.annotate(
                is_followed=Case(
                    When(id__in=following_ids, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField()
                )
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

            # Get suggested users (excluding followed users)
            excluded_ids = list(
                user.get_following().values_list('id', flat=True))
            excluded_ids.append(user.id)

            suggested_users = User.objects.filter(
                is_active=True
            ).exclude(id__in=excluded_ids)[:3]

            context.update({
                'followers_count': user.followers_count,
                'following_count': user.following_count,
                'suggested_users': suggested_users,
                'mutual_followers': user.get_mutual_followers()[:5],
            })

        return context


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

@login_required
def challenges_home(request):
    """Main challenges dashboard"""

    # Get filter parameters
    filter_form = ChallengeFilterForm(request.GET)
    challenges = GroupChallenge.objects.all()

    # Apply filters
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        challenge_type = filter_form.cleaned_data.get('challenge_type')
        duration = filter_form.cleaned_data.get('duration')
        search = filter_form.cleaned_data.get('search')
        my_challenges_only = filter_form.cleaned_data.get('my_challenges_only')

        if status:
            challenges = challenges.filter(status=status)
        if challenge_type:
            challenges = challenges.filter(challenge_type=challenge_type)
        if duration:
            challenges = challenges.filter(duration_days=duration)
        if search:
            challenges = challenges.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        if my_challenges_only:
            challenges = challenges.filter(participants__user=request.user)

    # Get user's active participations
    user_participations = ChallengeParticipant.objects.filter(
        user=request.user, status='active'
    ).select_related('challenge')

    # Get recent activity from user's challenges
    recent_check_ins = ChallengeCheckIn.objects.filter(
        participant__challenge__participants__user=request.user,
        is_shared_with_group=True
    ).select_related('participant__user', 'participant__challenge').order_by('-created_at')[:10]

    # Get recommended challenges
    # Logic: challenges in groups user is a member of, or public challenges of types user has participated in
    user_groups = request.user.group_memberships.filter(
        status__in=['active', 'moderator', 'admin']
    ).values_list('group', flat=True)

    participated_types = request.user.challenge_participations.values_list(
        'challenge__challenge_type', flat=True
    ).distinct()

    recommended_challenges = GroupChallenge.objects.filter(
        Q(group__id__in=user_groups) |
        (Q(is_public=True) & Q(challenge_type__in=participated_types)),
        status__in=['upcoming', 'active']
    ).exclude(
        participants__user=request.user
    ).distinct()[:6]

    # Pagination
    paginator = Paginator(challenges, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'user_participations': user_participations,
        'recent_check_ins': recent_check_ins,
        'recommended_challenges': recommended_challenges,
        'total_challenges': challenges.count(),
        'active_challenges': GroupChallenge.objects.filter(status='active').count(),
    }

    return render(request, 'accounts/challenges/challenges_home.html', context)


@login_required
def challenge_detail(request, challenge_id):
    """View challenge details and leaderboard"""

    challenge = get_object_or_404(GroupChallenge, id=challenge_id)

    # Check if user can view this challenge
    if not challenge.is_public:
        if not challenge.group.memberships.filter(
            user=request.user, status__in=['active', 'moderator', 'admin']
        ).exists():
            messages.error(
                request, "You don't have permission to view this challenge.")
            return redirect('accounts:challenges_home')

    # Get user's participation if any
    user_participation = None
    try:
        user_participation = challenge.participants.get(user=request.user)
    except ChallengeParticipant.DoesNotExist:
        pass

    # Get leaderboard (top participants by completion)
    leaderboard = challenge.participants.filter(
        status='active'
    ).order_by('-days_completed', '-current_streak', '-longest_streak')[:10]

    # Get recent shared check-ins
    recent_check_ins = ChallengeCheckIn.objects.filter(
        participant__challenge=challenge,
        is_shared_with_group=True
    ).select_related('participant__user').order_by('-created_at')[:20]

    # Challenge statistics
    stats = {
        'total_participants': challenge.participant_count,
        'completion_rate': challenge.completion_rate,
        'average_streak': challenge.participants.filter(status='active').aggregate(
            avg_streak=Avg('current_streak')
        )['avg_streak'] or 0,
        'total_check_ins': ChallengeCheckIn.objects.filter(
            participant__challenge=challenge
        ).count(),
    }

    context = {
        'challenge': challenge,
        'user_participation': user_participation,
        'leaderboard': leaderboard,
        'recent_check_ins': recent_check_ins,
        'stats': stats,
        'can_join': challenge.can_join(request.user)[0] if not user_participation else False,
    }

    return render(request, 'accounts/challenges/challenge_detail.html', context)


@login_required
def create_challenge(request, group_id=None):
    """Create a new group challenge"""

    group = None
    if group_id:
        group = get_object_or_404(RecoveryGroup, id=group_id)
        # Check if user can create challenges in this group
        if not group.memberships.filter(
            user=request.user,
            status__in=['active', 'moderator', 'admin']
        ).exists():
            messages.error(
                request, "You don't have permission to create challenges in this group.")
            return redirect('accounts:group_detail', pk=group_id)

    if request.method == 'POST':
        form = GroupChallengeForm(request.POST, user=request.user)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.creator = request.user
            if group:
                challenge.group = group
            else:
                # If no group specified, create in user's first active group or require selection
                user_groups = request.user.group_memberships.filter(
                    status__in=['active', 'moderator', 'admin']
                )
                if user_groups.exists():
                    challenge.group = user_groups.first().group
                else:
                    messages.error(
                        request, "You must be a member of a group to create challenges.")
                    return redirect('accounts:groups_list')

            challenge.save()
            messages.success(
                request, f'Challenge "{challenge.title}" created successfully!')
            return redirect('accounts:challenge_detail', challenge_id=challenge.id)
    else:
        form = GroupChallengeForm(user=request.user)

    context = {
        'form': form,
        'group': group,
        'title': f'Create Challenge{"" if not group else f" in {group.name}"}',
    }

    return render(request, 'accounts/challenges/create_challenge.html', context)


@login_required
def join_challenge(request, challenge_id):
    """Join a challenge"""

    challenge = get_object_or_404(GroupChallenge, id=challenge_id)
    can_join, reason = challenge.can_join(request.user)

    if not can_join:
        messages.error(request, f"Cannot join challenge: {reason}")
        return redirect('accounts:challenge_detail', challenge_id=challenge_id)

    if request.method == 'POST':
        form = JoinChallengeForm(request.POST)
        if form.is_valid():
            participation = form.save(commit=False)
            participation.challenge = challenge
            participation.user = request.user
            participation.save()

            messages.success(
                request, f'You have joined "{challenge.title}"! Good luck!')
            return redirect('accounts:challenge_detail', challenge_id=challenge_id)
    else:
        form = JoinChallengeForm()

    context = {
        'form': form,
        'challenge': challenge,
    }

    return render(request, 'accounts/challenges/join_challenge.html', context)


@login_required
def challenge_check_in(request, challenge_id):
    """Daily check-in for a challenge"""

    challenge = get_object_or_404(GroupChallenge, id=challenge_id)

    try:
        participation = challenge.participants.get(
            user=request.user, status='active')
    except ChallengeParticipant.DoesNotExist:
        messages.error(request, "You are not participating in this challenge.")
        return redirect('accounts:challenge_detail', challenge_id=challenge_id)

    today = timezone.now().date()

    # Check if already checked in today
    existing_check_in = ChallengeCheckIn.objects.filter(
        participant=participation, date=today
    ).first()

    if request.method == 'POST':
        form = ChallengeCheckInForm(
            request.POST, instance=existing_check_in, challenge=challenge)
        if form.is_valid():
            check_in = form.save(commit=False)
            check_in.participant = participation
            check_in.date = today
            check_in.save()

            if existing_check_in:
                messages.success(request, 'Check-in updated successfully!')
            else:
                messages.success(request, 'Check-in recorded successfully!')

            return redirect('accounts:my_challenges')
    else:
        form = ChallengeCheckInForm(
            instance=existing_check_in, challenge=challenge)

    # Get recent check-ins for context
    recent_check_ins = participation.check_ins.order_by('-date')[:7]

    context = {
        'form': form,
        'challenge': challenge,
        'participation': participation,
        'existing_check_in': existing_check_in,
        'recent_check_ins': recent_check_ins,
        'today': today,
    }

    return render(request, 'accounts/challenges/check_in.html', context)


@login_required
def my_challenges(request):
    """User's challenge dashboard"""

    # Get user's active participations
    active_participations = request.user.challenge_participations.filter(
        status='active'
    ).select_related('challenge').order_by('-joined_date')

    # Get completed participations
    completed_participations = request.user.challenge_participations.filter(
        status='completed'
    ).select_related('challenge').order_by('-completion_date')

    # Get today's check-ins needed
    today = timezone.now().date()
    todays_check_ins = []

    for participation in active_participations:
        check_in_today = ChallengeCheckIn.objects.filter(
            participant=participation, date=today
        ).first()
        todays_check_ins.append({
            'participation': participation,
            'check_in': check_in_today,
            'needs_check_in': not check_in_today and participation.challenge.enable_daily_check_in
        })

    # Get user's badges
    user_badges = request.user.challenge_badges.select_related(
        'badge').order_by('-earned_date')

    # Calculate total stats
    total_challenges_completed = completed_participations.count()
    total_days_participated = sum(p.days_completed for p in active_participations) + \
        sum(p.days_completed for p in completed_participations)
    current_streaks = [
        p.current_streak for p in active_participations if p.current_streak > 0]
    longest_current_streak = max(current_streaks) if current_streaks else 0

    context = {
        'active_participations': active_participations,
        # Show recent 5
        'completed_participations': completed_participations[:5],
        'todays_check_ins': todays_check_ins,
        'user_badges': user_badges[:10],  # Show recent 10
        'stats': {
            'total_challenges_completed': total_challenges_completed,
            'total_days_participated': total_days_participated,
            'longest_current_streak': longest_current_streak,
            'badges_earned': user_badges.count(),
        }
    }

    return render(request, 'accounts/challenges/my_challenges.html', context)


@login_required
def challenge_feed(request, challenge_id):
    """Activity feed for a specific challenge"""

    challenge = get_object_or_404(GroupChallenge, id=challenge_id)

    # Check access
    if not challenge.is_public:
        if not challenge.group.memberships.filter(
            user=request.user, status__in=['active', 'moderator', 'admin']
        ).exists():
            messages.error(
                request, "You don't have permission to view this challenge.")
            return redirect('accounts:challenges_home')

    # Get shared check-ins with comments
    check_ins = ChallengeCheckIn.objects.filter(
        participant__challenge=challenge,
        is_shared_with_group=True
    ).select_related(
        'participant__user', 'participant__user__profile'
    ).prefetch_related('comments__user').order_by('-created_at')

    # Pagination
    paginator = Paginator(check_ins, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'challenge': challenge,
        'page_obj': page_obj,
        'comment_form': ChallengeCommentForm(),
    }

    return render(request, 'accounts/challenges/challenge_feed.html', context)


@login_required
def add_challenge_comment(request, check_in_id):
    """Add comment to a challenge check-in (AJAX)"""

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    check_in = get_object_or_404(ChallengeCheckIn, id=check_in_id)

    # Check if user can comment (member of group or public challenge)
    challenge = check_in.participant.challenge
    if not challenge.is_public:
        if not challenge.group.memberships.filter(
            user=request.user, status__in=['active', 'moderator', 'admin']
        ).exists():
            return JsonResponse({'error': 'Permission denied'}, status=403)

    form = ChallengeCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.check_in = check_in
        comment.user = request.user
        comment.save()

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': comment.user.get_full_name() or comment.user.username,
                'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
            }
        })

    return JsonResponse({'error': 'Invalid form'}, status=400)


@login_required
def give_encouragement(request, check_in_id):
    """Give encouragement to a check-in (AJAX)"""

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    check_in = get_object_or_404(ChallengeCheckIn, id=check_in_id)

    # Toggle encouragement
    if request.user in check_in.encouragement_received.all():
        check_in.encouragement_received.remove(request.user)
        encouraged = False
    else:
        check_in.encouragement_received.add(request.user)
        encouraged = True

    return JsonResponse({
        'success': True,
        'encouraged': encouraged,
        'total_encouragements': check_in.encouragement_count
    })


@login_required
def leave_challenge(request, challenge_id):
    """Leave a challenge"""

    challenge = get_object_or_404(GroupChallenge, id=challenge_id)

    try:
        participation = challenge.participants.get(
            user=request.user, status='active')
    except ChallengeParticipant.DoesNotExist:
        messages.error(request, "You are not participating in this challenge.")
        return redirect('accounts:challenge_detail', challenge_id=challenge_id)

    if request.method == 'POST':
        participation.status = 'dropped'
        participation.save()

        # Remove pal partnership if exists
        if participation.accountability_partner:
            partner = participation.accountability_partner
            partner.accountability_partner = None
            partner.save()
            participation.accountability_partner = None
            participation.save()

        messages.success(request, f'You have left "{challenge.title}".')
        return redirect('accounts:my_challenges')

    context = {
        'challenge': challenge,
        'participation': participation,
    }

    return render(request, 'accounts/challenges/leave_challenge.html', context)


@login_required
def notifications_api(request):
    """API endpoint to get user's notifications"""
    notifications = request.user.notifications.all()[:20]

    # Filter by read status if requested
    filter_unread = request.GET.get('unread_only', 'false').lower() == 'true'
    if filter_unread:
        notifications = notifications.filter(is_read=False)

    # Prepare notification data
    notification_data = []
    for notif in notifications:
        time_diff = timezone.now() - notif.created_at
        if time_diff.days > 0:
            time_ago = f"{time_diff.days}d ago"
        elif time_diff.seconds > 3600:
            time_ago = f"{time_diff.seconds // 3600}h ago"
        elif time_diff.seconds > 60:
            time_ago = f"{time_diff.seconds // 60}m ago"
        else:
            time_ago = "Just now"

        notification_data.append({
            'id': notif.id,
            'type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'link': notif.link,
            'is_read': notif.is_read,
            'time_ago': time_ago,
            'icon': notif.get_icon(),
            'sender_name': notif.sender.get_full_name() or notif.sender.username if notif.sender else None,
            'sender_avatar': notif.sender.avatar.url if notif.sender and notif.sender.avatar else None,
        })

    return JsonResponse({'notifications': notification_data})


@login_required
def unread_count_api(request):
    """API endpoint to get unread notification count"""
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(
        Notification, id=notification_id, recipient=request.user
    )
    notification.mark_as_read()
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all user's notifications as read"""
    request.user.notifications.filter(is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    return JsonResponse({'success': True})


@login_required
def notifications_page(request):
    """Full page view of all notifications"""
    notifications = request.user.notifications.all()

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Mark viewed notifications as read
    notification_ids = [n.id for n in page_obj if not n.is_read]
    if notification_ids:
        Notification.objects.filter(
            id__in=notification_ids[:10]  # Mark first 10 as read
        ).update(is_read=True, read_at=timezone.now())

    context = {
        'page_obj': page_obj,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    }
    return render(request, 'accounts/notifications.html', context)

# Helper function to create notifications


def create_notification(recipient, sender, notification_type, title, message, link='', content_object=None):
    """Helper function to create notifications"""
    if recipient == sender:  # Don't notify yourself
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        content_object=content_object
    )
    return notification
