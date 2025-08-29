from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Resource, ResourceCategory, ResourceType,
    ResourceBookmark, ResourceRating, CrisisResource
)


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'order', 'is_active', 'resource_count']
    list_editable = ['order', 'is_active', 'icon']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']

    def resource_count(self, obj):
        return obj.resources.count()
    resource_count.short_description = 'Resources'


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color_preview']
    prepopulated_fields = {'slug': ('name',)}

    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; '
            'border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_preview.short_description = 'Color'


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'resource_type',
        'access_level', 'featured', 'is_active',
        'views', 'downloads'
    ]
    list_filter = [
        'category', 'resource_type', 'access_level',
        'featured', 'is_active', 'created_at'
    ]
    list_editable = ['featured', 'is_active']
    search_fields = ['title', 'description', 'content']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views', 'downloads', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'resource_type', 'description')
        }),
        ('Content', {
            'fields': ('content', 'file', 'external_url')
        }),
        ('Access & Display', {
            'fields': ('access_level', 'featured', 'is_active')
        }),
        ('Statistics', {
            'fields': ('views', 'downloads'),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': ('meta_description',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CrisisResource)
class CrisisResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number',
                    'text_number', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']


@admin.register(ResourceBookmark)
class ResourceBookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'resource', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'resource__title']
    date_hierarchy = 'created_at'


@admin.register(ResourceRating)
class ResourceRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'resource', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'resource__title', 'review']
    readonly_fields = ['created_at', 'updated_at']
