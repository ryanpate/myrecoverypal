from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    @admin.display(description='Products')
    def product_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'source', 'is_featured', 'is_active')
    list_filter = ('category', 'source', 'is_featured', 'is_active')
    list_editable = ('is_featured', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview', 'created_at', 'updated_at')
    fields = (
        'name', 'slug', 'category', 'description', 'price',
        'image', 'image_preview', 'external_url', 'source',
        'is_featured', 'is_active', 'created_at', 'updated_at',
    )

    @admin.display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 160px; border-radius: 8px;" />',
                obj.image.url,
            )
        return "No image"
