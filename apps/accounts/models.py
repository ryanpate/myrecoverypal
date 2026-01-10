from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from datetime import timedelta
# At the top of apps/accounts/models.py, add:
from .invite_models import WaitlistRequest, InviteCode, SystemSettings
from .payment_models import Subscription, Transaction, PaymentMethod, Invoice, SubscriptionPlan
from .ab_testing import ABTest, ABTestVariant, ABTestAssignment, ABTestConversion

# Recovery stage choices for onboarding and matching
RECOVERY_STAGE_CHOICES = [
    ('starting', 'Just Starting (0-30 days)'),
    ('building', 'Building Foundation (1-6 months)'),
    ('growing', 'Growing Stronger (6-12 months)'),
    ('thriving', 'Thriving (1+ years)'),
    ('supporting', 'Supporting Others'),
]

# Predefined interest categories for onboarding
INTEREST_CATEGORIES = {
    'recovery_focus': [
        ('alcohol', 'Alcohol'),
        ('drugs', 'Drugs'),
        ('prescription', 'Prescription'),
        ('gambling', 'Gambling'),
        ('other', 'Other'),
    ],
    'activities': [
        ('exercise', 'Exercise'),
        ('meditation', 'Meditation'),
        ('art', 'Art & Creative'),
        ('music', 'Music'),
        ('reading', 'Reading'),
        ('outdoors', 'Outdoors'),
        ('cooking', 'Cooking'),
        ('sports', 'Sports'),
    ],
    'support_type': [
        ('peer_support', 'Peer Support'),
        ('professional', 'Professional Help'),
        ('faith_based', 'Faith-Based'),
        ('family', 'Family Support'),
        ('online', 'Online Community'),
    ],
    'goals': [
        ('career', 'Career'),
        ('relationships', 'Relationships'),
        ('health', 'Physical Health'),
        ('mental_health', 'Mental Health'),
        ('education', 'Education'),
        ('hobbies', 'New Hobbies'),
    ],
}


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

    # Engagement email tracking
    welcome_email_1_sent = models.DateTimeField(null=True, blank=True,
        help_text="Welcome email Day 1 sent timestamp")
    welcome_email_2_sent = models.DateTimeField(null=True, blank=True,
        help_text="Welcome email Day 3 sent timestamp")
    welcome_email_3_sent = models.DateTimeField(null=True, blank=True,
        help_text="Welcome email Day 7 sent timestamp")
    last_checkin_reminder_sent = models.DateTimeField(null=True, blank=True,
        help_text="Last check-in reminder sent")
    last_weekly_digest_sent = models.DateTimeField(null=True, blank=True,
        help_text="Last weekly digest sent")

    # Timestamps
    last_seen = models.DateTimeField(null=True, blank=True)

    # Onboarding tracking
    has_completed_onboarding = models.BooleanField(
        default=False, help_text="Has the user completed the onboarding wizard?")

    # Recovery stage for matching (NEW)
    recovery_stage = models.CharField(
        max_length=20,
        choices=RECOVERY_STAGE_CHOICES,
        blank=True,
        null=True,
        help_text="Where user is in their recovery journey"
    )

    # Interests for matching (NEW - stored as JSON array)
    interests = models.JSONField(
        default=list,
        blank=True,
        help_text="User's selected interests for matching"
    )

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

    def get_checkin_streak(self):
        """Calculate consecutive days of check-ins ending today or yesterday"""
        from datetime import timedelta
        today = timezone.now().date()

        # Get all check-in dates for this user, ordered by date descending
        checkin_dates = set(
            self.daily_checkins.values_list('date', flat=True)
        )

        if not checkin_dates:
            return 0

        # Start counting from today or yesterday
        streak = 0
        current_date = today

        # Check if they checked in today
        if today in checkin_dates:
            streak = 1
            current_date = today - timedelta(days=1)
        elif (today - timedelta(days=1)) in checkin_dates:
            # Started yesterday, still counts as active streak
            streak = 1
            current_date = today - timedelta(days=2)
        else:
            return 0

        # Count consecutive days backwards
        while current_date in checkin_dates:
            streak += 1
            current_date -= timedelta(days=1)

        return streak

    def get_milestone_to_celebrate(self):
        """Check if user just hit a sobriety milestone today"""
        days = self.get_days_sober()

        # Define milestone days
        milestones = {
            1: ("1 Day", "Your journey begins! 🌱"),
            7: ("1 Week", "One week strong! 💪"),
            14: ("2 Weeks", "Two weeks of progress! 🌟"),
            30: ("1 Month", "A whole month! Amazing! 🎉"),
            60: ("2 Months", "60 days of strength! 🔥"),
            90: ("3 Months", "90 days - a huge milestone! 🏆"),
            180: ("6 Months", "Half a year of recovery! 🌈"),
            365: ("1 Year", "ONE YEAR! Incredible! 🎊"),
            730: ("2 Years", "Two years of freedom! ⭐"),
            1095: ("3 Years", "Three years strong! 🏅"),
            1825: ("5 Years", "FIVE YEARS! You're an inspiration! 💎"),
        }

        if days in milestones:
            title, message = milestones[days]
            return {
                'days': days,
                'title': title,
                'message': message,
                'is_milestone': True
            }
        return None

    def get_next_milestone(self):
        """Get the next upcoming sobriety milestone"""
        days = self.get_days_sober()
        milestones = [1, 7, 14, 30, 60, 90, 180, 365, 730, 1095, 1825]

        for milestone in milestones:
            if days < milestone:
                return {
                    'days': milestone,
                    'days_until': milestone - days
                }

        # Beyond 5 years, next milestone is next year anniversary
        years = (days // 365) + 1
        next_milestone = years * 365
        return {
            'days': next_milestone,
            'days_until': next_milestone - days
        }

    def get_profile_completion(self):
        """
        Calculate profile completion percentage for progressive onboarding.
        Returns dict with percentage and list of incomplete items.
        """
        completed = 0
        total = 6
        incomplete_items = []

        # Check each profile component
        if self.recovery_stage:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'recovery_stage',
                'label': 'Recovery stage',
                'step': 1
            })

        if self.interests and len(self.interests) > 0:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'interests',
                'label': 'Interests',
                'step': 2
            })

        if self.first_name:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'first_name',
                'label': 'Display name',
                'step': 3
            })

        if self.bio:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'bio',
                'label': 'Bio',
                'step': 3
            })

        if self.avatar:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'avatar',
                'label': 'Profile photo',
                'step': 3
            })

        # Check if user has followed anyone
        if self.following_count > 0:
            completed += 1
        else:
            incomplete_items.append({
                'field': 'following',
                'label': 'Follow someone',
                'step': 5
            })

        percentage = int((completed / total) * 100)

        return {
            'percentage': percentage,
            'completed': completed,
            'total': total,
            'incomplete_items': incomplete_items,
            'is_complete': completed == total,
            'next_step': incomplete_items[0]['step'] if incomplete_items else None
        }

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.username})

    @property
    def has_unread_messages(self):
        return self.received_messages.filter(is_read=False).exists()

    # NEW COMMUNITY METHODS
    def get_following(self):
        """Get users this user is following"""
        return User.objects.filter(
            follower_connections__follower=self,
            follower_connections__connection_type='follow'
        ).distinct()

    def get_followers(self):
        """Get users following this user"""
        return User.objects.filter(
            following_connections__following=self,
            following_connections__connection_type='follow'
        ).distinct()

    def is_following(self, user):
        """Check if this user is following another user"""
        return UserConnection.objects.filter(
            follower=self,
            following=user,
            connection_type='follow'
        ).exists()

    def follow_user(self, user):
        """Follow another user"""
        if user == self:
            return None
        connection, created = UserConnection.objects.get_or_create(
            follower=self,
            following=user,
            connection_type='follow'
        )
        return connection

    def unfollow_user(self, user):
        """Unfollow a user"""
        UserConnection.objects.filter(
            follower=self,
            following=user,
            connection_type='follow'
        ).delete()

    def get_mutual_followers(self):
        """Get users who follow each other mutually"""
        return User.objects.filter(
            follower_connections__follower=self,
            follower_connections__connection_type='follow',
            follower_connections__is_mutual=True
        ).distinct()

    def get_active_sponsorships(self):
        """Get active sponsorships where this user is the sponsor"""
        return self.sponsee_relationships.filter(status='active')

    def get_active_sponsor(self):
        """Get this user's active sponsor"""
        relationship = self.sponsor_relationships.filter(
            status='active').first()
        return relationship.sponsor if relationship else None

    def get_recovery_pal(self):
        """Get active recovery pal"""
        pal = RecoveryPal.objects.filter(
            models.Q(user1=self) | models.Q(user2=self),
            status='active'
        ).first()
        return pal.get_partner(self) if pal else None

    def get_joined_groups(self):
        """Get groups this user has joined"""
        return RecoveryGroup.objects.filter(
            memberships__user=self,
            memberships__status__in=['active', 'moderator', 'admin']
        ).distinct()

    @property
    def followers_count(self):
        return self.follower_connections.filter(connection_type='follow').count()

    @property
    def following_count(self):
        return self.following_connections.filter(connection_type='follow').count()


class UserProfile(models.Model):
    """
    Extended user profile information (keeping for compatibility)
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='profiles/', blank=True)
    phone = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)

    # Privacy settings
    is_public = models.BooleanField(default=False)
    show_sobriety_date = models.BooleanField(default=False)
    allow_messages = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


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

    @property
    def calculated_days_sober(self):
        """
        Dynamically calculate days sober at the time this milestone was achieved
        based on the milestone date and the user's sobriety date
        """
        if self.user.sobriety_date:
            delta = self.date_achieved - self.user.sobriety_date
            return max(0, delta.days)  # Ensure we don't get negative days
        return None

    @property
    def display_milestone_type(self):
        """
        Display the milestone type with calculated days for 'days' type milestones
        """
        if self.milestone_type == 'days':
            days = self.calculated_days_sober
            if days is not None:
                if days == 0:
                    return "Day 1 - Recovery Begins"
                elif days == 1:
                    return "1 Day Sober"
                else:
                    return f"{days} Days Sober"
        return self.get_milestone_type_display()

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


# ACTIVITY FEED MODELS
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

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)

    # Generic foreign key to link to any model
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Activity details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)

    # Engagement
    likes = models.ManyToManyField(
        User, blank=True, related_name='liked_activities')

    # Metadata
    # For additional activity-specific data
    extra_data = models.JSONField(default=dict, blank=True)

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
            'journal_entry_shared': '📓',
            'user_joined': '👋',
            'profile_updated': '✏️',
            'achievement_unlocked': '🎉',
            'support_message_sent': '💌',
            'resource_bookmarked': '📖',
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

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='daily_checkins')
    date = models.DateField(default=timezone.now)

    # Check-in data
    mood = models.IntegerField(choices=MOOD_CHOICES)
    craving_level = models.IntegerField(
        choices=CRAVING_LEVEL_CHOICES, default=0)
    energy_level = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)])  # 1-5 scale

    # Optional fields
    gratitude = models.TextField(
        blank=True, help_text="What are you grateful for today?")
    challenge = models.TextField(
        blank=True, help_text="What's your biggest challenge today?")
    goal = models.TextField(
        blank=True, help_text="What's your goal for today?")

    # Social sharing
    is_shared = models.BooleanField(
        default=False, help_text="Share with community")

    # Engagement
    likes = models.ManyToManyField(
        User, blank=True, related_name='liked_checkins')

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
    activity = models.ForeignKey(
        ActivityFeed, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.activity}"


# COMMUNITY CONNECTION MODELS
class UserConnection(models.Model):
    """
    Handle follow/following relationships between users
    """
    CONNECTION_TYPES = (
        ('follow', 'Following'),
        ('block', 'Blocked'),
        ('friend', 'Friend'),  # For mutual following
    )

    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following_connections'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower_connections'
    )
    connection_type = models.CharField(
        max_length=10,
        choices=CONNECTION_TYPES,
        default='follow'
    )

    # Connection metadata
    created_at = models.DateTimeField(auto_now_add=True)
    # Both users follow each other
    is_mutual = models.BooleanField(default=False)

    class Meta:
        unique_together = ('follower', 'following', 'connection_type')
        indexes = [
            models.Index(fields=['follower', 'connection_type']),
            models.Index(fields=['following', 'connection_type']),
        ]

    def __str__(self):
        return f"{self.follower.username} {self.get_connection_type_display()} {self.following.username}"

    def save(self, *args, **kwargs):
        # Prevent self-following
        if self.follower == self.following:
            raise ValueError("Users cannot follow themselves")

        # Check if connection is mutual BEFORE saving
        if self.connection_type == 'follow' and not kwargs.get('update_fields'):
            mutual_exists = UserConnection.objects.filter(
                follower=self.following,
                following=self.follower,
                connection_type='follow'
            ).exists()

            if mutual_exists:
                self.is_mutual = True

        super().save(*args, **kwargs)

        # Update the other side to be mutual (use .update() to avoid recursion)
        if self.connection_type == 'follow' and self.is_mutual:
            UserConnection.objects.filter(
                follower=self.following,
                following=self.follower,
                connection_type='follow'
            ).update(is_mutual=True)


class SponsorRelationship(models.Model):
    """
    Formal sponsor/sponsee relationships for recovery mentorship
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
        ('terminated', 'Terminated'),
    )

    sponsor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sponsee_relationships'
    )
    sponsee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sponsor_relationships'
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Relationship details
    started_date = models.DateField(null=True, blank=True)
    ended_date = models.DateField(null=True, blank=True)
    notes = models.TextField(
        blank=True, help_text="Private notes about the relationship")

    # Meeting/communication preferences
    meeting_frequency = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., Weekly, Bi-weekly, As needed"
    )
    communication_method = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., Phone calls, In-person, Video chat"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('sponsor', 'sponsee')
        indexes = [
            models.Index(fields=['sponsor', 'status']),
            models.Index(fields=['sponsee', 'status']),
        ]

    def __str__(self):
        return f"{self.sponsor.username} sponsoring {self.sponsee.username} ({self.status})"

    def save(self, *args, **kwargs):
        # Set started_date when status becomes active
        if self.status == 'active' and not self.started_date:
            self.started_date = timezone.now().date()

        # Set ended_date when relationship ends
        if self.status in ['completed', 'terminated'] and not self.ended_date:
            self.ended_date = timezone.now().date()

        super().save(*args, **kwargs)


class RecoveryPal(models.Model):
    """
    Mutual support partnerships between users
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('ended', 'Ended'),
    )

    user1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pal_relationships_as_user1'
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pal_relationships_as_user2'
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Partnership details
    started_date = models.DateField(null=True, blank=True)
    ended_date = models.DateField(null=True, blank=True)

    # Support preferences
    check_in_frequency = models.CharField(
        max_length=50,
        blank=True,
        help_text="How often you want to check in with each other"
    )
    shared_goals = models.TextField(
        blank=True,
        help_text="Shared recovery goals and commitments"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user1', 'user2')
        indexes = [
            models.Index(fields=['user1', 'status']),
            models.Index(fields=['user2', 'status']),
        ]

    def __str__(self):
        return f"Recovery Pals: {self.user1.username} & {self.user2.username}"

    def get_partner(self, user):
        """Get the other user in the pal relationship"""
        return self.user2 if self.user1 == user else self.user1

    def save(self, *args, **kwargs):
        # Ensure user1 has lower ID (prevents duplicate relationships)
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1

        if self.status == 'active' and not self.started_date:
            self.started_date = timezone.now().date()

        if self.status == 'ended' and not self.ended_date:
            self.ended_date = timezone.now().date()

        super().save(*args, **kwargs)


# RECOVERY GROUP MODELS
class RecoveryGroup(models.Model):
    """
    Interest-based support groups for recovery community
    """
    GROUP_TYPES = (
        ('addiction_type', 'By Addiction Type'),
        ('location', 'Location-based'),
        ('recovery_stage', 'Recovery Stage'),
        ('interest', 'Shared Interest'),
        ('age_group', 'Age Group'),
        ('gender', 'Gender-specific'),
        ('family', 'Family/Supporters'),
        ('professional', 'Professional Support'),
    )

    PRIVACY_LEVELS = (
        ('public', 'Public - Anyone can join'),
        ('private', 'Private - Approval required'),
        ('secret', 'Secret - Invitation only'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES)
    privacy_level = models.CharField(
        max_length=10, choices=PRIVACY_LEVELS, default='public')

    # Group settings
    max_members = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    meeting_schedule = models.CharField(max_length=200, blank=True)

    # Group management
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_groups')
    moderators = models.ManyToManyField(
        User, blank=True, related_name='moderated_groups')

    # Group image and branding
    group_image = models.ImageField(upload_to='groups/', blank=True)
    group_color = models.CharField(
        max_length=7, default='#52b788')  # Hex color

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['group_type', 'privacy_level']),
            models.Index(fields=['is_active', 'created_at']),
        ]

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.memberships.filter(status='active').count()

    @property
    def is_full(self):
        if self.max_members:
            return self.member_count >= self.max_members
        return False


class GroupMembership(models.Model):
    """
    Track user membership in recovery groups
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Administrator'),
        ('banned', 'Banned'),
        ('left', 'Left Group'),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(
        RecoveryGroup, on_delete=models.CASCADE, related_name='memberships')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # Membership details
    joined_date = models.DateField(null=True, blank=True)
    left_date = models.DateField(null=True, blank=True)
    role_notes = models.TextField(blank=True)

    # Engagement tracking
    last_active = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'group')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['group', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.status})"

    def save(self, *args, **kwargs):
        # Set joined_date when status becomes active
        if self.status in ['active', 'moderator', 'admin'] and not self.joined_date:
            self.joined_date = timezone.now().date()

        # Set left_date when user leaves
        if self.status in ['left', 'banned'] and not self.left_date:
            self.left_date = timezone.now().date()

        super().save(*args, **kwargs)


class GroupPost(models.Model):
    """
    Posts shared within recovery groups
    """
    POST_TYPES = (
        ('discussion', 'Discussion'),
        ('milestone', 'Milestone Share'),
        ('resource', 'Resource Share'),
        ('question', 'Question'),
        ('support', 'Support Request'),
        ('event', 'Event/Meeting'),
    )

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='group_posts')
    group = models.ForeignKey(
        RecoveryGroup, on_delete=models.CASCADE, related_name='posts')

    post_type = models.CharField(
        max_length=20, choices=POST_TYPES, default='discussion')
    title = models.CharField(max_length=200)
    content = models.TextField()

    # Post engagement
    likes = models.ManyToManyField(
        User, blank=True, related_name='liked_group_posts')
    is_pinned = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['group', 'post_type']),
            models.Index(fields=['author', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} in {self.group.name}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()


class GroupPostComment(models.Model):
    """
    Comments on group posts
    """
    post = models.ForeignKey(
        GroupPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='group_post_comments')
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class GroupChallenge(models.Model):
    """
    Group challenges for recovery milestones and wellness goals
    """
    CHALLENGE_TYPES = (
        ('sobriety', '🎯 Sobriety Challenge'),
        ('wellness', '💪 Wellness Challenge'),
        ('mindfulness', '🧘 Mindfulness Challenge'),
        ('community', '🤝 Community Engagement'),
        ('self_care', '🌿 Self-Care Challenge'),
        ('gratitude', '🙏 Gratitude Challenge'),
        ('exercise', '🏃 Exercise Challenge'),
        ('learning', '📚 Learning Challenge'),
        ('service', '🤲 Service Challenge'),
        ('creativity', '🎨 Creative Challenge'),
    )

    DURATION_CHOICES = (
        (7, '7 Days'),
        (14, '14 Days'),
        (21, '21 Days'),
        (30, '30 Days'),
        (60, '60 Days'),
        (90, '90 Days'),
    )

    STATUS_CHOICES = (
        ('draft', '📝 Draft'),
        ('upcoming', '⏳ Upcoming'),
        ('active', '🔥 Active'),
        ('completed', '✅ Completed'),
        ('cancelled', '❌ Cancelled'),
    )

    # Basic Challenge Info
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPES)

    # Challenge Settings
    duration_days = models.IntegerField(choices=DURATION_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()

    # Rules and Guidelines
    daily_goal_description = models.TextField(
        help_text="What participants need to do each day"
    )
    rules_and_guidelines = models.TextField(blank=True)

    # Group and Creator
    group = models.ForeignKey(
        RecoveryGroup,
        on_delete=models.CASCADE,
        related_name='challenges'
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_challenges'
    )

    # Challenge Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(
        default=True,
        help_text="Allow non-group members to see and join"
    )
    max_participants = models.IntegerField(
        null=True,
        blank=True,
        help_text="Leave blank for unlimited"
    )

    # Engagement Features
    allow_pal_system = models.BooleanField(
        default=True,
        help_text="Allow participants to pair up for accountability"
    )
    enable_leaderboard = models.BooleanField(
        default=True,
        help_text="Show participant progress rankings"
    )
    enable_daily_check_in = models.BooleanField(
        default=True,
        help_text="Require daily check-ins"
    )

    # Rewards and Recognition
    completion_badge_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom badge name for completing this challenge"
    )
    completion_message = models.TextField(
        blank=True,
        help_text="Message shown when someone completes the challenge"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['challenge_type', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.group.name})"

    @property
    def participant_count(self):
        return self.participants.filter(status='active').count()

    @property
    def completion_rate(self):
        active_participants = self.participants.filter(status='active').count()
        if active_participants == 0:
            return 0
        completed_participants = self.participants.filter(
            status='completed').count()
        return round((completed_participants / active_participants) * 100, 1)

    @property
    def days_remaining(self):
        if self.status == 'completed':
            return 0
        today = timezone.now().date()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days

    @property
    def is_full(self):
        if not self.max_participants:
            return False
        return self.participant_count >= self.max_participants

    def can_join(self, user):
        """Check if a user can join this challenge"""
        if self.is_full:
            return False, "Challenge is full"
        if self.status not in ['upcoming', 'active']:
            return False, "Challenge is not accepting participants"
        if self.participants.filter(user=user).exists():
            return False, "Already participating"
        if not self.is_public and not self.group.memberships.filter(
            user=user, status__in=['active', 'moderator', 'admin']
        ).exists():
            return False, "Must be a group member"
        return True, "Can join"

    def save(self, *args, **kwargs):
        # Auto-calculate end_date if not set
        if not self.end_date and self.start_date:
            self.end_date = self.start_date + \
                timezone.timedelta(days=self.duration_days - 1)

        # Auto-update status based on dates
        today = timezone.now().date()
        if self.status == 'draft':
            pass  # Keep as draft until manually activated
        elif today < self.start_date:
            self.status = 'upcoming'
        elif today <= self.end_date:
            self.status = 'active'
        elif today > self.end_date:
            self.status = 'completed'

        super().save(*args, **kwargs)


class ChallengeParticipant(models.Model):
    """
    Track user participation in group challenges
    """
    STATUS_CHOICES = (
        ('active', '🔥 Active'),
        ('completed', '✅ Completed'),
        ('dropped', '😞 Dropped Out'),
        ('paused', '⏸️ Paused'),
    )

    challenge = models.ForeignKey(
        GroupChallenge,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='challenge_participations'
    )

    # Participation Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active')
    joined_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    # Progress Tracking
    days_completed = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)

    # Motivation and Notes
    personal_goal = models.TextField(
        blank=True,
        help_text="Personal goal for this challenge"
    )
    motivation_note = models.TextField(
        blank=True,
        help_text="Why you're taking this challenge"
    )

    # Pal System
    accountability_partner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pal_partnerships'
    )

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('challenge', 'user')
        ordering = ['-days_completed', '-current_streak']
        indexes = [
            models.Index(fields=['challenge', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.challenge.title}"

    @property
    def completion_percentage(self):
        return round((self.days_completed / self.challenge.duration_days) * 100, 1)

    @property
    def is_completed(self):
        return self.days_completed >= self.challenge.duration_days

    def update_progress(self):
        """Update completion status based on check-ins"""
        if self.is_completed and self.status == 'active':
            self.status = 'completed'
            self.completion_date = timezone.now()
            self.save()


class ChallengeCheckIn(models.Model):
    """
    Daily check-ins for challenge participants
    """
    MOOD_CHOICES = (
        ('great', '😄 Great'),
        ('good', '😊 Good'),
        ('okay', '😐 Okay'),
        ('struggling', '😔 Struggling'),
        ('difficult', '😞 Difficult'),
    )

    participant = models.ForeignKey(
        ChallengeParticipant,
        on_delete=models.CASCADE,
        related_name='check_ins'
    )
    date = models.DateField(default=timezone.now)

    # Check-in Content
    completed_daily_goal = models.BooleanField(default=False)
    mood = models.CharField(
        max_length=20, choices=MOOD_CHOICES, default='okay')
    progress_note = models.TextField(
        blank=True,
        help_text="How did today go? Any challenges or wins?"
    )

    # Metrics (challenge-specific)
    custom_metric_1 = models.FloatField(
        null=True,
        blank=True,
        help_text="Exercise minutes, meditation time, etc."
    )
    custom_metric_2 = models.FloatField(
        null=True,
        blank=True,
        help_text="Additional metric tracking"
    )

    # Social Features
    is_shared_with_group = models.BooleanField(
        default=False,
        help_text="Share this check-in with the group"
    )
    encouragement_received = models.ManyToManyField(
        User,
        blank=True,
        related_name='given_encouragements'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('participant', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['participant', 'date']),
            models.Index(fields=['date', 'is_shared_with_group']),
        ]

    def __str__(self):
        return f"{self.participant.user.username} - {self.date}"

    @property
    def encouragement_count(self):
        return self.encouragement_received.count()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update participant progress
        if self.completed_daily_goal:
            participant = self.participant
            participant.days_completed = participant.check_ins.filter(
                completed_daily_goal=True
            ).count()

            # Update streak logic
            yesterday = self.date - timezone.timedelta(days=1)
            if participant.check_ins.filter(
                date=yesterday, completed_daily_goal=True
            ).exists():
                participant.current_streak += 1
            else:
                participant.current_streak = 1

            if participant.current_streak > participant.longest_streak:
                participant.longest_streak = participant.current_streak

            participant.update_progress()


class ChallengeComment(models.Model):
    """
    Comments and encouragement on challenge check-ins
    """
    check_in = models.ForeignKey(
        ChallengeCheckIn,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)

    # Comment types
    is_encouragement = models.BooleanField(
        default=True,
        help_text="Is this an encouragement/support comment?"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username}"


class ChallengeBadge(models.Model):
    """
    Badges earned through challenge completion
    """
    BADGE_TYPES = (
        ('completion', '🏆 Completion Badge'),
        ('streak', '🔥 Streak Badge'),
        ('participation', '⭐ Participation Badge'),
        ('leadership', '👑 Leadership Badge'),
        ('support', '🤝 Support Badge'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    icon = models.CharField(
        max_length=10,
        default='🏆',
        help_text="Emoji icon for the badge"
    )

    # Badge Requirements
    challenge_type = models.CharField(
        max_length=20,
        choices=GroupChallenge.CHALLENGE_TYPES,
        null=True,
        blank=True,
        help_text="Leave blank for universal badges"
    )
    required_completions = models.IntegerField(default=1)
    required_streak_days = models.IntegerField(default=0)

    # Rarity and Points
    rarity_level = models.IntegerField(
        default=1,
        help_text="1=Common, 2=Uncommon, 3=Rare, 4=Epic, 5=Legendary"
    )
    points_value = models.IntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.icon} {self.name}"


class UserChallengeBadge(models.Model):
    """
    Badges earned by users
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='challenge_badges'
    )
    badge = models.ForeignKey(ChallengeBadge, on_delete=models.CASCADE)
    challenge = models.ForeignKey(
        GroupChallenge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Specific challenge this was earned in"
    )

    earned_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge', 'challenge')
        ordering = ['-earned_date']

    def __str__(self):
        return f"{self.user.username} earned {self.badge.name}"


class Notification(models.Model):
    """
    Universal notification system for all user interactions
    """
    NOTIFICATION_TYPES = (
        ('pal_request', 'Recovery Pal Request'),
        ('pal_accepted', 'Pal Request Accepted'),
        ('message', 'New Message'),
        ('follow', 'New Follower'),
        ('sponsor_request', 'Sponsor Request'),
        ('sponsor_accepted', 'Sponsor Request Accepted'),
        ('challenge_invite', 'Challenge Invitation'),
        ('challenge_pal', 'Challenge Pal Request'),
        ('milestone', 'Milestone Achievement'),
        ('group_invite', 'Group Invitation'),
        ('group_post', 'New Group Post'),
        ('group_comment', 'New Group Comment'),
        ('group_join', 'New Group Member'),
        ('comment', 'New Comment'),
        ('like', 'New Like'),
        ('meeting_reminder', 'Meeting Reminder'),
    )

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_notifications',
        null=True, blank=True
    )

    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)

    # Related object (optional)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def get_icon(self):
        """Return appropriate icon for notification type"""
        icons = {
            'pal_request': 'fa-user-friends',
            'pal_accepted': 'fa-handshake',
            'message': 'fa-envelope',
            'follow': 'fa-user-plus',
            'sponsor_request': 'fa-hand-holding-heart',
            'sponsor_accepted': 'fa-heart',
            'challenge_invite': 'fa-trophy',
            'challenge_pal': 'fa-users',
            'milestone': 'fa-award',
            'group_invite': 'fa-users',
            'comment': 'fa-comment',
            'like': 'fa-heart',
        }
        return icons.get(self.notification_type, 'fa-bell')


class SocialPost(models.Model):
    """User-generated social media posts for the community feed"""
    VISIBILITY_CHOICES = [
        ('public', 'Everyone'),
        ('friends', 'Friends Only'),
        ('private', 'Only Me'),
    ]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_posts')
    content = models.TextField(blank=True, help_text="Share your thoughts, wins, or encouragement")
    image = models.ImageField(upload_to='social_posts/', blank=True, null=True)
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='public')

    # Engagement
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Social Post'
        verbose_name_plural = 'Social Posts'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return f"{self.author.username} - {self.content[:50]}"

    @property
    def likes_count(self):
        return self.likes.count()

    def is_visible_to(self, user):
        """Check if a post is visible to a specific user"""
        if self.visibility == 'public':
            return True
        if self.visibility == 'private':
            return user == self.author
        if self.visibility == 'friends':
            # Visible to author and their followers/following (mutual connections)
            if user == self.author:
                return True
            return UserConnection.objects.filter(
                follower=self.author,
                following=user,
                connection_type='follow'
            ).exists() or UserConnection.objects.filter(
                follower=user,
                following=self.author,
                connection_type='follow'
            ).exists()
        return False

    def get_reaction_counts(self):
        """Get count of each reaction type"""
        from django.db.models import Count
        reactions = self.reactions.values('reaction_type').annotate(count=Count('id'))
        return {r['reaction_type']: r['count'] for r in reactions}

    def get_user_reaction(self, user):
        """Get the reaction type for a specific user, if any"""
        if not user.is_authenticated:
            return None
        reaction = self.reactions.filter(user=user).first()
        return reaction.reaction_type if reaction else None


class PostReaction(models.Model):
    """Emoji reactions on social posts (beyond simple likes)"""
    REACTION_CHOICES = [
        ('like', '❤️'),
        ('support', '🙏'),
        ('strong', '💪'),
        ('celebrate', '🎉'),
    ]

    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES, default='like')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')  # One reaction per user per post
        indexes = [
            models.Index(fields=['post', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.username} reacted {self.get_reaction_type_display()} to post {self.post.id}"

    @classmethod
    def get_emoji(cls, reaction_type):
        """Get emoji for a reaction type"""
        emoji_map = dict(cls.REACTION_CHOICES)
        return emoji_map.get(reaction_type, '❤️')


class SocialPostComment(models.Model):
    """Comments on social posts"""
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(max_length=500)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Social Post Comment'
        verbose_name_plural = 'Social Post Comments'

    def __str__(self):
        return f"{self.author.username} on {self.post.id}"

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def replies_count(self):
        return self.replies.count()
