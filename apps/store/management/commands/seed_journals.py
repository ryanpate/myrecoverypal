"""
Seed the Recovery Shop with Ryan's Amazon KDP recovery journals.

Usage:
    python manage.py seed_journals

Idempotent — safe to re-run. Products are matched by slug and updated
in place. Cover images are downloaded best-effort from Amazon's media
CDN; if a download fails the product is still created without an image
(the shop template shows a placeholder).
"""
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.store.models import Category, Product

JOURNALS = [
    {
        "name": "The 90 Day Christian Recovery Journal: A Daily Companion for Faith and Sobriety",
        "price": "12.99",
        "url": "https://www.amazon.com/dp/B0H1WQM2X2",
        "image": "https://m.media-amazon.com/images/I/51pfXVJKbSL._SY522_.jpg",
        "featured": True,
        "description": (
            "A 90-day daily companion for the first 90 days of recovery, rooted in Christ. "
            "A five-part daily ritual paired with NIV scripture — morning intention, "
            "reflection, gratitude, and an evening review — where faith and sobriety "
            "finally meet in the same room."
        ),
    },
    {
        "name": "The 90-Day Cannabis-Free Journal: A Daily Companion for Clarity and Recovery",
        "price": "12.99",
        "url": "https://www.amazon.com/dp/B0H1D8RFKC",
        "image": "https://m.media-amazon.com/images/I/41JmLAuI1SL._SY522_.jpg",
        "featured": False,
        "description": (
            "Ninety days, two pages a day. A judgment-free daily companion for anyone "
            "giving cannabis a real pause — no labels required, just a structured way "
            "to find out what 90 days of clarity actually feel like."
        ),
    },
    {
        "name": "30 Day Recovery Journal: Daily Prompts, Affirmations, and Reflections to Support Your Healing Journey",
        "price": "8.99",
        "url": "https://www.amazon.com/dp/B0FPGGSTDZ",
        "image": "https://m.media-amazon.com/images/I/51eXmRvJ-QL._SY522_.jpg",
        "featured": False,
        "description": (
            "One month of guided reflection, encouragement, and self-discovery. "
            "Thoughtful daily prompts and affirmations that build a practice supporting "
            "sobriety, mental health, and resilience — progress, not perfection."
        ),
    },
    {
        "name": "90 Day Recovery Journal: Extended Guided Prompts for Lasting Sobriety, Healing, and Growth",
        "price": "9.99",
        "url": "https://www.amazon.com/dp/B0FR4MPHSW",
        "image": "https://m.media-amazon.com/images/I/51B-ZcQk2PL._SY522_.jpg",
        "featured": True,
        "description": (
            "The extended edition of the 30-Day Recovery Journal from the Normalize "
            "Sobriety series. The same proven first 30 days, then 60 brand-new prompts "
            "for lasting sobriety, healing, and growth."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed the Recovery Shop with Amazon KDP recovery journals (idempotent)."

    def _fetch_image(self, url):
        try:
            import requests

            resp = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (MyRecoveryPal seed_journals)"},
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001 — best-effort, never block seeding
            self.stdout.write(self.style.WARNING(f"  image download failed: {exc}"))
            return None

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug="journals",
            defaults={
                "name": "Recovery Journals",
                "description": "Guided journals for sobriety, healing, and growth.",
            },
        )

        for item in JOURNALS:
            slug = slugify(item["name"])[:50]
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": item["name"],
                    "category": category,
                    "description": item["description"],
                    "price": Decimal(item["price"]),
                    "external_url": item["url"],
                    "source": Product.SOURCE_AMAZON_KDP,
                    "is_featured": item["featured"],
                    "is_active": True,
                },
            )

            if not product.image:
                content = self._fetch_image(item["image"])
                if content:
                    product.image.save(f"{slug}.jpg", ContentFile(content), save=True)

            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb}: {product.name}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone — {len(JOURNALS)} journals in the shop."))
