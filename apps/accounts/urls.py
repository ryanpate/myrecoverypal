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
    # This should be the correct pattern
    path('edit-profile/', views.edit_profile_view, name='edit_profile'),

    # Milestones
    path('milestones/', views.MilestoneListView.as_view(), name='milestones'),
    path('milestones/add/', views.MilestoneCreateView.as_view(), name='add_milestone'),

    # Community
    path('community/', views.CommunityView.as_view(), name='community'),

    # Messages
    path('messages/', views.MessageListView.as_view(), name='messages'),
    path('send-message/<str:username>/',
         views.send_message_view, name='send_message'),
]
