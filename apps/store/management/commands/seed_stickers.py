"""
Seed the Recovery Shop with Printify Pop-Up stickers.

Usage:
    python manage.py seed_stickers

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

STICKERS = [
    {
        "name": "Recovering From A Number Of Things Sticker — Funny Relatable Laptop Decal",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28769117",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc744c66a3d537e0f1171/"
            "45750/2176/recovering-from-a-number-of-things-sticker-funny-"
            "relatable-laptop-decal.jpg?camera_label=context-1&revision=1779287926812"
        ),
        "featured": True,
        "description": (
            "Recovery has many faces — and a sense of humor helps. A funny, "
            "relatable die-cut vinyl sticker for the laptop, water bottle, "
            "or notebook of anyone working a program. Durable, weather-"
            "resistant, and an easy conversation starter."
        ),
    },
    {
        "name": "Recovery Mom Sticker — Retro Sobriety Support Gift for Moms",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768872",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc3f3305f3b940f0662fb/"
            "45750/2176/recovery-mom-sticker-retro-sobriety-support-gift-for-"
            "moms-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287358925"
        ),
        "featured": True,
        "description": (
            "For the moms holding it down in recovery. A retro die-cut vinyl "
            "sticker celebrating sober moms — durable, weatherproof, and "
            "perfect for laptops, water bottles, journals, or the back of a "
            "minivan. A small token of love for someone's whole world."
        ),
    },
    {
        "name": "Recovery Dad Sticker — Retro Sobriety Support Gift for Dads",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768788",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc2849740d0b7ee02993f/"
            "45750/2176/recovery-dad-sticker-retro-sobriety-support-gift-for-"
            "dads-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779286736609"
        ),
        "featured": False,
        "description": (
            "For the dads showing up sober every day. A retro die-cut vinyl "
            "sticker — weatherproof and tough enough for the truck, toolbox, "
            "laptop, or Yeti. A meaningful, low-key gift that says \"I see "
            "you, and I'm proud of you.\""
        ),
    },
    {
        "name": "Recovery Wife Sticker — Retro Sobriety Support Gift for Wives",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768888",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc4429740d0b7ee029a6a/"
            "45750/2176/recovery-wife-sticker-retro-sobriety-support-gift-"
            "for-wives-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287347918"
        ),
        "featured": False,
        "description": (
            "For the wife walking the recovery road. A retro die-cut vinyl "
            "sticker celebrating sober wives and partners. Weatherproof, "
            "durable, and a small daily reminder of the strength it takes "
            "to choose recovery — together."
        ),
    },
    {
        "name": "Recovery Husband Sticker — Retro Sobriety Support Gift for Husbands",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768954",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc58a888486cde4070e5c/"
            "45750/2176/recovery-husband-sticker-retro-sobriety-support-gift-"
            "for-husbands-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287484440"
        ),
        "featured": False,
        "description": (
            "For the husband doing the work, one day at a time. A retro die-"
            "cut vinyl sticker — durable, weatherproof, and built for the "
            "toolbox, truck, or laptop. A quiet way to say \"proud of you\" "
            "to the partner showing up sober."
        ),
    },
    {
        "name": "Recovery Sister Sticker — Retro Sobriety Support Gift for Sisters",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768974",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc5c59db714d32d096197/"
            "45750/2176/recovery-sister-sticker-retro-sobriety-support-gift-"
            "for-sisters-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287544557"
        ),
        "featured": False,
        "description": (
            "For the sister in recovery — or the one cheering her on. A "
            "retro die-cut vinyl sticker, weatherproof and durable, that "
            "celebrates sisters doing the work. A small but meaningful gift "
            "for the person who's always been in your corner."
        ),
    },
    {
        "name": "Recovery Brother Sticker — Retro Sobriety Support Gift for Brothers",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28768765",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc0f6d7d0a5084202d6dc/"
            "45750/2176/recovery-brother-sticker-retro-sobriety-support-gift-"
            "for-brothers-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779286624176"
        ),
        "featured": False,
        "description": (
            "For the brother choosing sobriety — and the one walking with "
            "him. A retro die-cut vinyl sticker, weatherproof and built to "
            "last. A simple way to say \"I'm in your corner\" to a brother "
            "doing the hardest, most worthwhile work of his life."
        ),
    },
    {
        "name": "Recovery Grandma Sticker — Retro Sobriety Support Gift for Grandmothers",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28769032",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc6631462f924e50c4f89/"
            "45750/2176/recovery-grandma-sticker-retro-sobriety-support-gift-"
            "for-grandmothers-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287703292"
        ),
        "featured": False,
        "description": (
            "For grandma in recovery — proof that it's never too late. A "
            "retro die-cut vinyl sticker, weatherproof and durable. A "
            "loving reminder for the matriarch holding the family together, "
            "one sober day at a time."
        ),
    },
    {
        "name": "Recovery Grandpa Sticker — Retro Sobriety Support Gift for Grandfathers",
        "price": "3.99",
        "url": "https://myrecoverypal.printify.me/product/28769072",
        "image": (
            "https://images-api.printify.com/mockup/6a0dc6b49740d0b7ee029bd4/"
            "45750/2176/recovery-grandpa-sticker-retro-sobriety-support-gift-"
            "for-grandfathers-die-cut-vinyl-recovery-sticker.jpg?camera_label=context-1&revision=1779287792556"
        ),
        "featured": False,
        "description": (
            "For grandpa in recovery — the quiet kind of strength that "
            "shapes a whole family. A retro die-cut vinyl sticker, "
            "weatherproof and tough. A small, lasting way to honor the "
            "patriarch who chose a better way, one day at a time."
        ),
    },
]

CATEGORY_DEFS = {
    "stickers": {
        "name": "Stickers",
        "description": (
            "Die-cut vinyl recovery and sobriety stickers — small, durable, "
            "and meaningful gifts for laptops, water bottles, and journals."
        ),
    },
}


class Command(BaseCommand):
    help = "Seed the Recovery Shop with Printify Pop-Up stickers (idempotent)."

    def _fetch_image(self, url):
        try:
            import requests

            resp = requests.get(
                url,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0 (MyRecoveryPal seed_stickers)"},
            )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:  # noqa: BLE001 — best-effort, never block seeding
            self.stdout.write(self.style.WARNING(f"  image download failed: {exc}"))
            return None

    def handle(self, *args, **options):
        categories = {}
        for cat_slug, cat_def in CATEGORY_DEFS.items():
            categories[cat_slug], _ = Category.objects.get_or_create(
                slug=cat_slug, defaults=cat_def
            )

        for item in STICKERS:
            slug = slugify(item["name"])[:50]
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": item["name"],
                    "category": categories["stickers"],
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

        self.stdout.write(self.style.SUCCESS(f"\nDone — {len(STICKERS)} sticker(s) in the shop."))
