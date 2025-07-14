from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.urls import reverse


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
