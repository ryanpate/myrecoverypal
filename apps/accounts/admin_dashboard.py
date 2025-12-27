"""
Admin Engagement Dashboard for MyRecoveryPal

Provides key metrics for monitoring user engagement and growth.
Access at: /admin/dashboard/
A/B Testing results at: /admin/dashboard/ab-tests/
"""

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate, TruncWeek
from datetime import timedelta
from .models import (
    User, SocialPost, DailyCheckIn, UserConnection,
    RecoveryGroup, GroupMembership, Milestone, Notification,
    ActivityFeed, SupportMessage
)
from .ab_testing import ABTest, ABTestingService


@staff_member_required
def engagement_dashboard(request):
    """Main engagement dashboard view"""
    now = timezone.now()
    today = now.date()

    # Time ranges
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)

    # ===========================================
    # USER GROWTH METRICS
    # ===========================================

    total_users = User.objects.filter(is_active=True).count()

    new_users_7d = User.objects.filter(
        date_joined__gte=last_7_days, is_active=True
    ).count()

    new_users_30d = User.objects.filter(
        date_joined__gte=last_30_days, is_active=True
    ).count()

    # Users who completed onboarding
    onboarded_users = User.objects.filter(
        has_completed_onboarding=True, is_active=True
    ).count()

    onboarding_rate = round((onboarded_users / total_users * 100), 1) if total_users > 0 else 0

    # Daily signups for chart (last 30 days)
    daily_signups = list(
        User.objects.filter(date_joined__gte=last_30_days)
        .annotate(date=TruncDate('date_joined'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # ===========================================
    # ENGAGEMENT METRICS
    # ===========================================

    # Check-ins
    total_checkins = DailyCheckIn.objects.count()
    checkins_7d = DailyCheckIn.objects.filter(created_at__gte=last_7_days).count()
    checkins_30d = DailyCheckIn.objects.filter(created_at__gte=last_30_days).count()

    # Users who checked in today
    users_checked_in_today = DailyCheckIn.objects.filter(date=today).values('user').distinct().count()

    # Average check-ins per active user (last 30 days)
    active_users_30d = User.objects.filter(
        daily_checkins__created_at__gte=last_30_days
    ).distinct().count()
    avg_checkins_per_user = round(checkins_30d / active_users_30d, 1) if active_users_30d > 0 else 0

    # Posts
    total_posts = SocialPost.objects.count()
    posts_7d = SocialPost.objects.filter(created_at__gte=last_7_days).count()
    posts_30d = SocialPost.objects.filter(created_at__gte=last_30_days).count()

    # Mood distribution (last 30 days)
    mood_distribution = list(
        DailyCheckIn.objects.filter(created_at__gte=last_30_days)
        .values('mood')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ===========================================
    # RETENTION METRICS
    # ===========================================

    # Active users (users who did something in the time period)
    def get_active_users(days):
        cutoff = now - timedelta(days=days)
        return User.objects.filter(
            Q(daily_checkins__created_at__gte=cutoff) |
            Q(social_posts__created_at__gte=cutoff) |
            Q(last_seen__gte=cutoff)
        ).distinct().count()

    active_users_1d = get_active_users(1)
    active_users_7d = get_active_users(7)
    active_users_30d = get_active_users(30)

    # DAU/MAU ratio (stickiness)
    dau_mau_ratio = round((active_users_1d / active_users_30d * 100), 1) if active_users_30d > 0 else 0

    # Users with streaks
    users_with_streaks = 0
    for user in User.objects.filter(is_active=True)[:500]:  # Sample for performance
        if user.get_checkin_streak() >= 3:
            users_with_streaks += 1

    # ===========================================
    # SOCIAL METRICS
    # ===========================================

    # Connections
    total_connections = UserConnection.objects.filter(status='active').count()
    new_connections_7d = UserConnection.objects.filter(
        created_at__gte=last_7_days, status='active'
    ).count()

    # Groups
    total_groups = RecoveryGroup.objects.filter(is_active=True).count()
    total_group_members = GroupMembership.objects.filter(
        status__in=['active', 'moderator', 'admin']
    ).count()

    # Avg members per group
    avg_members_per_group = round(total_group_members / total_groups, 1) if total_groups > 0 else 0

    # ===========================================
    # MILESTONE METRICS
    # ===========================================

    total_milestones = Milestone.objects.count()
    milestones_7d = Milestone.objects.filter(created_at__gte=last_7_days).count()

    # Milestone types distribution
    milestone_types = list(
        Milestone.objects.values('milestone_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ===========================================
    # EMAIL ENGAGEMENT (if tracking fields exist)
    # ===========================================

    welcome_email_1_sent = User.objects.filter(welcome_email_1_sent__isnull=False).count()
    welcome_email_2_sent = User.objects.filter(welcome_email_2_sent__isnull=False).count()
    welcome_email_3_sent = User.objects.filter(welcome_email_3_sent__isnull=False).count()

    # ===========================================
    # TOP USERS
    # ===========================================

    # Most active posters (last 30 days)
    top_posters = list(
        User.objects.filter(social_posts__created_at__gte=last_30_days)
        .annotate(post_count=Count('social_posts'))
        .order_by('-post_count')[:10]
    )

    # Most followed users
    top_followed = list(
        User.objects.annotate(
            follower_count=Count('followers', filter=Q(followers__status='active'))
        ).order_by('-follower_count')[:10]
    )

    # ===========================================
    # WEEKLY TRENDS
    # ===========================================

    weekly_checkins = list(
        DailyCheckIn.objects.filter(created_at__gte=last_90_days)
        .annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    weekly_posts = list(
        SocialPost.objects.filter(created_at__gte=last_90_days)
        .annotate(week=TruncWeek('created_at'))
        .values('week')
        .annotate(count=Count('id'))
        .order_by('week')
    )

    context = {
        # User Growth
        'total_users': total_users,
        'new_users_7d': new_users_7d,
        'new_users_30d': new_users_30d,
        'onboarded_users': onboarded_users,
        'onboarding_rate': onboarding_rate,
        'daily_signups': daily_signups,

        # Engagement
        'total_checkins': total_checkins,
        'checkins_7d': checkins_7d,
        'checkins_30d': checkins_30d,
        'users_checked_in_today': users_checked_in_today,
        'avg_checkins_per_user': avg_checkins_per_user,
        'total_posts': total_posts,
        'posts_7d': posts_7d,
        'posts_30d': posts_30d,
        'mood_distribution': mood_distribution,

        # Retention
        'active_users_1d': active_users_1d,
        'active_users_7d': active_users_7d,
        'active_users_30d': active_users_30d,
        'dau_mau_ratio': dau_mau_ratio,
        'users_with_streaks': users_with_streaks,

        # Social
        'total_connections': total_connections,
        'new_connections_7d': new_connections_7d,
        'total_groups': total_groups,
        'total_group_members': total_group_members,
        'avg_members_per_group': avg_members_per_group,

        # Milestones
        'total_milestones': total_milestones,
        'milestones_7d': milestones_7d,
        'milestone_types': milestone_types,

        # Email
        'welcome_email_1_sent': welcome_email_1_sent,
        'welcome_email_2_sent': welcome_email_2_sent,
        'welcome_email_3_sent': welcome_email_3_sent,

        # Top Users
        'top_posters': top_posters,
        'top_followed': top_followed,

        # Trends
        'weekly_checkins': weekly_checkins,
        'weekly_posts': weekly_posts,

        # Meta
        'now': now,
        'title': 'Engagement Dashboard',
    }

    return render(request, 'admin/engagement_dashboard.html', context)


@staff_member_required
def ab_test_results(request):
    """A/B Testing results dashboard"""

    # Get all tests with their results
    tests = ABTest.objects.all().order_by('-created_at')
    test_results = []

    for test in tests:
        results = ABTestingService.get_test_results(test.name)
        test_results.append({
            'test': test,
            'results': results,
            'is_running': test.is_running(),
        })

    context = {
        'test_results': test_results,
        'title': 'A/B Test Results',
    }

    return render(request, 'admin/ab_test_results.html', context)
