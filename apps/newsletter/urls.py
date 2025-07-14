from django.urls import path
from . import views

app_name = 'newsletter'

urlpatterns = [
    # Public pages
    path('', views.subscribe_view, name='subscribe'),
    path('success/', views.subscribe_success_view, name='subscribe_success'),
    path('confirm/<uuid:token>/', views.confirm_subscription_view, name='confirm'),
    path('preferences/<uuid:token>/', views.preferences_view, name='preferences'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe_view, name='unsubscribe'),
    path('unsubscribe/', views.unsubscribe_view, name='unsubscribe_form'),
    path('archive/', views.NewsletterListView.as_view(), name='archive'),
    path('preview/<int:pk>/', views.newsletter_preview_view, name='preview'),
    
    # Admin pages (staff only)
    path('dashboard/', views.newsletter_dashboard_view, name='dashboard'),
]