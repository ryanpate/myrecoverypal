from django.urls import path
from . import audio_views, program_views, reflection_views, views, worksheet_views

app_name = 'resources'

urlpatterns = [
    # Interactive worksheet library
    path('worksheets/', worksheet_views.worksheet_index, name='worksheets'),
    path('worksheets/mine/', worksheet_views.my_worksheets, name='my_worksheets'),
    path('worksheets/entry/<int:pk>/', worksheet_views.worksheet_entry,
         name='worksheet_entry'),
    path('worksheets/entry/<int:pk>/pdf/', worksheet_views.worksheet_entry_pdf,
         name='worksheet_entry_pdf'),
    path('worksheets/entry/<int:pk>/anchor/', worksheet_views.worksheet_entry_coach,
         name='worksheet_entry_coach'),
    path('worksheets/entry/<int:pk>/delete/', worksheet_views.worksheet_entry_delete,
         name='worksheet_entry_delete'),
    # Guided day-by-day programs
    path('programs/', program_views.program_index, name='programs'),
    path('programs/<slug:slug>/', program_views.program_detail, name='program_detail'),
    path('programs/<slug:slug>/start/', program_views.program_enroll, name='program_enroll'),
    path('programs/<slug:slug>/restart/', program_views.program_restart, name='program_restart'),
    path('programs/<slug:slug>/reminders/', program_views.program_reminders, name='program_reminders'),
    path('programs/<slug:slug>/cohort/', program_views.program_cohort_join, name='program_cohort_join'),
    path('programs/<slug:slug>/day/<int:day>/', program_views.program_day, name='program_day'),
    path('programs/<slug:slug>/day/<int:day>/complete/', program_views.program_complete,
         name='program_complete'),
    path('programs/<slug:slug>/day/<int:day>/journal/', program_views.program_journal,
         name='program_journal'),
    # Daily reflection library
    path('reflections/', reflection_views.reflection_index, name='reflections'),
    path('reflections/favorites/', reflection_views.reflection_favorites,
         name='reflection_favorites'),
    path('reflections/<slug:slug>/', reflection_views.reflection_detail,
         name='reflection_detail'),
    path('reflections/<slug:slug>/card.png', reflection_views.reflection_card,
         name='reflection_card'),
    path('reflections/<slug:slug>/favorite/', reflection_views.reflection_favorite,
         name='reflection_favorite'),
    path('reflections/<slug:slug>/journal/', reflection_views.reflection_journal,
         name='reflection_journal'),
    # Audio library (guided sessions + reflections read aloud)
    path('audio/', audio_views.audio_index, name='audio'),
    path('audio/<slug:slug>/', audio_views.audio_detail, name='audio_detail'),
    path('audio/<slug:slug>/play/', audio_views.audio_play, name='audio_play'),
    path('audio/<slug:slug>/preview/', audio_views.audio_preview, name='audio_preview'),
    path('audio/<slug:slug>/reminder/', audio_views.audio_reminder, name='audio_reminder'),
    path('workbook/', worksheet_views.workbook_builder, name='workbook'),
    path('workbook/pdf/', worksheet_views.workbook_pdf, name='workbook_pdf'),
    path('worksheets/<slug:slug>/', worksheet_views.worksheet_detail,
         name='worksheet_detail'),
    path('worksheets/<slug:slug>/pdf/', worksheet_views.worksheet_blank_pdf,
         name='worksheet_blank_pdf'),
    path('worksheets/<slug:slug>/save/', worksheet_views.worksheet_save,
         name='worksheet_save'),

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
