"""
Create/verify the Stripe "Court Compliance" product + recurring prices and sync
the SubscriptionPlan rows (tier='court') with the resulting Stripe IDs.

Once the monthly plan row exists, the pricing page automatically swaps its
`mailto:` placeholder for a real Stripe checkout button (see
payment_views.py `court_monthly_plan`), and the existing checkout + webhook
flow already grants tier='court' on success. This command is the last piece.

Idempotent: prices are keyed by Stripe `lookup_key` so re-runs reuse existing
prices. Changing an amount creates a new price, transfers the lookup_key, and
archives the old one (Stripe prices are immutable).

Defaults to DRY-RUN. Pass --commit to actually create/update.

Run against Railway (uses Railway's STRIPE_SECRET_KEY + prod DB):
    railway run -- python3 manage.py setup_court_stripe            # dry-run
    railway run -- python3 manage.py setup_court_stripe --commit   # for real
"""
import os
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.payment_models import SubscriptionPlan

PRODUCT_NAME = "MyRecoveryPal Court Compliance"
PRODUCT_DESC = ("Court-ready proof of meeting attendance — hash-verified PDF "
                "reports, email-to-PO delivery, and a public verification URL "
                "for DUI/drug-court/family-court requirements.")
MONTHLY_LOOKUP = "court_monthly"
YEARLY_LOOKUP = "court_yearly"
MONTHLY_CENTS = 1999


class Command(BaseCommand):
    help = "Create/verify the Stripe Court Compliance product + prices and sync SubscriptionPlan rows."

    def add_arguments(self, parser):
        parser.add_argument('--yearly', type=int, default=179,
                            help='Yearly price in whole USD (default 179). 0 = monthly only.')
        parser.add_argument('--commit', action='store_true',
                            help='Actually create/update. Default is a dry-run.')

    def handle(self, *args, **opts):
        key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.environ.get('STRIPE_SECRET_KEY')
        if not key:
            raise CommandError("STRIPE_SECRET_KEY is not set in this environment.")
        stripe.api_key = key
        mode = 'LIVE' if key.startswith('sk_live') else ('TEST' if key.startswith('sk_test') else 'UNKNOWN')
        commit = opts['commit']
        yearly = opts['yearly']

        self.stdout.write(self.style.WARNING(f"Stripe mode: {mode}"))
        self.stdout.write(f"Mode: {'COMMIT (writing changes)' if commit else 'DRY-RUN (no changes will be made)'}")
        self.stdout.write(f"Monthly: $19.99   Yearly: {'(none)' if yearly == 0 else f'${yearly}.00'}")
        self.stdout.write("")

        product_id = self._ensure_product(commit)
        self.stdout.write("Prices:")
        monthly_price_id = self._ensure_price(MONTHLY_LOOKUP, MONTHLY_CENTS, 'month', product_id, commit)
        yearly_price_id = None
        if yearly > 0:
            yearly_price_id = self._ensure_price(YEARLY_LOOKUP, yearly * 100, 'year', product_id, commit)

        self.stdout.write("\nSubscriptionPlan rows:")
        self._sync_plan('monthly', Decimal('19.99'), product_id, monthly_price_id, True, commit)
        if yearly > 0:
            self._sync_plan('yearly', Decimal(f'{yearly}.00'), product_id, yearly_price_id, True, commit)
        else:
            self._sync_plan('yearly', None, product_id, None, False, commit)  # deactivate

        self.stdout.write("")
        if commit:
            self.stdout.write(self.style.SUCCESS("Done. Stripe product/prices ensured and SubscriptionPlan rows synced."))
        else:
            self.stdout.write(self.style.WARNING("Dry-run complete. Re-run with --commit to apply."))

    # ---- Stripe helpers --------------------------------------------------

    def _ensure_product(self, commit):
        # Reuse the product from any existing court price first.
        for lk in (MONTHLY_LOOKUP, YEARLY_LOOKUP):
            data = stripe.Price.list(lookup_keys=[lk], active=True, limit=1, expand=['data.product']).data
            if data:
                prod = data[0].product
                pid = prod if isinstance(prod, str) else prod.id
                self.stdout.write(f"Product: reuse {pid} (from existing price '{lk}')")
                return pid
        # Else look up by metadata tag.
        try:
            res = stripe.Product.search(query="active:'true' AND metadata['mrp_tier']:'court'").data
        except Exception:
            res = []
        if res:
            self.stdout.write(f"Product: reuse {res[0].id} (metadata mrp_tier=court)")
            return res[0].id
        self.stdout.write(f"Product: MISSING — will create '{PRODUCT_NAME}'")
        if not commit:
            return None
        prod = stripe.Product.create(name=PRODUCT_NAME, description=PRODUCT_DESC,
                                     metadata={'mrp_tier': 'court'})
        self.stdout.write(self.style.SUCCESS(f"Product: created {prod.id}"))
        return prod.id

    def _ensure_price(self, lookup_key, cents, interval, product_id, commit):
        found = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1).data
        if found:
            p = found[0]
            if p.unit_amount == cents and p.recurring and p.recurring.interval == interval:
                self.stdout.write(f"  {lookup_key}: reuse {p.id} (${cents/100:.2f}/{interval})")
                return p.id
            self.stdout.write(
                f"  {lookup_key}: exists at ${p.unit_amount/100:.2f} but want ${cents/100:.2f} — "
                f"will create new price, transfer lookup_key, archive old")
            if not commit:
                return p.id
            newp = stripe.Price.create(product=product_id, unit_amount=cents, currency='usd',
                                       recurring={'interval': interval}, lookup_key=lookup_key,
                                       transfer_lookup_key=True)
            stripe.Price.modify(p.id, active=False)
            self.stdout.write(self.style.SUCCESS(f"  {lookup_key}: created {newp.id}, archived {p.id}"))
            return newp.id
        self.stdout.write(f"  {lookup_key}: MISSING — will create ${cents/100:.2f}/{interval}")
        if not commit:
            return None
        if not product_id:
            return None
        newp = stripe.Price.create(product=product_id, unit_amount=cents, currency='usd',
                                   recurring={'interval': interval}, lookup_key=lookup_key)
        self.stdout.write(self.style.SUCCESS(f"  {lookup_key}: created {newp.id}"))
        return newp.id

    # ---- DB sync ---------------------------------------------------------

    def _sync_plan(self, billing, price, product_id, price_id, active, commit):
        plan = SubscriptionPlan.objects.filter(tier='court', billing_period=billing).first()
        if not plan:
            self.stdout.write(f"  court/{billing}: row MISSING — will create (active={active})")
            if commit and active:
                SubscriptionPlan.objects.create(
                    tier='court', billing_period=billing,
                    name='Court Compliance (Yearly)' if billing == 'yearly' else 'Court Compliance',
                    price=price or Decimal('0.00'), is_active=active,
                    stripe_product_id=product_id or '', stripe_price_id=price_id or '',
                )
            return
        changes = []
        if active and product_id and plan.stripe_product_id != product_id:
            changes.append('stripe_product_id')
        if active and price_id and plan.stripe_price_id != price_id:
            changes.append('stripe_price_id')
        if active and price is not None and plan.price != price:
            changes.append(f'price {plan.price}->{price}')
        if plan.is_active != active:
            changes.append(f'is_active {plan.is_active}->{active}')
        self.stdout.write(f"  court/{billing}: plan #{plan.id} changes={changes or 'none'}")
        if commit:
            if active:
                if product_id:
                    plan.stripe_product_id = product_id
                if price_id:
                    plan.stripe_price_id = price_id
                if price is not None:
                    plan.price = price
            plan.is_active = active
            plan.save()
