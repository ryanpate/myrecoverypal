from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from django.contrib import messages
from .models import NewsletterCategory, Newsletter, Subscriber, EmailLog, NewsletterTemplate
from .tasks import send_newsletter_task

@admin.register(NewsletterCategory)
class NewsletterCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subscriber_count']
    prepopulated_fields = {'slug': ('name',)}
    
    def subscriber_count(self, obj):
        return obj.subscriber_set.filter(is_active=True).count()
    subscriber_count.short_description = 'Active Subscribers'

@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'category', 'status', 'scheduled_for', 'sent_at', 'sent_count']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'subject', 'content']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'subject', 'preheader', 'category')
        }),
        ('Content', {
            'fields': ('intro_content', 'main_content')
        }),
        ('Featured Section', {
            'fields': ('featured_title', 'featured_content', 'featured_link', 'featured_link_text'),
            'classes': ('collapse',)
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_url'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('status', 'scheduled_for')
        }),
        ('Statistics', {
            'fields': ('sent_count', 'opens', 'clicks'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['sent_count', 'opens', 'clicks']
    
    actions = ['send_newsletter', 'duplicate_newsletter']
    
    def send_newsletter(self, request, queryset):
        for newsletter in queryset:
            if newsletter.status == 'draft':
                try:
                    # Queue newsletter for sending via Celery
                    send_newsletter_task.delay(newsletter.id)
                    newsletter.status = 'sending'
                    newsletter.save()
                    messages.success(request, f'Newsletter "{newsletter.title}" queued for sending.')
                except Exception as e:
                    # Celery broker unavailable - cannot queue newsletter
                    messages.error(
                        request,
                        f'Could not queue "{newsletter.title}": Celery broker unavailable. '
                        f'Please ensure the celery-worker service is running. Error: {str(e)}'
                    )
            else:
                messages.warning(request, f'Newsletter "{newsletter.title}" is not in draft status.')
    send_newsletter.short_description = "Send selected newsletters"
    
    def duplicate_newsletter(self, request, queryset):
        for newsletter in queryset:
            newsletter.pk = None
            newsletter.title = f"Copy of {newsletter.title}"
            newsletter.status = 'draft'
            newsletter.is_sent = False
            newsletter.sent_at = None
            newsletter.sent_count = 0
            newsletter.opens = 0
            newsletter.clicks = 0
            newsletter.save()
            messages.success(request, f'Newsletter duplicated: {newsletter.title}')
    duplicate_newsletter.short_description = "Duplicate selected newsletters"
    
    def view_on_site(self, obj):
        return reverse('newsletter:preview', kwargs={'pk': obj.pk})

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'get_full_name', 'is_active', 'is_confirmed', 'frequency', 'subscribed_at']
    list_filter = ['is_active', 'is_confirmed', 'frequency', 'categories']
    search_fields = ['email', 'first_name', 'last_name', 'user__username']
    date_hierarchy = 'subscribed_at'
    actions = ['activate_subscribers', 'deactivate_subscribers', 'export_subscribers']
    
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'user', 'first_name', 'last_name')
        }),
        ('Preferences', {
            'fields': ('is_active', 'categories', 'frequency')
        }),
        ('Confirmation', {
            'fields': ('is_confirmed', 'confirmed_at', 'confirmation_token')
        }),
        ('Engagement', {
            'fields': ('emails_received', 'emails_opened', 'links_clicked', 'last_email_sent'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('source', 'subscribed_at', 'unsubscribed_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['confirmation_token', 'emails_received', 'emails_opened', 'links_clicked']
    
    def activate_subscribers(self, request, queryset):
        count = queryset.update(is_active=True, unsubscribed_at=None)
        messages.success(request, f'{count} subscribers activated.')
    activate_subscribers.short_description = "Activate selected subscribers"
    
    def deactivate_subscribers(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(is_active=False, unsubscribed_at=timezone.now())
        messages.success(request, f'{count} subscribers deactivated.')
    deactivate_subscribers.short_description = "Deactivate selected subscribers"

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['newsletter', 'subscriber', 'sent_at', 'opened_at', 'clicked_at']
    list_filter = ['sent_at', 'newsletter']
    search_fields = ['subscriber__email', 'newsletter__title']
    readonly_fields = ['tracking_id']

@admin.register(NewsletterTemplate)
class NewsletterTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}