from django.db import models
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import uuid

class NewsletterCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Newsletter Categories'
    
    def __str__(self):
        return self.name

class Newsletter(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
    )
    
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=200, help_text="Email subject line")
    preheader = models.CharField(max_length=200, blank=True, help_text="Preview text shown in email clients")
    category = models.ForeignKey(NewsletterCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Content sections
    intro_content = models.TextField(help_text="Introduction paragraph")
    main_content = models.TextField(help_text="Main newsletter content (supports HTML)")
    
    # Featured content
    featured_title = models.CharField(max_length=200, blank=True)
    featured_content = models.TextField(blank=True)
    featured_link = models.URLField(blank=True)
    featured_link_text = models.CharField(max_length=100, default="Read More")
    
    # Call to action
    cta_text = models.CharField(max_length=100, blank=True, help_text="Call to action button text")
    cta_url = models.URLField(blank=True, help_text="Call to action button URL")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="When to send the newsletter")
    
    # Tracking
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_count = models.IntegerField(default=0)
    
    # Stats
    opens = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return f"/newsletter/{self.id}/"

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='newsletter_subscription'
    )
    
    # Subscriber info
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Preferences
    is_active = models.BooleanField(default=True)
    categories = models.ManyToManyField(NewsletterCategory, blank=True)
    frequency = models.CharField(max_length=20, choices=[
        ('immediately', 'Immediately'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
    ], default='weekly')
    
    # Tracking
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False)
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Engagement
    last_email_sent = models.DateTimeField(null=True, blank=True)
    emails_received = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    links_clicked = models.IntegerField(default=0)
    
    # Timestamps
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    
    # Source
    source = models.CharField(max_length=50, default='website', help_text="How they subscribed")
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        if self.user:
            return self.user.get_full_name()
        return ""

class EmailLog(models.Model):
    """Track individual email sends"""
    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE, related_name='email_logs')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='email_logs')
    
    sent_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    # Unique tracking ID
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False)
    
    class Meta:
        unique_together = ['newsletter', 'subscriber']
    
    def __str__(self):
        return f"{self.newsletter.title} to {self.subscriber.email}"

class NewsletterTemplate(models.Model):
    """Reusable email templates"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    # Template content
    html_template = models.TextField(help_text="HTML template with variables")
    text_template = models.TextField(help_text="Plain text template", blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name