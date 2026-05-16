"""
Seed the Recovery Shop with Printify Pop-Up apparel.

Usage:
    python manage.py seed_apparel

Idempotent — safe to re-run. Products are matched by slug and updated
in place. Mockup images are downloaded best-effort from Printify's CDN;
if a download fails the product is still created without an image
(the shop template shows a placeholder).
"""
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.store.models import Category, Product

APPAREL = [
    {
        "name": "Hold Fast Steady Anchor T-Shirt | Recovery & Sobriety Tee | Gildan Softstyle Unisex",
        "price": "28.00",
        "url": "https://myrecoverypal.printify.me/product/28661678",
        "image": (
            "https://images-api.printify.com/mockup/6a07cc24153d7a24ba029ab2/"
            "38192/97993/hold-fast-steady-anchor-t-shirt-recovery-sobriety-tee-"
            "gildan-softstyle-unisex.jpg?camera_label=back&revision=1778896010323&s=2048"
        ),
        "featured": True,
        "description": (
            "Recovery isn't a straight line — it's a daily decision to hold on. "
            "A vintage \"Hold Fast\" banner on the front and a bold nautical anchor "
            "with \"Steady\" on the back. Premium Gildan Softstyle ringspun cotton, "
            "unisex fit, in White, Black, and Charcoal. Every purchase supports "
            "MyRecoveryPal, a free recovery community."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed the Recovery Shop with Printify Pop-Up apparel (idempotent)."

    def _fetch_image(self, url):
        try:
            import requests

            resp = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (MyRecoveryPal seed_apparel)"},
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001 — best-effort, never block seeding
            self.stdout.write(self.style.WARNING(f"  image download failed: {exc}"))
            return None

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug="apparel",
            defaults={
                "name": "Apparel",
                "description": "Recovery and sobriety apparel — wear the message.",
            },
        )

        for item in APPAREL:
            slug = slugify(item["name"])[:50]
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": item["name"],
                    "category": category,
                    "description": item["description"],
                    "price": Decimal(item["price"]),
                    "external_url": item["url"],
                    "source": Product.SOURCE_PRINTIFY,
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

        self.stdout.write(self.style.SUCCESS(f"\nDone — {len(APPAREL)} apparel item(s) in the shop."))
