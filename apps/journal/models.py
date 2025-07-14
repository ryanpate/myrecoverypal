from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse

class JournalPrompt(models.Model):
    CATEGORY_CHOICES = (
        ('gratitude', 'Gratitude'),
        ('reflection', 'Daily Reflection'),
        ('goals', 'Goals & Aspirations'),
        ('triggers', 'Triggers & Challenges'),
        ('coping', 'Coping Strategies'),
        ('milestones', 'Milestones & Progress'),
        ('relationships', 'Relationships'),
        ('self_care', 'Self Care'),
        ('emotions', 'Emotional Check-in'),
    )
    
    STAGE_CHOICES = (
        ('early', 'Early Recovery (0-30 days)'),
        ('middle', 'Sustained Recovery (31-365 days)'),
        ('ongoing', 'Ongoing Recovery (1+ years)'),
        ('all', 'All Stages'),
    )
    
    title = models.CharField(max_length=200)
    prompt = models.TextField(help_text="The question or prompt for the user")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='all',
                           help_text="Recovery stage this prompt is most relevant for")
    
    # Optional follow-up questions
    follow_up_1 = models.TextField(blank=True, help_text="Optional follow-up question")
    follow_up_2 = models.TextField(blank=True, help_text="Optional second follow-up")
    
    # When to show
    min_days_sober = models.IntegerField(default=0, help_text="Minimum days sober to see this prompt")
    max_days_sober = models.IntegerField(null=True, blank=True, help_text="Maximum days sober (leave blank for no limit)")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'min_days_sober']
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"
    
    def is_relevant_for_user(self, user):
        """Check if this prompt is relevant for a user based on their recovery stage"""
        if not self.is_active:
            return False
            
        days_sober = user.get_days_sober()
        
        if days_sober < self.min_days_sober:
            return False
            
        if self.max_days_sober and days_sober > self.max_days_sober:
            return False
            
        return True

class JournalEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_entries')
    prompt = models.ForeignKey(JournalPrompt, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Entry content
    title = models.CharField(max_length=200, blank=True, help_text="Optional title for your entry")
    content = models.TextField()
    
    # Mood tracking (1-10 scale)
    mood_rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)], 
        null=True, 
        blank=True,
        help_text="How are you feeling today? (1=lowest, 10=highest)"
    )
    
    # Additional tracking
    gratitude_1 = models.CharField(max_length=200, blank=True, help_text="Something you're grateful for")
    gratitude_2 = models.CharField(max_length=200, blank=True)
    gratitude_3 = models.CharField(max_length=200, blank=True)
    
    # Sobriety check-in
    cravings_today = models.BooleanField(default=False, help_text="Did you experience cravings today?")
    craving_intensity = models.IntegerField(
        choices=[(i, i) for i in range(1, 11)], 
        null=True, 
        blank=True,
        help_text="If yes, how intense? (1=mild, 10=severe)"
    )
    
    # Privacy
    is_private = models.BooleanField(default=True, help_text="Keep this entry private")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Tags for searching
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Journal entries'
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d')} - {self.title or 'Untitled'}"
    
    def get_absolute_url(self):
        return reverse('journal:entry_detail', kwargs={'pk': self.pk})
    
    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

class JournalStreak(models.Model):
    """Track journaling streaks to encourage consistency"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_entry_date = models.DateField(null=True, blank=True)
    total_entries = models.IntegerField(default=0)
    
    def update_streak(self):
        """Update streak based on journal entries"""
        today = timezone.now().date()
        
        # Get the last entry
        last_entry = self.user.journal_entries.order_by('-created_at').first()
        
        if not last_entry:
            self.current_streak = 0
            self.save()
            return
        
        last_entry_date = last_entry.created_at.date()
        
        # If entry is today, streak continues
        if last_entry_date == today:
            return
        
        # If entry was yesterday, increment streak
        elif last_entry_date == today - timezone.timedelta(days=1):
            self.current_streak += 1
            self.longest_streak = max(self.longest_streak, self.current_streak)
            self.last_entry_date = today
        
        # If more than 1 day gap, reset streak
        else:
            self.current_streak = 1
            self.last_entry_date = today
        
        self.total_entries = self.user.journal_entries.count()
        self.save()
    
    def __str__(self):
        return f"{self.user.username}'s journal streak: {self.current_streak} days"

class JournalReminder(models.Model):
    """Email/notification reminders for journaling"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journal_reminders')
    time = models.TimeField(help_text="Time to send daily reminder")
    is_active = models.BooleanField(default=True)
    
    # Days of week (0=Monday, 6=Sunday)
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)
    saturday = models.BooleanField(default=True)
    sunday = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Daily at {self.time}"