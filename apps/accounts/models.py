from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class User(AbstractUser):
    # Additional fields for recovery
    email = models.EmailField(unique=True)
    sobriety_date = models.DateField(
        null=True, blank=True, help_text="Your sobriety start date")
    recovery_goals = models.TextField(
        blank=True, help_text="Your personal recovery goals")
    is_sponsor = models.BooleanField(
        default=False, help_text="Are you available as a sponsor?")
    bio = models.TextField(blank=True, help_text="Tell us about yourself")
    location = models.CharField(max_length=100, blank=True)

    # Privacy settings
    is_profile_public = models.BooleanField(
        default=False, help_text="Make your profile visible to other members")
    show_sobriety_date = models.BooleanField(
        default=True, help_text="Display your sobriety date on your profile")
    allow_messages = models.BooleanField(
        default=True, help_text="Allow other members to message you")

    # Profile
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Email settings
    email_notifications = models.BooleanField(default=True)
    newsletter_subscriber = models.BooleanField(default=True)

    # Timestamps
    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.username

    def get_days_sober(self):
        if self.sobriety_date:
            return (timezone.now().date() - self.sobriety_date).days
        return 0

    def get_sobriety_milestone(self):
        days = self.get_days_sober()
        if days >= 365:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''}"
        elif days >= 30:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''}"
        else:
            return f"{days} day{'s' if days != 1 else ''}"

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.username})

    @property
    def has_unread_messages(self):
        return self.received_messages.filter(is_read=False).exists()


class Milestone(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date_achieved = models.DateField(default=timezone.now)
    days_sober = models.IntegerField(null=True, blank=True)

    # Milestone types
    MILESTONE_CHOICES = (
        ('days', 'Days Sober'),
        ('personal', 'Personal Achievement'),
        ('health', 'Health Milestone'),
        ('relationship', 'Relationship Milestone'),
        ('career', 'Career Achievement'),
        ('other', 'Other'),
    )
    milestone_type = models.CharField(
        max_length=20, choices=MILESTONE_CHOICES, default='days')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_achieved']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class SupportMessage(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"From {self.sender} to {self.recipient}: {self.subject}"


# NEW ACTIVITY FEED MODELS

class ActivityFeed(models.Model):
    """
    Track all user activities for the community feed
    """
    ACTIVITY_TYPES = (
        ('milestone_created', 'Milestone Created'),
        ('blog_post_published', 'Blog Post Published'),
        ('comment_posted', 'Comment Posted'),
        ('journal_entry_shared', 'Journal Entry Shared'),
        ('user_joined', 'User Joined'),
        ('profile_updated', 'Profile Updated'),
        ('achievement_unlocked', 'Achievement Unlocked'),
        ('support_message_sent', 'Support Message Sent'),
        ('resource_bookmarked', 'Resource Bookmarked'),
        ('check_in_posted', 'Check-in Posted'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    
    # Generic foreign key to link to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Activity details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    
    # Engagement
    likes = models.ManyToManyField(User, blank=True, related_name='liked_activities')
    
    # Metadata
    extra_data = models.JSONField(default=dict, blank=True)  # For additional activity-specific data
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Feed Item'
        verbose_name_plural = 'Activity Feed Items'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    def get_activity_icon(self):
        """Return emoji icon for activity type"""
        icons = {
            'milestone_created': '🏆',
            'blog_post_published': '📝',
            'comment_posted': '💬',
            'journal_entry_shared': '📔',
            'user_joined': '👋',
            'profile_updated': '✏️',
            'achievement_unlocked': '🎉',
            'support_message_sent': '💌',
            'resource_bookmarked': '🔖',
            'check_in_posted': '✅',
        }
        return icons.get(self.activity_type, '📌')
    
    def get_activity_url(self):
        """Get URL for the activity if content_object exists"""
        if self.content_object and hasattr(self.content_object, 'get_absolute_url'):
            try:
                return self.content_object.get_absolute_url()
            except:
                return None
        return None


class DailyCheckIn(models.Model):
    """
    Daily mood/status check-ins for community engagement
    """
    MOOD_CHOICES = [
        (1, '😰 Struggling'),
        (2, '😔 Down'),
        (3, '😐 Okay'),
        (4, '😊 Good'),
        (5, '😄 Great'),
        (6, '🌟 Amazing'),
    ]
    
    CRAVING_LEVEL_CHOICES = [
        (0, 'None'),
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Strong'),
        (4, 'Intense'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_checkins')
    date = models.DateField(default=timezone.now)
    
    # Check-in data
    mood = models.IntegerField(choices=MOOD_CHOICES)
    craving_level = models.IntegerField(choices=CRAVING_LEVEL_CHOICES, default=0)
    energy_level = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 scale
    
    # Optional fields
    gratitude = models.TextField(blank=True, help_text="What are you grateful for today?")
    challenge = models.TextField(blank=True, help_text="What's your biggest challenge today?")
    goal = models.TextField(blank=True, help_text="What's your goal for today?")
    
    # Social sharing
    is_shared = models.BooleanField(default=False, help_text="Share with community")
    
    # Engagement
    likes = models.ManyToManyField(User, blank=True, related_name='liked_checkins')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']  # One check-in per day per user
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"
    
    @property
    def likes_count(self):
        return self.likes.count()
    
    def get_mood_display_with_emoji(self):
        mood_dict = dict(self.MOOD_CHOICES)
        return mood_dict.get(self.mood, '😐 Okay')


class ActivityComment(models.Model):
    """
    Comments on activity feed items
    """
    activity = models.ForeignKey(ActivityFeed, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.activity}"