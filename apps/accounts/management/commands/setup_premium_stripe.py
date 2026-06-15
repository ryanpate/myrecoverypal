"""
Create/verify the Stripe "Premium" product + recurring prices and sync the
SubscriptionPlan rows (tier='premium') with the resulting Stripe IDs.

WHY THIS EXISTS: Premium price IDs were originally hardcoded in migration
0023_seed_subscription_plans.py. A migration cannot create real Stripe prices,
so those IDs can drift from the live Stripe account (classic test-vs-live
mismatch → "No such price" at checkout → $0 revenue). This command is the
court/supporter-style idempotent fix, and it also DIAGNOSES the current rows
by retrieving their stripe_price_id from Stripe and reporting validity.

Idempotent: prices are keyed by Stripe `lookup_key` so re-runs reuse existing
prices. Changing an amount creates a new price, transfers the lookup_key, and
archives the old one (Stripe prices are immutable).

Defaults to DRY-RUN. Pass --commit to actually create/update.

Run against Railway (uses Railway's STRIPE_SECRET_KEY + prod DB):
    railway run -- python3 manage.py setup_premium_stripe            # dry-run + diagnose
    railway run -- python3 manage.py setup_premium_stripe --commit   # for real
"""
import os
from decimal import Decimal

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.payment_models import SubscriptionPlan

PRODUCT_NAME = "MyRecoveryPal Premium"
PRODUCT_DESC = ("Unlimited AI Recovery Coach, unlimited groups, 90-day "
                "analytics, journal export, and a Premium badge.")
MONTHLY_LOOKUP = "premium_monthly"
YEARLY_LOOKUP = "premium_yearly"

# Phase 2 repricing defaults (was $4.99 / $29.99).
DEFAULT_MONTHLY = Decimal('9.99')
DEFAULT_YEARLY = Decimal('59.99')


class Command(BaseCommand):
    help = "Create/verify the Stripe Premium product + prices and sync SubscriptionPlan rows."

    def add_arguments(self, parser):
        parser.add_argument('--monthly', type=str, default=str(DEFAULT_MONTHLY),
                            help=f'Monthly price in USD (default {DEFAULT_MONTHLY}).')
        parser.add_argument('--yearly', type=str, default=str(DEFAULT_YEARLY),
                            help=f'Yearly price in USD (default {DEFAULT_YEARLY}). 0 = monthly only.')
        parser.add_argument('--commit', action='store_true',
                            help='Actually create/update. Default is a dry-run.')

    def handle(self, *args, **opts):
        key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.environ.get('STRIPE_SECRET_KEY')
        if not key:
            raise CommandError("STRIPE_SECRET_KEY is not set in this environment.")
        stripe.api_key = key
        mode = 'LIVE' if key.startswith('sk_live') else ('TEST' if key.startswith('sk_test') else 'UNKNOWN')
        commit = opts['commit']
        monthly = Decimal(opts['monthly'])
        yearly = Decimal(opts['yearly'])

        self.stdout.write(self.style.WARNING(f"Stripe mode: {mode}"))
        self.stdout.write(f"Mode: {'COMMIT (writing changes)' if commit else 'DRY-RUN (no changes will be made)'}")
        self.stdout.write(f"Monthly: ${monthly}   Yearly: {'(none)' if yearly == 0 else f'${yearly}'}")
        self.stdout.write("")

        # ---- DIAGNOSE existing rows first (the root-cause check) ----------
        self._diagnose_existing(mode)

        product_id = self._ensure_product(commit)
        self.stdout.write("Prices:")
        monthly_price_id = self._ensure_price(MONTHLY_LOOKUP, self._cents(monthly), 'month', product_id, commit)
        yearly_price_id = None
        if yearly > 0:
            yearly_price_id = self._ensure_price(YEARLY_LOOKUP, self._cents(yearly), 'year', product_id, commit)

        self.stdout.write("\nSubscriptionPlan rows:")
        self._sync_plan('monthly', monthly, product_id, monthly_price_id, True, commit)
        if yearly > 0:
            self._sync_plan('yearly', yearly, product_id, yearly_price_id, True, commit)

        self.stdout.write("")
        if commit:
            self.stdout.write(self.style.SUCCESS("Done. Stripe product/prices ensured and SubscriptionPlan rows synced."))
        else:
            self.stdout.write(self.style.WARNING("Dry-run complete. Re-run with --commit to apply."))

    @staticmethod
    def _cents(amount):
        return int((amount * 100).to_integral_value())

    # ---- Diagnosis -------------------------------------------------------

    def _diagnose_existing(self, mode):
        self.stdout.write("Diagnosing existing Premium SubscriptionPlan rows:")
        rows = SubscriptionPlan.objects.filter(tier='premium').order_by('billing_period')
        if not rows:
            self.stdout.write("  (no premium rows found)")
            self.stdout.write("")
            return
        for plan in rows:
            pid = plan.stripe_price_id or ''
            label = f"  premium/{plan.billing_period} #{plan.id} active={plan.is_active} ${plan.price} price_id={pid or '(blank)'}"
            if not pid:
                self.stdout.write(self.style.ERROR(label + "  -> BLANK price id (checkout will fail)"))
                continue
            try:
                p = stripe.Price.retrieve(pid)
                amt = f"${p.unit_amount/100:.2f}/{p.recurring.interval}" if p.recurring else f"${p.unit_amount/100:.2f}"
                ok = "VALID" if p.active else "INACTIVE"
                self.stdout.write(self.style.SUCCESS(label + f"  -> {ok} in {mode} ({amt})"))
            except stripe.error.InvalidRequestError as e:
                self.stdout.write(self.style.ERROR(label + f"  -> INVALID in {mode}: {e.user_message or e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(label + f"  -> ERROR: {e}"))
        self.stdout.write("")

    # ---- Stripe helpers --------------------------------------------------

    def _ensure_product(self, commit):
        for lk in (MONTHLY_LOOKUP, YEARLY_LOOKUP):
            data = stripe.Price.list(lookup_keys=[lk], active=True, limit=1, expand=['data.product']).data
            if data:
                prod = data[0].product
                pid = prod if isinstance(prod, str) else prod.id
                self.stdout.write(f"Product: reuse {pid} (from existing price '{lk}')")
                return pid
        try:
            res = stripe.Product.search(query="active:'true' AND metadata['mrp_tier']:'premium'").data
        except Exception:
            res = []
        if res:
            self.stdout.write(f"Product: reuse {res[0].id} (metadata mrp_tier=premium)")
            return res[0].id
        self.stdout.write(f"Product: MISSING — will create '{PRODUCT_NAME}'")
        if not commit:
            return None
        prod = stripe.Product.create(name=PRODUCT_NAME, description=PRODUCT_DESC,
                                     metadata={'mrp_tier': 'premium'})
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
        plan = SubscriptionPlan.objects.filter(tier='premium', billing_period=billing).first()
        if not plan:
            self.stdout.write(f"  premium/{billing}: row MISSING — will create (active={active})")
            if commit and active:
                SubscriptionPlan.objects.create(
                    tier='premium', billing_period=billing,
                    name='Premium (Yearly)' if billing == 'yearly' else 'Premium',
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
        self.stdout.write(f"  premium/{billing}: plan #{plan.id} changes={changes or 'none'}")
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
