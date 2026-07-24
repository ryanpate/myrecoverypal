# Stripe Integration Setup Guide for MyRecoveryPal

**Phase 1 Implementation Complete!**
**Date:** 2025-11-14

This guide will help you complete the Stripe integration for subscription payments on MyRecoveryPal.

---

## Table of Contents

1. [What Was Implemented](#what-was-implemented)
2. [Stripe Account Setup](#stripe-account-setup)
3. [Creating Products & Prices](#creating-products--prices)
4. [Environment Variables](#environment-variables)
5. [Database Migration](#database-migration)
6. [Testing the Integration](#testing-the-integration)
7. [Webhook Setup](#webhook-setup)
8. [Going Live](#going-live)

---

## What Was Implemented

### ✅ Models Created
- `Subscription` - User subscription tracking
- `Transaction` - Payment history
- `PaymentMethod` - Stored payment methods
- `Invoice` - Invoice records
- `SubscriptionPlan` - Available plans

### ✅ Views & Features
- **Pricing Page** - Beautiful pricing table with plan comparison
- **Stripe Checkout** - Secure payment processing
- **Subscription Management** - Cancel, reactivate, view billing history
- **Customer Portal** - Stripe-hosted payment method management
- **Webhook Handler** - Automated subscription updates

### ✅ Security & UX
- Feature gating decorators (`@premium_required`, `@pro_required`)
- Automatic free subscription creation for new users
- Rate limiting already configured
- Sentry error monitoring ready

---

## Stripe Account Setup

### Step 1: Create Stripe Account

1. Go to https://dashboard.stripe.com/register
2. Sign up with your email
3. Complete business verification

### Step 2: Get Your API Keys

1. In Stripe Dashboard, go to **Developers** → **API keys**
2. You'll see two keys:
   - **Publishable key** (starts with `pk_test_` for test mode)
   - **Secret key** (starts with `sk_test_` for test mode)

**⚠️ IMPORTANT:** Never share your secret key or commit it to Git!

---

## Creating Products & Prices

You need to create products in Stripe Dashboard for each subscription tier.

### Option 1: Manual Setup (Recommended for Learning)

#### Create Premium Monthly

1. Go to **Products** → **Add Product**
2. Fill in:
   - **Name:** MyRecoveryPal Premium Monthly
   - **Description:** Full access to premium features
   - **Pricing:**
     - **Price:** $9.99
     - **Billing period:** Monthly
     - **Recurring**
   - Click **Save**
3. **Copy the Price ID** (starts with `price_xxx`)

#### Create Premium Yearly

1. Same product, click **Add another price**
2. Fill in:
   - **Price:** $99.00
   - **Billing period:** Yearly
   - **Recurring**
3. **Copy the Price ID**

#### Create Pro Monthly

1. Create new product: **MyRecoveryPal Professional Monthly**
2. **Price:** $19.99, Monthly, Recurring
3. **Copy the Price ID**

#### Create Pro Yearly

1. Same product, add another price
2. **Price:** $199.00, Yearly, Recurring
3. **Copy the Price ID**

### Option 2: Quick Setup with Stripe CLI (Advanced)

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login

# Create Premium Monthly
stripe products create \
  --name="MyRecoveryPal Premium Monthly" \
  --description="Full access to premium features"

stripe prices create \
  --product=prod_xxx \
  --unit-amount=999 \
  --currency=usd \
  --recurring[interval]=month

# Repeat for other plans
```

---

## Environment Variables

### Railway Production Setup

1. Go to Railway dashboard → Your project
2. Click **Variables** tab
3. Add these variables:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### Local Development Setup

1. Copy `.env.example` to `.env`
2. Add your Stripe keys:

```bash
# Stripe Payment Processing
STRIPE_SECRET_KEY=sk_test_51xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_51xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx  # You'll get this after webhook setup
```

---

## Database Migration

Now that the models are created, you need to create and run migrations.

### Step 1: Create Migrations

```bash
# Navigate to your project directory
cd /home/user/myrecoverypal

# Create migrations for payment models
python manage.py makemigrations accounts

# You should see output like:
# Migrations for 'accounts':
#   accounts/migrations/0XXX_subscription_payment_models.py
#     - Create model Subscription
#     - Create model Transaction
#     - Create model PaymentMethod
#     - Create model Invoice
#     - Create model SubscriptionPlan
```

### Step 2: Apply Migrations

```bash
# Apply migrations to database
python manage.py migrate

# You should see:
# Running migrations:
#   Applying accounts.0XXX_subscription_payment_models... OK
```

### Step 3: Create Subscription Plans in Database

Create a Django management command or use the Django shell:

```bash
python manage.py shell
```

Then run this Python code:

```python
from apps.accounts.payment_models import SubscriptionPlan

# Premium Monthly
SubscriptionPlan.objects.create(
    name="Premium Monthly",
    tier="premium",
    billing_period="monthly",
    price=9.99,
    currency="USD",
    stripe_price_id="price_xxxxx",  # Replace with your Stripe Price ID
    description="Full access to all premium features",
    features=[
        "Unlimited groups",
        "Unlimited messaging",
        "Advanced journaling",
        "Private groups",
        "Ad-free experience",
        "Custom themes",
        "Priority support"
    ],
    is_active=True,
    sort_order=1
)

# Premium Yearly
SubscriptionPlan.objects.create(
    name="Premium Yearly",
    tier="premium",
    billing_period="yearly",
    price=99.00,
    currency="USD",
    stripe_price_id="price_xxxxx",  # Replace with your Stripe Price ID
    description="Full access to all premium features (Save $20/year!)",
    features=[
        "Unlimited groups",
        "Unlimited messaging",
        "Advanced journaling",
        "Private groups",
        "Ad-free experience",
        "Custom themes",
        "Priority support"
    ],
    is_active=True,
    sort_order=2
)

# Pro Monthly
SubscriptionPlan.objects.create(
    name="Professional Monthly",
    tier="pro",
    billing_period="monthly",
    price=19.99,
    currency="USD",
    stripe_price_id="price_xxxxx",  # Replace with your Stripe Price ID
    description="For sponsors, counselors, and recovery professionals",
    features=[
        "All Premium features",
        "Sponsor up to 10 people",
        "Create unlimited challenges",
        "Professional badge",
        "Group analytics",
        "Custom branding",
        "Early access to new features"
    ],
    is_active=True,
    sort_order=3
)

# Pro Yearly
SubscriptionPlan.objects.create(
    name="Professional Yearly",
    tier="pro",
    billing_period="yearly",
    price=199.00,
    currency="USD",
    stripe_price_id="price_xxxxx",  # Replace with your Stripe Price ID
    description="For sponsors, counselors, and recovery professionals (Save $40/year!)",
    features=[
        "All Premium features",
        "Sponsor up to 10 people",
        "Create unlimited challenges",
        "Professional badge",
        "Group analytics",
        "Custom branding",
        "Early access to new features"
    ],
    is_active=True,
    sort_order=4
)

# Exit shell
exit()
```

---

## Testing the Integration

### Test Mode (Always Start Here!)

Stripe provides test mode so you can test without real money.

#### Test Card Numbers

Use these test cards for different scenarios:

| Card Number | Scenario |
|-------------|----------|
| `4242 4242 4242 4242` | Successful payment |
| `4000 0000 0000 0002` | Card declined |
| `4000 0000 0000 9995` | Insufficient funds |

**Any future expiry date and any 3-digit CVC works.**

### Testing Steps

1. **Visit Pricing Page**
   ```
   http://localhost:8000/accounts/pricing/
   ```

2. **Click "Upgrade Now"** on Premium plan

3. **Complete Stripe Checkout** using test card: `4242 4242 4242 4242`

4. **Verify Success Page** appears

5. **Check Database**
   ```bash
   python manage.py shell
   ```
   ```python
   from apps.accounts.payment_models import Subscription
   sub = Subscription.objects.get(user__username='your_username')
   print(f"Tier: {sub.tier}")  # Should be 'premium'
   print(f"Status: {sub.status}")  # Should be 'active'
   ```

6. **Test Subscription Management**
   ```
   http://localhost:8000/accounts/subscription/
   ```

7. **Test Cancellation** - Should schedule cancellation at period end

---

## Webhook Setup

Webhooks keep your database in sync with Stripe events (renewals, failures, cancellations).

### Step 1: Install Stripe CLI (for local testing)

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux
# Download from: https://github.com/stripe/stripe-cli/releases

# Windows
# Download from: https://github.com/stripe/stripe-cli/releases

# Verify installation
stripe --version
```

### Step 2: Forward Webhooks to Local Dev

```bash
# Login to Stripe CLI
stripe login

# Forward webhooks to your local server
stripe listen --forward-to localhost:8000/accounts/webhook/stripe/

# This will give you a webhook signing secret like:
# whsec_xxxxxxxxxxxxx
```

**Copy this secret** and add to your `.env`:
```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### Step 3: Test Webhook Events

In another terminal:

```bash
# Trigger a test payment event
stripe trigger payment_intent.succeeded

# Check your Django logs to see the webhook received
```

### Step 4: Production Webhook Setup

1. Go to Stripe Dashboard → **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Enter endpoint URL:
   ```
   https://www.myrecoverypal.com/accounts/webhook/stripe/
   ```
4. Select events to listen to:
   - `checkout.session.completed`
   - `invoice.paid`
   - `invoice.payment_failed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `customer.subscription.trial_will_end`

5. Click **Add endpoint**
6. **Copy the Signing secret** (starts with `whsec_`)
7. Add to Railway environment variables:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```

---

## Going Live

### Pre-Launch Checklist

- [ ] Test mode working perfectly
- [ ] Webhooks tested and working
- [ ] All environment variables set in Railway
- [ ] Subscription plans created in database
- [ ] Test user able to upgrade/downgrade
- [ ] Cancellation flow working
- [ ] Email receipts working
- [ ] Sentry monitoring errors

### Switch to Live Mode

1. In Stripe Dashboard, toggle from **Test mode** to **Live mode** (top right)

2. Get your **Live API keys**:
   - Go to **Developers** → **API keys**
   - Copy **Live** publishable and secret keys

3. Update Railway environment variables:
   ```bash
   STRIPE_SECRET_KEY=sk_live_xxxxx
   STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
   ```

4. Set up **Live webhooks**:
   - Follow same steps as test webhooks
   - Use live endpoint URL
   - Get live webhook secret

5. Update Railway:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_live_xxxxx
   ```

6. **Deploy to production**

### First Real Customer Test

1. Create a test account on production
2. Use a real card (your own)
3. Subscribe to $1 test plan (if you create one)
4. Verify everything works
5. Cancel immediately
6. Enable real plans

---

## Common Issues & Solutions

### Issue: "No Stripe publishable key found"

**Solution:** Check that `STRIPE_PUBLISHABLE_KEY` is set in environment variables and deployed.

### Issue: "Invalid API key"

**Solution:** Make sure you're using the correct key for test/live mode. Test keys start with `pk_test_`, live keys with `pk_live_`.

### Issue: Webhook signature verification failed

**Solution:**
1. Check that `STRIPE_WEBHOOK_SECRET` matches the webhook endpoint secret
2. Make sure you're using the correct secret for test/live mode
3. Restart your Django server after adding the secret

### Issue: User subscribed but database not updated

**Solution:** Check webhook logs in Sentry. The webhook might not be configured or there's an error in the webhook handler.

### Issue: "No such price" error

**Solution:** Double-check that the `stripe_price_id` in your SubscriptionPlan database matches the actual Price ID in Stripe Dashboard.

---

## Security Best Practices

1. **Never commit API keys to Git**
   - Use environment variables
   - Add `.env` to `.gitignore`

2. **Use webhook secrets**
   - Always verify webhook signatures
   - Prevents spoofed webhooks

3. **Test mode first**
   - Never test in live mode
   - Use test cards only

4. **Monitor with Sentry**
   - Catch payment errors immediately
   - Set up alerts for failed webhooks

5. **PCI Compliance**
   - Never store card numbers
   - Use Stripe Checkout (PCI compliant)
   - Use Customer Portal for payment updates

---

## Next Steps

After completing Stripe integration:

1. **Phase 2: Premium Features**
   - Implement feature gating
   - Build premium-only features
   - Add upgrade prompts

2. **Phase 3: Marketing**
   - Add pricing link to navigation
   - Create upgrade CTAs in app
   - Email campaigns for free users

3. **Phase 4: Analytics**
   - Track conversion rates
   - A/B test pricing
   - Monitor churn

---

## Support Resources

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Testing:** https://stripe.com/docs/testing
- **Stripe Webhooks:** https://stripe.com/docs/webhooks
- **Stripe CLI:** https://stripe.com/docs/stripe-cli

---

## Quick Reference

### Important Files Created

```
apps/accounts/
├── payment_models.py          # Subscription, Transaction models
├── payment_views.py           # Checkout, webhooks, management
├── decorators.py              # @premium_required, @pro_required
├── signals.py                 # Auto-create subscriptions
├── urls.py                    # Payment routes
└── templates/accounts/
    ├── pricing.html           # Pricing page
    ├── payment_success.html   # Success page
    ├── payment_canceled.html  # Canceled page
    └── subscription_management.html  # Manage subscription
```

### Key URLs

```
/accounts/pricing/              # Pricing page
/accounts/subscription/         # Manage subscription
/accounts/subscription/cancel/  # Cancel subscription
/accounts/webhook/stripe/       # Stripe webhook endpoint
```

### Test Cards

```
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
Insufficient: 4000 0000 0000 9995
```

---

**Phase 1 Complete! 🎉**

You now have a fully functional Stripe subscription system. Follow this guide to get it live, then move on to Phase 2 (Premium Features) and Phase 3 (Marketing).

Questions? Check Sentry logs, Stripe Dashboard logs, or review the code comments.

Good luck with your launch! 🚀
