from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    SOURCE_PRINTIFY = 'printify'
    SOURCE_AMAZON_KDP = 'amazon_kdp'
    SOURCE_OTHER = 'other'
    SOURCE_CHOICES = [
        (SOURCE_PRINTIFY, 'Printify'),
        (SOURCE_AMAZON_KDP, 'Amazon KDP'),
        (SOURCE_OTHER, 'Other'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # External storefront fields — purchases are fulfilled off-site
    # (Printify Pop-Up Store / Amazon KDP), never on MyRecoveryPal.
    external_url = models.URLField(
        max_length=500,
        help_text="The buy link — Printify product page or Amazon listing.",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_PRINTIFY,
        help_text="Where the product is sold. Controls the badge and button label.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured products are shown first.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.name

    @property
    def cta_label(self):
        if self.source == self.SOURCE_AMAZON_KDP:
            return "Buy on Amazon"
        if self.source == self.SOURCE_PRINTIFY:
            return "Shop on Printify"
        return "Buy Now"

    @property
    def source_label(self):
        return self.get_source_display()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
