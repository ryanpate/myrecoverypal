# SETUP AND INTEGRATION GUIDE FOR SUPPORT SERVICES

# ============================================
# 1. CREATE THE APP
# ============================================
# Run this command in your project root:
# python manage.py startapp support_services

# Move it to the apps directory:
# mv support_services apps/

# ============================================
# 2. apps/support_services/urls.py
# ============================================

from apps.support_services.models import Meeting, SupportService
import requests
import json
from django.utils import timezone
from django.utils.text import slugify
from django.core.management.base import BaseCommand
from django.urls import path, include
from .models import Meeting, SupportService, ServiceSubmission, UserBookmark
from django.utils.html import format_html
from django.contrib import admin
from django.urls import path
from . import views

app_name = 'support_services'

urlpatterns = [
    # Main pages
    path('', views.support_services_home, name='home'),

    # Meetings
    path('meetings/', views.meeting_list, name='meeting_list'),
    path('meetings/submit/', views.submit_meeting, name='submit_meeting'),
    path('meetings/<slug:slug>/', views.meeting_detail, name='meeting_detail'),

    # Services
    path('services/', views.service_list, name='service_list'),
    path('services/submit/', views.submit_service, name='submit_service'),
    path('services/<slug:service_id>/',
         views.service_detail, name='service_detail'),

    # Crisis resources
    path('crisis/', views.crisis_resources, name='crisis_resources'),

    # User features
    path('bookmarks/', views.my_bookmarks, name='my_bookmarks'),
    path('bookmark/<str:item_type>/<int:item_id>/',
         views.bookmark_toggle, name='bookmark_toggle'),

    # API endpoints
    path('api/meetings.json', views.meeting_guide_json, name='meeting_guide_json'),
    path('api/services.json', views.support_services_json, name='services_json'),
    path('api/nearby/', views.nearby_meetings, name='nearby_meetings'),
]

# ============================================
# 3. apps/support_services/admin.py
# ============================================


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
        ('7th Tradition', {
            'fields': ('venmo', 'square', 'paypal'),
            'classes': ('collapse',)
        }),
        ('Meeting Details', {
            'fields': ('types', 'notes')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active', 'submitted_by', 'approved_by',
                       'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('submitted_by', 'approved_by')


@admin.register(SupportService)
class SupportServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'category', 'phone_display',
                    'is_approved', 'is_active', 'is_featured']
    list_filter = ['type', 'category', 'cost',
                   'is_approved', 'is_active', 'is_featured']
    search_fields = ['name', 'description', 'organization', 'city']
    prepopulated_fields = {'service_id': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('service_id', 'name', 'type', 'category', 'organization', 'description')
        }),
        ('Contact', {
            'fields': ('phone', 'phone_display', 'text_support', 'chat_support',
                       'website', 'email')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'postal_code', 'formatted_address',
                       'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Service Details', {
            'fields': ('hours', 'languages', 'services', 'specializations',
                       'insurance_accepted', 'cost', 'formats')
        }),
        ('Support Group Info', {
            'fields': ('meeting_finder', 'approach'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_approved', 'is_active', 'is_featured', 'submitted_by',
                       'approved_by', 'created_at', 'updated_at')
        }),
    )

    actions = ['approve_services', 'feature_services']

    def approve_services(self, request, queryset):
        updated = queryset.update(is_approved=True, approved_by=request.user)
        self.message_user(request, f'{updated} services approved.')
    approve_services.short_description = 'Approve selected services'

    def feature_services(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} services featured.')
    feature_services.short_description = 'Feature selected services'

    def phone_display(self, obj):
        if obj.phone_display:
            return obj.phone_display
        return obj.phone
    phone_display.short_description = 'Phone'


@admin.register(ServiceSubmission)
class ServiceSubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission_type', 'get_name', 'status', 'submitted_by',
                    'submitted_email', 'created_at', 'action_buttons']
    list_filter = ['submission_type', 'status', 'created_at']
    search_fields = ['submission_data', 'submitted_email']
    readonly_fields = ['submission_type',
                       'submission_data', 'created_at', 'updated_at']

    fieldsets = (
        ('Submission', {
            'fields': ('submission_type', 'submission_data', 'status', 'review_notes')
        }),
        ('Submitter', {
            'fields': ('submitted_by', 'submitted_email', 'submitted_phone')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_name(self, obj):
        return obj.submission_data.get('name', 'N/A')
    get_name.short_description = 'Name'

    def action_buttons(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a class="button" href="/admin/support_services/servicesubmission/{}/change/">Review</a>',
                obj.pk
            )
        return obj.get_status_display()
    action_buttons.short_description = 'Actions'

    actions = ['approve_submissions', 'reject_submissions']

    def approve_submissions(self, request, queryset):
        approved = 0
        for submission in queryset.filter(status='pending'):
            if submission.approve(request.user):
                approved += 1
        self.message_user(
            request, f'{approved} submissions approved and created.')
    approve_submissions.short_description = 'Approve selected submissions'

    def reject_submissions(self, request, queryset):
        updated = queryset.update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} submissions rejected.')
    reject_submissions.short_description = 'Reject selected submissions'


@admin.register(UserBookmark)
class UserBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_item', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'notes']

    def get_item(self, obj):
        if obj.meeting:
            return f"Meeting: {obj.meeting.name}"
        return f"Service: {obj.service.name}"
    get_item.short_description = 'Bookmarked Item'

# ============================================
# 4. UPDATE settings.py
# ============================================


# Add to INSTALLED_APPS:
INSTALLED_APPS = [
    # ... existing apps ...
    'apps.support_services',
]

# Note: Google API key for geocoding has been removed
# Geocoding functionality is no longer supported

# ============================================
# 5. UPDATE recovery_hub/urls.py
# ============================================

# Add to your main urls.py:

urlpatterns = [
    # ... existing patterns ...
    path('support/', include('apps.support_services.urls')),
]

# ============================================
# 6. CREATE MANAGEMENT COMMAND
# ============================================
# Create file: apps/support_services/management/commands/import_meeting_guide.py


class Command(BaseCommand):
    help = 'Import meetings from Meeting Guide JSON feed or local file'

    def add_arguments(self, parser):
        parser.add_argument(
            'source',
            type=str,
            help='URL or file path to Meeting Guide JSON'
        )
        parser.add_argument(
            '--approve',
            action='store_true',
            help='Auto-approve imported meetings'
        )

    def handle(self, *args, **options):
        source = options['source']
        auto_approve = options.get('approve', False)

        # Load JSON data
        if source.startswith('http'):
            response = requests.get(source)
            data = response.json()
        else:
            with open(source, 'r') as f:
                data = json.load(f)

        # Import meetings
        imported = 0
        skipped = 0

        meetings_data = data if isinstance(
            data, list) else data.get('meetings', [])

        for meeting_data in meetings_data:
            # Check if meeting exists
            slug = meeting_data.get('slug')
            if not slug:
                slug = slugify(meeting_data['name']) + \
                    '-import-' + str(imported)

            if Meeting.objects.filter(slug=slug).exists():
                skipped += 1
                continue

            # Create meeting
            meeting = Meeting(
                name=meeting_data['name'],
                slug=slug,
                is_approved=auto_approve,
                is_active=True
            )

            # Map fields
            field_mapping = {
                'day': 'day',
                'time': 'time',
                'end_time': 'end_time',
                'timezone': 'timezone',
                'types': 'types',
                'location': 'location',
                'formatted_address': 'formatted_address',
                'address': 'address',
                'city': 'city',
                'state': 'state',
                'postal_code': 'postal_code',
                'country': 'country',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'region': 'region',
                'group': 'group',
                'group_notes': 'group_notes',
                'website': 'website',
                'email': 'email',
                'phone': 'phone',
                'conference_url': 'conference_url',
                'conference_url_notes': 'conference_url_notes',
                'attendance_option': 'attendance_option',
                'notes': 'notes',
                'venmo': 'venmo',
                'square': 'square',
                'paypal': 'paypal',
            }

            for json_field, model_field in field_mapping.items():
                if json_field in meeting_data:
                    setattr(meeting, model_field, meeting_data[json_field])

            meeting.save()
            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {imported} meetings ({skipped} skipped)'
            )
        )
