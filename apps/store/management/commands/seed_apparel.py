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

# category: "apparel" (default) or "accessories". Order within the shop is
# controlled by `featured` first, then newest. Slugs are derived from `name`
# (first 50 chars) — never rename an existing product or it creates a duplicate.
APPAREL = [
    {
        "name": "Hold Fast Steady Anchor T-Shirt | Recovery & Sobriety Tee | Gildan Softstyle Unisex",
        "price": "28.00",
        "url": "https://myrecoverypal.printify.me/product/28661678",
        "category": "apparel",
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
    {
        "name": "I Love a Sober Person T-Shirt — Recovery Pride Tee",
        "price": "28.99",
        "url": "https://myrecoverypal.printify.me/product/28720170",
        "category": "apparel",
        "image": (
            "https://images-api.printify.com/mockup/6a0b1ee54f2a062db108ccd5/"
            "38191/97992/i-a-sober-person-t-shirt-recovery-pride-tee-for-"
            "sobriety-support.jpg?s=2048"
        ),
        "featured": True,
        "description": (
            "For the people who love someone in recovery — and aren't quiet about "
            "it. A bold heart statement that turns sober support into something you "
            "can wear with pride. Soft unisex cotton tee. A meaningful gift for a "
            "partner, parent, sponsor, or friend cheering someone on."
        ),
    },
    {
        "name": "Recovery Team T-Shirt — The Roster Chalkboard Design",
        "price": "28.99",
        "url": "https://myrecoverypal.printify.me/product/28721070",
        "category": "apparel",
        "image": (
            "https://images-api.printify.com/mockup/6a0b2c9df927a982860ddd0a/"
            "38192/97992/recovery-team-t-shirt-the-roster-chalkboard-design.jpg?s=2048"
        ),
        "featured": False,
        "description": (
            "Nobody gets sober alone. A team-roster chalkboard design celebrating "
            "the sponsors, therapists, friends, and fellow travelers who show up. "
            "Premium unisex tee — perfect for group anniversaries, meetings, and "
            "recovery community events."
        ),
    },
    {
        "name": "Tab Open: 24 Hours — Supportive Caregiver T-Shirt",
        "price": "28.99",
        "url": "https://myrecoverypal.printify.me/product/28721652",
        "category": "apparel",
        "image": (
            "https://images-api.printify.com/mockup/6a0b3308f927a982860ddfff/"
            "94871/97993/t-shirt-tab-open-24-hours-supportive-caregiver-tee.jpg?s=2048"
        ),
        "featured": False,
        "description": (
            "For the ones who keep the tab open — always available, day or night. "
            "A quietly powerful tee for caregivers, sponsors, and the people who "
            "answer the 2 a.m. call. Soft, durable unisex cotton."
        ),
    },
    {
        "name": "My Higher Power Is Caffeine — Funny Recovery T-Shirt",
        "price": "16.46",
        "url": "https://myrecoverypal.printify.me/product/28719732",
        "category": "apparel",
        "image": (
            "https://images-api.printify.com/mockup/6a0b185aadbae2f3b1056790/"
            "63303/97992/my-higher-power-is-caffeine-funny-recovery-sobriety-"
            "t-shirt-retro-coffee-lover-tee.jpg?s=2048"
        ),
        "featured": False,
        "description": (
            "Recovery has room for humor. A retro coffee-lover design for anyone "
            "who traded one ritual for a much better one. Lighthearted, "
            "conversation-starting, and the easiest gift on the list for the sober "
            "caffeine devotee in your life."
        ),
    },
    {
        "name": "Steady Anchor Phone Case — Recovery & Sobriety Gift",
        "price": "30.00",
        "url": "https://myrecoverypal.printify.me/product/28729269",
        "category": "accessories",
        "image": (
            "https://images-api.printify.com/mockup/6a0b831d4b7d21db750ab545/"
            "103590/100651/steady-anchor-phone-case-recovery-sobriety-gift-"
            "vintage-tattoo-style-iphone-android-case.jpg?s=2048"
        ),
        "featured": True,
        "description": (
            "Carry the reminder everywhere. A vintage tattoo-style anchor — the "
            "symbol of holding steady — on a durable iPhone or Android case. The "
            "small daily nudge that recovery is something you choose, one day at "
            "a time."
        ),
    },
    {
        "name": "One Day. Then Another. — Recovery & Sobriety T-Shirt",
        "price": "28.00",
        "url": "https://myrecoverypal.printify.me/product/28732414",
        "category": "apparel",
        "image": (
            "https://images-api.printify.com/mockup/6a0bad13e859ea852a0bdd1b/"
            "38193/97992/one-day-then-another-then-another-recovery-sobriety-"
            "t-shirt-minimalist-sober-gift-tee.jpg?s=2048"
        ),
        "featured": True,
        "description": (
            "The whole program in three words. A clean, minimalist statement — "
            "cream type on forest green — for anyone living recovery one day at "
            "a time. Soft unisex cotton tee that says everything without saying "
            "much at all."
        ),
    },
    {
        "name": "One Day. Then Another. Phone Case — Minimalist Recovery Gift",
        "price": "30.00",
        "url": "https://myrecoverypal.printify.me/product/28732508",
        "category": "accessories",
        "image": (
            "https://images-api.printify.com/mockup/6a0baeee56c75ac490101114/"
            "102547/99511/one-day-then-another-phone-case-minimalist-recovery-"
            "sobriety-gift-iphone-android-case.jpg?s=2048"
        ),
        "featured": False,
        "description": (
            "A quiet daily reminder in your hand. Minimalist cream lettering on "
            "muted blue with a small rising-sun accent, on a durable iPhone or "
            "Android case. One day, then another — that's how it's done."
        ),
    },
]

CATEGORY_DEFS = {
    "apparel": {
        "name": "Apparel",
        "description": "Recovery and sobriety apparel — wear the message.",
    },
    "accessories": {
        "name": "Accessories",
        "description": "Everyday recovery accessories and meaningful gifts.",
    },
}


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
        categories = {}
        for cat_slug, cat_def in CATEGORY_DEFS.items():
            categories[cat_slug], _ = Category.objects.get_or_create(
                slug=cat_slug, defaults=cat_def
            )

        for item in APPAREL:
            slug = slugify(item["name"])[:50]
            category = categories[item.get("category", "apparel")]
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
