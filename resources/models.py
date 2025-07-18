from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.urls import reverse

User = get_user_model()


class ResourceCategory(models.Model):
    """Categories for organizing resources"""
    CATEGORY_ICONS = {
        'educational': '📚',
        'support': '🤝',
        'tools': '🛠️',
        'wellness': '🧘',
        'family': '👨‍👩‍👧‍👦',
        'professional': '⚕️',
        'crisis': '🚨',
    }

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='📁')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Resource Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Auto-set icon based on category slug
        if not self.icon and self.slug in self.CATEGORY_ICONS:
            self.icon = self.CATEGORY_ICONS[self.slug]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('resources:category', kwargs={'slug': self.slug})


class ResourceType(models.Model):
    """Types of resources (PDF, Video, Article, etc.)"""
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    color = models.CharField(
        max_length=7,
        default='#10B981',
        help_text='Hex color code for the badge'
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text='Emoji icon for this resource type'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Resource(models.Model):
    """Individual recovery resources"""
    ACCESS_LEVELS = [
        ('free', 'Free'),
        ('registered', 'Registered Users'),
        ('premium', 'Premium Users'),
    ]

    INTERACTION_TYPES = [
        ('static', 'Static Content'),
        ('interactive', 'Interactive Tool'),
        ('hybrid', 'Both Static and Interactive'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.CASCADE,
        related_name='resources'
    )
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.SET_NULL,
        null=True
    )
    description = models.TextField()
    content = models.TextField(
        blank=True,
        help_text='Full content for articles, leave blank for external resources'
    )

    # File/Link fields
    file = models.FileField(
        upload_to='resources/files/',
        blank=True,
        null=True,
        help_text='Upload files like PDFs, worksheets, etc.'
    )
    external_url = models.URLField(
        blank=True,
        help_text='Link to external resource'
    )

    # Interactive features
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES,
        default='static'
    )
    is_interactive = models.BooleanField(
        default=False,
        help_text='Does this resource have an interactive component?'
    )
    interactive_component = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name of the React/JS component for interactive resources'
    )

    # Access control
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVELS,
        default='free'
    )

    # Tracking
    views = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)

    # Metadata
    featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_resources'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SEO
    meta_description = models.TextField(
        blank=True,
        help_text='SEO meta description'
    )

    # Additional fields for enhanced functionality
    estimated_time = models.CharField(
        max_length=50,
        blank=True,
        help_text='Estimated time to complete (e.g., "10 minutes")'
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        blank=True
    )

    class Meta:
        ordering = ['-featured', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        # Set is_interactive based on interaction_type
        if self.interaction_type in ['interactive', 'hybrid']:
            self.is_interactive = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('resources:detail', kwargs={'slug': self.slug})

    def get_interactive_url(self):
        """URL for interactive version of the resource"""
        if self.is_interactive:
            return reverse('resources:interactive', kwargs={'slug': self.slug})
        return None

    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])

    def increment_downloads(self):
        self.downloads += 1
        self.save(update_fields=['downloads'])

    @property
    def is_external(self):
        return bool(self.external_url)

    @property
    def is_downloadable(self):
        return bool(self.file)

    @property
    def has_both_versions(self):
        """Check if resource has both PDF and interactive versions"""
        return self.interaction_type == 'hybrid'


class ResourceBookmark(models.Model):
    """Allow users to bookmark resources"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'resource']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.resource.title}"


class ResourceRating(models.Model):
    """User ratings for resources"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'resource']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.resource.title} ({self.rating}★)"


class ResourceUsage(models.Model):
    """Track how users interact with resources"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='usage_records'
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ('view', 'Viewed'),
            ('download', 'Downloaded'),
            ('complete', 'Completed'),
            ('interact', 'Used Interactive'),
        ]
    )
    duration = models.DurationField(
        null=True,
        blank=True,
        help_text='Time spent on resource'
    )
    completed = models.BooleanField(default=False)
    progress_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Store progress data for interactive resources'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.resource.title}"


class InteractiveResourceProgress(models.Model):
    """Store detailed progress for interactive resources like checklists"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='interactive_progress'
    )
    session_data = models.JSONField(
        default=dict,
        help_text='Store session-specific data (e.g., checked items)'
    )
    completed_items = models.IntegerField(default=0)
    total_items = models.IntegerField(default=0)
    completion_percentage = models.FloatField(default=0.0)
    started_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-last_updated']

    def __str__(self):
        return f"{self.user.username} - {self.resource.title} ({self.completion_percentage}%)"

    def calculate_completion(self):
        """Calculate and update completion percentage"""
        if self.total_items > 0:
            self.completion_percentage = (
                self.completed_items / self.total_items) * 100
        else:
            self.completion_percentage = 0
        self.save(update_fields=['completion_percentage'])


class CrisisResource(models.Model):
    """Special model for crisis/emergency resources"""
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    text_number = models.CharField(max_length=20, blank=True)
    description = models.TextField()
    url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
