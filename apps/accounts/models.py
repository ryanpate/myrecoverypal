from django.contrib.auth.models import AbstractUser, PermissionsMixin
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

    def get_recovery_buddy(self):
        """Get active recovery buddy"""
        buddy = RecoveryBuddy.objects.filter(
            models.Q(user1=self) | models.Q(user2=self),
            status='active'
        ).first()
        return buddy.get_partner(self) if buddy else None

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

        super().save(*args, **kwargs)

        # Check if connection is now mutual
        if self.connection_type == 'follow':
            mutual_connection = UserConnection.objects.filter(
                follower=self.following,
                following=self.follower,
                connection_type='follow'
            ).first()

            if mutual_connection:
                self.is_mutual = True
                mutual_connection.is_mutual = True
                self.save(update_fields=['is_mutual'])
                mutual_connection.save(update_fields=['is_mutual'])


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


class RecoveryBuddy(models.Model):
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
        related_name='buddy_relationships_as_user1'
    )
    user2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buddy_relationships_as_user2'
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
        return f"Recovery Buddies: {self.user1.username} & {self.user2.username}"

    def get_partner(self, user):
        """Get the other user in the buddy relationship"""
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
