# apps/support_services/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import RegexValidator
import json

# Note: We removed the ArrayField import since SQLite doesn't support it
# If you're using PostgreSQL, uncomment the next line:
# from django.contrib.postgres.fields import ArrayField


class Meeting(models.Model):
    """Recovery meeting following Meeting Guide API specification"""

    DAY_CHOICES = [
        (0, 'Sunday'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
    ]

    ATTENDANCE_CHOICES = [
        ('in_person', 'In-Person'),
        ('online', 'Online'),
        ('hybrid', 'Hybrid'),
    ]

    MEETING_TYPES = [
        ('11', '11th Step Meditation'),
        ('12x12', '12 Steps & 12 Traditions'),
        ('A', 'Secular/Agnostic'),
        ('ABSI', 'As Bill Sees It'),
        ('BA', 'Babysitting Available'),
        ('B', 'Big Book'),
        ('H', 'Birthday'),
        ('BRK', 'Breakfast'),
        ('BUS', 'Business'),
        ('CF', 'Child-Friendly'),
        ('C', 'Closed'),
        ('AL-AN', 'Concurrent with Al-Anon'),
        ('AL', 'Concurrent with Alateen'),
        ('XT', 'Cross Talk Permitted'),
        ('DR', 'Daily Reflections'),
        ('D', 'Discussion'),
        ('DD', 'Dual Diagnosis'),
        ('EN', 'English'),
        ('FF', 'Fragrance Free'),
        ('FR', 'French'),
        ('G', 'Gay'),
        ('GR', 'Grapevine'),
        ('IT', 'Italian'),
        ('JA', 'Japanese'),
        ('KOR', 'Korean'),
        ('L', 'Lesbian'),
        ('LIT', 'Literature'),
        ('LS', 'Living Sober'),
        ('LGBTQ', 'LGBTQ'),
        ('MED', 'Meditation'),
        ('M', 'Men'),
        ('N', 'Native American'),
        ('BE', 'Newcomer'),
        ('NS', 'No Smoking'),
        ('O', 'Open'),
        ('ONL', 'Online'),
        ('POC', 'People of Color'),
        ('POL', 'Polish'),
        ('POR', 'Portuguese'),
        ('P', 'Professionals'),
        ('PUN', 'Punjabi'),
        ('RUS', 'Russian'),
        ('SM', 'Smoking Permitted'),
        ('S', 'Spanish'),
        ('SP', 'Speaker'),
        ('ST', 'Step Meeting'),
        ('TR', 'Tradition Study'),
        ('T', 'Transgender'),
        ('X', 'Wheelchair Access'),
        ('XB', 'Wheelchair-Accessible Bathroom'),
        ('W', 'Women'),
        ('Y', 'Young People'),
    ]

    # Required fields
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)

    # Schedule fields
    day = models.IntegerField(choices=DAY_CHOICES, null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='America/Chicago')

    # Location fields
    location = models.CharField(max_length=255, blank=True)
    formatted_address = models.CharField(max_length=500, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=2, default='US')
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True)
    region = models.CharField(max_length=100, blank=True)

    # Group information
    group = models.CharField(max_length=255, blank=True)
    group_notes = models.TextField(blank=True)

    # Contact information
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mailing_address = models.CharField(max_length=500, blank=True)

    # Online meeting fields
    conference_url = models.URLField(blank=True)
    conference_url_notes = models.TextField(blank=True)
    conference_phone = models.CharField(max_length=30, blank=True)
    conference_phone_notes = models.TextField(blank=True)
    attendance_option = models.CharField(
        max_length=20, choices=ATTENDANCE_CHOICES, default='in_person')

    # Meeting types (stored as JSON)
    types = models.JSONField(default=list, blank=True)

    # Donation options
    venmo = models.CharField(max_length=50, blank=True)
    square = models.CharField(max_length=50, blank=True)
    paypal = models.CharField(max_length=50, blank=True)

    # Additional fields
    notes = models.TextField(blank=True)

    # Status fields
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_meetings'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_meetings'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day', 'time', 'name']
        indexes = [
            models.Index(fields=['day', 'time']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_approved', 'is_active']),
        ]

    def __str__(self):
        day_display = self.get_day_display() if self.day is not None else 'No day set'
        time_display = self.time.strftime(
            '%I:%M %p') if self.time else 'No time set'
        return f"{self.name} - {day_display} {time_display}"

    def to_meeting_guide_format(self):
        """Convert to Meeting Guide API format"""
        data = {
            'name': self.name,
            'slug': self.slug,
            'updated': self.updated_at.isoformat(),
        }

        # Add optional fields if they exist
        optional_fields = [
            'day', 'time', 'end_time', 'timezone', 'types',
            'location', 'formatted_address', 'address', 'city',
            'state', 'postal_code', 'country', 'latitude', 'longitude',
            'region', 'group', 'group_notes', 'website', 'email', 'phone',
            'mailing_address', 'conference_url', 'conference_url_notes',
            'conference_phone', 'conference_phone_notes', 'attendance_option',
            'notes', 'venmo', 'square', 'paypal'
        ]

        for field in optional_fields:
            value = getattr(self, field)
            if value:
                if field == 'time' or field == 'end_time':
                    data[field] = value.strftime('%H:%M') if value else None
                elif field == 'latitude' or field == 'longitude':
                    data[field] = float(value) if value else None
                else:
                    data[field] = value

        return data


class SupportService(models.Model):
    """Support services including helplines, treatment facilities, etc."""

    SERVICE_TYPES = [
        ('helpline', 'Helpline'),
        ('support_group', 'Support Group'),
        ('treatment_facility', 'Treatment Facility'),
        ('online_resource', 'Online Resource'),
        ('community_service', 'Community Service'),
        ('recovery_program', 'Recovery Program'),
    ]

    CATEGORY_CHOICES = [
        ('local', 'Local'),
        ('regional', 'Regional'),
        ('national', 'National'),
        ('online', 'Online'),
    ]

    COST_CHOICES = [
        ('free', 'Free'),
        ('donation', 'Donation Based'),
        ('sliding_scale', 'Sliding Scale'),
        ('insurance', 'Insurance Accepted'),
        ('fee_required', 'Fee Required'),
        ('unknown', 'Unknown'),
    ]

    # Basic information
    service_id = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    organization = models.CharField(max_length=255, blank=True)
    description = models.TextField()

    # Contact information
    phone = models.CharField(max_length=30, blank=True)
    phone_display = models.CharField(max_length=50, blank=True)
    text_support = models.CharField(max_length=100, blank=True)
    chat_support = models.URLField(blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)

    # Location (for physical facilities)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    formatted_address = models.CharField(max_length=500, blank=True)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True)

    # Service details (using JSONField for SQLite compatibility)
    hours = models.CharField(max_length=100, blank=True)
    languages = models.JSONField(default=list, blank=True)
    services = models.JSONField(default=list, blank=True)
    specializations = models.JSONField(default=list, blank=True)
    insurance_accepted = models.JSONField(default=list, blank=True)
    cost = models.CharField(
        max_length=20, choices=COST_CHOICES, default='unknown')

    # Formats
    # ['in-person', 'online', 'hybrid', 'phone']
    formats = models.JSONField(default=list, blank=True)

    # Meeting finder URL (for support groups)
    meeting_finder = models.URLField(blank=True)
    approach = models.TextField(blank=True)

    # Status fields
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_services'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_services'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'type', 'name']
        indexes = [
            models.Index(fields=['type', 'category']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['is_approved', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    def to_json(self):
        """Convert to JSON format for API"""
        return {
            'id': self.service_id,
            'name': self.name,
            'type': self.type,
            'category': self.category,
            'organization': self.organization,
            'description': self.description,
            'phone': self.phone,
            'phone_display': self.phone_display,
            'text_support': self.text_support,
            'chat_support': self.chat_support,
            'website': self.website,
            'email': self.email,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'formatted_address': self.formatted_address,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'hours': self.hours,
            'languages': self.languages,
            'services': self.services,
            'specializations': self.specializations,
            'insurance_accepted': self.insurance_accepted,
            'cost': self.get_cost_display(),
            'formats': self.formats,
            'meeting_finder': self.meeting_finder,
            'approach': self.approach,
            'updated': self.updated_at.isoformat(),
        }


class ServiceSubmission(models.Model):
    """Track submissions for moderation"""

    SUBMISSION_TYPES = [
        ('meeting', 'Meeting'),
        ('service', 'Support Service'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('needs_info', 'Needs More Information'),
    ]

    submission_type = models.CharField(max_length=20, choices=SUBMISSION_TYPES)
    submission_data = models.JSONField()

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    review_notes = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_submissions'
    )
    submitted_email = models.EmailField(blank=True)
    submitted_phone = models.CharField(max_length=20, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_submission_type_display()} - {self.get_status_display()} - {self.created_at}"

    def approve(self, user):
        """Approve and create the actual meeting or service"""
        self.status = 'approved'
        self.reviewed_by = user
        self.reviewed_at = timezone.now()

        if self.submission_type == 'meeting':
            # Create Meeting from submission data
            meeting = Meeting(**self.submission_data)
            meeting.is_approved = True
            meeting.approved_by = user
            meeting.submitted_by = self.submitted_by
            meeting.save()
        elif self.submission_type == 'service':
            # Create SupportService from submission data
            service = SupportService(**self.submission_data)
            service.is_approved = True
            service.approved_by = user
            service.submitted_by = self.submitted_by
            service.save()

        self.save()
        return True


class UserBookmark(models.Model):
    """Allow users to bookmark meetings and services"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_bookmarks'
    )
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(
        SupportService, on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Meeting reminder settings
    reminder_enabled = models.BooleanField(default=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [
            ['user', 'meeting'],
            ['user', 'service'],
        ]

    def __str__(self):
        if self.meeting:
            return f"{self.user.username} - {self.meeting.name}"
        return f"{self.user.username} - {self.service.name}"
