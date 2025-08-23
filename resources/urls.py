from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    # Class-based views
    path('', views.ResourceListView.as_view(), name='list'),
    path('category/<slug:slug>/',
         views.CategoryDetailView.as_view(), name='category'),
    path('resource/<slug:slug>/', views.ResourceDetailView.as_view(), name='detail'),

    # Educational resources page
    path('educational/', views.educational_resources_view,
         name='educational_resources'),

    # Function-based views
    path('resource/<slug:slug>/bookmark/',
         views.bookmark_resource, name='toggle_bookmark'),
    path('resource/<slug:slug>/rate/', views.rate_resource, name='rate'),
    path('resource/<slug:slug>/download/',
         views.download_resource_pdf, name='download'),
    path('resource/<slug:slug>/interactive/',
         views.interactive_resource_view, name='interactive'),
    path('my-bookmarks/', views.my_bookmarks_view, name='my_bookmarks'),
    path('professional-help/', views.professional_help_view,
         name='professional_help'),

    # Keep existing daily checklist URLs for backward compatibility if they exist
    # Comment these out if daily_checklist_interactive and download_checklist_pdf don't exist in views.py
    # path('tools/daily-checklist/', views.daily_checklist_interactive, name='daily_checklist'),
    # path('tools/daily-checklist/download/', views.download_checklist_pdf, name='download_checklist'),

    # AJAX endpoint for saving interactive progress
    path('ajax/save-progress/<slug:slug>/',
         views.save_interactive_progress, name='save_progress'),
]
