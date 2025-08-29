# apps/support_services/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Meeting, SupportService, ServiceSubmission, UserBookmark


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['name', 'day', 'time', 'city', 'state',
                    'attendance_option', 'is_approved', 'is_active']
    list_filter = ['day', 'attendance_option',
                   'is_approved', 'is_active', 'state']
    search_fields = ['name', 'group', 'location', 'city', 'notes']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'group', 'group_notes')
        }),
        ('Schedule', {
            'fields': ('day', 'time', 'end_time', 'timezone')
        }),
        ('Location', {
            'fields': ('attendance_option', 'location', 'address', 'city', 'state',
                       'postal_code', 'country', 'latitude', 'longitude', 'region')
        }),
        ('Online Meeting', {
            'fields': ('conference_url', 'conference_url_notes', 'conference_phone',
                       'conference_phone_notes'),
            'classes': ('collapse',)
        }),
        ('Contact', {
            'fields': ('website', 'email', 'phone', 'mailing_address')
        }),
        ('Meeting Details', {
            'fields': ('types', 'notes')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active', 'submitted_by', 'approved_by',
                       'created_at', 'updated_at')
        }),
    )


@admin.register(SupportService)
class SupportServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'category', 'phone',
                    'is_approved', 'is_active', 'is_featured']
    list_filter = ['type', 'category', 'cost',
                   'is_approved', 'is_active', 'is_featured']
    search_fields = ['name', 'description', 'organization', 'city']
    prepopulated_fields = {'service_id': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    actions = ['approve_services', 'feature_services']

    def approve_services(self, request, queryset):
        updated = queryset.update(is_approved=True, approved_by=request.user)
        self.message_user(request, f'{updated} services approved.')
    approve_services.short_description = 'Approve selected services'

    def feature_services(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} services featured.')
    feature_services.short_description = 'Feature selected services'


@admin.register(ServiceSubmission)
class ServiceSubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission_type', 'get_name',
                    'status', 'submitted_email', 'created_at']
    list_filter = ['submission_type', 'status', 'created_at']
    readonly_fields = ['submission_data', 'created_at', 'updated_at']

    def get_name(self, obj):
        return obj.submission_data.get('name', 'N/A')
    get_name.short_description = 'Name'

    actions = ['approve_submissions']

    def approve_submissions(self, request, queryset):
        approved = 0
        for submission in queryset.filter(status='pending'):
            if submission.approve(request.user):
                approved += 1
        self.message_user(request, f'{approved} submissions approved.')
    approve_submissions.short_description = 'Approve selected submissions'


@admin.register(UserBookmark)
class UserBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_item', 'created_at']
    list_filter = ['created_at']

    def get_item(self, obj):
        if obj.meeting:
            return f"Meeting: {obj.meeting.name}"
        return f"Service: {obj.service.name}"
    get_item.short_description = 'Bookmarked Item'
