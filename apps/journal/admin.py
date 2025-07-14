from django.contrib import admin
from .models import JournalPrompt, JournalEntry, JournalStreak, JournalReminder

@admin.register(JournalPrompt)
class JournalPromptAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'stage', 'min_days_sober', 'max_days_sober', 'is_active']
    list_filter = ['category', 'stage', 'is_active']
    search_fields = ['title', 'prompt']
    ordering = ['category', 'min_days_sober']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'prompt', 'category', 'stage')
        }),
        ('Follow-up Questions', {
            'fields': ('follow_up_1', 'follow_up_2'),
            'classes': ('collapse',)
        }),
        ('Display Rules', {
            'fields': ('min_days_sober', 'max_days_sober', 'is_active')
        }),
    )

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'prompt', 'mood_rating', 'created_at', 'is_private']
    list_filter = ['created_at', 'mood_rating', 'cravings_today', 'is_private']
    search_fields = ['user__username', 'title', 'content', 'tags']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('user', 'prompt', 'title', 'content')
        }),
        ('Mood & Tracking', {
            'fields': ('mood_rating', 'gratitude_1', 'gratitude_2', 'gratitude_3')
        }),
        ('Sobriety Check-in', {
            'fields': ('cravings_today', 'craving_intensity')
        }),
        ('Meta', {
            'fields': ('tags', 'is_private', 'created_at', 'updated_at')
        }),
    )

@admin.register(JournalStreak)
class JournalStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'longest_streak', 'total_entries', 'last_entry_date']
    search_fields = ['user__username']

@admin.register(JournalReminder)
class JournalReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'time', 'is_active', 'created_at']
    list_filter = ['is_active', 'time']
    search_fields = ['user__username']