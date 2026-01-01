from django.urls import path
from . import views
from .views import IndexView, AboutView, ContactView


app_name = 'core'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('demo/', views.DemoView.as_view(), name='demo'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('team/', views.TeamView.as_view(), name='team'),
    path('guidelines/', views.GuidelinesView.as_view(), name='guidelines'),
    path('success-stories/', views.SuccessStoriesView.as_view(),name='success_stories'),
    path('cookies/', views.CookiesView.as_view(), name='cookies'),
    path('crisis/', views.CrisisView.as_view(), name='crisis'),
    path('offline/', views.OfflineView.as_view(), name='offline'),
    path('install/', views.InstallGuideView.as_view(), name='install_guide'),
    path('get-app/', views.GetAppView.as_view(), name='get_app'),
    path('sober-grid-alternative/', views.SoberGridAlternativeView.as_view(), name='sober_grid_alternative'),
]