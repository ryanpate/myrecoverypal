from django.urls import path
from .views import (
    DashboardView, ProfileView, ProfileUpdateView, 
    SobrietyUpdateView, MilestoneListView
)

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/edit/', ProfileUpdateView.as_view(), name='profile_edit'),
    path('sobriety/', SobrietyUpdateView.as_view(), name='sobriety_update'),
    path('milestones/', MilestoneListView.as_view(), name='milestones'),
]