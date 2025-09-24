# Replace your entire apps/accounts/urls.py file with this:

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:index'), name='logout'),

    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),

    # User dashboard and profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),

    # Milestones
    path('milestones/', views.MilestoneListView.as_view(), name='milestones'),
    path('milestones/add/', views.MilestoneCreateView.as_view(), name='add_milestone'),

    # Community
    #path('community/', views.CommunityView.as_view(), name='community'),
    path('community/', views.EnhancedCommunityView.as_view(), name='community'),
    path('community/suggested/', views.suggested_users, name='suggested_users'),


    # Messages
    path('messages/', views.MessageListView.as_view(), name='messages'),
    path('send-message/<str:username>/', views.send_message_view, name='send_message'),
    
    # Activity Feed URLs
    path('daily-checkin/', views.daily_checkin_view, name='daily_checkin'),
    path('like-activity/<int:activity_id>/', views.like_activity, name='like_activity'),
    path('comment-on-activity/<int:activity_id>/', views.comment_on_activity, name='comment_on_activity'),

    # Follow/Following System
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    path('users/<str:username>/followers/', views.followers_list, name='followers_list'),
    path('users/<str:username>/following/', views.following_list, name='following_list'),
    path('suggested-users/', views.suggested_users, name='suggested_users'),

    # Sponsor Relationships
    path('sponsors/', views.sponsor_dashboard, name='sponsor_dashboard'),
    path('sponsors/request/<str:username>/', views.request_sponsor, name='request_sponsor'),
    path('sponsors/respond/<int:relationship_id>/', views.respond_sponsor_request, name='respond_sponsor_request'),

    # Recovery Pal System
    path('pals/', views.pal_dashboard, name='pal_dashboard'),
    path('pals/request/<str:username>/',
         views.request_pal, name='request_pal'),
    # Recovery Groups
    path('groups/', views.RecoveryGroupListView.as_view(), name='groups_list'),
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/<int:pk>/', views.RecoveryGroupDetailView.as_view(), name='group_detail'),
    path('groups/my-groups/', views.my_groups, name='my_groups'),
    path('groups/<int:group_id>/join/', views.join_group, name='join_group'),

    # Challenge System URLs
    path('challenges/', views.challenges_home, name='challenges_home'),
    path('challenges/create/', views.create_challenge, name='create_challenge'),
    path('challenges/create/<int:group_id>/',
         views.create_challenge, name='create_group_challenge'),
    path('challenges/<int:challenge_id>/',
         views.challenge_detail, name='challenge_detail'),
    path('challenges/<int:challenge_id>/join/',
         views.join_challenge, name='join_challenge'),
    path('challenges/<int:challenge_id>/leave/',
         views.leave_challenge, name='leave_challenge'),
    path('challenges/<int:challenge_id>/check-in/',
         views.challenge_check_in, name='challenge_check_in'),
    path('challenges/<int:challenge_id>/feed/',
         views.challenge_feed, name='challenge_feed'),
    path('challenges/<int:challenge_id>/pal/<int:user_id>/',
         views.request_challenge_pal, name='request_challenge_pal'),
    path('my-challenges/', views.my_challenges, name='my_challenges'),
    
    # AJAX endpoints for challenge interactions
    path('ajax/challenge-comment/<int:check_in_id>/',
         views.add_challenge_comment, name='add_challenge_comment'),
    path('ajax/encourage/<int:check_in_id>/',
         views.give_encouragement, name='give_encouragement'),

    # Add these notification URLs
    path('notifications/', views.notifications_page, name='notifications'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/unread-count/',
         views.unread_count_api, name='unread_count_api'),
    path('api/notifications/<int:notification_id>/read/',
         views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/',
         views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('update-last-seen/', views.update_last_seen, name='update_last_seen'),
]