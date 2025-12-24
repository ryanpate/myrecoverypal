"""
Accounts app views for MyRecoveryPal.
Handles user authentication, profiles, social features, and recovery tracking.
"""
from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView, ListView, CreateView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Prefetch, Avg
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .models import GroupPost, User, Milestone, SupportMessage, ActivityFeed, DailyCheckIn, ActivityComment, UserConnection, SponsorRelationship, RecoveryPal, RecoveryGroup, GroupMembership, SocialPost, SocialPostComment
from .forms import CustomUserCreationForm, UserProfileForm, MilestoneForm, SupportMessageForm, SponsorRequestForm, RecoveryPalForm, RecoveryGroupForm, GroupPostForm, GroupMembershipForm
from .signals import create_profile_update_activity
from django.core.paginator import Paginator
from django.db import transaction
from datetime import timedelta, datetime
from django.conf import settings
import cloudinary.uploader
from django.core.serializers import serialize
import json
from django.views.decorators.csrf import csrf_exempt
from .invite_models import WaitlistRequest, InviteCode, SystemSettings
from .forms import WaitlistRequestForm, CustomUserCreationFormWithInvite
from .models import (
    GroupChallenge, ChallengeParticipant, ChallengeCheckIn,
    ChallengeComment, ChallengeBadge, UserChallengeBadge, Notification
)
from .forms import (
    GroupChallengeForm, JoinChallengeForm, ChallengeCheckInForm,
    ChallengeCommentForm, PalRequestForm, ChallengeFilterForm
)
from .payment_models import Subscription

def register_view(request):
    """
    Registration view with invite code requirement
    """
    # Check system settings
    settings = SystemSettings.get_settings()

    # Check if we've hit user limit
    if settings.max_users:
        current_user_count = User.objects.filter(is_active=True).count()
        if current_user_count >= settings.max_users:
            messages.error(
                request,
                'We\'ve reached our maximum capacity. Please join the waitlist!'
            )
            return redirect('accounts:request_access')

    # If not in invite-only mode, use regular registration
    if not settings.invite_only_mode:
        if request.method == 'POST':
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password1')

                # Create subscription for user
                Subscription.objects.get_or_create(
                    user=user,
                    defaults={
                        'tier': 'free',
                        'status': 'active',
                    }
                )

                messages.success(
                    request, f'Welcome to the community, {username}!')

                user = authenticate(username=username, password=password)
                login(request, user)

                if user.sobriety_date:
                    Milestone.objects.create(
                        user=user,
                        title="Started My Recovery Journey",
                        description="The day I decided to change my life.",
                        date_achieved=user.sobriety_date,
                        milestone_type='days',
                        days_sober=0
                    )

                # Redirect to onboarding for new users
                return redirect('accounts:onboarding')
        else:
            form = CustomUserCreationForm()

        return render(request, 'registration/register.html', {
            'form': form,
        })

    # Invite-only mode is enabled
    # Check if invite code is in URL
    invite_code = request.GET.get('invite', '')

    if request.method == 'POST':
        form = CustomUserCreationFormWithInvite(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')

            # Create subscription for user
            Subscription.objects.get_or_create(
                user=user,
                defaults={
                    'tier': 'free',
                    'status': 'active',
                }
            )

            messages.success(request, f'Welcome to the community, {username}!')

            user = authenticate(username=username, password=password)
            login(request, user)

            if user.sobriety_date:
                Milestone.objects.create(
                    user=user,
                    title="Started My Recovery Journey",
                    description="The day I decided to change my life.",
                    date_achieved=user.sobriety_date,
                    milestone_type='days',
                    days_sober=0
                )

            # Redirect to onboarding for new users
            return redirect('accounts:onboarding')
    else:
        # Pre-fill invite code if provided in URL
        initial = {'invite_code': invite_code} if invite_code else {}
        form = CustomUserCreationFormWithInvite(initial=initial)

    context = {
        'form': form,
        'invite_only': True,
        'settings': settings,
    }
    return render(request, 'registration/register.html', context)


@login_required
def onboarding_view(request):
    """
    Multi-step onboarding wizard for new users.
    Step 1: Profile photo + bio
    Step 2: Recovery info (goals, sobriety date)
    Step 3: Follow suggested users
    """
    user = request.user

    # If already completed onboarding, redirect to social feed
    if user.has_completed_onboarding:
        return redirect('accounts:social_feed')

    # Get current step from query param (default to 1)
    step = int(request.GET.get('step', 1))

    if request.method == 'POST':
        if step == 1:
            # Handle profile photo and bio
            bio = request.POST.get('bio', '').strip()
            location = request.POST.get('location', '').strip()

            user.bio = bio[:500]  # Max 500 chars
            user.location = location[:100]

            # Handle avatar upload
            if 'avatar' in request.FILES:
                try:
                    avatar_file = request.FILES['avatar']
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        avatar_file,
                        folder='avatars/',
                        transformation=[
                            {'width': 300, 'height': 300, 'crop': 'fill', 'gravity': 'face'}
                        ]
                    )
                    user.avatar = result['secure_url']
                except Exception as e:
                    messages.warning(request, 'Could not upload photo. You can add it later in settings.')

            user.save()
            return redirect(reverse('accounts:onboarding') + '?step=2')

        elif step == 2:
            # Handle recovery info
            recovery_goals = request.POST.get('recovery_goals', '').strip()
            sobriety_date = request.POST.get('sobriety_date', '').strip()
            is_profile_public = request.POST.get('is_profile_public') == 'on'

            user.recovery_goals = recovery_goals
            user.is_profile_public = is_profile_public

            if sobriety_date:
                try:
                    from datetime import datetime
                    user.sobriety_date = datetime.strptime(sobriety_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            user.save()
            return redirect(reverse('accounts:onboarding') + '?step=3')

        elif step == 3:
            # Handle following users
            users_to_follow = request.POST.getlist('follow_users')

            for user_id in users_to_follow:
                try:
                    user_to_follow = User.objects.get(id=user_id)
                    if user_to_follow != user:
                        user.follow_user(user_to_follow)
                except User.DoesNotExist:
                    pass

            # Mark onboarding as complete
            user.has_completed_onboarding = True
            user.save()

            messages.success(request, "Welcome to MyRecoveryPal! Your profile is all set up.")
            return redirect('accounts:social_feed')

    # GET request - show appropriate step
    context = {
        'step': step,
        'total_steps': 3,
        'progress_percent': int((step / 3) * 100),
    }

    if step == 3:
        # Get suggested users for step 3
        excluded_ids = list(user.get_following().values_list('id', flat=True))
        excluded_ids.append(user.id)

        # Get active users with profiles
        suggested = User.objects.filter(
            is_active=True,
            is_profile_public=True,
        ).exclude(
            id__in=excluded_ids
        ).exclude(
            bio=''
        ).order_by('-date_joined')[:10]

        # If not enough users with bios, get any active public users
        if suggested.count() < 5:
            more_users = User.objects.filter(
                is_active=True,
                is_profile_public=True,
            ).exclude(
                id__in=excluded_ids
            ).exclude(
                id__in=suggested.values_list('id', flat=True)
            ).order_by('-last_seen', '-date_joined')[:10 - suggested.count()]
            suggested = list(suggested) + list(more_users)

        context['suggested_users'] = suggested

    return render(request, 'accounts/onboarding.html', context)


@login_required
def skip_onboarding(request):
    """Allow users to skip onboarding and complete it later"""
    user = request.user
    user.has_completed_onboarding = True
    user.save()
    messages.info(request, "You can complete your profile anytime in Settings.")
    return redirect('accounts:social_feed')


@login_required
def invite_friends_view(request):
    """
    Allow users to generate and share invite codes to grow the community.
    """
    user = request.user

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate':
            # Check if user already has an active multi-use code
            existing_code = InviteCode.objects.filter(
                created_by=user,
                status='active',
                max_uses__gt=1,
                uses_remaining__gt=0
            ).first()

            if existing_code:
                messages.info(request, "You already have an active invite code!")
            else:
                # Generate a new multi-use invite code for this user
                invite_code = InviteCode.objects.create(
                    created_by=user,
                    max_uses=10,  # Each user can invite up to 10 people
                    uses_remaining=10,
                    notes=f"Personal invite code for {user.username}"
                )
                messages.success(request, "Your invite code has been created! Share it with friends.")

        return redirect('accounts:invite_friends')

    # Get user's active invite codes
    my_codes = InviteCode.objects.filter(
        created_by=user,
        status='active',
        uses_remaining__gt=0
    ).order_by('-created_at')

    # Get stats on successful invites
    successful_invites = InviteCode.objects.filter(
        created_by=user,
        status='used'
    ).count()

    # Count people who used any of user's codes
    people_invited = User.objects.filter(
        used_invite_codes__created_by=user
    ).distinct().count()

    # Build the invite URL for the first active code
    invite_url = None
    primary_code = my_codes.first()
    if primary_code:
        invite_url = f"{settings.SITE_URL}/accounts/register/?invite={primary_code.code}"

    context = {
        'my_codes': my_codes,
        'primary_code': primary_code,
        'invite_url': invite_url,
        'successful_invites': successful_invites,
        'people_invited': people_invited,
    }

    return render(request, 'accounts/invite_friends.html', context)


@require_http_methods(["GET", "POST"])
def request_access_view(request):
    """
    Waitlist request form
    """
    settings = SystemSettings.get_settings()

    # Check if waitlist is enabled
    if not settings.waitlist_enabled:
        messages.error(request, settings.registration_closed_message)
        return redirect('core:index')

    if request.method == 'POST':
        form = WaitlistRequestForm(request.POST)
        if form.is_valid():
            waitlist_request = form.save()

            # Auto-approve if enabled
            if settings.auto_approve_waitlist:
                invite_code = waitlist_request.approve()
                # Optionally send email here
                # invite_code.send_invite_email()

                messages.success(
                    request,
                    f'You\'ve been approved! Your invite code is: {invite_code.code}'
                )
                return redirect('accounts:register')
            else:
                messages.success(
                    request,
                    'Thank you! We\'ll review your request and send you an invite code soon.'
                )
                return redirect('core:index')
    else:
        form = WaitlistRequestForm()

    context = {
        'form': form,
        'settings': settings
    }
    return render(request, 'registration/request_access.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def admin_approve_waitlist(request, request_id):
    """
    Quick approve from admin interface
    """
    import logging

    logger = logging.getLogger('apps.accounts')
    waitlist_request = get_object_or_404(WaitlistRequest, id=request_id)

    if waitlist_request.status == 'pending':
        invite_code = waitlist_request.approve(admin_user=request.user)

        # Try to send email synchronously with error handling
        try:
            logger.info(
                f"Attempting to send invite email to {waitlist_request.email}")
            success = invite_code.send_invite_email()

            if success:
                messages.success(
                    request,
                    f'✅ Approved! Invite code <strong>{invite_code.code}</strong> generated and emailed to {waitlist_request.email}'
                )
            else:
                messages.warning(
                    request,
                    f'⚠️ Approved! Invite code <strong>{invite_code.code}</strong> generated for {waitlist_request.email}. '
                    f'Email failed to send - please copy this code and send manually.'
                )

        except Exception as e:
            logger.error(
                f"Email sending failed for {waitlist_request.email}: {e}", exc_info=True)
            messages.warning(
                request,
                f'⚠️ Approved! Invite code <strong>{invite_code.code}</strong> generated for {waitlist_request.email}. '
                f'Email error: {str(e)}. Please copy this code and send manually.'
            )
    else:
        messages.info(request, 'This request has already been processed.')

    return redirect('admin:accounts_waitlistrequest_changelist')

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

    # Social posts for mobile feed (gracefully handle if table doesn't exist yet)
    try:
        social_posts = SocialPost.objects.select_related('author').prefetch_related(
            'likes',
            'comments__author'
        ).all()[:10]

        # Filter posts based on visibility
        visible_social_posts = []
        for post in social_posts:
            if post.is_visible_to(user):
                visible_social_posts.append(post)

        context['social_posts'] = visible_social_posts
    except Exception:
        # Migration not run yet, social posts table doesn't exist
        context['social_posts'] = []

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
class RecoveryGroupListView(LoginRequiredMixin, ListView):
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

class RecoveryGroupDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a recovery group"""
    model = RecoveryGroup
    template_name = 'accounts/groups/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()

        # Get user's membership status
        membership = None
        is_member = False
        is_admin = False
        is_moderator = False
        if self.request.user.is_authenticated:
            membership = GroupMembership.objects.filter(
                user=self.request.user,
                group=group,
                status__in=['active', 'moderator', 'admin', 'pending']
            ).first()
            is_member = membership and membership.status in ['active', 'moderator', 'admin']
            is_admin = membership and membership.status == 'admin'
            is_moderator = membership and membership.status in ['admin', 'moderator']

        context['membership'] = membership
        context['is_member'] = is_member
        context['is_admin'] = is_admin
        context['is_moderator'] = is_moderator

        # Get group members (limit to 12 for display)
        context['members'] = User.objects.filter(
            group_memberships__group=group,
            group_memberships__status__in=['active', 'moderator', 'admin']
        ).distinct()[:12]

        # Get pending members for admins/moderators
        if is_moderator:
            context['pending_members'] = GroupMembership.objects.filter(
                group=group,
                status='pending'
            ).select_related('user').order_by('-created_at')
        else:
            context['pending_members'] = []

        # Get recent posts if user is a member (with comments)
        if is_member:
            context['recent_posts'] = group.posts.select_related('author').prefetch_related(
                'comments__author'
            ).order_by('-is_pinned', '-created_at')[:10]
        else:
            context['recent_posts'] = []

        # Get all members for transfer ownership (admin only)
        if is_admin:
            context['transferable_members'] = GroupMembership.objects.filter(
                group=group,
                status__in=['active', 'moderator']
            ).select_related('user')
        else:
            context['transferable_members'] = []

        return context


@login_required
def create_group(request):
    """Create a new recovery group"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        group_type = request.POST.get('group_type', '')
        privacy_level = request.POST.get('privacy_level', 'public')
        location = request.POST.get('location', '').strip()
        meeting_schedule = request.POST.get('meeting_schedule', '').strip()
        max_members = request.POST.get('max_members', '')
        group_color = request.POST.get('group_color', '#52b788')

        # Check if user is trying to create a private/secret group
        if privacy_level in ['private', 'secret']:
            if not (hasattr(request.user, 'subscription') and request.user.subscription.is_premium()):
                messages.warning(
                    request,
                    'Creating private groups is a Premium feature. Upgrade now to create private groups!'
                )
                return redirect('accounts:pricing')

        if name and description and group_type:
            group = RecoveryGroup.objects.create(
                name=name,
                description=description,
                group_type=group_type,
                privacy_level=privacy_level,
                location=location,
                meeting_schedule=meeting_schedule,
                max_members=int(max_members) if max_members else None,
                group_color=group_color,
                creator=request.user
            )

            # Auto-add creator as admin member
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                status='admin',
                joined_date=timezone.now().date()
            )

            messages.success(request, f'Group "{name}" created successfully!')
            return redirect('accounts:group_detail', pk=group.id)
        else:
            messages.error(request, 'Please fill in all required fields (name, description, and group type).')

    context = {
        'group_types': RecoveryGroup.GROUP_TYPES,
    }
    return render(request, 'accounts/groups/create_group.html', context)


@login_required
def my_groups(request):
    """User's joined groups"""
    from .models import GroupMembership

    # Get memberships (not groups) - template expects membership objects with .group attribute
    memberships = GroupMembership.objects.filter(
        user=request.user,
        status__in=['active', 'moderator', 'admin']
    ).select_related('group', 'group__creator').order_by('-last_active', '-joined_date')

    return render(request, 'accounts/groups/my_groups.html', {'memberships': memberships})


@login_required
@require_POST
def join_group(request, group_id):
    """Join a recovery group"""
    from .models import RecoveryGroup, GroupMembership
    from django.utils import timezone

    try:
        group = get_object_or_404(RecoveryGroup, id=group_id)

        # Check if user is already a member
        existing = GroupMembership.objects.filter(
            user=request.user,
            group=group,
            status__in=['active', 'moderator', 'admin', 'pending']
        ).first()

        if existing:
            return JsonResponse({
                'success': False,
                'message': 'You are already a member of this group.'
            })

        # Check group limit for free users
        if not (hasattr(request.user, 'subscription') and request.user.subscription.is_premium()):
            current_groups = GroupMembership.objects.filter(
                user=request.user,
                status__in=['active', 'moderator', 'admin']
            ).count()

            if current_groups >= 2:
                return JsonResponse({
                    'success': False,
                    'message': 'You\'ve reached the free tier limit of 2 groups. Upgrade to Premium for unlimited groups!',
                    'redirect': '/accounts/pricing/'
                })

        # Check if group is full
        if group.is_full:
            return JsonResponse({
                'success': False,
                'message': 'This group has reached its maximum capacity.'
            })

        # Create membership
        status = 'pending' if group.privacy_level == 'private' else 'active'
        membership = GroupMembership.objects.create(
            user=request.user,
            group=group,
            status=status,
            joined_date=timezone.now().date() if status == 'active' else None
        )

        # Send notifications
        from .models import Notification
        joiner_name = request.user.get_full_name() or request.user.username

        if status == 'active':
            message = f'You have successfully joined {group.name}!'
            # Notify group admins/moderators about new member
            admin_members = GroupMembership.objects.filter(
                group=group,
                status__in=['admin', 'moderator']
            ).select_related('user')
            for admin in admin_members:
                if admin.user != request.user:
                    Notification.objects.create(
                        recipient=admin.user,
                        sender=request.user,
                        notification_type='group_join',
                        title=f'New member in {group.name}',
                        message=f'{joiner_name} has joined {group.name}',
                        link=f'/accounts/groups/{group.id}/'
                    )
        else:
            message = f'Your request to join {group.name} is pending approval.'
            # Notify admins about pending request
            admin_members = GroupMembership.objects.filter(
                group=group,
                status__in=['admin', 'moderator']
            ).select_related('user')
            for admin in admin_members:
                Notification.objects.create(
                    recipient=admin.user,
                    sender=request.user,
                    notification_type='group_invite',
                    title=f'Membership request for {group.name}',
                    message=f'{joiner_name} has requested to join {group.name}',
                    link=f'/accounts/groups/{group.id}/'
                )

        return JsonResponse({
            'success': True,
            'message': message,
            'status': status
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=400)


@login_required
@require_POST
def create_group_post(request, group_id):
    """Create a post within a recovery group"""
    from .models import RecoveryGroup, GroupMembership, GroupPost

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if user is a member
    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['active', 'moderator', 'admin']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'You must be a member of this group to post.'
        }, status=403)

    post_type = request.POST.get('post_type', 'discussion')
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    is_anonymous = request.POST.get('is_anonymous') == 'on'

    if not title or not content:
        return JsonResponse({
            'success': False,
            'message': 'Title and content are required.'
        }, status=400)

    post = GroupPost.objects.create(
        author=request.user,
        group=group,
        post_type=post_type,
        title=title,
        content=content,
        is_anonymous=is_anonymous
    )

    # Update membership last_active
    membership.last_active = timezone.now()
    membership.save(update_fields=['last_active'])

    # Notify group members about new post
    poster_name = 'Someone' if is_anonymous else (request.user.get_full_name() or request.user.username)
    notify_group_members(
        group=group,
        sender=None if is_anonymous else request.user,
        notification_type='group_post',
        title=f'New post in {group.name}',
        message=f'{poster_name} posted "{title}" in {group.name}',
        link=f'/accounts/groups/{group.id}/',
        exclude_user=request.user
    )

    return JsonResponse({
        'success': True,
        'message': 'Post created successfully!',
        'post_id': post.id
    })


@login_required
@require_POST
def leave_group(request, group_id):
    """Leave a recovery group"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['active', 'moderator']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'You are not a member of this group.'
        }, status=400)

    # Prevent admin from leaving (they must transfer ownership first)
    if membership.status == 'admin':
        return JsonResponse({
            'success': False,
            'message': 'As the group administrator, you cannot leave. Transfer ownership first.'
        }, status=400)

    membership.status = 'left'
    membership.left_date = timezone.now().date()
    membership.save()

    return JsonResponse({
        'success': True,
        'message': f'You have left {group.name}.'
    })


@login_required
@require_POST
def approve_member(request, group_id, user_id):
    """Approve a pending member request"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin or moderator
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['admin', 'moderator']
    ).first()

    if not admin_membership:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to approve members.'
        }, status=403)

    # Get the pending membership
    pending_membership = GroupMembership.objects.filter(
        user_id=user_id,
        group=group,
        status='pending'
    ).first()

    if not pending_membership:
        return JsonResponse({
            'success': False,
            'message': 'No pending request found for this user.'
        }, status=404)

    # Approve the membership
    pending_membership.status = 'active'
    pending_membership.joined_date = timezone.now().date()
    pending_membership.save()

    return JsonResponse({
        'success': True,
        'message': f'{pending_membership.user.username} has been approved to join the group.'
    })


@login_required
@require_POST
def reject_member(request, group_id, user_id):
    """Reject a pending member request"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin or moderator
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['admin', 'moderator']
    ).first()

    if not admin_membership:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to reject members.'
        }, status=403)

    # Get the pending membership
    pending_membership = GroupMembership.objects.filter(
        user_id=user_id,
        group=group,
        status='pending'
    ).first()

    if not pending_membership:
        return JsonResponse({
            'success': False,
            'message': 'No pending request found for this user.'
        }, status=404)

    # Delete the membership request
    username = pending_membership.user.username
    pending_membership.delete()

    return JsonResponse({
        'success': True,
        'message': f'{username}\'s request has been rejected.'
    })


@login_required
def edit_group(request, group_id):
    """Edit group settings - only for group admin"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status='admin'
    ).first()

    if not admin_membership:
        messages.error(request, 'You do not have permission to edit this group.')
        return redirect('accounts:group_detail', pk=group_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        group_type = request.POST.get('group_type', '')
        privacy_level = request.POST.get('privacy_level', 'public')
        location = request.POST.get('location', '').strip()
        meeting_schedule = request.POST.get('meeting_schedule', '').strip()
        max_members = request.POST.get('max_members', '')
        group_color = request.POST.get('group_color', '#52b788')

        # Check premium for private/secret groups
        if privacy_level in ['private', 'secret'] and group.privacy_level == 'public':
            if not (hasattr(request.user, 'subscription') and request.user.subscription.is_premium()):
                messages.warning(request, 'Private groups require a Premium subscription.')
                return redirect('accounts:edit_group', group_id=group_id)

        if name and description and group_type:
            group.name = name
            group.description = description
            group.group_type = group_type
            group.privacy_level = privacy_level
            group.location = location
            group.meeting_schedule = meeting_schedule
            group.max_members = int(max_members) if max_members else None
            group.group_color = group_color
            group.save()

            messages.success(request, 'Group settings updated successfully!')
            return redirect('accounts:group_detail', pk=group_id)
        else:
            messages.error(request, 'Please fill in all required fields.')

    context = {
        'group': group,
        'group_types': RecoveryGroup.GROUP_TYPES,
    }
    return render(request, 'accounts/groups/edit_group.html', context)


def notify_group_members(group, sender, notification_type, title, message, link, exclude_user=None):
    """Helper function to notify all active group members"""
    from .models import GroupMembership, Notification

    members = GroupMembership.objects.filter(
        group=group,
        status__in=['active', 'moderator', 'admin']
    ).select_related('user')

    notifications = []
    for membership in members:
        if membership.user != exclude_user and membership.user != sender:
            notifications.append(Notification(
                recipient=membership.user,
                sender=sender,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link
            ))

    if notifications:
        Notification.objects.bulk_create(notifications)


@login_required
@require_POST
def comment_group_post(request, group_id, post_id):
    """Add a comment to a group post"""
    from .models import RecoveryGroup, GroupMembership, GroupPost, GroupPostComment, Notification

    group = get_object_or_404(RecoveryGroup, id=group_id)
    post = get_object_or_404(GroupPost, id=post_id, group=group)

    # Check if user is a member
    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['active', 'moderator', 'admin']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'You must be a member of this group to comment.'
        }, status=403)

    content = request.POST.get('content', '').strip()
    is_anonymous = request.POST.get('is_anonymous') == 'on'

    if not content:
        return JsonResponse({
            'success': False,
            'message': 'Comment cannot be empty.'
        }, status=400)

    comment = GroupPostComment.objects.create(
        post=post,
        author=request.user,
        content=content,
        is_anonymous=is_anonymous
    )

    # Notify the post author (if not commenting on own post)
    if post.author != request.user:
        commenter_name = 'Someone' if is_anonymous else request.user.get_full_name() or request.user.username
        Notification.objects.create(
            recipient=post.author,
            sender=None if is_anonymous else request.user,
            notification_type='group_comment',
            title='New comment on your post',
            message=f'{commenter_name} commented on your post "{post.title}" in {group.name}',
            link=f'/accounts/groups/{group.id}/'
        )

    # Update membership last_active
    membership.last_active = timezone.now()
    membership.save(update_fields=['last_active'])

    return JsonResponse({
        'success': True,
        'message': 'Comment added successfully!',
        'comment_id': comment.id,
        'author': 'Anonymous' if is_anonymous else (request.user.get_full_name() or request.user.username),
        'content': content,
        'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p')
    })


@login_required
@require_POST
def transfer_group_ownership(request, group_id):
    """Transfer group ownership to another member"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status='admin'
    ).first()

    if not admin_membership:
        return JsonResponse({
            'success': False,
            'message': 'Only the group admin can transfer ownership.'
        }, status=403)

    new_owner_id = request.POST.get('new_owner_id')
    if not new_owner_id:
        return JsonResponse({
            'success': False,
            'message': 'Please select a new owner.'
        }, status=400)

    # Get the new owner's membership
    new_owner_membership = GroupMembership.objects.filter(
        user_id=new_owner_id,
        group=group,
        status__in=['active', 'moderator']
    ).first()

    if not new_owner_membership:
        return JsonResponse({
            'success': False,
            'message': 'Selected user is not an active member of this group.'
        }, status=400)

    # Transfer ownership
    new_owner_membership.status = 'admin'
    new_owner_membership.save()

    admin_membership.status = 'active'
    admin_membership.save()

    # Update the group creator
    group.creator = new_owner_membership.user
    group.save()

    # Notify the new owner
    from .models import Notification
    Notification.objects.create(
        recipient=new_owner_membership.user,
        sender=request.user,
        notification_type='group_invite',
        title='You are now the group admin',
        message=f'{request.user.get_full_name() or request.user.username} has transferred ownership of "{group.name}" to you.',
        link=f'/accounts/groups/{group.id}/'
    )

    return JsonResponse({
        'success': True,
        'message': f'Ownership transferred to {new_owner_membership.user.username} successfully!'
    })


@login_required
def get_group_members_for_transfer(request, group_id):
    """Get list of members eligible to receive ownership"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status='admin'
    ).first()

    if not admin_membership:
        return JsonResponse({'success': False, 'message': 'Not authorized'}, status=403)

    members = GroupMembership.objects.filter(
        group=group,
        status__in=['active', 'moderator']
    ).select_related('user')

    member_list = [{
        'id': m.user.id,
        'username': m.user.username,
        'name': m.user.get_full_name() or m.user.username,
        'status': m.status
    } for m in members]

    return JsonResponse({'success': True, 'members': member_list})


@login_required
@require_POST
def archive_group(request, group_id):
    """Archive a group (soft delete) - only for group admin"""
    from .models import RecoveryGroup, GroupMembership

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if current user is admin
    admin_membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status='admin'
    ).first()

    if not admin_membership:
        return JsonResponse({
            'success': False,
            'message': 'Only the group admin can archive this group.'
        }, status=403)

    # Archive the group (set is_active to False)
    group.is_active = False
    group.save()

    # Notify all members that the group has been archived
    notify_group_members(
        group=group,
        sender=request.user,
        notification_type='group_invite',
        title=f'{group.name} has been archived',
        message=f'The group "{group.name}" has been archived by its administrator.',
        link='/accounts/groups/',
        exclude_user=request.user
    )

    return JsonResponse({
        'success': True,
        'message': f'Group "{group.name}" has been archived successfully.'
    })


@login_required
@require_POST
def like_group_post(request, group_id, post_id):
    """Like or unlike a group post"""
    from .models import RecoveryGroup, GroupMembership, GroupPost

    group = get_object_or_404(RecoveryGroup, id=group_id)
    post = get_object_or_404(GroupPost, id=post_id, group=group)

    # Check if user is a member
    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['active', 'moderator', 'admin']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'You must be a member of this group to like posts.'
        }, status=403)

    # Toggle like
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
        message = 'Post unliked'
    else:
        post.likes.add(request.user)
        liked = True
        message = 'Post liked'

        # Notify post author (if not liking own post and not anonymous)
        if post.author != request.user and not post.is_anonymous:
            from .models import Notification
            Notification.objects.create(
                recipient=post.author,
                sender=request.user,
                notification_type='like',
                title='Someone liked your post',
                message=f'{request.user.get_full_name() or request.user.username} liked your post "{post.title}" in {group.name}',
                link=f'/accounts/groups/{group.id}/'
            )

    return JsonResponse({
        'success': True,
        'message': message,
        'liked': liked,
        'likes_count': post.likes.count()
    })


@login_required
@require_POST
def pin_group_post(request, group_id, post_id):
    """Pin or unpin a group post - admin/moderator only"""
    from .models import RecoveryGroup, GroupMembership, GroupPost

    group = get_object_or_404(RecoveryGroup, id=group_id)
    post = get_object_or_404(GroupPost, id=post_id, group=group)

    # Check if user is admin or moderator
    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['admin', 'moderator']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'Only admins and moderators can pin posts.'
        }, status=403)

    # Toggle pin
    post.is_pinned = not post.is_pinned
    post.save()

    return JsonResponse({
        'success': True,
        'message': f'Post {"pinned" if post.is_pinned else "unpinned"} successfully.',
        'is_pinned': post.is_pinned
    })


@login_required
def generate_group_invite(request, group_id):
    """Generate or get invite link for a group"""
    from .models import RecoveryGroup, GroupMembership
    import hashlib
    import time

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Check if user is admin or moderator
    membership = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['admin', 'moderator']
    ).first()

    if not membership:
        return JsonResponse({
            'success': False,
            'message': 'Only admins and moderators can generate invite links.'
        }, status=403)

    # Generate a simple invite code based on group id and a secret
    # In production, you'd want to store these in a model with expiry
    invite_code = hashlib.md5(f"{group.id}-{group.created_at}".encode()).hexdigest()[:12]

    # Build the invite URL
    invite_url = request.build_absolute_uri(f'/accounts/groups/{group.id}/join-invite/{invite_code}/')

    return JsonResponse({
        'success': True,
        'invite_url': invite_url,
        'invite_code': invite_code,
        'group_name': group.name
    })


@login_required
def join_group_via_invite(request, group_id, invite_code):
    """Join a group via invite link"""
    from .models import RecoveryGroup, GroupMembership
    import hashlib

    group = get_object_or_404(RecoveryGroup, id=group_id)

    # Verify invite code
    expected_code = hashlib.md5(f"{group.id}-{group.created_at}".encode()).hexdigest()[:12]

    if invite_code != expected_code:
        messages.error(request, 'Invalid or expired invite link.')
        return redirect('accounts:groups_list')

    # Check if already a member
    existing = GroupMembership.objects.filter(
        user=request.user,
        group=group,
        status__in=['active', 'moderator', 'admin', 'pending']
    ).first()

    if existing:
        if existing.status == 'pending':
            messages.info(request, 'Your membership is pending approval.')
        else:
            messages.info(request, 'You are already a member of this group.')
        return redirect('accounts:group_detail', pk=group.id)

    # Check group capacity
    if group.is_full:
        messages.error(request, 'This group has reached its maximum capacity.')
        return redirect('accounts:groups_list')

    # Create membership (bypasses private group approval for invite links)
    GroupMembership.objects.create(
        user=request.user,
        group=group,
        status='active',
        joined_date=timezone.now().date()
    )

    messages.success(request, f'Welcome to {group.name}!')
    return redirect('accounts:group_detail', pk=group.id)


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

    # Check message limit for free users
    if not (hasattr(request.user, 'subscription') and request.user.subscription.is_premium()):
        from datetime import datetime
        messages_this_month = request.user.sent_messages.filter(
            sent_at__month=datetime.now().month,
            sent_at__year=datetime.now().year
        ).count()

        if messages_this_month >= 10:
            messages.warning(
                request,
                'You\'ve reached the free tier limit of 10 messages per month. '
                'Upgrade to Premium for unlimited messaging!'
            )
            return redirect('accounts:pricing')

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

# Update the EnhancedCommunityView class
class EnhancedCommunityView(LoginRequiredMixin, ListView):
    """Enhanced community view with follow functionality and online status"""
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

        # NEW: Online filter
        if connection_filter == 'online':
            # Show users active in the last 5 minutes
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            queryset = queryset.filter(last_seen__gte=five_minutes_ago)
        elif connection_filter == 'following' and self.request.user.is_authenticated:
            queryset = queryset.filter(
                id__in=self.request.user.get_following())
        elif connection_filter == 'sponsors':
            queryset = queryset.filter(is_sponsor=True)
        elif connection_filter == 'new':
            queryset = queryset.filter(
                date_joined__gte=timezone.now() - timedelta(days=30)
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

        # Order by last_seen to show most recently active first
        return queryset.select_related('profile').order_by('-last_seen', '-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate online count
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        online_count = User.objects.filter(
            is_active=True,
            last_seen__gte=five_minutes_ago
        ).count()

        context['online_count'] = online_count

        if self.request.user.is_authenticated:
            user = self.request.user

            # Update user's last_seen
            user.last_seen = timezone.now()
            user.save(update_fields=['last_seen'])

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


# Add this new view to handle AJAX updates of last_seen
@login_required
@require_POST
def update_last_seen(request):
    """AJAX endpoint to update user's last seen timestamp"""
    request.user.last_seen = timezone.now()
    request.user.save(update_fields=['last_seen'])
    return JsonResponse({'status': 'updated', 'timestamp': request.user.last_seen.isoformat()})

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

    # Check challenge creation limits
    if not (hasattr(request.user, 'subscription') and request.user.subscription.is_premium()):
        # Free users can't create challenges
        messages.warning(
            request,
            'Creating challenges is a Premium feature. Upgrade to Premium or Pro to create and lead your own challenges!'
        )
        return redirect('accounts:pricing')
    elif hasattr(request.user, 'subscription') and request.user.subscription.tier == 'premium':
        # Premium users limited to 3 active challenges
        active_challenges = GroupChallenge.objects.filter(
            creator=request.user,
            status__in=['active', 'upcoming']
        ).count()

        if active_challenges >= 3:
            messages.warning(
                request,
                'You\'ve reached the Premium limit of 3 active challenges. Upgrade to Pro for unlimited challenge creation!'
            )
            return redirect('accounts:pricing')

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


# Social Feed Views

def social_feed_view(request):
    """Display the social media feed"""
    try:
        # Get posts visible to the current user
        posts = SocialPost.objects.select_related('author').prefetch_related(
            'likes',
            'comments__author'
        ).all()

        # Filter posts based on visibility
        visible_posts = []
        for post in posts:
            if post.is_visible_to(request.user):
                visible_posts.append(post)

        # For anonymous users, limit to 3 posts to encourage signup
        is_gated = False
        total_posts_count = len(visible_posts)
        if not request.user.is_authenticated and len(visible_posts) > 3:
            visible_posts = visible_posts[:3]
            is_gated = True

        # Pagination (only for authenticated users)
        if request.user.is_authenticated:
            paginator = Paginator(visible_posts, 20)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
        else:
            page_obj = None

        context = {
            'page_obj': page_obj,
            'posts': visible_posts if not request.user.is_authenticated else page_obj,
            'is_gated': is_gated,
            'total_posts_count': total_posts_count,
        }
        return render(request, 'accounts/social_feed.html', context)
    except Exception:
        # Migration not run yet, show empty feed
        from django.contrib import messages
        messages.warning(request, 'Social feed is currently being set up. Please check back soon!')
        return redirect('accounts:dashboard')


def hybrid_landing_view(request):
    """
    Hybrid landing page combining dashboard stats with social feed.
    Accessible to both authenticated and unauthenticated users.
    Unauthenticated users can only view public posts and cannot post/comment.
    """
    user = request.user

    # Redirect to onboarding if not completed (for authenticated users)
    if user.is_authenticated and hasattr(user, 'has_completed_onboarding') and not user.has_completed_onboarding:
        return redirect('accounts:onboarding')

    try:
        # Initialize context
        context = {}

        if user.is_authenticated:
            # Dashboard data for authenticated users
            days_sober = user.get_days_sober()
            recent_milestones = user.milestones.all()[:5]
            unread_messages = user.received_messages.filter(is_read=False).count()

            # User's connection stats
            followers_count = user.followers_count
            following_count = user.following_count

            # User's recovery connections
            active_sponsor = user.get_active_sponsor()
            recovery_pal = user.get_recovery_pal()
            active_sponsorships = user.get_active_sponsorships()[:3]

            # User's groups
            user_groups = user.get_joined_groups()[:3]

            # Social feed data - Get posts visible to the current user
            posts = SocialPost.objects.select_related('author').prefetch_related(
                'likes',
                'comments__author'
            ).all()

            # Filter posts based on visibility for authenticated users
            visible_posts = []
            for post in posts:
                if post.is_visible_to(user):
                    visible_posts.append(post)

            context.update({
                # User basics
                'user': user,
                'days_sober': days_sober,
                'unread_messages': unread_messages,

                # Milestones
                'recent_milestones': recent_milestones,

                # User connections
                'followers_count': followers_count,
                'following_count': following_count,

                # Recovery connections
                'active_sponsor': active_sponsor,
                'recovery_pal': recovery_pal,
                'active_sponsorships': active_sponsorships,

                # Groups
                'user_groups': user_groups,
            })
        else:
            # For unauthenticated users, only show public posts
            visible_posts = list(SocialPost.objects.select_related('author').prefetch_related(
                'likes',
                'comments__author'
            ).filter(visibility='public'))

        # Pagination (same for both authenticated and unauthenticated)
        paginator = Paginator(visible_posts, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context.update({
            # Social feed
            'page_obj': page_obj,
            'posts': page_obj,
        })

        # Add suggested users if feed is empty (for authenticated users)
        if user.is_authenticated and len(visible_posts) == 0:
            excluded_ids = list(user.get_following().values_list('id', flat=True))
            excluded_ids.append(user.id)

            # Get active users with public profiles to suggest
            suggested_for_empty_feed = User.objects.filter(
                is_active=True,
                is_profile_public=True,
            ).exclude(
                id__in=excluded_ids
            ).order_by('-last_seen', '-date_joined')[:8]

            context['suggested_users_for_feed'] = suggested_for_empty_feed
            context['feed_is_empty'] = True

        return render(request, 'accounts/hybrid_landing.html', context)
    except Exception:
        # Fallback behavior
        if user.is_authenticated:
            from django.contrib import messages
            messages.warning(request, 'Loading your personalized dashboard...')
            return redirect('accounts:dashboard')
        else:
            # For unauthenticated users, redirect to main landing page
            return redirect('core:index')


@login_required
@require_POST
def create_social_post(request):
    """Create a new social post via AJAX"""
    content = request.POST.get('content', '').strip()
    visibility = request.POST.get('visibility', 'public')
    image = request.FILES.get('image')

    # Require either content or image
    if not content and not image:
        return JsonResponse({'error': 'Post must have either text or an image'}, status=400)

    if content and len(content) > 1000:
        return JsonResponse({'error': 'Post is too long (max 1000 characters)'}, status=400)

    try:
        # Create the post
        post = SocialPost.objects.create(
            author=request.user,
            content=content,
            visibility=visibility,
            image=image
        )

        # Return post data for dynamic update
        return JsonResponse({
            'success': True,
            'post': {
                'id': post.id,
                'author': {
                    'username': post.author.username,
                    'full_name': post.author.get_full_name(),
                    'avatar_url': post.author.avatar.url if post.author.avatar else None,
                },
                'content': post.content,
                'image_url': post.image.url if post.image else None,
                'visibility': post.get_visibility_display(),
                'created_at': post.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'likes_count': 0,
                'comments_count': 0,
            }
        })
    except Exception:
        return JsonResponse({'error': 'Social feed is being set up. Please try again later.'}, status=503)


@login_required
@require_POST
def like_social_post(request, post_id):
    """Toggle like on a social post"""
    try:
        post = get_object_or_404(SocialPost, id=post_id)

        # Check if post is visible to user
        if not post.is_visible_to(request.user):
            return JsonResponse({'error': 'Post not found'}, status=404)

        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True

            # Create notification for post author
            if post.author != request.user:
                create_notification(
                    recipient=post.author,
                    sender=request.user,
                    notification_type='like',
                    title='New Like',
                    message=f'{request.user.get_full_name() or request.user.username} liked your post',
                    link=f'/accounts/social-feed/'
                )

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': post.likes.count()
        })
    except Exception:
        return JsonResponse({'error': 'Social feed is being set up. Please try again later.'}, status=503)


@login_required
@require_POST
def comment_social_post(request, post_id):
    """Add a comment to a social post"""
    try:
        post = get_object_or_404(SocialPost, id=post_id)

        # Check if post is visible to user
        if not post.is_visible_to(request.user):
            return JsonResponse({'error': 'Post not found'}, status=404)

        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'error': 'Comment content is required'}, status=400)

        if len(content) > 500:
            return JsonResponse({'error': 'Comment is too long (max 500 characters)'}, status=400)

        # Create comment
        comment = SocialPostComment.objects.create(
            post=post,
            author=request.user,
            content=content
        )

        # Create notification for post author
        if post.author != request.user:
            create_notification(
                recipient=post.author,
                sender=request.user,
                notification_type='comment',
                title='New Comment',
                message=f'{request.user.get_full_name() or request.user.username} commented on your post',
                link=f'/accounts/social-feed/'
            )

        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': {
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name(),
                    'avatar_url': comment.author.avatar.url if comment.author.avatar else None,
                },
                'content': comment.content,
                'created_at': comment.created_at.strftime('%B %d, %Y at %I:%M %p'),
            }
        })
    except Exception:
        return JsonResponse({'error': 'Social feed is being set up. Please try again later.'}, status=503)


@login_required
@require_POST
def delete_social_post(request, post_id):
    """Delete a social post (only by author)"""
    try:
        post = get_object_or_404(SocialPost, id=post_id, author=request.user)
        post.delete()

        return JsonResponse({'success': True})
    except Exception:
        return JsonResponse({'error': 'Social feed is being set up. Please try again later.'}, status=503)


@login_required
@require_POST
def like_comment(request, comment_id):
    """Toggle like on a comment"""
    try:
        comment = get_object_or_404(SocialPostComment, id=comment_id)

        # Check if the post is visible to user
        if not comment.post.is_visible_to(request.user):
            return JsonResponse({'error': 'Comment not found'}, status=404)

        if request.user in comment.likes.all():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True

            # Create notification for comment author
            if comment.author != request.user:
                create_notification(
                    recipient=comment.author,
                    sender=request.user,
                    notification_type='like',
                    title='Comment Liked',
                    message=f'{request.user.get_full_name() or request.user.username} liked your comment',
                    link=f'/accounts/social-feed/'
                )

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': comment.likes_count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=503)


@login_required
@require_POST
def reply_to_comment(request, comment_id):
    """Reply to a comment"""
    try:
        parent_comment = get_object_or_404(SocialPostComment, id=comment_id)

        # Check if the post is visible to user
        if not parent_comment.post.is_visible_to(request.user):
            return JsonResponse({'error': 'Comment not found'}, status=404)

        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({'error': 'Reply content is required'}, status=400)

        if len(content) > 500:
            return JsonResponse({'error': 'Reply is too long (max 500 characters)'}, status=400)

        # Create reply
        reply = SocialPostComment.objects.create(
            post=parent_comment.post,
            author=request.user,
            content=content,
            parent=parent_comment
        )

        # Create notification for comment author
        if parent_comment.author != request.user:
            create_notification(
                recipient=parent_comment.author,
                sender=request.user,
                notification_type='comment',
                title='New Reply',
                message=f'{request.user.get_full_name() or request.user.username} replied to your comment',
                link=f'/accounts/social-feed/'
            )

        return JsonResponse({
            'success': True,
            'reply': {
                'id': reply.id,
                'author': {
                    'username': reply.author.username,
                    'full_name': reply.author.get_full_name(),
                    'avatar_url': reply.author.avatar.url if reply.author.avatar else None,
                },
                'content': reply.content,
                'created_at': reply.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'likes_count': 0,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=503)
