from django.db import models
from django.conf import settings
from django.utils import timezone

class JournalPrompt(models.Model):
    CATEGORY_CHOICES = (
        ('gratitude', 'Gratitude'),
        ('reflection', 'Reflection'),
        ('goals', 'Goals'),
        ('triggers', 'Triggers'),
        ('coping', 'Coping Strategies'),
        ('milestones', 'Milestones'),
    )
    
    title = models.CharField(max_length=200)
    prompt = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # When to show
    min_days_sober = models.IntegerField(default=0)
    max_days_sober = models.IntegerField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'min_days_sober']
    
    def __str__(self):
        return self.title

class JournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_entries')
    prompt = models.ForeignKey(JournalPrompt, on_delete=models.SET_NULL, null=True, blank=True)
    
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    
    # Mood tracking
    mood = models.IntegerField(choices=[(i, i) for i in range(1, 11)], null=True, blank=True)
    
    # Privacy
    is_private = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags for searching
    tags = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Journal entries'
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at.strftime('%Y-%m-%d')}"

class Milestone(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    date_achieved = models.DateField(default=timezone.now)
    
    # Milestone types
    days_sober = models.IntegerField(null=True, blank=True)
    custom_milestone = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_achieved']
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"