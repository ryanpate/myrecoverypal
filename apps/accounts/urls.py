# Replace your entire apps/accounts/urls.py file with this:

from django.urls import path
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from . import views
from . import payment_views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('onboarding/skip/', views.skip_onboarding, name='skip_onboarding'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='core:index'), name='logout'),

    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             success_url='/accounts/password-reset/done/'),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/accounts/password-reset-complete/'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),

    # User dashboard and profile
    path('', lambda request: redirect('accounts:social_feed'), name='hybrid_landing'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),
    path('invite-friends/', views.invite_friends_view, name='invite_friends'),
    path('invite-friends/send-email/', views.send_invite_email_view, name='send_invite_email'),

    # Milestones
    path('milestones/', views.MilestoneListView.as_view(), name='milestones'),
    path('milestones/add/', views.MilestoneCreateView.as_view(), name='add_milestone'),

    # Community
    #path('community/', views.CommunityView.as_view(), name='community'),
    path('community/', views.EnhancedCommunityView.as_view(), name='community'),
    path('community/suggested/', views.suggested_users, name='suggested_users'),


    # Messages
    path('messages/', views.MessageListView.as_view(), name='messages'),
    path('messages/<int:message_id>/delete/', views.delete_message_view, name='delete_message'),
    path('send-message/<str:username>/', views.send_message_view, name='send_message'),
    
    # Activity Feed URLs
    path('daily-checkin/', views.daily_checkin_view, name='daily_checkin'),
    path('quick-checkin/', views.quick_checkin, name='quick_checkin'),
    path('checkin-status/', views.get_checkin_status, name='checkin_status'),
    path('progress/', views.progress_view, name='progress'),
    path('like-activity/<int:activity_id>/', views.like_activity, name='like_activity'),
    path('comment-on-activity/<int:activity_id>/', views.comment_on_activity, name='comment_on_activity'),

    # Social Feed URLs (MyRecoveryCircle)
    path('social-feed/', views.hybrid_landing_view, name='social_feed'),
    path('social-feed/posts/', views.social_feed_posts_api, name='social_feed_posts_api'),
    path('social-feed/create/', views.create_social_post, name='create_social_post'),
    path('social-feed/post/<int:post_id>/like/', views.like_social_post, name='like_social_post'),
    path('social-feed/post/<int:post_id>/react/', views.react_to_post, name='react_to_post'),
    path('social-feed/post/<int:post_id>/comment/', views.comment_social_post, name='comment_social_post'),
    path('social-feed/post/<int:post_id>/delete/', views.delete_social_post, name='delete_social_post'),
    path('social-feed/post/<int:post_id>/edit/', views.edit_social_post, name='edit_social_post'),
    path('social-feed/comment/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('social-feed/comment/<int:comment_id>/reply/', views.reply_to_comment, name='reply_to_comment'),

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
    path('groups/<int:group_id>/leave/', views.leave_group, name='leave_group'),
    path('groups/<int:group_id>/post/', views.create_group_post, name='create_group_post'),
    path('groups/<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('groups/<int:group_id>/approve/<int:user_id>/', views.approve_member, name='approve_member'),
    path('groups/<int:group_id>/reject/<int:user_id>/', views.reject_member, name='reject_member'),
    path('groups/<int:group_id>/post/<int:post_id>/comment/', views.comment_group_post, name='comment_group_post'),
    path('groups/<int:group_id>/post/<int:post_id>/like/', views.like_group_post, name='like_group_post'),
    path('groups/<int:group_id>/post/<int:post_id>/pin/', views.pin_group_post, name='pin_group_post'),
    path('groups/<int:group_id>/post/<int:post_id>/delete/', views.delete_group_post, name='delete_group_post'),
    path('groups/<int:group_id>/post/<int:post_id>/edit/', views.edit_group_post, name='edit_group_post'),
    path('groups/<int:group_id>/transfer/', views.transfer_group_ownership, name='transfer_group_ownership'),
    path('groups/<int:group_id>/members-for-transfer/', views.get_group_members_for_transfer, name='get_group_members_for_transfer'),
    path('groups/<int:group_id>/archive/', views.archive_group, name='archive_group'),
    path('groups/<int:group_id>/invite/', views.generate_group_invite, name='generate_group_invite'),
    path('groups/<int:group_id>/join-invite/<str:invite_code>/', views.join_group_via_invite, name='join_group_via_invite'),

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
    path('challenges/<int:challenge_id>/checkin/<int:checkin_id>/delete/',
         views.delete_challenge_checkin, name='delete_challenge_checkin'),
    path('challenges/<int:challenge_id>/checkin/<int:checkin_id>/edit/',
         views.edit_challenge_checkin, name='edit_challenge_checkin'),

    # Add these notification URLs
    path('notifications/', views.notifications_page, name='notifications'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notifications/unread-count/',
         views.unread_count_api, name='unread_count_api'),
    path('api/notifications/<int:notification_id>/read/',
         views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/',
         views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('api/update-last-seen/', views.update_last_seen, name='update_last_seen'),

    # Push notification device token endpoints
    path('api/device-token/register/',
         views.register_device_token, name='register_device_token'),
    path('api/device-token/unregister/',
         views.unregister_device_token, name='unregister_device_token'),

    path('request-access/', views.request_access_view, name='request_access'),
    path('admin/approve-waitlist/<int:request_id>/',
         views.admin_approve_waitlist, name='admin_approve_waitlist'),

    # Payment and Subscription URLs
    path('pricing/', payment_views.pricing, name='pricing'),
    path('checkout/create-session/', payment_views.create_checkout_session, name='create_checkout_session'),
    path('payment/success/', payment_views.payment_success, name='payment_success'),
    path('payment/canceled/', payment_views.payment_canceled, name='payment_canceled'),
    path('subscription/', payment_views.subscription_management, name='subscription_management'),
    path('subscription/cancel/', payment_views.cancel_subscription, name='cancel_subscription'),
    path('subscription/reactivate/', payment_views.reactivate_subscription, name='reactivate_subscription'),
    path('subscription/portal/', payment_views.create_customer_portal_session, name='customer_portal'),
    path('webhook/stripe/', payment_views.stripe_webhook, name='stripe_webhook'),

]