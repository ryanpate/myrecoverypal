from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # Dashboard
    path('', views.journal_dashboard, name='dashboard'),

    # Entries
    path('entries/', views.JournalEntryListView.as_view(), name='entry_list'),
    path('entry/<int:pk>/', views.JournalEntryDetailView.as_view(),
         name='entry_detail'),
    path('write/', views.create_entry, name='create_entry'),

    # Guided journaling
    path('guided/', views.guided_entry, name='guided_entry'),
    path('guided/<int:prompt_id>/', views.guided_entry,
         name='guided_entry_with_prompt'),
    path('prompts/', views.PromptsListView.as_view(), name='prompts_list'),

    # Stats and settings
    path('stats/', views.journal_stats, name='stats'),
    path('reminders/', views.manage_reminders, name='manage_reminders'),
]
