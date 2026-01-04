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
    path('alcohol-recovery-app/', views.AlcoholRecoveryAppView.as_view(), name='alcohol_recovery_app'),
    path('drug-addiction-recovery-app/', views.DrugAddictionRecoveryAppView.as_view(), name='drug_addiction_recovery_app'),
    path('sobriety-counter-app/', views.SobrietyCounterAppView.as_view(), name='sobriety_counter_app'),
    path('free-aa-app/', views.FreeAAAppView.as_view(), name='free_aa_app'),
    path('opioid-recovery-app/', views.OpioidRecoveryAppView.as_view(), name='opioid_recovery_app'),
    path('gambling-addiction-app/', views.GamblingAddictionAppView.as_view(), name='gambling_addiction_app'),
    path('mental-health-recovery-app/', views.MentalHealthRecoveryAppView.as_view(), name='mental_health_recovery_app'),
    path('sobriety-calculator/', views.SobrietyCalculatorView.as_view(), name='sobriety_calculator'),
]