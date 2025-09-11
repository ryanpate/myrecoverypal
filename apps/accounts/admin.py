from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Milestone, SupportMessage, ActivityFeed, DailyCheckIn, ActivityComment


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active',
                    'sobriety_date', 'get_days_sober', 'is_sponsor']
    list_filter = ['is_active', 'is_staff',
                   'is_sponsor', 'newsletter_subscriber']

    fieldsets = UserAdmin.fieldsets + (
        ('Recovery Information', {
            'fields': ('sobriety_date', 'recovery_goals', 'is_sponsor')
        }),
        ('Profile', {
            'fields': ('bio', 'location', 'avatar')
        }),
        ('Privacy Settings', {
            'fields': ('is_profile_public', 'show_sobriety_date', 'allow_messages')
        }),
        ('Email Preferences', {
            'fields': ('email_notifications', 'newsletter_subscriber')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'sobriety_date')
        }),
    )


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'milestone_type',
                    'date_achieved', 'days_sober']
    list_filter = ['milestone_type', 'date_achieved']
    search_fields = ['user__username', 'title', 'description']
    date_hierarchy = 'date_achieved'


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'subject', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username',
                     'recipient__username', 'subject', 'message']
    date_hierarchy = 'created_at'


@admin.register(ActivityFeed)
class ActivityFeedAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'title', 'is_public', 'created_at', 'likes_count']
    list_filter = ['activity_type', 'is_public', 'created_at']
    search_fields = ['user__username', 'title', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'likes_count']
    
    def likes_count(self, obj):
        return obj.likes_count
    likes_count.short_description = 'Likes'


@admin.register(DailyCheckIn)
class DailyCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'mood', 'craving_level', 'energy_level', 'is_shared', 'likes_count']
    list_filter = ['mood', 'craving_level', 'energy_level', 'is_shared', 'date']
    search_fields = ['user__username', 'gratitude', 'challenge', 'goal']
    date_hierarchy = 'date'
    readonly_fields = ['created_at', 'likes_count']
    
    def likes_count(self, obj):
        return obj.likes_count
    likes_count.short_description = 'Likes'


@admin.register(ActivityComment)
class ActivityCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'content', 'activity__title']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


# Register the custom user admin
admin.site.register(User, CustomUserAdmin)